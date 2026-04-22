import pandas as pd
from pathlib import Path
import cloudscraper
import requests
import time
from rapidfuzz import process, fuzz

def search_egs_catalog(scraper: cloudscraper.CloudScraper, keywords: str) -> list[dict]:
    """Search the EGS catalog using the GraphQL endpoint."""
    url = "https://store.epicgames.com/graphql"
    headers = {"Content-Type": "application/json"}

    # We use a relatively high count (10) to make sure we get good fuzzy match candidates
    payload = {
        "query": """query searchStoreQuery($keywords: String!) {
            Catalog {
                searchStore(keywords: $keywords, category: "games/edition/base|bundles/games|games/edition/pack", count: 10) {
                    elements {
                        title
                        id
                        namespace
                        productSlug
                        customAttributes { key value }
                    }
                }
            }
        }""",
        "variables": {"keywords": keywords}
    }

    try:
        response = scraper.post(url, headers=headers, json=payload, timeout=10)
        response.raise_for_status()
        data = response.json()
        elements = data.get("data", {}).get("Catalog", {}).get("searchStore", {}).get("elements", [])
        return elements
    except Exception as e:
        print(f"  Error searching EGS for '{keywords}': {e}")
        return []

def get_product_details(slug: str) -> dict:
    """Fetch product details from the static content API using the slug."""
    url = f"https://store-content.ak.epicgames.com/api/en-US/content/products/{slug}"
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        print(f"  Error fetching product details for slug '{slug}': {e}")
        return {}

def process_game(title: str, scraper: cloudscraper.CloudScraper) -> dict:
    """Process a single game title to find its EGS info."""
    print(f"\nProcessing: {title}")
    result = {
        "egs_search_title": None,
        "egs_slug": None,
        "egs_match_score": None,
        "egs_product_name": None,
        "egs_developer": None,
        "egs_publisher": None
    }

    elements = search_egs_catalog(scraper, title)

    if not elements:
        print(f"  No search results found for {title}")
        return result

    # Extract titles for fuzzy matching
    epic_titles = {el['title']: el for el in elements}

    # Use rapidfuzz to find the best match
    match = process.extractOne(title, list(epic_titles.keys()), scorer=fuzz.token_set_ratio)

    if match:
        best_title, score, _ = match
        result["egs_search_title"] = best_title
        result["egs_match_score"] = score

        print(f"  Best match: '{best_title}' (Score: {score:.1f}%)")

        if score >= 85:
            matched_element = epic_titles[best_title]

            # Extract slug
            slug = matched_element.get('productSlug')

            # Sometimes productSlug is None but there's a custom attribute for it
            if not slug:
                for attr in matched_element.get('customAttributes', []):
                    if attr.get('key') == 'com.epicgames.app.productSlug':
                        slug = attr.get('value')
                        break

            if slug:
                # Sometimes slug has a suffix like '/home', try stripping it if needed, or maybe it works directly for static endpoint?
                # Actually, /home doesn't work for the store-content API. We should use the base slug.
                clean_slug = slug.split('/')[0] if '/' in slug else slug

                result["egs_slug"] = clean_slug
                print(f"  Found slug: {slug} (cleaned to {clean_slug}). Fetching product page...")

                # Fetch product page
                product_data = get_product_details(clean_slug)
                if product_data:
                    result["egs_product_name"] = product_data.get("productName")

                    # Extract developer/publisher from customAttributes or pages if available
                    # The static endpoint sometimes has different structures, but we try standard fields
                    result["egs_developer"] = product_data.get("developerName") or product_data.get("developer")
                    result["egs_publisher"] = product_data.get("publisherName") or product_data.get("publisher")

                    # Also try to extract from customAttributes of the search result
                    for attr in matched_element.get('customAttributes', []):
                        if attr.get('key') == 'developerName' and not result["egs_developer"]:
                            result["egs_developer"] = attr.get('value')
                        if attr.get('key') == 'publisherName' and not result["egs_publisher"]:
                            result["egs_publisher"] = attr.get('value')

                    print(f"  Successfully fetched details: Product Name='{result['egs_product_name']}', Developer='{result['egs_developer']}'")
            else:
                print("  No slug found in match data.")
        else:
            print("  Score too low, skipping detail fetch.")

    time.sleep(1) # Be nice to the APIs
    return result

def main():
    data_dir = Path("data")
    input_file = data_dir / "2026-04-21-wiki.csv"

    if not input_file.exists():
        print(f"File not found: {input_file}")
        return

    df = pd.read_csv(input_file)
    print(f"Loaded {len(df)} rows from {input_file}")

    # Test on a small subset
    df_sample = df.head(5).copy()

    scraper = cloudscraper.create_scraper()

    results = []
    for title in df_sample['Title']:
        info = process_game(title, scraper)
        results.append(info)

    # Combine results
    results_df = pd.DataFrame(results)
    final_df = pd.concat([df_sample.reset_index(drop=True), results_df], axis=1)

    print("\nFinal Results Summary:")
    print(final_df[['Title', 'egs_search_title', 'egs_slug', 'egs_developer']].to_string())

    # Save to outputs directory
    out_dir = Path("outputs")
    out_dir.mkdir(exist_ok=True)
    out_path = out_dir / "direct_egs_scrape_results.csv"
    final_df.to_csv(out_path, index=False)
    print(f"\nSaved results to {out_path}")

if __name__ == "__main__":
    main()

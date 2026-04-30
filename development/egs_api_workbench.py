import marimo

__generated_with = "0.23.2"
app = marimo.App(width="medium")


@app.cell
def _():
    """Marimo cell that imports the helper module and notebook dependencies."""

    import sys
    from pathlib import Path

    import marimo as mo
    import pandas as pd

    notebook_dir = Path(__file__).resolve().parent
    if str(notebook_dir) not in sys.path:
        sys.path.append(str(notebook_dir))

    from egs_api_helpers import (
        DATA_DIR,
        OUTPUT_DIR,
        batch_search_scan,
        clean_slug,
        create_clients,
        direct_graphql,
        extract_product_about,
        fetch_product,
        fetch_tag_lookup,
        free_games_frame,
        get_latest_file,
        json_preview,
        offer_catalog_frame,
        pick_best_search_match,
        product_requirements_frame,
        search_candidates_frame,
    )

    return (
        DATA_DIR,
        OUTPUT_DIR,
        batch_search_scan,
        clean_slug,
        create_clients,
        direct_graphql,
        extract_product_about,
        fetch_product,
        fetch_tag_lookup,
        free_games_frame,
        get_latest_file,
        json_preview,
        mo,
        offer_catalog_frame,
        pd,
        pick_best_search_match,
        product_requirements_frame,
        search_candidates_frame,
    )


@app.cell
def _(mo):
    """Marimo cell that introduces the Epic API QA workbench."""

    mo.md(
        """
        # Epic API Workbench

        This notebook is meant for manual title QA and quick API spelunking.

        The most reliable flow right now is:
        1. Search by title and inspect the scored candidates.
        2. Grab or override the slug.
        3. Pull the product page and offer records.
        4. Decode tag IDs and inspect any raw payloads you need.

        A nice side benefit: the direct free-games endpoint and the wrapper are both responding in the current environment, so you can use either depending on what you want to inspect.
        """
    )
    return


@app.cell
def _(create_clients, fetch_tag_lookup, mo):
    """Marimo cell that initializes the Epic API clients and tag lookup."""

    api, scraper = create_clients()
    tag_lookup = fetch_tag_lookup(api)

    mo.md(
        f"""
        **Session ready**

        - tag lookup size: `{len(tag_lookup):,}`
        - default locale/country: `en-US / US`
        - if you want another market later, just re-run `create_clients(locale=..., country=...)`
        """
    )
    return api, scraper, tag_lookup


@app.cell
def _(DATA_DIR, OUTPUT_DIR, get_latest_file, pd):
    """Marimo cell that loads a few local title sources for QA."""

    merged_path = DATA_DIR / "cleaned_merged_data.csv"
    abnormal_path = OUTPUT_DIR / "abnormal_gameset.csv"
    latest_wiki_path = get_latest_file(DATA_DIR, "20*-wiki.csv")

    merged_df = pd.read_csv(merged_path) if merged_path.exists() else pd.DataFrame()
    abnormal_df = (
        pd.read_csv(abnormal_path) if abnormal_path.exists() else pd.DataFrame()
    )
    wiki_df = pd.read_csv(latest_wiki_path) if latest_wiki_path else pd.DataFrame()
    return abnormal_df, merged_df


@app.cell
def _(abnormal_df, merged_df, pd):
    """Marimo cell that builds a small seed list of interesting titles."""

    manual_titles = [
        "Celeste",
        "Cat Quest II",
        "Cat Quest 2",
        "Sid Meier's Civilization VI",
        ">observer_",
        "[REDACTED]",
        "DEATH STRANDING - DIRECTORS CUT",
        "KID A MNESIA EXHIBITION",
        "LISA: Definitive Edition",
        "Fallout® Classic Collection",
    ]

    abnormal_titles = []
    if not abnormal_df.empty:
        for column in ["NAME", "NAME / NOTES", "Title"]:
            if column not in abnormal_df.columns:
                continue
            abnormal_titles.extend(
                abnormal_df[column]
                .dropna()
                .astype("string")
                .str.strip()
                .loc[lambda value: value.ne("")]
                .tolist()
            )

    merged_titles = []
    if not merged_df.empty and "Title" in merged_df.columns:
        merged_titles = (
            merged_df["Title"]
            .dropna()
            .astype("string")
            .str.strip()
            .loc[lambda value: value.ne("")]
            .head(25)
            .tolist()
        )

    seed_titles = list(
        dict.fromkeys(
            manual_titles
            + abnormal_titles[:15]
            + merged_titles[:10]
        )
    )

    pd.DataFrame({"seed_title": seed_titles})
    return (seed_titles,)


@app.cell
def _():
    """Marimo cell holding the main title query and optional slug override."""

    title_query = "Celeste"
    candidate_count = 8

    # If the best search hit is wrong, paste a slug here and re-run the next cells.
    slug_override = ""
    return candidate_count, slug_override, title_query


@app.cell
def _(api, candidate_count, search_candidates_frame, tag_lookup, title_query):
    """Marimo cell that shows scored search candidates for the current title."""

    candidate_df = search_candidates_frame(
        api,
        title=title_query,
        count=candidate_count,
        tag_lookup=tag_lookup,
    )
    candidate_df
    return


@app.cell
def _(api, candidate_count, pick_best_search_match, title_query):
    """Marimo cell that resolves the current best match from search."""

    best_match = pick_best_search_match(
        api,
        title=title_query,
        count=candidate_count,
        min_score=70.0,
    )
    best_match
    return (best_match,)


@app.cell
def _(api, best_match, clean_slug, fetch_product, pd, slug_override):
    """Marimo cell that fetches a product page using the best hit or manual slug."""

    resolved_slug = slug_override.strip() or clean_slug(
        (best_match or {}).get("_clean_slug") or (best_match or {}).get("productSlug"),
        (best_match or {}).get("customAttributes") or [],
    )

    product_payload = fetch_product(api, resolved_slug)
    pd.Series({"resolved_slug": resolved_slug, "has_product_payload": bool(product_payload)})
    return product_payload, resolved_slug


@app.cell
def _(extract_product_about, pd, product_payload):
    """Marimo cell that extracts the most useful product-level fields."""

    about = extract_product_about(product_payload)
    pd.Series(about)
    return


@app.cell
def _(api, offer_catalog_frame, product_payload, tag_lookup):
    """Marimo cell that shows offer-level fields like price, categories, and tags."""

    offers_df = offer_catalog_frame(
        api,
        product_payload,
        tag_lookup=tag_lookup,
    )
    offers_df
    return


@app.cell
def _(product_payload, product_requirements_frame):
    """Marimo cell that flattens system requirements when available."""

    requirements_df = product_requirements_frame(product_payload)
    requirements_df
    return


@app.cell
def _(best_match, json_preview, product_payload, resolved_slug):
    """Marimo cell that gives you a compact raw JSON preview for debugging."""

    debug_preview = {
        "resolved_slug": resolved_slug,
        "best_match": best_match,
        "product_keys": sorted(product_payload.keys()) if product_payload else [],
        "product_preview": product_payload,
    }
    print(json_preview(debug_preview, max_chars=5000))
    return


@app.cell
def _(free_games_frame, scraper):
    """Marimo cell that previews the current direct free-games endpoint."""

    free_games_df = free_games_frame(scraper)
    free_games_df
    return


@app.cell
def _(api, batch_search_scan, seed_titles):
    """Marimo cell that batch-checks a handful of edge-case titles."""

    batch_df = batch_search_scan(
        api,
        titles=seed_titles[:10],
        count=8,
        min_score=70.0,
        sleep_seconds=0.0,
    )
    batch_df
    return


@app.cell
def _(direct_graphql, json_preview, scraper, title_query):
    """Marimo cell with an editable direct GraphQL stub for deeper exploration."""

    query = """
    query searchStoreDebug(
      $keywords: String!
      $country: String!
      $locale: String
      $count: Int!
    ) {
      Catalog {
        searchStore(
          keywords: $keywords
          count: $count
          country: $country
          locale: $locale
          category: "games/edition/base|bundles/games|games/edition/pack"
        ) {
          elements {
            title
            id
            namespace
            productSlug
            urlSlug
            seller {
              name
            }
            customAttributes {
              key
              value
            }
          }
        }
      }
    }
    """

    variables = {
        "keywords": title_query,
        "count": 5,
        "country": "US",
        "locale": "en-US",
    }

    graphql_preview = direct_graphql(scraper, query, variables)
    print(json_preview(graphql_preview, max_chars=3500))
    return


@app.cell
def _(mo):
    """Marimo cell that leaves a few practical hints for manual QA work."""

    mo.md(
        """
        ## Hints

        - Start with the candidate table, not the fuzzy best hit. For weird packs and renamed titles, the right match is often in rank 2-4.
        - If a candidate has a good namespace but a messy `productSlug`, use the manual `slug_override` cell and keep moving.
        - `offer_catalog_frame(...)` is often where the cleanest price, category, and tag info shows up.
        - `extract_product_about(...)` is the quickest way to see whether the product page has the developer, publisher, and longer description you care about.
        - The final GraphQL cell is there on purpose: if you want some other field, edit that query first before you write a brand-new scraper.
        """
    )
    return


if __name__ == "__main__":
    app.run()

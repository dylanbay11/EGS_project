import marimo

__generated_with = "0.23.2"
app = marimo.App(width="medium")


@app.cell
def _():
    # For interactive exploration of the Epic Games API, edge cases, etc. to develop stuff to later become a full scraper to augment the game data already collected and match up game titles to their catalog entries

    from __future__ import annotations

    import json
    from pathlib import Path  
    import sys
    import time
    from typing import Any

    import cloudscraper
    from epicstore_api import EpicGamesStoreAPI, OfferData
    import marimo as mo
    import pandas as pd
    from rapidfuzz import fuzz

    notebook_dir = Path(__file__).resolve().parent
    if str(notebook_dir) not in sys.path:
        sys.path.append(str(notebook_dir))

    PROJECT_ROOT = Path(__file__).resolve().parent.parent
    DATA_DIR = PROJECT_ROOT / "data"
    OUTPUT_DIR = PROJECT_ROOT / "outputs"
    GRAPHQL_URL = "https://store.epicgames.com/graphql"
    FREE_GAMES_URL = (
        "https://store-site-backend-static.ak.epicgames.com/freeGamesPromotions"
    )
    return (
        Any,
        DATA_DIR,
        EpicGamesStoreAPI,
        FREE_GAMES_URL,
        GRAPHQL_URL,
        OUTPUT_DIR,
        OfferData,
        Path,
        cloudscraper,
        fuzz,
        json,
        mo,
        pd,
        time,
    )


@app.cell
def _(
    Any,
    EpicGamesStoreAPI,
    FREE_GAMES_URL,
    GRAPHQL_URL,
    OfferData,
    Path,
    cloudscraper,
    fuzz,
    json,
    pd,
    time,
):
    # ABSTRACTED helper functions - do not need to deeply understand

    def create_clients(
        locale: str = "en-US",
        country: str = "US",
    ) -> tuple[EpicGamesStoreAPI, cloudscraper.CloudScraper]:
        """Create a shared scraper session and API wrapper client."""

        scraper = cloudscraper.create_scraper()
        api = EpicGamesStoreAPI(locale=locale, country=country, session=scraper)
        return api, scraper

    def get_latest_file(directory: Path, pattern: str) -> Path | None:
        """Return the newest file matching a glob pattern."""

        matches = sorted(directory.glob(pattern), reverse=True)
        if not matches:
            return None
        return matches[0]

    def json_preview(payload: Any, max_chars: int = 4000) -> str:
        """Return a truncated pretty-printed JSON preview for notebook display."""

        text = json.dumps(payload, indent=2, default=str, ensure_ascii=False)
        if len(text) <= max_chars:
            return text
        return text[:max_chars] + "\n... <truncated>"

    def search_store(
        api: EpicGamesStoreAPI,
        title: str,
        count: int = 10,
        *,
        with_price: bool = True,
    ) -> dict[str, Any]:
        """Search the Epic Games Store catalog for a title."""

        return api.fetch_store_games(
            keywords=title,
            count=count,
            with_price=with_price,
        )

    def direct_graphql(
        scraper: cloudscraper.CloudScraper,
        query: str,
        variables: dict[str, Any],
    ) -> dict[str, Any]:
        """Run a direct GraphQL query against the Epic store endpoint."""

        response = scraper.post(
            GRAPHQL_URL,
            json={"query": query, "variables": variables},
            headers={"content-type": "application/json;charset=UTF-8"},
            timeout=30,
        )
        response.raise_for_status()
        return response.json()

    def decode_tag_ids(
        tag_ids: list[str] | None,
        tag_lookup: dict[str, str] | None,
    ) -> list[str]:
        """Turn Epic tag IDs into readable names when a lookup is available."""

        if not tag_ids:
            return []
        if not tag_lookup:
            return tag_ids
        return [tag_lookup.get(tag_id, tag_id) for tag_id in tag_ids]

    def fetch_product(api: EpicGamesStoreAPI, slug: str | None) -> dict[str, Any]:
        """Fetch a product payload from the direct content endpoint via the wrapper."""

        clean = clean_slug(slug)
        if not clean:
            return {}
        return api.get_product(clean)

    def looks_like_page_slug(value: str | None) -> bool:
        """Return True when a slug looks like a real page slug instead of an opaque ID."""

        if not value:
            return False
        if len(value) >= 24 and all(character in "0123456789abcdef" for character in value.lower()):
            return False
        return True

    def fetch_offer_catalog_records(
        api: EpicGamesStoreAPI,
        product: dict[str, Any],
    ) -> list[dict[str, Any]]:
        """Fetch offer-level catalog records tied to a product page."""

        offers = offer_records_from_product(product)
        if not offers:
            return []

        payload = api.get_offers_data(*offers)
        records: list[dict[str, Any]] = []
        for chunk in payload:
            record = chunk.get("data", {}).get("Catalog", {}).get("catalogOffer", {})
            if record:
                records.append(record)
        return records


    # SEMI-ABSTRACTED helper functions: flatten and extract json payloads or other parsing

    def normalize_title(title: str | None) -> str:
        """Normalize a title for rough matching and spot-check comparisons."""

        if not title:
            return ""

        cleaned = (
            pd.Series([title], dtype="string")
            .str.lower()
            .str.replace(r"[^a-z0-9]+", " ", regex=True)
            .str.replace(r"\s+", " ", regex=True)
            .str.strip()
            .iloc[0]
        )
        return str(cleaned)

    def search_elements(search_payload: dict[str, Any]) -> list[dict[str, Any]]:
        """Extract store search elements from a search payload."""

        return (
            search_payload.get("data", {})
            .get("Catalog", {})
            .get("searchStore", {})
            .get("elements", [])
        )

    def first_product_page(product: dict[str, Any]) -> dict[str, Any]:
        """Return the first product page block from a product payload."""

        pages = product.get("pages") or []
        if not pages:
            return {}
        return pages[0]

    def product_requirements_frame(product: dict[str, Any]) -> pd.DataFrame:
        """Flatten product system requirements into a table."""

        page = first_product_page(product)
        requirements = (page.get("data") or {}).get("requirements") or {}
        systems = requirements.get("systems") or []
        rows: list[dict[str, Any]] = []

        for system in systems:
            for detail in system.get("details") or []:
                rows.append(
                    {
                        "system_type": system.get("systemType"),
                        "requirement": detail.get("title"),
                        "minimum": detail.get("minimum"),
                        "recommended": detail.get("recommended"),
                    }
                )

        return pd.DataFrame(rows)

    def fetch_tag_lookup(api: EpicGamesStoreAPI) -> dict[str, str]:
        """Build a tag ID to tag name lookup from the wrapper's tag query."""

        payload = api.fetch_catalog_tags()
        elements = (
            payload.get("data", {})
            .get("Catalog", {})
            .get("tags", {})
            .get("elements", [])
        )
        return {
            str(element["id"]): element["name"]
            for element in elements
            if element.get("id") and element.get("name")
        }

    def extract_product_about(product: dict[str, Any]) -> dict[str, Any]:
        """Extract the most immediately useful product fields for QA."""

        page = first_product_page(product)
        about = (page.get("data") or {}).get("about") or {}

        return {
            "product_name": product.get("productName") or page.get("productName"),
            "namespace": product.get("namespace") or page.get("namespace"),
            "page_slug": page.get("_slug"),
            "page_type": page.get("type"),
            "offer_id": (page.get("offer") or {}).get("id"),
            "item_id": (page.get("item") or {}).get("catalogId"),
            "developer": about.get("developerAttribution"),
            "publisher": about.get("publisherAttribution"),
            "short_description": about.get("shortDescription"),
            "description": about.get("description"),
            "data_sections": sorted((page.get("data") or {}).keys()),
        }

    def free_games_frame(
        scraper: cloudscraper.CloudScraper,
        locale: str = "en-US",
        country: str = "US",
        allow_countries: str | None = None,
    ) -> pd.DataFrame:
        """Flatten the current free-games payload into a compact DataFrame."""

        payload = fetch_free_games_payload(
            scraper=scraper,
            locale=locale,
            country=country,
            allow_countries=allow_countries,
        )
        elements = (
            payload.get("data", {})
            .get("Catalog", {})
            .get("searchStore", {})
            .get("elements", [])
        )
        rows: list[dict[str, Any]] = []

        for element in elements:
            total_price = (element.get("price") or {}).get("totalPrice") or {}
            rows.append(
                {
                    "title": element.get("title"),
                    "product_slug": clean_slug(element.get("productSlug")),
                    "namespace": element.get("namespace"),
                    "effective_date": element.get("effectiveDate"),
                    "original_price": total_price.get("originalPrice"),
                    "discount_price": total_price.get("discountPrice"),
                    "display_price": (total_price.get("fmtPrice") or {}).get(
                        "originalPrice",
                    ),
                    "seller": (element.get("seller") or {}).get("name"),
                }
            )

        return pd.DataFrame(rows)

    def fetch_free_games_payload(
        scraper: cloudscraper.CloudScraper,
        locale: str = "en-US",
        country: str = "US",
        allow_countries: str | None = None,
    ) -> dict[str, Any]:
        """Fetch the current free-games promotions payload directly."""

        allowed = allow_countries or country
        response = scraper.get(
            FREE_GAMES_URL,
            params={
                "locale": locale,
                "country": country,
                "allowCountries": allowed,
            },
            timeout=30,
        )
        response.raise_for_status()
        return response.json()


    # IMPORTANT helper functions to understand

    def clean_slug(
        raw_slug: str | None,
        custom_attributes: list[dict[str, Any]] | None = None,
        url_slug: str | None = None,
    ) -> str | None:
        """Clean a product slug and fall back to custom attributes when needed."""

        slug = raw_slug

        if not slug and custom_attributes:
            for attribute in custom_attributes:
                if attribute.get("key") == "com.epicgames.app.productSlug":
                    slug = attribute.get("value")
                    break

        if not slug and looks_like_page_slug(url_slug):
            slug = url_slug

        if not slug:
            return None

        return slug.split("/")[0]


    def search_candidates_frame(
        api: EpicGamesStoreAPI,
        title: str,
        count: int = 10,
        *,
        tag_lookup: dict[str, str] | None = None,
    ) -> pd.DataFrame:
        """Return a scored DataFrame of candidate store matches for a title."""

        payload = search_store(api, title=title, count=count, with_price=True)
        elements = search_elements(payload)
        normalized_query = normalize_title(title)
        rows: list[dict[str, Any]] = []

        for rank, element in enumerate(elements, start=1):
            candidate_title = str(element.get("title", ""))
            custom_attributes = element.get("customAttributes") or []
            total_price = (element.get("price") or {}).get("totalPrice") or {}
            tag_ids = [
                str(tag["id"])
                for tag in (element.get("tags") or [])
                if isinstance(tag, dict) and tag.get("id")
            ]

            rows.append(
                {
                    "rank": rank,
                    "query_title": title,
                    "candidate_title": candidate_title,
                    "exact_match": candidate_title.casefold() == title.casefold(),
                    "token_set_score": round(fuzz.token_set_ratio(title, candidate_title), 1),
                    "token_sort_score": round(
                        fuzz.token_sort_ratio(title, candidate_title),
                        1,
                    ),
                    "normalized_score": round(
                        fuzz.ratio(normalized_query, normalize_title(candidate_title)),
                        1,
                    ),
                    "seller": (element.get("seller") or {}).get("name"),
                    "raw_product_slug": element.get("productSlug"),
                    "product_slug": clean_slug(
                        element.get("productSlug"),
                        custom_attributes,
                        element.get("urlSlug"),
                    ),
                    "url_slug": element.get("urlSlug"),
                    "namespace": element.get("namespace"),
                    "offer_id": element.get("id"),
                    "original_price": total_price.get("originalPrice"),
                    "discount_price": total_price.get("discountPrice"),
                    "display_price": (total_price.get("fmtPrice") or {}).get(
                        "originalPrice",
                    ),
                    "categories": " | ".join(
                        category["path"]
                        for category in (element.get("categories") or [])
                        if category.get("path")
                    ),
                    "tag_ids": tag_ids,
                    "tags": decode_tag_ids(tag_ids, tag_lookup),
                }
            )

        if not rows:
            return pd.DataFrame()

        return (
            pd.DataFrame(rows)
            .sort_values(
                by=["exact_match", "token_set_score", "normalized_score", "rank"],
                ascending=[False, False, False, True],
            )
            .reset_index(drop=True)
        )


    def pick_best_search_match(
        api: EpicGamesStoreAPI,
        title: str,
        count: int = 10,
        *,
        min_score: float = 75.0,
    ) -> dict[str, Any] | None:
        """Pick the best available search hit for a title and annotate its score."""

        elements = search_elements(search_store(api, title=title, count=count))
        if not elements:
            return None

        best_match: dict[str, Any] | None = None
        best_score = -1.0
        normalized_query = normalize_title(title)

        for element in elements:
            candidate_title = str(element.get("title", ""))
            exact = candidate_title.casefold() == title.casefold()
            score = fuzz.token_set_ratio(title, candidate_title)
            normalized_score = fuzz.ratio(
                normalized_query,
                normalize_title(candidate_title),
            )
            combined_score = max(score, normalized_score)
            if exact:
                combined_score = 100.0

            if combined_score <= best_score:
                continue

            best_score = combined_score
            best_match = dict(element)
            best_match["_match_score"] = round(combined_score, 1)
            best_match["_clean_slug"] = clean_slug(
                element.get("productSlug"),
                element.get("customAttributes") or [],
                element.get("urlSlug"),
            )
            best_match["_meets_threshold"] = best_match["_match_score"] >= min_score

        if not best_match:
            return None
        return best_match


    def offer_records_from_product(product: dict[str, Any]) -> list[OfferData]:
        """Build OfferData records from a product payload for follow-up calls."""

        offers: list[OfferData] = []

        for page in product.get("pages") or []:
            offer = page.get("offer") or {}
            namespace = page.get("namespace") or offer.get("namespace")
            offer_id = offer.get("id")
            if not namespace or not offer_id:
                continue
            offers.append(OfferData(namespace=namespace, offer_id=offer_id))

        return offers


    def offer_catalog_frame(
        api: EpicGamesStoreAPI,
        product: dict[str, Any],
        *,
        tag_lookup: dict[str, str] | None = None,
    ) -> pd.DataFrame:
        """Flatten offer-level catalog data into a QA-friendly DataFrame."""

        records = fetch_offer_catalog_records(api, product)
        rows: list[dict[str, Any]] = []

        for record in records:
            total_price = (record.get("price") or {}).get("totalPrice") or {}
            custom_attributes = record.get("customAttributes") or []
            attribute_lookup = {
                attribute["key"]: attribute["value"]
                for attribute in custom_attributes
                if attribute.get("key")
            }
            tag_ids = [
                str(tag["id"])
                for tag in (record.get("tags") or [])
                if isinstance(tag, dict) and tag.get("id")
            ]

            rows.append(
                {
                    "title": record.get("title"),
                    "namespace": record.get("namespace"),
                    "offer_id": record.get("id"),
                    "product_slug": clean_slug(
                        record.get("productSlug"),
                        custom_attributes,
                        record.get("urlSlug"),
                    ),
                    "developer": attribute_lookup.get("developerName"),
                    "publisher": attribute_lookup.get("publisherName"),
                    "original_price": total_price.get("originalPrice"),
                    "discount_price": total_price.get("discountPrice"),
                    "display_price": (total_price.get("fmtPrice") or {}).get(
                        "originalPrice",
                    ),
                    "categories": " | ".join(
                        category["path"]
                        for category in (record.get("categories") or [])
                        if category.get("path")
                    ),
                    "tag_ids": tag_ids,
                    "tags": decode_tag_ids(tag_ids, tag_lookup),
                }
            )

        return pd.DataFrame(rows)


    def batch_search_scan(
        api: EpicGamesStoreAPI,
        titles: list[str],
        *,
        count: int = 8,
        min_score: float = 75.0,
        sleep_seconds: float = 0.0,
    ) -> pd.DataFrame:
        """Run a lightweight best-match scan across a list of titles."""

        rows: list[dict[str, Any]] = []

        for title in titles:
            best = pick_best_search_match(
                api,
                title=title,
                count=count,
                min_score=min_score,
            )
            if not best:
                rows.append(
                    {
                        "query_title": title,
                        "matched_title": None,
                        "match_score": None,
                        "product_slug": None,
                        "seller": None,
                    }
                )
            else:
                rows.append(
                    {
                        "query_title": title,
                        "matched_title": best.get("title"),
                        "match_score": best.get("_match_score"),
                        "product_slug": best.get("_clean_slug"),
                        "seller": (best.get("seller") or {}).get("name"),
                    }
                )

            if sleep_seconds > 0:
                time.sleep(sleep_seconds)

        return pd.DataFrame(rows)


    return (
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

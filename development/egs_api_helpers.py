"""Helper functions for interactive Epic Games Store API QA work."""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any

import cloudscraper
import pandas as pd
from epicstore_api import EpicGamesStoreAPI, OfferData
from rapidfuzz import fuzz

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_ROOT / "data"
OUTPUT_DIR = PROJECT_ROOT / "outputs"
GRAPHQL_URL = "https://store.epicgames.com/graphql"
FREE_GAMES_URL = (
    "https://store-site-backend-static.ak.epicgames.com/freeGamesPromotions"
)


def looks_like_page_slug(value: str | None) -> bool:
    """Return True when a slug looks like a real page slug instead of an opaque ID."""

    if not value:
        return False
    if len(value) >= 24 and all(character in "0123456789abcdef" for character in value.lower()):
        return False
    return True


def create_clients(
    locale: str = "en-US",
    country: str = "US",
) -> tuple[EpicGamesStoreAPI, cloudscraper.CloudScraper]:
    """Create a shared scraper session and API wrapper client."""

    scraper = cloudscraper.create_scraper()
    api = EpicGamesStoreAPI(locale=locale, country=country, session=scraper)
    return api, scraper


def json_preview(payload: Any, max_chars: int = 4000) -> str:
    """Return a truncated pretty-printed JSON preview for notebook display."""

    text = json.dumps(payload, indent=2, default=str, ensure_ascii=False)
    if len(text) <= max_chars:
        return text
    return text[:max_chars] + "\n... <truncated>"


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


def get_latest_file(directory: Path, pattern: str) -> Path | None:
    """Return the newest file matching a glob pattern."""

    matches = sorted(directory.glob(pattern), reverse=True)
    if not matches:
        return None
    return matches[0]


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


def search_elements(search_payload: dict[str, Any]) -> list[dict[str, Any]]:
    """Extract store search elements from a search payload."""

    return (
        search_payload.get("data", {})
        .get("Catalog", {})
        .get("searchStore", {})
        .get("elements", [])
    )


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


def fetch_product(api: EpicGamesStoreAPI, slug: str | None) -> dict[str, Any]:
    """Fetch a product payload from the direct content endpoint via the wrapper."""

    clean = clean_slug(slug)
    if not clean:
        return {}
    return api.get_product(clean)


def first_product_page(product: dict[str, Any]) -> dict[str, Any]:
    """Return the first product page block from a product payload."""

    pages = product.get("pages") or []
    if not pages:
        return {}
    return pages[0]


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

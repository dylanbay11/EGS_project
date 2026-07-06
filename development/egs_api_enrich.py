"""Enrich the giveaway titles with Epic Games Store catalog data.

This promotes the manual QA logic from ``egs_api_workbench.py`` and
``direct_egs_scraper.py`` into a production enrichment pass. For each unique
giveaway title we search the EGS storefront, pick the best fuzzy match, and pull
store-side fields (price, tags, developer/publisher, dates, description).

The EGS API is a *storefront* API, so we can only see store-reachable data
(catalog price, store tags/categories, seller attribution, EGS dates) - there is
no developer-console / sales data here.

Operational discipline (the one hard constraint): be polite to the endpoints.
Every title is cached to ``outputs/egs_api_cache.json`` keyed by title, so a
second run makes ~zero network calls and an interrupted run resumes cleanly.

Run a small slice first:
    uv run python development/egs_api_enrich.py --limit 10
Then the full pass:
    uv run python development/egs_api_enrich.py
"""

from __future__ import annotations

import argparse
import json
import re
import time
from pathlib import Path
from typing import Any

import cloudscraper
from epicstore_api import EpicGamesStoreAPI, OfferData
from rapidfuzz import fuzz

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_ROOT / "data"
OUTPUT_DIR = PROJECT_ROOT / "outputs"
INPUT_FILE = DATA_DIR / "cleaned_merged_data.csv"
OUTPUT_FILE = DATA_DIR / "egs-enriched.csv"
CACHE_FILE = OUTPUT_DIR / "egs_api_cache.json"

TITLE_COLUMN = "Title"  # current cleaned schema (was Title_gsheets in older runs)
MATCH_THRESHOLD = 80.0  # below this we keep the guess but flag it as low confidence
SEARCH_COUNT = 10
SAVE_EVERY = 10

# Manual match corrections from the July 2026 data-quality review (REVIEW_NEEDED.md
# items A-C, plus a token-subset audit of all "confident" matches). Every entry was
# verified against the live storefront. Three shapes:
#   {"action": "skip", "note": ...}
#       the right product is no longer on EGS; leave the title unmatched instead of
#       letting the fuzzy matcher grab the nearest wrong string
#   {"action": "pick", "keywords": ..., "match_title": ..., ("seller": ...,) "note": ...}
#       re-search with better keywords and pin the exact store listing by title (and
#       seller when several listings share a title); treated as a trusted match
#   {"action": "null_price", "note": ...}
#       the match is right but the store reports $0 for a non-purchasable offer;
#       enrich normally, then blank the price fields
MANUAL_OVERRIDES: dict[str, dict[str, str]] = {
    # -- wrong product matched; the real listing exists --
    "Control": {
        "action": "pick", "keywords": "Control", "match_title": "Control",
        "seller": "505 Games",
        "note": "search rank 1 is an unrelated Overwolf app; pinned the 505 Games listing",
    },
    "Thimbleweed Park": {
        "action": "pick", "keywords": "Thimbleweed Park", "match_title": "Thimbleweed Park",
        "note": "was matched to the free Delores spinoff",
    },
    "Rogue Legacy": {
        "action": "pick", "keywords": "Rogue Legacy", "match_title": "Rogue Legacy",
        "note": "token-subset scoring matched an Assassin's Creed Rogue DLC",
    },
    "Vampire Survivors": {
        "action": "pick", "keywords": "Vampire Survivors", "match_title": "Vampire Survivors",
        "note": "was matched to the Vampire Crawlers spinoff",
    },
    "The Bridge": {
        "action": "pick", "keywords": "The Bridge", "match_title": "The Bridge",
        "note": "was matched to Bridge Constructor: The Walking Dead",
    },
    "MudRunner": {
        "action": "pick", "keywords": "MudRunner", "match_title": "MudRunner",
        "note": "was matched to Expeditions: A MudRunner Game (different game)",
    },
    "Stories Untold": {
        "action": "pick", "keywords": "Stories Untold", "match_title": "Stories Untold",
        "note": "was matched to Lovecraft's Untold Stories",
    },
    "Tiny Tina's Wonderlands": {
        "action": "pick", "keywords": "Tiny Tina's Wonderlands",
        "match_title": "Tiny Tina's Wonderlands",
        "note": "was matched to the Assault on Dragon Keep one-shot",
    },
    "Ghostwire: Tokyo": {
        "action": "pick", "keywords": "Ghostwire Tokyo", "match_title": "Ghostwire: Tokyo",
        "note": "was matched to the DEATHLOOP + Ghostwire bundle",
    },
    "Shenmue III": {
        "action": "pick", "keywords": "Shenmue III", "match_title": "Shenmue III",
        "note": "was matched to the Deluxe Edition; standard listing exists",
    },
    "Hand of Fate 2": {
        "action": "pick", "keywords": "Hand of Fate 2", "match_title": "Hand of Fate 2",
        "note": "was matched to the Game & DLC bundle; base listing exists",
    },
    # -- store shortened/renamed the title, so the search missed it --
    "The Dungeon of Naheulbeuk: The Amulet Of Chaos": {
        "action": "pick", "keywords": "Dungeon of Naheulbeuk",
        "match_title": "The Dungeon of Naheulbeuk",
        "note": "store listing dropped the subtitle",
    },
    "Encased: A Sci-Fi Post-Apocalyptic RPG": {
        "action": "pick", "keywords": "Encased", "match_title": "Encased",
        "note": "store listing dropped the subtitle",
    },
    "Bad North: Jotunn Edition": {
        "action": "pick", "keywords": "Bad North", "match_title": "Bad North",
        "note": "Jotunn Edition is the free-update rename of the same game",
    },
    "Tormentor❌Punisher": {
        "action": "pick", "keywords": "Tormentor Punisher", "match_title": "Tormentor x Punisher",
        "note": "store spells the ❌ as 'x'",
    },
    # -- original edition delisted; a same-content re-release is the current listing --
    "Trine 4: The Nightmare Prince": {
        "action": "pick", "keywords": "Trine 4", "match_title": "Trine 4: Definitive Edition",
        "note": "original delisted; Definitive Edition is the successor re-release",
    },
    "Model Builder": {
        "action": "pick", "keywords": "Model Builder",
        "match_title": "Model Builder: Complete Edition",
        "note": "original delisted; Complete Edition is the successor re-release",
    },
    # -- the real product is gone from EGS; nearest string was a wrong match --
    "Hitman": {
        "action": "skip",
        "note": "HITMAN (2016) is delisted; current World of Assassination SKUs are different products",
    },
    "Train Sim World 2": {
        "action": "skip",
        "note": "TSW2 is delisted; only TSW6 editions and a free dev kit remain",
    },
    "Football Manager 2024": {
        "action": "skip",
        "note": "FM main games are not on EGS; nearest hit is the FM2020 in-game editor DLC",
    },
    "Football Manager 2020": {
        "action": "skip",
        "note": "FM2020 base game is delisted; only its in-game editor DLC remains",
    },
    "Thief": {
        "action": "skip",
        "note": "Thief (2014) is not in EGS search; nearest hit is an Arsene Lupin subtitle",
    },
    # -- correct match, unusable price --
    "Borderlands 2": {
        "action": "null_price",
        "note": "store reports $0 for this non-purchasable offer; price nulled",
    },
    "Borderlands: The Pre-Sequel": {
        "action": "null_price",
        "note": "store reports $0 for this non-purchasable offer; price nulled",
    },
}

PRICE_FIELDS = [
    "egs_original_price_usd",
    "egs_original_price_cents",
    "egs_discount_price_cents",
    "egs_currency",
]

# columns that survive in the output for low-confidence matches; everything else is
# nulled so a garbage match can't leak a wrong price/seller into the analysis
LOW_CONFIDENCE_KEEP = [
    "title",
    "egs_match_title",
    "egs_match_score",
    "egs_meets_threshold",
    "egs_notes",
]

# the order we write columns out; keeps the csv stable across runs
OUTPUT_COLUMNS = [
    "title",
    "egs_match_title",
    "egs_match_score",
    "egs_meets_threshold",
    "egs_slug",
    "egs_namespace",
    "egs_offer_id",
    "egs_seller",
    "egs_developer",
    "egs_publisher",
    "egs_original_price_usd",
    "egs_original_price_cents",
    "egs_discount_price_cents",
    "egs_currency",
    "egs_release_date",
    "egs_effective_date",
    "egs_categories",
    "egs_tags",
    "egs_tag_ids",
    "egs_short_description",
    "egs_description",
    "egs_notes",
]


# --- small ported helpers (the marimo workbench is not importable) ---

def normalize_title(title: str | None) -> str:
    """Lowercase, strip punctuation, and collapse whitespace for rough matching."""
    if not title:
        return ""
    lowered = title.lower()
    lowered = re.sub(r"[^a-z0-9]+", " ", lowered)
    return re.sub(r"\s+", " ", lowered).strip()


def looks_like_page_slug(value: str | None) -> bool:
    """Return True when a slug looks like a real page slug, not an opaque hex id."""
    if not value:
        return False
    if len(value) >= 24 and all(ch in "0123456789abcdef" for ch in value.lower()):
        return False
    return True


def clean_slug(
    raw_slug: str | None,
    custom_attributes: list[dict[str, Any]] | None = None,
    url_slug: str | None = None,
) -> str | None:
    """Clean a product slug, falling back to custom attributes or the url slug."""
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


def search_elements(payload: dict[str, Any]) -> list[dict[str, Any]]:
    """Pull the search result elements out of a fetch_store_games payload."""
    return (
        payload.get("data", {})
        .get("Catalog", {})
        .get("searchStore", {})
        .get("elements", [])
    )


def price_block(element: dict[str, Any]) -> dict[str, Any]:
    """Return the totalPrice block from a search/offer element (or empty)."""
    return (element.get("price") or {}).get("totalPrice") or {}


def cents_to_usd(cents: Any, decimals: int = 2) -> float | None:
    """Convert an integer cents price to a float (assumes 2 decimal places)."""
    if cents is None:
        return None
    try:
        return round(int(cents) / (10 ** decimals), 2)
    except (TypeError, ValueError):
        return None


def tag_names(element: dict[str, Any], tag_lookup: dict[str, str]) -> tuple[list[str], list[str]]:
    """Return (tag_ids, readable_tag_names) for a search/offer element."""
    ids = [
        str(tag["id"])
        for tag in (element.get("tags") or [])
        if isinstance(tag, dict) and tag.get("id")
    ]
    names = [tag_lookup.get(tid, tid) for tid in ids]
    return ids, names


def category_paths(element: dict[str, Any]) -> str:
    """Join the catalog category paths (e.g. games/edition/base) into one string."""
    return " | ".join(
        category["path"]
        for category in (element.get("categories") or [])
        if category.get("path")
    )


def build_tag_lookup(api: EpicGamesStoreAPI) -> dict[str, str]:
    """Build a tag-id -> tag-name lookup once for the whole run."""
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


# --- matching + enrichment ---

def pick_best_match(title: str, elements: list[dict[str, Any]]) -> tuple[dict[str, Any] | None, float]:
    """Pick the highest-scoring catalog element for a title.

    Scores each candidate with token_set_ratio and a normalized ratio, takes the
    max, and treats a casefold-exact title as a perfect 100. Returns the best
    element and its score (or (None, 0.0) when there are no candidates).
    """
    best_element: dict[str, Any] | None = None
    best_score = 0.0
    normalized_query = normalize_title(title)

    for element in elements:
        candidate = str(element.get("title", ""))
        if candidate.casefold() == title.casefold():
            score = 100.0
        else:
            token_set = fuzz.token_set_ratio(title, candidate)
            normalized = fuzz.ratio(normalized_query, normalize_title(candidate))
            score = max(token_set, normalized)

        if score > best_score:
            best_score = score
            best_element = element

    return best_element, round(best_score, 1)


def fetch_offer_record(api: EpicGamesStoreAPI, namespace: str | None, offer_id: str | None) -> dict[str, Any]:
    """Fetch the offer-level catalog record for cleaner price/tags/attribution.

    Returns an empty dict on any failure - this is best-effort enrichment, so a
    flaky offer call should never sink the whole title.
    """
    if not namespace or not offer_id:
        return {}
    try:
        payload = api.get_offers_data(OfferData(namespace=namespace, offer_id=offer_id))
    except Exception:
        return {}
    for chunk in payload:
        record = chunk.get("data", {}).get("Catalog", {}).get("catalogOffer", {})
        if record:
            return record
    return {}


def fetch_product_about(api: EpicGamesStoreAPI, slug: str | None) -> dict[str, Any]:
    """Fetch the product page and extract about-level fields (best-effort)."""
    if not slug:
        return {}
    try:
        product = api.get_product(slug)
    except Exception:
        return {}

    pages = product.get("pages") or []
    page = pages[0] if pages else {}
    about = (page.get("data") or {}).get("about") or {}
    return {
        "developer": about.get("developerAttribution"),
        "publisher": about.get("publisherAttribution"),
        "short_description": about.get("shortDescription"),
        "description": about.get("description"),
    }


def enrich_title(
    api: EpicGamesStoreAPI,
    title: str,
    tag_lookup: dict[str, str],
    override: dict[str, str] | None = None,
) -> dict[str, Any]:
    """Search, match, and enrich a single title into one flat record.

    Casts a wide net but degrades gracefully: any field that cannot be fetched is
    left null and the reason is appended to ``egs_notes`` rather than raising.
    When a ``MANUAL_OVERRIDES`` entry is passed, it steers the outcome: "skip"
    returns an unmatched record, "pick" pins an exact store listing, and
    "null_price" enriches normally then blanks the price fields. Override records
    carry the note under ``egs_override`` so cache invalidation can spot stale ones.
    """
    record: dict[str, Any] = {"title": title}
    notes: list[str] = []

    if override:
        record["egs_override"] = override["note"]
        if override["action"] == "skip":
            record["egs_notes"] = "manual override: " + override["note"]
            return record

    keywords = override["keywords"] if override and override["action"] == "pick" else title
    try:
        payload = api.fetch_store_games(keywords=keywords, count=SEARCH_COUNT, with_price=True)
        elements = search_elements(payload)
    except Exception as exc:
        record["egs_notes"] = "search failed: " + str(exc)
        return record

    if override and override["action"] == "pick":
        elements = [
            element for element in elements
            if element.get("title") == override["match_title"]
            and ("seller" not in override
                 or (element.get("seller") or {}).get("name") == override["seller"])
        ]
        if not elements:
            record["egs_notes"] = "manual override: pinned listing not found in search"
            return record
        notes.append("manual override: " + override["note"])

    if not elements:
        record["egs_notes"] = "no search results"
        return record

    best, score = pick_best_match(title, elements)
    if best is None:
        record["egs_notes"] = "no scoreable candidate"
        return record

    custom_attributes = best.get("customAttributes") or []
    slug = clean_slug(best.get("productSlug"), custom_attributes, best.get("urlSlug"))
    namespace = best.get("namespace")
    offer_id = best.get("id")
    # a pinned listing is trusted even when its title differs a lot from ours
    meets = score >= MATCH_THRESHOLD or bool(override and override["action"] == "pick")

    # search-level fields are always available
    search_price = price_block(best)
    tag_ids, tag_readable = tag_names(best, tag_lookup)
    record.update(
        {
            "egs_match_title": best.get("title"),
            "egs_match_score": score,
            "egs_meets_threshold": meets,
            "egs_slug": slug,
            "egs_namespace": namespace,
            "egs_offer_id": offer_id,
            "egs_seller": (best.get("seller") or {}).get("name"),
            "egs_original_price_cents": search_price.get("originalPrice"),
            "egs_original_price_usd": cents_to_usd(search_price.get("originalPrice")),
            "egs_discount_price_cents": search_price.get("discountPrice"),
            "egs_currency": search_price.get("currencyCode"),
            "egs_release_date": best.get("releaseDate"),
            "egs_effective_date": best.get("effectiveDate"),
            "egs_categories": category_paths(best),
            "egs_tag_ids": ", ".join(tag_ids),
            "egs_tags": ", ".join(tag_readable),
            # the search element carries a short blurb directly, no page needed
            "egs_short_description": best.get("description"),
        }
    )

    # only spend deeper calls on confident matches
    if not meets:
        notes.append("low confidence match (< {:.0f})".format(MATCH_THRESHOLD))
        record["egs_notes"] = "; ".join(notes)
        return record

    # offer record: cleaner attribution + price/tags when present
    offer = fetch_offer_record(api, namespace, offer_id)
    if offer:
        attrs = {
            a["key"]: a["value"]
            for a in (offer.get("customAttributes") or [])
            if a.get("key")
        }
        record["egs_developer"] = attrs.get("developerName") or offer.get("developerDisplayName")
        record["egs_publisher"] = attrs.get("publisherName") or offer.get("publisherDisplayName")
        offer_price = price_block(offer)
        if offer_price.get("originalPrice") is not None:
            record["egs_original_price_cents"] = offer_price.get("originalPrice")
            record["egs_original_price_usd"] = cents_to_usd(offer_price.get("originalPrice"))
            record["egs_discount_price_cents"] = offer_price.get("discountPrice")
            record["egs_currency"] = offer_price.get("currencyCode") or record.get("egs_currency")
        if not record.get("egs_categories"):
            record["egs_categories"] = category_paths(offer)
        if not record.get("egs_tags"):
            offer_ids, offer_readable = tag_names(offer, tag_lookup)
            record["egs_tag_ids"] = ", ".join(offer_ids)
            record["egs_tags"] = ", ".join(offer_readable)
    else:
        notes.append("offer record unavailable")

    # product page: richer description + best attribution when a real slug exists
    about = fetch_product_about(api, slug)
    if about:
        record["egs_developer"] = record.get("egs_developer") or about.get("developer")
        record["egs_publisher"] = record.get("egs_publisher") or about.get("publisher")
        if about.get("short_description"):
            record["egs_short_description"] = about.get("short_description")
        record["egs_description"] = about.get("description")
    else:
        notes.append("no product page (opaque/missing slug)")

    # seller is the storefront distributor; a decent publisher fallback
    if not record.get("egs_publisher"):
        record["egs_publisher"] = record.get("egs_seller")
    if not record.get("egs_developer"):
        notes.append("developer unavailable")

    # only null the price while the store actually reports $0; a restored real
    # price should win over the override
    if override and override["action"] == "null_price" and not record.get("egs_original_price_cents"):
        for field in PRICE_FIELDS:
            record[field] = None
        notes.append("manual override: " + override["note"])

    if notes:
        record["egs_notes"] = "; ".join(notes)
    return record


# --- cache + driver ---

def load_cache(refresh: bool) -> dict[str, dict[str, Any]]:
    """Load the per-title cache, or start empty when refreshing/missing."""
    if refresh or not CACHE_FILE.exists():
        return {}
    with open(CACHE_FILE, "r", encoding="utf-8") as handle:
        return json.load(handle)


def save_cache(cache: dict[str, dict[str, Any]]) -> None:
    """Persist the per-title cache so interrupted runs resume cleanly."""
    OUTPUT_DIR.mkdir(exist_ok=True)
    with open(CACHE_FILE, "w", encoding="utf-8") as handle:
        json.dump(cache, handle, ensure_ascii=False, indent=2)


def load_unique_titles(limit: int | None) -> list[str]:
    """Load unique, non-empty giveaway titles from the cleaned dataset."""
    import pandas as pd

    df = pd.read_csv(INPUT_FILE)
    if TITLE_COLUMN not in df.columns:
        raise KeyError("Expected a {!r} column in {}".format(TITLE_COLUMN, INPUT_FILE))

    titles = (
        pd.Series(df[TITLE_COLUMN])
        .dropna()
        .astype(str)
        .str.strip()
        .loc[lambda s: s.ne("")]
        .drop_duplicates()
        .tolist()
    )
    if limit is not None:
        return titles[:limit]
    return titles


def write_output(cache: dict[str, dict[str, Any]], titles: list[str]) -> None:
    """Write the enrichment table for the requested titles, in input order.

    Low-confidence matches keep their provenance columns (match title, score,
    threshold flag, notes) but have every substantive field nulled - the cache
    retains the raw guess, the analysis surface does not.
    """
    import pandas as pd

    rows = [cache[title] for title in titles if title in cache]
    df = pd.DataFrame(rows)
    for column in OUTPUT_COLUMNS:
        if column not in df.columns:
            df[column] = None
    df = df[OUTPUT_COLUMNS]

    low_confidence = ~df["egs_meets_threshold"].eq(True)
    null_columns = [c for c in OUTPUT_COLUMNS if c not in LOW_CONFIDENCE_KEEP]
    df.loc[low_confidence, null_columns] = None
    print("Nulled substantive fields for {} low-confidence matches.".format(
        int((low_confidence & df["egs_match_title"].notna()).sum())), flush=True)

    df.to_csv(OUTPUT_FILE, index=False)
    print("Wrote {} rows to {}".format(len(df), OUTPUT_FILE), flush=True)


def parse_args() -> argparse.Namespace:
    """Parse the small CLI for slice testing, refreshes, and polite delays."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--limit", type=int, default=None, help="only process the first N unique titles")
    parser.add_argument("--refresh", action="store_true", help="ignore the cache and re-fetch everything")
    parser.add_argument("--delay", type=float, default=1.0, help="seconds between live title fetches")
    return parser.parse_args()


def main() -> None:
    """Run the EGS enrichment pass over the unique giveaway titles."""
    args = parse_args()

    titles = load_unique_titles(args.limit)
    print("Considering {} unique titles.".format(len(titles)), flush=True)

    cache = load_cache(args.refresh)
    print("Loaded {} cached titles from {}.".format(len(cache), CACHE_FILE), flush=True)

    scraper = cloudscraper.create_scraper()
    api = EpicGamesStoreAPI(locale="en-US", country="US", session=scraper)
    tag_lookup = build_tag_lookup(api)
    print("Tag lookup ready ({} tags).".format(len(tag_lookup)), flush=True)

    # a title is pending when uncached, or when its manual override changed since
    # it was cached (the egs_override marker records which note was applied)
    pending = [
        title for title in titles
        if title not in cache
        or cache[title].get("egs_override") != (MANUAL_OVERRIDES.get(title) or {}).get("note")
    ]
    print("Fetching {} new titles (cache covers the rest).".format(len(pending)), flush=True)

    for index, title in enumerate(pending, start=1):
        print("[{}/{}] {}".format(index, len(pending), title), flush=True)
        cache[title] = enrich_title(api, title, tag_lookup, MANUAL_OVERRIDES.get(title))
        match = cache[title].get("egs_match_title")
        score = cache[title].get("egs_match_score")
        print("  -> {} (score={})".format(match, score), flush=True)

        if index % SAVE_EVERY == 0:
            save_cache(cache)

        if args.delay > 0 and index != len(pending):
            time.sleep(args.delay)

    save_cache(cache)
    write_output(cache, titles)


if __name__ == "__main__":
    main()

# egdata GitHub source review: useful shortcuts without a redesign

Reviewed 2026-09-10 at these repository revisions:

- [`egdata-api` at `0fe8c553`](https://github.com/egdata-app/egdata-api/tree/0fe8c5536b6546565c6f6caf0e60e2165ccbb807)
- [`egdata` at `0281cd3c`](https://github.com/egdata-app/egdata/tree/0281cd3c44f59d2fbf9f2b39bfe25e52b09a4138)

This review asks a narrow question: what can this Python/pandas project consume or independently
reimplement to avoid duplicate work, while keeping the current source → clean → enrich → canonical
tables → dashboard structure?

## Short answer

Add one small, optional **egdata reconciliation enricher**. Do not replace the existing pipeline and
do not port their TypeScript application.

The highest-value pieces are:

1. Download egdata's offer-linked giveaway history once per refresh.
2. Use per-offer giveaway history and bulk offer-existence checks to audit current EGS matches.
3. Keep egdata's offer and namespace IDs as separate candidate/provenance columns.
4. Experiment with price history only after measuring date coverage.
5. Borrow several data-model ideas—especially occurrence/offer/game grain and price semantics—by
   independently implementing them in Python.

The public repositories contain the API-serving and website code, but not the ingestion system that
collects the Epic catalog. Regeneration routes submit work to a separate job service. There is no
ready-made superior Epic scraper here to lift into `development/`.

## What can be consumed directly

| Source | How it fits | Recommendation |
|---|---|---|
| `GET /free-games/history` | Dated raw event source; exact offer ID, namespace, UTC window, offer type, store metadata, and current regional price | **Use now as a reconciliation snapshot** |
| `GET /offers/{id}/giveaways` | Returns every giveaway window for one offer | **Use now to validate known offer IDs** |
| `POST /offers/exists` | Divides submitted IDs into existing/non-existing lists | **Use now as a cheap cache audit** |
| `POST /offers/slugs` | Maps store slugs to an offer ID and namespace | **Candidate generator only** |
| `GET /offers/{id}` or `/overview` | Store metadata for a known ID | Optional replacement for some EGS enrichment calls after identity is trustworthy |
| `GET /offers/{id}/price-history` | Historical regional price observations | Experimental; require coverage and ordering repairs locally |
| `GET /offers/{id}/hltb` | HLTB ID and sometimes time arrays | Audit/fallback only; do not replace the current HLTB cache yet |
| `GET /offers/{id}/ratings` | External ratings, observed as OpenCritic in a live response | Complement to Metacritic, not a replacement |
| `GET /offers/{id}/igdb` | IGDB game metadata | Optional gap-filler after identity is resolved |
| `GET /free-games/stats` | egdata's headline totals | Do not ingest as analytical truth; calculate locally under explicit definitions |

The history route is implemented as a simple dated event collection joined to offer and price data,
with a hard page cap of 25 records ([source](https://github.com/egdata-app/egdata-api/blob/0fe8c5536b6546565c6f6caf0e60e2165ccbb807/src/routes/free-games.tsx#L253-L338)).
At the current 691 records, a full refresh is about 28 requests—not hundreds of per-title searches.
It returns an array rather than pagination metadata, so a client should increment `page` until the
response contains fewer than 25 records.

The endpoint emits an ETag and honored `If-None-Match` with `304 Not Modified` in a live test. This
fits the repo's one-day refresh and rolling-fallback convention: retain the ETag with the cached
snapshot and avoid downloading unchanged pages.

### Minimal new artifact

A future `development/egdata_reconcile.py` can remain one linear script with ordinary functions:

```python
def fetch_history_page(page: int, etag: str | None = None) -> tuple[list[dict], str | None]:
    """Fetch one page of egdata giveaway history, honoring a cached ETag."""


def flatten_history(records: list[dict]) -> pd.DataFrame:
    """Flatten only the offer, window, identity, type, and price fields used here."""


def reconcile_events(base: pd.DataFrame, history: pd.DataFrame) -> pd.DataFrame:
    """Compare local giveaway events with egdata without silently correcting either source."""
```

Suggested outputs:

- `data/YYYY-MM-DD-egdata.csv`: flattened daily source snapshot; keep the newest and one fallback.
- `outputs/egdata_http_cache.json`: page ETags and refresh metadata.
- `outputs/egdata_reconciliation.csv`: local/egdata agreement, match method, and unresolved rows.

Initially, do **not** attach this data in `build_dataset.py`. Treat it as QA evidence until the
source-grain repair is complete. After acceptance it can behave like the existing enrichment inputs,
adding `egdata_*` columns without changing the overall pipeline.

## Identity strategy to riff on

egdata's schema makes three grains visible even though its UI sometimes merges them:

1. **Giveaway occurrence:** offer ID + start + end + platform.
2. **Store offer:** one purchasable/listed edition identified by offer ID and namespace.
3. **Displayed game:** a human-facing grouping that may combine offers or platform variants.

The current repo has event- and title-level tables, but title matching blurs the second and third
grains. Add offer identity without replacing the tables:

- Keep raw `egdata_offer_id` and `egdata_namespace` separate from the current `egs_offer_id`.
- Define the egdata occurrence key as `(offer_id, start_date, end_date, platform)`.
- Match events in this order:
  1. offer ID + calendar-date window;
  2. namespace + exact normalized title + window;
  3. exact normalized title + window, marked for review;
  4. unmatched.
- Never use fuzzy title similarity to silently alter a giveaway window.

Use calendar dates for the Sheet comparison because the Sheet stores dates while egdata stores UTC
timestamps. Preserve the original UTC timestamps in provenance columns.

The frontend groups current platform variants by `namespace:title`, retains all underlying offers,
and unions their platforms ([source](https://github.com/egdata-app/egdata/blob/0281cd3c44f59d2fbf9f2b39bfe25e52b09a4138/src/utils/merge-freebies.ts#L8-L27)).
That is a useful **display** rule, not a source deduplication. Preserve the raw occurrences, then
derive a presentation grouping if the dashboard needs it.

## Why slug resolution is not authoritative

`POST /offers/slugs` expands each slug to both `slug` and `slug/home`, searches several catalog
fields, excludes pre-purchase offers, and returns the first match
([source](https://github.com/egdata-app/egdata-api/blob/0fe8c5536b6546565c6f6caf0e60e2165ccbb807/src/routes/offers/index.ts#L864-L939)).

A live test using saved local values found:

| Title | Local saved offer ID | egdata slug result |
|---|---|---|
| Alien: Isolation | `d37…f9d3` | same ID |
| Control | `562…7016` | `8a9…27da` |
| Subnautica | `a6d…1272` | `9ac…c0b3` |

All three local IDs still passed `/offers/exists`, but the saved Control and Subnautica IDs returned
no giveaway history. This is exactly why slug resolution should propose a candidate rather than
overwrite an existing historical identity. A current store slug can point at a replacement offer,
edition, or relisting.

The strongest immediate QA rule is therefore:

> A supposed giveaway offer match should normally have an egdata giveaway window that agrees with
> at least one local event. “The offer exists” and “the title looks right” are insufficient.

This rule would identify some wrong or nonhistorical EGS matches without expanding the manual
override list by hand.

## Search endpoint: useful bug knowledge, poor matching foundation

The source implementation expects the parameter `title` and applies an OpenSearch multi-match over
title, description, and ID
([source](https://github.com/egdata-app/egdata-api/blob/0fe8c5536b6546565c6f6caf0e60e2165ccbb807/src/routes/free-games.tsx#L350-L445)).
The committed OpenAPI contract instead documents the parameter as `query`
([source](https://github.com/egdata-app/egdata-api/blob/0fe8c5536b6546565c6f6caf0e60e2165ccbb807/src/openapi/paths.ts#L1409-L1423)).

This explains why the earlier `query=Alien: Isolation` test behaved as an unfiltered search. Even
with `title=Control`, the live endpoint returned 14 broad matches. Use this route only to generate a
small candidate set followed by exact title/window checks. Do not replace the current auditable
matching logic with its search ranking.

## Price ideas worth independently implementing

### 1. Keep integer minor units

egdata stores prices in minor units and converts only at display time. JPY and KRW are treated as
full-unit currencies rather than divided by 100
([source](https://github.com/egdata-app/egdata/blob/0281cd3c44f59d2fbf9f2b39bfe25e52b09a4138/src/lib/calculate-price.ts#L1-L12)).
This is safer than using floating-point currency as the canonical representation. The repo already
keeps cents; retain cents as authoritative and derive display dollars.

### 2. Treat promotions as half-open intervals

Their UI considers a promotion active when `start <= timestamp < end`, and can infer a return to
regular price when the last observed sale window has ended
([source](https://github.com/egdata-app/egdata/blob/0281cd3c44f59d2fbf9f2b39bfe25e52b09a4138/src/lib/effective-price.ts#L20-L146)).
That interval convention is a good fit for giveaway windows and avoids double-counting a boundary
instant shared by consecutive promotions.

### 3. Do not promise price-at-giveaway yet

The price-history API accepts `region` and `since`, but its implementation sorts on `date` while
the live records inspected had `date: null` and usable `updatedAt` timestamps
([source](https://github.com/egdata-app/egdata-api/blob/0fe8c5536b6546565c6f6caf0e60e2165ccbb807/src/routes/offers/price.ts#L16-L72)).
Sort locally by parsed `updatedAt`.

More importantly, Alien: Isolation's live US price history began in February 2023, after its 2020
and 2021 giveaways. Price history can support a new column only when an observation or promotion
rule actually covers the giveaway timestamp. Otherwise leave `price_at_giveaway` null and report
coverage. Never substitute the earliest later observation.

### 4. Be explicit about “total value”

egdata's stats implementation sums the **current price record once per unique offer**, while its
giveaway count counts occurrences and its “repeated” value counts offer IDs appearing more than once
([source](https://github.com/egdata-app/egdata-api/blob/0fe8c5536b6546565c6f6caf0e60e2165ccbb807/src/routes/free-games.tsx#L535-L642)).
These are defensible but mixed-grain definitions. Reimplement the concepts as clearly named local
metrics:

- `giveaway_occurrences`
- `unique_offers`
- `offers_repeated_at_least_once`
- `repeat_occurrences_beyond_first`
- `current_unique_offer_list_value`
- `observed_value_at_giveaway` with an explicit coverage percentage

This is a conceptual riff that improves the current dashboard without changing its stack.

## HLTB, ratings, IGDB, and images

- HLTB is keyed directly to offer ID and considers an ID sufficient even when time arrays are empty
  ([source](https://github.com/egdata-app/egdata-api/blob/0fe8c5536b6546565c6f6caf0e60e2165ccbb807/src/routes/offers/data.ts#L1840-L1882)).
  The live Alien response had an HLTB ID but empty arrays. Keep the current local HLTB enrichment;
  egdata can validate IDs or fill gaps only after checking for actual time values.
- Ratings are resolved offer → sandbox → product → rating record, so the score belongs to the
  product rather than necessarily the exact edition. The observed response was OpenCritic. Retain
  Metacritic and optionally add OpenCritic as a separate source; comparing them is analytical work,
  not a scraper replacement.
- IGDB could fill Wikipedia gaps, but replacing Wikipedia now would change provenance and trigger a
  larger redesign. Defer it.
- For future game cards, riff on egdata's deterministic image preference: choose a preferred image
  type from `keyImages`, fall back to the first image, and retain the image type. Do not hotlink
  images in a static export without deciding the desired dependency/privacy behavior.

## Reliability behavior to adopt

Implement a small `requests.Session`-based fetcher inside the reconciliation script:

- fixed 10–15 second timeout;
- descriptive `User-Agent` with a project URL or contact;
- retry `429`, `500`, `502`, `503`, and `504` with exponential backoff and `Retry-After` support;
- do not retry ordinary `400`, `401`, `403`, or `404` responses;
- conditional `If-None-Match` requests;
- page-level cache writes so interruption is resumable;
- preserve unknown JSON fields in raw cache, but flatten only explicitly selected fields;
- validate required fields and tolerate nullable optional fields.

The static marimo/WASM dashboard should **not** call egdata directly. Live responses allowed CORS
from `https://egdata.app`, not arbitrary deployment origins. Fetch during the Python build and ship
the resulting local data asset, which matches the existing dashboard architecture.

## What not to copy or adopt

- Do not port the Hono/Mongo/Redis/OpenSearch stack. It solves a different product problem.
- Do not use their aggregate stats as canonical facts; definitions and cutoffs differ.
- Do not replace exact event reconciliation with their full-text search ranking.
- Do not overwrite historical offer IDs with slug results.
- Do not treat missing price history as evidence that the price was unchanged.
- Do not copy their source code verbatim. Neither reviewed GitHub repository contains a license file
  or declares a license through the GitHub API. Public visibility permits reading and forking through
  GitHub, but it does not grant general reuse rights. The short Python sketches in this report are
  independent interface proposals, not translations of their implementation.

Their website's fair-use page describes why **they** collect factual Epic data; it is not a software
or database license for downstream users. The documented public API is still the cleanest route for
factual interoperability, but attribution, acceptable-use expectations, and redistribution should
be confirmed before making a public downloadable dataset substantially sourced from egdata.

## Recommended order of work

1. Finish the local source-grain repair already identified in `PROJECT_REVIEW.md`.
2. Add the read-only reconciliation script and dated history snapshot.
3. Produce an audit report; do not change canonical values automatically.
4. Review collisions and establish accepted event/offer mappings.
5. Add accepted `egdata_*` provenance columns to the canonical build.
6. Only then test price-history and optional OpenCritic/IGDB gap fills.

This takes advantage of egdata's strongest work—persistent catalog observation and stable technical
identifiers—while preserving this project's current Python pipeline and its more distinctive focus
on transparent giveaway analysis.

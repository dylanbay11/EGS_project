# Data Dictionary — Epic Games Giveaway Dataset

The canonical analysis dataset, produced by `development/build_dataset.py`.

## Files

| File | Grain | Rows | Description |
|------|-------|------|-------------|
| `data/egs_giveaways.parquet` (+`.csv`) | **event-level** | ~914 | one row per giveaway *occurrence* (repeats preserved) |
| `data/egs_giveaways_by_game.parquet` (+`.csv`) | **game-level** | ~683 | one row per unique title, with giveaway frequency |

Parquet is the canonical format; the `.csv` mirrors are for quick inspection only.

## Grain & keys

- **Event-level** keeps every giveaway event, so a title given away multiple times
  (e.g. *Bloons TD 6* ×12) appears multiple times. Use this for timing, cadence,
  and "dollars given away over time" analyses.
- **Game-level** is one row per unique `title`, with `giveaway_count`,
  `first_giveaway`, `last_giveaway`. Enrichment fields are constant within a title.
- Enrichment sources (Wikipedia, Metacritic, HLTB, EGS) are joined onto events by a
  **normalized title key** (lowercased-strip + collapsed whitespace). They are
  game-level, fanned out to events via a validated many-to-one join.

## Columns by source

### Core giveaway event (from the community Google Sheet)
| Column | Type | Notes |
|--------|------|-------|
| `title` | str | giveaway title (canonical join key; collections decomposed to member games) |
| `from_date` / `to_date` | datetime | giveaway window start/end |
| `giveaway_year` | int | year derived from `from_date` |
| `day_of_week` | str | weekday the giveaway started |
| `duration_days` | int | giveaway length in days |
| `giveaway_type` | str | null = standard game; `dupe`/`dupe2`/`dupe3` = repeat; `mobile`; `pack`/`pack2`/`pack3` = in-game content packs; `free`, `other`, `-` = collection member. (The transient `next` marker is relabeled to null at build time; provenance goes to `notes`.) |
| `is_repeat` | bool | derived: `giveaway_type` starts with `dupe` |
| `is_standalone_game` | bool | derived: True = grants a standalone playable game (incl. bundles of full games); False = DLC/pack/unlock/in-game content. Classified from notes/type/title patterns + curated exception lists in `build_dataset.py`. Filter on this for "real games" analyses. |
| `notes` | str | free-text notes; collection members carry `Part of collection: ...` |
| `color_category` | str | source-sheet cell color (curation signal) |

### Wikipedia enrichment (`*_wiki`)
English-Wikipedia metadata for the matched title. Sparse (~64% of events match a
wiki article). Key fields: `title_wiki`, `year_wiki`, `developer_wiki`,
`publisher_wiki`, `releasedate_wiki`, `genre_wiki`, `engine_wiki`, `mode_wiki`,
`platform_wiki`, `summary_wiki`, `background_wiki`, plus credits
(`director_wiki`, `artist_wiki`, `composer_wiki`, `designer_wiki`, `writer_wiki`,
`programmer_wiki`) and source links (`ru_link_wiki`, `source_wiki`, `link_wiki`,
`daterange_wiki`).

### Metacritic enrichment (`mc_*`)
| Column | Type | Notes |
|--------|------|-------|
| `mc_title` / `mc_slug` | str | matched Metacritic title/slug (null = no match) |
| `mc_criticScore` | float | Metacritic critic score, 0–100 |
| `mc_rating` | str | content rating (often blank) |
| `mc_releaseDate` | str | Metacritic release date |
| `mc_platforms` | str | comma-separated platforms |

### HowLongToBeat enrichment (`hltb_*`)
| Column | Type | Notes |
|--------|------|-------|
| `hltb_found` | bool | whether a confident HLTB match was made |
| `hltb_game_name` | str | matched HLTB title |
| `hltb_main_story` / `hltb_main_extra` / `hltb_completionist` / `hltb_all_styles` | float | playtime estimates, **hours** |
| `hltb_review_score` | float | HLTB user review score |
| `hltb_platforms` | str | comma-separated platforms |
| `hltb_release_world` | float | HLTB world release year |
| `hltb_match_score` / `hltb_similarity` | float | match confidence (threshold 0.84) |
| `hltb_query_used` | str | the query string that produced the match |

### Epic Games Store enrichment (`egs_*`)
Store-side catalog data (this is a *storefront* API — no developer-console data).
Matched by fuzzy title search; `egs_meets_threshold` flags trusted matches. ~24
titles carry manual corrections (`MANUAL_OVERRIDES` in `egs_api_enrich.py`): pinned
listings for wrong fuzzy picks, forced no-match where the product is delisted, and
nulled prices where the store reports $0 for a non-purchasable offer. Matches below
the threshold keep only provenance columns (match title/score/flag/notes) — their
substantive fields are nulled in the output.
| Column | Type | Notes |
|--------|------|-------|
| `egs_match_title` | str | matched EGS catalog title (null = no match) |
| `egs_match_score` | float | fuzzy match score, 0–100 (a pinned override can be trusted with a low score) |
| `egs_meets_threshold` | bool | trusted match: score ≥ 80 **or** manual override (deep fields only fetched when true) |
| `egs_original_price_usd` | float | full retail price in **USD** |
| `egs_original_price_cents` / `egs_discount_price_cents` | float | raw price in cents |
| `egs_currency` | str | price currency (USD) |
| `egs_seller` | str | storefront seller (reliable; good publisher proxy) |
| `egs_publisher` | str | publisher (offer attribution → product page → seller fallback) |
| `egs_developer` | str | developer (product-page attribution; null when slug is opaque/missing) |
| `egs_tags` / `egs_tag_ids` | str | store tags decoded to names (genre, platform, single/multiplayer) |
| `egs_categories` | str | catalog category path (e.g. `games/edition/base`) |
| `egs_release_date` / `egs_effective_date` | str | EGS release / catalog effective date |
| `egs_short_description` / `egs_description` | str | store blurb / longer description |
| `egs_slug` / `egs_namespace` / `egs_offer_id` | str | EGS catalog identifiers |
| `egs_notes` | str | per-row notes on any dropped/unavailable fields; manual overrides are recorded here as `manual override: ...` |

### Game-level only (`egs_giveaways_by_game`)
| Column | Type | Notes |
|--------|------|-------|
| `giveaway_count` | int | number of times this title was given away |
| `first_giveaway` / `last_giveaway` | datetime | earliest / latest giveaway date |
| `is_standalone_game` | bool | min over the title's events (any add-on verdict wins) |

## Known caveats
- EGS `egs_developer` and `egs_description` are sparse: they require a reachable
  product page, which is unavailable when a title's slug is opaque/missing. Such
  cases are logged in `egs_notes`. `egs_seller`/`egs_publisher` remain well populated.
- Wikipedia fields are the sparsest source; absence ≠ the game has no such data.
  Some `*_wiki` credit fields carry footnote artifacts (e.g. `13AM Games, [, a, ]`).
- "No EGS match" usually means the product is **no longer in the EGS search catalog**
  (delisted, replaced by newer SKUs, or in-game content that was never a store page) —
  not a matcher failure. Verified July 2026 for the standalone-looking cases.
- EGS prices are the *current* store price of the matched listing. Two titles
  (Borderlands 2, Borderlands: The Pre-Sequel) have correct matches but nulled
  prices — the store reports $0 for offers that are no longer individually
  purchasable. Two matches point at successor re-releases of delisted originals
  (Trine 4 → Definitive Edition, Model Builder → Complete Edition), noted in
  `egs_notes`.

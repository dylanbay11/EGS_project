# egdata.app comparison and novelty assessment

Checked 2026-09-10. The site named in the request appears to be
[egdata.app](https://egdata.app/) (without an `s`), whose production API is
documented at [docs.egdata.app](https://docs.egdata.app/docs).

## Verdict

This project is **partly a replication at the data-collection layer, but not doomed to be a
replication as an analysis project**.

egdata is already the stronger general-purpose Epic Games Store database. It tracks the whole
catalog, current and historical prices, discounts, giveaways, store metadata, achievements,
offer/item/sandbox relationships, changelogs, builds, reviews, and search. Its homepage currently
reports 41,231 tracked offers and 691 giveaway occurrences. Its public REST contract includes
dedicated historical-giveaway, per-offer giveaway, HLTB, external-ratings, IGDB, and price-history
endpoints.

The defensible purpose of this repository is different: a reproducible, research-oriented dataset
and interactive analysis of **what Epic has given away over time**, enriched across sources and
explicit about event/game grain, identity uncertainty, definitions, and data quality. egdata has a
giveaway browser and a few headline totals; it does not appear to offer the program-level analytical
story this project is aiming at.

Put bluntly: **the scrapers are mostly plumbing; the cleaning decisions, audit trail, derived
measures, analysis, and editorial product are where this project can be original.**

## What egdata already covers

The [API reference](https://docs.egdata.app/docs/api-reference) is generated from a public
[OpenAPI contract](https://raw.githubusercontent.com/egdata-app/egdata-api/main/openapi/egdata.openapi.json).
The contract labels itself `0.1.0-alpha.0`, although it describes the listed REST operations as
public/stable. The relevant groups and operations include:

- Giveaways: `GET /free-games`, `/free-games/history`, `/free-games/search`,
  `/free-games/stats`, `/free-games/sellers`, and `/offers/{id}/giveaways`.
- Store identity and metadata: offers, items, sandboxes, slugs, genres, features, media,
  bundles, collections, achievements, and age ratings.
- Prices: current regional price, price history, regional comparisons, fairness, and aggregate
  price statistics.
- External enrichment: `/offers/{id}/hltb`, `/offers/{id}/ratings`, and
  `/offers/{id}/igdb`.
- Change tracking: offer/item changelogs and search over observed changes.
- Areas outside this project's current scope: manifests, build/file histories, technologies,
  top-seller/wishlist positions, public reviews, profiles, and achievements.

The live giveaway statistics endpoint returned 691 giveaway occurrences, 603 offers, 80 repeats,
306 sellers, and USD 12,611.14 in original-price value on 2026-09-10. The
[giveaway page](https://egdata.app/freebies) exposes the same totals plus current and past giveaway
browsing. A live history response also contained stable offer/namespace IDs, exact UTC start/end
timestamps, title, offer type, seller/developer/publisher, store tags, categories, current price,
release dates, descriptions, images, and availability restrictions.

The API is unusually relevant to this repo because identity is offer-based rather than title-based.
For example, its Alien: Isolation offer history returns the two giveaway windows directly, attached
to one offer ID. That avoids much of the fuzzy title matching and title-only joining currently used
here.

## Feature-by-feature comparison

| Capability | This repository | egdata | Assessment |
|---|---|---|---|
| Historical giveaway dates | Community Sheet + Wikipedia merge | Native offer-linked history | Strong replication; egdata is likely the cleaner upstream/reference |
| Repeat identification | Derived from source labels and occurrences | Native occurrence history + repeat aggregate | Replication, with room for better analytical definitions |
| Total giveaway/value KPIs | Provisional calculations in the apps | First-class homepage/API stats | Direct replication; do not lead with these as novel findings |
| Epic IDs, slugs, price, tags, developer/publisher | Fuzzy EGS enrichment with overrides | Native offer/namespace/item records | Replication; egdata is structurally stronger |
| HLTB | Local title matcher; 550 of 683 titles matched | Public per-offer HLTB endpoint | Overlap, but egdata's coverage/payload quality needs auditing |
| Review scores | Metacritic scrape; 548 positive-score titles | External ratings endpoint (live Alien example was OpenCritic) | Similar concept, different source; not novel by itself |
| General game metadata | Wikipedia infobox + summaries/background | Store metadata + IGDB | Partial overlap; Wikipedia provenance and fields are distinctive but not inherently novel |
| Event-level and game-level analytical tables | Explicit canonical tables and data dictionary | API resources can be joined to construct them | Useful productization, not unique raw data |
| Data-quality triage and match evidence | Scores, thresholds, overrides, audits, validation | Stable IDs reduce matching; public UI emphasizes browsing | A real differentiator if made visible and rigorous |
| Program-level visual analysis | Cadence, cumulative value, distributions, score/price/time discovery | Giveaway list and headline totals found; broader site is catalog/deal oriented | Best current differentiation |
| Price/build/catalog tracking | Minimal/current-price snapshot | Deep specialty, including history and regional data | Do not compete here |

## Important qualification about the current local snapshot

The saved canonical tables contain 914 rows, 683 unique titles, and 776 distinct
`title/from_date/to_date` combinations through 2026-04-30. Those figures should not be compared
naively to egdata's 691 current giveaway occurrences. The repository's own independent review has
already shown that the title-only wiki join inflates rows (806 cleaned Sheet rows become 914), and
the project's definitions include add-ons/content and source-specific distinctions. Until source
grain and product identity are repaired, a larger local number is **not evidence of better
coverage**.

There is also an instructive warning in egdata's own data. Its documented historical search endpoint
returned broad, apparently weakly related results for an `Alien: Isolation` query during this check,
and the Alien HLTB payload contained an HLTB ID but empty time arrays. So egdata should be audited,
not treated as unquestionable ground truth.

## Where the novel work is

The strongest direction is a **Giveaway Atlas / research notebook**, not another store database.
These questions are not answered by a searchable giveaway list or four totals:

1. **How has Epic's giveaway strategy changed?** Track cadence, full games versus add-ons,
   release-to-giveaway lag, price tier, critic quality, playtime, genre mix, seller/publisher
   concentration, and repeat share by year or program phase.
2. **What kind of library did the program create?** Quantify playable hours, quality-adjusted hours,
   short/high-rated discoveries, genre breadth, single-player/co-op mix, and how these accumulated.
3. **What predicts a repeat giveaway?** Model time to repeat and repeat probability using publisher,
   age, price, genre, prior giveaway timing, and possibly egdata price/top-list history. Present this
   as descriptive/predictive—not causal—unless the design supports causal claims.
4. **How do definitions change the headline?** Let users toggle offers versus titles, events versus
   unique windows, base games versus all content, editions/bundles, PC versus mobile, and current
   list price versus price at giveaway. Showing the sensitivity is more honest and more interesting
   than one giant dollar total.
5. **Where do sources disagree?** Build a public reconciliation layer comparing the Sheet,
   Wikipedia, Epic/egdata offer IDs, and enrichment matches. A transparent disagreement explorer is
   uncommon and portfolio-worthy data engineering.
6. **Did the program's value proposition change?** Combine giveaway cohorts with contemporaneous
   rather than current price, review, HLTB, and release-age measures. egdata's price history and
   changelog data could make this materially better than the current snapshot-price analysis.

The most compelling first release would combine (1), (2), and (4): a visitor can see the program
change over time, explore the library they could have accumulated, and understand exactly how the
counts were defined.

## Recommended project adjustment

1. **Keep the independent sources for provenance, but add egdata as a reconciliation source.** Use
   its stable offer ID + exact UTC giveaway window as the identity spine where available. Preserve
   the Sheet and Wikipedia values beside it so disagreements remain inspectable.
2. **Stop expanding the general EGS scraper.** Do not spend portfolio time reproducing builds,
   price tracking, catalog search, or store metadata that egdata already exposes more deeply.
3. **Repair source grain before making comparative claims.** Resolve the documented 806→914 join
   expansion and define the primary population. Then compare local distinct offer-windows with
   egdata through the shared cutoff date.
4. **Replace current-price “library value” with better-labeled measures.** At minimum call it
   current/list-price value. Prefer price at the giveaway date if egdata's price history is complete
   enough, and publish coverage/sensitivity diagnostics.
5. **Lead the dashboard with a question, not totals.** “How did Epic's giveaway strategy change?”
   and “What would your claimed library look like?” are defensible. “How many games/value?” is
   already egdata's homepage.
6. **Treat the API as an external dependency cautiously.** The public docs warn about `429` and
   evolving schemas, recommend stable IDs and nullable-field tolerance, and describe change handling
   in their [client policy](https://docs.egdata.app/docs/changelog-deprecations). The GitHub API
   reported no declared license for either public repository during this check. Public endpoint
   access is documented, but reuse/redistribution terms and attribution should be clarified before
   making egdata the sole production source.

## Bottom line

If the intended deliverable is “a database of Epic offers and historical freebies,” egdata has
already built the more comprehensive version.

If the intended deliverable is “a transparent, reproducible analysis of Epic's giveaway program and
the library it created,” this project still has plenty of room. The novel artifact is not possession
of the rows; it is the trustworthy definitions, cross-source reconciliation, longitudinal analysis,
and visitor experience built on top of them.


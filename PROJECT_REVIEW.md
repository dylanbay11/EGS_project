# Project orientation and independent review

Reviewed September 5, 2026. Review branch: `codex/repository-orientation-review`, based on `origin/resolve-pending-review` at `d00ffaa`.

## Start here

**This is a substantial research prototype with a reproducible downstream build and usable exploration tools. It is not yet a trustworthy finished analysis dataset.** The largest remaining problem is the meaning and correctness of the records, rather than a shortage of features.

You do not need to understand every historical scraper to regain control. Concentrate on four things: what one record represents, whether enrichment belongs to the right product, what the headline statistics actually measure, and what experience you want a visitor to have.

My recommendation is to **keep the newer foundation, pause feature expansion, and repair the data contract before treating the charts as findings**. Going back to `main` would lose useful work without removing the core join defect. Going back conceptually to your source annotations and original research questions would help a great deal.

The most consequential findings are:

- The first source merge turns **806 cleaned Sheets rows into 914 rows**. Those extra 108 rows are join multiplication, not additional giveaways. Bloons TD 6 has four source rows but twelve merged rows. This invalidates the documented interpretation of the 914 count and distorts repeat rankings and event-weighted charts.
- Wrong game identities remain in both EGS and Metacritic enrichment. For example, **BioShock Remastered is linked to BioShock 2 Remastered at EGS with score 100**. BioShock Infinite's Metacritic record belongs to The Witcher 3. These are present in the saved data, not hypothetical risks.
- The 683-title count and $12,114.01 price sum are reproducible calculations, but still provisional measures: aliases, overlapping editions, mixed platforms, and unverified matches remain.
- The old “decisions needed” list mixed mechanical corrections with research choices. The newer “all resolved” log overstates closure. Neither is a sufficient agenda for your personal QA.

Evidence is reproducible with [outputs/repository_review_checks.py](outputs/repository_review_checks.py); its captured results are in [outputs/repository_review_checks.txt](outputs/repository_review_checks.txt). The script performs no live scraping and writes no datasets. Pipeline repairs are recommendations in this review, not changes applied here.

## Where the work actually lives

Remote references were refreshed successfully before review. There are nine non-Jules branch tips, excluding the `origin/HEAD` alias. At the start, your clean working tree was on `main`.

| Branch | Tip | Relationship and practical meaning |
|---|---|---|
| `main` | `6fb085b` | April 29 foundation: source collection, cleaning, MC/HLTB enrichment. Missing the newer canonical builder and explorers. |
| `manual-work` | `b6e4f92` | Nine commits ahead of main; workbench, expanded README, canonical event/game tables, EDA, validator, internal explorer, dictionary, diagram, original review questions. |
| `resolve-pending-review` | `d00ffaa` | Two commits beyond manual-work, eleven beyond main. Applies EGS overrides, title folds and classification; adds the public portfolio app and extract. Latest implementation, but its final commit explicitly calls the visualizer attempt unsatisfactory. |
| `feature/hltb-integration-14946634352642772600` | `5ab1c67` | Already an ancestor of main. Its useful HLTB matching work is included; no separate merge needed. |
| `feature/update-data-flow-3174093723568944651` | `d91db51` | Divergent older work: one unique commit, eighteen main-side commits absent. Its dated-file flow is superseded by main's rolling intermediate convention. No compelling reason to merge it wholesale. |
| `offline_edits` | `d8a7049` | June 2025 ancestor of main; earlier title-string/parquet work. Historical reference. |
| `original_track` | `73828cf` | May 2025 offshoot: one unique commit, 112 main-side commits absent. Small scraper edit and sample data; not another unfinished modern pipeline. |
| `aftermods` | `3946a53` | January 2025 ancestor of main; older review-fetcher exploration. |
| `lastday` | `e9f585e` | April 2024 ancestor of main; original Streamlit-era work. |

The two Jules-named branches were excluded as separate review targets, as requested. Their merged effects necessarily remain part of main and its descendants.

There is no need to reconcile nine active development directions. There is one modern continuation, two old divergent experiments, and historical checkpoints. I would use the latest continuation for targeted repairs, then consider integrating it into main after checking the repaired data. I have not merged, deleted, or pushed any branch.

## The project in four parts

| Part | Entry points | What exists / how much to trust it |
|---|---|---|
| Source history | `data_collection.py`, `wiki_scraper.py`, dated files in `data/` | Saved April 23/29 source snapshots; rolling raw-cache logic. Sheets contains titles, windows, notes, type codes, and colors. Source interpretation still needs QA. |
| Cleaning and enrichment | `enrich_wiki_data.py`, `clean_data.py`, MC/HLTB/EGS scripts | Substantial working transformations and saved caches. Identity, source grain, and refresh handling need repair. |
| Analysis tables | `build_dataset.py`, the two `egs_giveaways*.parquet` files | The intended canonical interface. Rebuild from the saved intermediate/caches reproduces both parquets exactly. That establishes reproducibility, not validity. |
| Exploration and presentation | `eda.py`, `explorer.py`, `portfolio_explorer.py` | Three distinct artifacts: fixed exploratory analysis; internal filtering/triage; public narrative prototype. All three executed in this review. None establishes product acceptance or statistical correctness. |

The detailed flow is in [DIAGRAM.md](DIAGRAM.md), with corrections to its claims listed below. A key exception to that diagram: **HLTB prefers `data/merge_mc.csv` if it exists**, only falling back to the cleaned base. That file is still operationally relevant despite being called legacy/debug.

The raw filenames are April 29, while the latest event start is April 30 because the source included announced upcoming giveaways. July commits do not imply July giveaway coverage. “Data through April 30” should distinguish an announcement snapshot from confirmed completed events. No new source scrape was performed for this review.

### What the saved snapshot contains

| Measure | Observed value | Interpretation |
|---|---:|---|
| Cleaned Sheets rows | 806 | Before Wikipedia merge; still includes platform distinctions and source quirks. Not a certified final event count. |
| Canonical rows | 914 | Inflated by the first join. |
| Canonical title groups | 683 | Includes add-ons, bundles, variants, and unresolved aliases. |
| Classified standalone title groups | 606 | Rule-derived; not independently verified. |
| EGS “trusted” matches / priced titles | 550 / 548 | Threshold-or-override acceptance; wrong matches remain. |
| Metacritic named records | 680 | A name being populated is weak evidence of a valid match. |
| Positive MC scores / literal zeros | 548 / 72 | App blanks zeros; canonical tables retain them. |
| HLTB named records / positive main-story times | 550 / 542 | Eight named matches have zero main-story time; meaning needs inspection. |
| Wiki title matches / populated developer fields | 377 / 217 | History-title matching is not the same as successful article enrichment. |

## What was done well

**The canonical build is a real improvement.** Separate event and title-level tables are the right direction. Most recent scripts use plain functions, explicit paths and source prefixes; I can follow the core flow without an elaborate framework. CSV inspection mirrors make the data accessible, and the saved caches allow offline investigation.

**The project retained useful evidence.** Dated xlsx files preserve the colors and layout that a CSV export would lose. Source titles, wiki links, original matching names, EGS IDs, scores and override notes make several failures diagnosable. Keeping unmatched rows through left joins is preferable to silently narrowing the population to easy-to-match games.

**The July corrections improved containment.** Below-threshold EGS guesses no longer leak substantive fields into the exported enrichment. Manual overrides are inspectable in one location and can be reapplied. The HLTB matcher has sequel guards, normalization, retry logic and query provenance, which are materially better than first-result matching.

**The documentation and notebooks provide a useful starting point.** The diagram, dictionary and runnable EDA reduce the cost of returning to the project. Your R notebook's concrete source notes are especially valuable: platform overlap, code meanings, collection quirks, Cat Quest aliases, and accidental giveaways. Those observations are more useful QA inputs than a generic “spot-check the data” task.

The problem is not that the work is worthless or must be rewritten. It is that implementation progress and documentation confidence advanced faster than independent evidence.

## Findings that should change the next work

### 1. Repair source grain before using event statistics

`development/clean_data.py:186` joins the two histories only on normalized title, with no cardinality validation. Wikipedia still has repeated giveaway rows. A title with four Sheets rows and three wiki rows therefore yields twelve combinations.

The effect is substantial: 108 extra rows, **13.4% above the cleaned source count**. Bloons TD 6 expands 4→12; Control 3→9; F.I.S.T. 2→6. For 2019, 69 source rows become 81; for 2022, 103 become 121. The distortion varies by year and title, so it cannot be corrected by scaling a final chart.

This affects cadence, frequency, event-weighted prices/tags/scores and the public app's “Times given” table. The title-level price sum is not multiplied directly by this particular join because the game table collapses titles; it has separate identity problems below.

**Do not fix this with a final `drop_duplicates(title, start, end)`.** There are already 30 repeated title/window keys in the cleaned Sheets data. Inspected examples are distinct PC/mobile rows, including Botany Manor and Eastern Exorcist. Platform and bundle membership belong in the record definition.

A simple repair direction: retain source row identity and platform context; attach one reconciled wiki metadata record per game with `validate="m:1"`; perform giveaway-history agreement as a separate title/date/platform comparison. If both histories are intentionally combined, define event matching explicitly. You should choose the meaning of an event; an engineer should implement row-preservation checks without asking you to approve each merge fix.

### 2. Treat game identity as unfinished across sources

These saved matches warrant correction, not a generic confidence disclaimer:

| Giveaway title | Source | Saved match |
|---|---|---|
| BioShock Remastered | EGS, score 100 | BioShock 2 Remastered |
| BioShock 2 Remastered | Metacritic | Call of Duty: Modern Warfare 2 Campaign Remastered |
| BioShock Infinite: The Complete Edition | Metacritic | The Witcher 3: Wild Hunt - Complete Edition |
| Cat Quest 2 | Metacritic | Cat Quest |
| Cat Quest II | Metacritic | Cat Quest III |
| STALCRAFT: X Edition Starter | Metacritic | Xenoblade Chronicles X: Definitive Edition |

`metacritic_scraper.py:132` takes the first result when no exact lowercase title matches. Some cached “titles” are even `%` or `?`, so extraction validation matters too. Its numerical range checks cannot distinguish an unrelated game's plausible score. The score median and quality-vs-price story are not ready for publication.

`egs_api_enrich.py:317` still uses the maximum of token-set and normalized similarity. A subset can score 100, and `score > best_score` preserves the first tied candidate. The offline test demonstrates that “Example Game Deluxe Edition” can beat a later exact “Example Game.” The July overrides repaired examples without repairing this general behavior. Increasing the cutoff alone will not fix it.

Keep source identifiers and use a small reviewed identity/alias table. Distinguish **same game**, **edition variant**, **bundle containing it**, **successor**, **wrong match**, and **unresolved**. A factual wrong sequel is an engineering correction; accepting a successor edition's price as a proxy is a research decision.

### 3. Reframe the price headline before polishing it

The $12,114.01 total reproduces from saved “trusted” title rows. It does not establish what Epic spent, what users saved, historical giveaway-day value, or a guaranteed lower bound on a non-overlapping library's value.

Three pairs of canonical titles share a trusted EGS offer ID: BioShock Remastered/BioShock 2 Remastered, Cat Quest 2/Cat Quest II, and Evoland 2/Evoland Legendary Edition. They represent different problems: a wrong match, an unresolved alias, and overlapping product content. Deduplicating offer IDs blindly would hide the first problem instead of fixing it.

The current app calls the line “today's store prices” and “conservative”/an “undercount” (`portfolio_explorer.py:292`, `:499`). Prices are cached with no per-record observation date; successor editions are accepted for Trine 4 and Model Builder; title and content overlap can inflate the sum. Missing prices alone do not prove the resulting estimate is conservative.

I recommend a first-release measure such as **“sum of observed US list prices for verified, distinct included products, with coverage and observation dates.”** Decide separately whether related editions may supply metadata, price, or neither. Keep historical acquisition-cost or Epic-expenditure claims out of this metric unless the corresponding data is collected.

### 4. Make validation check the claims, not just plausible values

The existing validator passes the current 914-row dataset with no findings. It checks nonempty tables, title-group counts, some ranges and whether sources contribute anything. It does not compare the event table to source records, check event uniqueness with platform, verify giveaway counts per game, or assess match correctness.

Furthermore, each enrichment loader in `build_dataset.py` silently uses `drop_duplicates(..., keep="first")` before the many-to-one join. Duplicate enrichment keys therefore do not necessarily “raise loudly,” despite the docstrings and diagram. Conflicting records can be discarded before validation sees them. The build's HLTB “matched” count uses whether its first enrichment column is non-null; a populated `False` flag counts as matched.

Useful small checks fit your no-pytest preference: preserve source IDs/counts through metadata joins; verify group totals; reject conflicting identity mappings; prevent below-threshold data leakage; test known wrong sequels and exact-match ties; check date nulls/status and classified platform; compare source coverage before/after a rebuild. Add a small reviewed reference set, not hundreds of implementation-mirroring tests.

There is also a reproducibility boundary: the downstream canonical build and CSV mirrors match exactly, and the app extract matches its documented projection. But reconstructing the initial merge from the saved raw inputs differs in wiki columns. In particular, the saved base has wiki metadata for BioShock 2 Remastered that the current normalization does not match on rebuild. Preserve that example when repairing normalization; do not assume every saved correction is encoded in today's source logic.

### 5. Resolve missing-data meaning in the canonical layer

The 72 literal MC zeros are treated as missing only by `build_app_data.py`. Consequently the public app and canonical EDA use different score populations. The existing review already records these as no-score values. Once source semantics are confirmed, moving that correction into the canonical flow is routine data engineering, not a major user preference.

HLTB's eight zero main-story values need a similar semantic check; a game without a meaningful main-story duration is different from a zero-hour game. HLTB also searches with `HIDE_DLC` even though the source includes DLC. High match coverage is not a sensible universal target for those rows.

Missingness is likely structured by platform, product type, age, edition and source availability. Report coverage within the population actually plotted. “Time to play it all” is too broad for a sum over the subset with usable estimates. Scores characterize the matched/scored subset; they do not by themselves establish an unbiased trend in overall giveaway quality.

### 6. Separate an April snapshot from a reliable refresh process

The scripts have useful caching, but “all scrapers resumable” and “productionized” imply more than the code supports:

- EGS and MC retain failed/no-result entries as processed. HLTB retains blank results as processed too. Ordinary reruns do not retry them just because a temporary problem has passed. Price observations have no expiry policy or timestamp.
- EGS writes the requested title slice to the normal output. `--limit 10` can replace the full enrichment CSV with ten titles; `--refresh --limit 10` also starts a new ten-title cache and saves it over the normal cache. A sample run needs separate output semantics.
- Cache saves overwrite files directly; there is no atomic replacement of a validated complete cache. EGS performs tag lookup even when every title is already cached, so the normal enricher entry point is not fully offline.
- Wiki enrichment re-fetches all titles without per-title checkpointing, then overwrites the rolling intermediate. It is not resumable like the other caches.
- `build_dataset.py:131` relabels **every** `next` record as completed/standard, regardless of date. The synthetic test relabels a 2099 event and says its window has completed. This was a snapshot correction embedded as a permanent rule.
- The Sheets command also initializes the wrapper and runs an API experiment for its first five rows. HLTB prefers the old MC merged file. There is no single documented refresh command that guarantees inputs, caches and public extract belong to the same run.

These are repairable operational gaps, not a call for a workflow platform. Choose whether the next release is a dated research snapshot or an automatically refreshed product; then implement only the reliability that choice requires.

## What actually needs your judgment

The prior conversation is not available as proof of personal approval. I cannot tell from a committed resolution log which choices you approved versus which an agent inferred. The following recommendations are proposals, not new decisions made on your behalf.

| Decision | More useful question | Suggested starting position |
|---|---|---|
| Population | Are the main conclusions about recurring PC game giveaways, or everything the sheet tracks, including mobile, packs, permanent freebies and accidents? | Retain all source rows, publish a clearly defined primary view, and make excluded categories inspectable. A PC-focused main view is reasonable if it matches your original question. |
| Record meaning | Do you want to count promotional windows, product entitlements, component games, or opportunities on each platform? | Keep event/offer identity separate from game identity; expose explicitly named counts. A bundle is one offer that may grant several games. |
| Product equivalence | When may another edition stand in for the original, and for which fields? | Exact product for pricing by default; reviewed aliases for identity; annotate related-edition metadata separately. |
| Research claim | What should a visitor learn: program cadence, variety, ratings, or a hypothetical library's list-price total? | Choose two or three answerable questions. Let them determine which enrichments are worth repairing first. |
| Product experience | Should visitors follow a curated story, ask flexible questions, or both? | Test the existing prototypes against three visitor questions before choosing charts or rebuilding the interface. The latest commit's “unsatisfactory” label remains a valid acceptance signal. |
| Release model | Do you want an honest fixed-date portfolio study first, or a maintained ongoing tracker? | A verified snapshot first reduces simultaneous uncertainties; refresh automation can follow. |

Specific implementation tasks should not be sent back to you as decisions: preventing row multiplication, rejecting unrelated sequels, preserving unknowns, encoding an agreed missing-score rule, retrying transient failures, or repairing stale documentation.

### Reassessing the original A–E questions

| Old item | Fresh assessment |
|---|---|
| A: approve each $0 match | Useful diagnostic examples, poor division of labor. Verify identity and whether the price is usable; ask you only about accepted valuation proxies. Keep the useful overrides. |
| B: approve nulling weak matches | Containing unsupported guesses is routine. The omitted question was whether high scores actually establish identity; the saved BioShock error shows they do not. |
| C: review unmatched titles / decide whether DLC belongs | The population question is real. “Not returned by search” alone does not establish delisting. Keep unmatched rows and separate absence, error, wrong product and unresolved search. Do not make you exhaustively research every unmatched title before cadence analysis can proceed. |
| D: keep/drop/relabel `next` | Ask about announced versus confirmed events and the release cutoff. An unconditional relabel is not a durable solution. |
| E: dismiss publisher disagreements as labels | Reasonable to defer if publishers are not a main question. If you analyze them, define original publisher versus current seller/distributor and preserve both. Sampling a few discrepancies does not settle all the rest. |

The older list understated urgency (“refinements”), while the replacement overstates completion (“all resolved,” “nothing urgent”). The right response is neither to repeat A–E indefinitely nor to accept blanket closure. Replace that agenda with the six definitions above and a bounded evidence review.

## A manageable personal QA session

Start with a 60–90 minute working session; this is orientation and rule-setting, not an expectation that you manually verify 683 titles.

1. **Read your own source notes first**: [development/R_EDA.qmd](development/R_EDA.qmd), especially its import/quality comments. They flag PC/mobile overlap, `dupe3`, Cat Quest 2/II, collections, unusual durations and the accidental Director's Cut offer. Its Hitman starter-pack note also conflicts with the later resolution's 2016-game framing; verify the actual source entitlement rather than treating either note as authoritative.
2. **Inspect the xlsx with its legend and colors**, then a few source-to-output traces: Bloons TD 6, Botany Manor, Eastern Exorcist, the BioShock collection, a Sims/Destiny add-on group, and one ordinary giveaway. Agree on what should be one row and what each count should mean. Keep a source row number in the eventual evidence record.
3. **Review identities, not just low scores**: use the BioShock and Cat Quest mismatches above, Control's publisher-specific override, Evoland overlap, and Trine 4/Model Builder successor matches. Decide the edition/proxy policy; have engineering apply it consistently.
4. **Read the proposed public claims aloud**: “every giveaway,” “today's prices,” “conservative,” “time to play it all,” and “are they any good?” Decide which you could defend from the evidence and which need narrower wording or a different statistic.
5. **Try three visitor tasks**: find a game and its giveaway history; compare like-for-like years; identify a well-reviewed game with a short playtime. Judge whether the app lets a stranger answer them, understand missing data and inspect sources. Do this after enough data repair that obvious bad records do not dominate the session.

The engineering follow-up should turn this into a small reference set: source evidence, expected identity/event interpretation, reason, and approved rule. Include ordinary random examples as well as deliberately difficult cases, and sample accepted high-confidence matches. You need not become the permanent manual matching engine.

## Documentation: what to keep reading, what to distrust

The branch-tip inventory contained **34 distinct documentation blobs** across Markdown, RTF, QMD and bundled RST files. I reviewed the documents and their changed versions, traced the active scripts, and inspected relevant archived application code. The eight archived ipynb files contain no Markdown cells; they are historical code experiments rather than missing narrative specifications. This was not an exhaustive execution of every archived notebook or a fresh verification of every externally linked article.

| Document(s) | How to use them now |
|---|---|
| `README.md` | Good broad purpose, little operational orientation. Needs a quickstart, active branch/release explanation and data cutoff once the flow is accepted. |
| `PROGRESS.md` | Useful chronology, internally contradictory status. It simultaneously says canonical work is unfinished and that a canonical dataset exists; retains 686 and 683 counts; points to removed `egs_api_helpers.py`; calls the initial join adequate. This review's status note takes precedence over those inherited claims. |
| `DIAGRAM.md` | Best navigation aid. Correct its HLTB input, duplicate-detection assurances, blanket resumability claim, and the “Bloons ×12” interpretation during repairs. |
| `DATA_DICTIONARY.md` | Useful field catalog, but its key description says lowercase where the builder preserves case. Wiki event dates/years are carried into the game table via an arbitrary first row, contradicting the claim that all enrichment fields are constant per title. `free`, `other` and `-` should not be conflated as collection membership. |
| `REVIEW_NEEDED.md`, including manual-work version | Valuable issue history, not an independent certificate of truth or your consent. Preserve the evidence behind corrections and reopen the specific assumptions above. |
| `development/R_EDA.qmd` and `outputs/abnormal_gameset.csv` | High-value source notes and edge-case material. The R file still uses missing April 21 inputs and a machine-specific path, so read its annotations rather than expect it to run unchanged. |
| `development/MARIMO_NOTES.md` | Practical implementation guide; installed lock resolves to 0.23.2 here. The project dependency is a minimum version, so retain the frozen lock for reproducibility. |
| `EGS_API_report.md`, `outputs/potential_epic_info.md` | Historical hypotheses, not today's API specification. The report already contains your correction about current free-game listings versus historical giveaways. Its Tiny Tina example blurs two different products, whereas later overrides explicitly separate them. Follow tested code and evidence, not the earlier optimistic recommendation. |
| MC/HLTB feasibility reports | Explain why the sources were added. “Feasible” and early sample success do not establish population-wide matching accuracy. The MC report suggests 2–4 second delays; current code uses 0.1 seconds. |
| `archive/misc/2026-03-Update.md` | An April-state document despite its filename; obsolete dependency and file-location guidance. Useful history. |
| Archived source report | Describes a different Google Sheet ID from the active collector. Do not assume its rich-column claims describe the actual seven-column input. |
| Archived background blog post, original README, RTF brainstorm | Recover your intended questions and chronology. The post contains time-relative counts and market claims needing source/date rechecking before reuse. The brainstorm already asked about tag overlap and useful interactions; it is not a requirement to reproduce every old chart. |
| `AGENTS.md`; bundled wrapper README/RST | Working conventions and API reference. The wrapper actually imports from the uv environment's site-packages, not the copied reference tree. |

Smaller maintainability issues are secondary: mixed exploratory/operational entry points, hardcoded input dates in old helpers, an unused pytest dependency despite the stated preference, and repeated collection logic that can drift. Do not spend the first repair pass reorganizing the archive or adding abstraction layers.

## Suggested next sequence and stopping criteria

1. **Definitions and a small reference set.** Record your population, event and identity choices. Done when the difficult examples above have expected interpretations and ordinary examples are included too.
2. **Source and identity repair.** Stop join multiplication, preserve platform/bundle information, address MC wrong matches and EGS ties, resolve aliases and score missingness. Done when source-to-output traces pass and count changes are explained. Do not impose 806 as a permanent target before source QA.
3. **One coherent offline rebuild.** Build from frozen sources/caches, validate semantic invariants, report usable coverage, regenerate the app extract, update the dictionary/diagram/status. Done when the same inputs reproduce the same accepted records and no display-only correction changes analytical meaning.
4. **Answer two or three research questions.** Choose event-weighted versus unique-game summaries deliberately, identify partial years, separate mobile growth from PC trends, and show missing-data denominators. Defer modeling until the outcome and population are defensible.
5. **Accept or revise the public experience.** Test visitor tasks, empty filters, table/chart agreement and a real browser export. Choose deployment only after that. A new UI framework or another large one-shot visualizer is not the first dependency.

## Verification and limits

The frozen uv environment resolved to Python 3.13.5, pandas 3.0.2 and marimo 0.23.2. Active development Python files passed a Python 3.11 grammar parse; this is not a Python 3.11 runtime test, nor does it validate code stored inside marimo's `_unparsable_cell` strings (one exists in `compartmentalized.py`).

Both canonical tables reproduce exactly from the saved base and enrichment caches. Their CSV mirrors agree, and the public extract agrees with the documented canonical projection. The first raw-source merge has the wiki reproducibility discrepancy described above. Existing validator functions report no findings despite the demonstrated semantic defects.

Static HTML execution exports succeeded for `eda.py`, `explorer.py` and `portfolio_explorer.py`. `spotcheck.py` failed because its API-details input paths are missing; it is not currently a reliable QA entry point. Marimo also reported malformed user configuration at `C:/Users/Malachi/.config/marimo/marimo.toml`, line 26, column 177. That is an environment issue outside this review's repository edits, and did not stop the three successful exports. Export-triggered notebook formatting changes were reverted.

To reproduce the principal offline checks from the repository root:

```powershell
uv run --frozen python outputs/repository_review_checks.py
uv run --frozen python development/validate_dataset.py
```

Local ignored previews were generated at `outputs/review_eda.html`, `outputs/review_explorer.html` and `outputs/review_portfolio.html`. These establish default notebook execution only: interactive filter behavior, visual acceptance, WASM deployment, live endpoint availability and the historical storefront-verification claims were not certified. No datasets or production scripts were deliberately changed, and no site was published.

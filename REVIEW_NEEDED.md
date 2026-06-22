# Review Needed — Human Eyes & Decisions

This is a **stopping point**. The data foundation (Stage 0) and EDA (Stage 1) are built,
validated, and committed. Before Stage 2 (the interactive explorer), a few things genuinely
need *your* judgment — mostly data-quality calls that aren't mechanical. Everything below is
self-contained: the specific items are listed inline.

Nothing here is on fire. The dataset is usable as-is; these are refinements.

---

## How to look at things

```bash
# interactive EDA (best way to explore — has all charts + the Data Issues list at the bottom)
uv run marimo edit development/eda.py

# or a static snapshot you can open in a browser (already generated locally; gitignored)
uv run marimo export html development/eda.py -o outputs/eda.html && open outputs/eda.html

# poke the data directly
uv run python -c "import pandas as pd; g=pd.read_parquet('data/egs_giveaways_by_game.parquet'); print(g.head())"
```

Datasets: `data/egs_giveaways.parquet` (event-level, 914) and
`data/egs_giveaways_by_game.parquet` (game-level, 686). Columns explained in `DATA_DICTIONARY.md`.

---

## Decisions that need you

### A. The 11 `$0`-priced matches  ← highest value, smallest effort
A `$0` retail price on a game that clearly exists (has Metacritic/HLTB data) is either a genuinely
free game or a wrong match. My read is below — **confirm or correct each**:

| Title | EGS match (score) | My read |
|-------|-------------------|---------|
| 3 out of 10, EP 1 | exact (100) | ✅ genuinely free (episodic freebie) |
| 3 out of 10: Season Two | exact (100) | ✅ genuinely free |
| KID A MNESIA EXHIBITION | exact (100) | ✅ genuinely free (art experience) |
| Predecessor | exact (100) | ✅ free-to-play MOBA |
| RAWMEN: Food Fighter Arena | exact (100) | ✅ free-to-play |
| Control | "Control" / pub **Overwolf** (100) | ❌ **wrong** — Control is 505 Games, not Overwolf |
| Hitman | "Hit and Boom" (55.6) | ❌ **wrong** (below threshold) |
| Thimbleweed Park | "Delores: A … mini-adventure" (100) | ❌ **wrong** — matched a free spinoff |
| Train Sim World 2 | "Train Sim World Dev Kit" (93.8) | ❌ **wrong** — matched the free dev kit |
| Borderlands 2 | "Borderlands 2" / 2K (100) | ⚠️ correct title but `$0` for a paid game — verify price |
| Borderlands: The Pre-Sequel | "…Pre-Sequel" / 2K (100) | ⚠️ same — verify price |

**Decision:** which of these to (a) keep as-is, (b) null out the EGS fields as a bad match, or
(c) hand-correct the slug/price. Once you decide, I can apply it (e.g. a small slug-override map in
`egs_api_enrich.py`, or a correction step in `build_dataset.py`).

### B. Low-confidence EGS matches (score < 90)
Most of these are garbage matches where the real game just isn't findable on EGS, and the matcher
grabbed the nearest string. Matches scoring **< 80 do not get deep fields** (dev/tags/desc) and are
flagged `egs_meets_threshold = False`, but they still carry a (usually `$0`) price you may want nulled.

Clearly-wrong (drop/null): `FEZ→Color Fear (30.8)`, `Hob→Bloody Hell Hotel (20)`,
`Hue→688(I) Hunter/Killer (27.3)`, `Pine→Anime Reaper (25)`, `RiME→Dreadful River (33.3)`,
`SIFU/Sifu→Artist Life Simulator (32)`, `Vampyr→Vampire Clans (52.6)`, `Steep→Cube Step (57.1)`,
`Minit→Minigolf Blast (52.6)`, `SOMA→Soar (75)`, `The Fall→Survive the Fall (66.7)`,
`Hitman→Hit and Boom (55.6)`.

Borderline — **these meet the ≥80 threshold so they DID get treated as real**, worth a look:
`ABZÛ→ABZU (85.7)` ✅ likely fine (just the accent), `Evoland 2→Evoland Legendary Edition (87.5)` ✅ likely fine,
`Football Manager 2024→Football Manager 2020 In-game Editor (86.5)` ❌ wrong edition/year,
`The Drone Racing League Simulator→The Drone Racing League® (82.1)` ⚠️ check.

**Decision:** OK to auto-null EGS fields for everything scoring < 80? And fix the two borderline wrong
ones (FM2024, maybe Drone Racing)?

### C. ~122 titles with no EGS match
Mostly **DLC, promo bundles, and in-game unlocks** that aren't standalone store games — almost
certainly *correctly* unmatched. Sample: `Apex Legends™: Ash Free Unlock Bundle`,
`Albion Online - Free Welcome Gift`, `Antstream - Epic Welcome Pack`,
`Borderlands 2 - Commander Lilith & the Fight for Sanctuary`, `Crime Boss … - Dragon's Gold Cup`.
Full list: filter `egs_giveaways_by_game.parquet` where `egs_match_title` is null.

**Decision:** skim for any *standalone game* that was wrongly missed (I don't expect many). These also
raise the broader scope question — **do DLC/bundle/unlock rows belong in the analysis at all**, or
should they be filtered to "real games"? (The `giveaway_type` and `egs_categories` columns can drive that.)

### D. The 2 `next` marker rows
`Firestone Online Idle RPG - Special Offer` and `Oddsparks: An Automation Adventure` (both
`from_date 2026-04-30`) carry `giveaway_type = "next"` — the current/upcoming giveaway at scrape time.
**Decision:** keep, drop, or relabel as standard giveaways.

### E. Publisher disagreements (EGS vs Wikipedia): 95 of 186 comparable
Usually *both* are right (regional labels, parent vs studio, "2K" vs "2K Games"). Probably no action,
but worth eyeballing a handful in the EDA's "Publisher disagreements" cell to confirm it's noise, not a
join bug.

---

## Methodology note to remember
For any **price/tag analysis, filter to `egs_meets_threshold == True`** — it excludes the low-confidence
matches in B. Impact on the headline is negligible (total retail value: `$17,272` all vs `$17,053`
confident-only), but it's the correct habit.

---

## What's already handled (don't worry about these)
- `uv run python development/validate_dataset.py` passes (grain, price/date/score sanity, source coverage).
- All scrapers are **resumable and cached** — re-running fetches ~nothing. EGS enrichment cache:
  `outputs/egs_api_cache.json`; Metacritic: `outputs/metacritic_cache.json`; HLTB: `outputs/hltb_data.csv`.
- The old `Title_gsheets` scraper crash is fixed; caches are in sync with the current schema.
- Source coverage (game-level): Metacritic 683/686, HLTB 553/686, EGS 564/686, Wikipedia 380/686.

## Spot-check recipe (optional confidence pass)
```bash
# eyeball a random sample of matches against what you know
uv run python -c "
import pandas as pd
g = pd.read_parquet('data/egs_giveaways_by_game.parquet')
print(g[g['egs_meets_threshold']==True].sample(15)[['title','egs_match_title','egs_original_price_usd','egs_developer','mc_criticScore']].to_string())
"
```

---

## After you've reviewed
Tell me your calls on A–D and I'll apply them (slug overrides / null-out rules / type filtering), then
we move to **Stage 2 — the interactive explorer** (I'll start with a marimo docs + conventions pass first,
per your note). The deeper analysis (Stage 3) follows that.

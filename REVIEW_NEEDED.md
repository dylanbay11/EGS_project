# Review Log — Resolved July 2026

The A–E data-quality questions this file used to hold are **resolved**: every suspect
match was verified against the live EGS storefront (case by case, ~70 titles probed) and
the corrections are applied in the pipeline. This file now records the decisions and the
few things still worth human eyes. The original questions live in git history
(`git show b6e4f92:REVIEW_NEEDED.md`).

## Decisions applied

### A. The `$0`-priced matches
- **Genuinely free, kept as-is**: 3 out of 10 EP 1 / Season Two, KID A MNESIA
  EXHIBITION, Predecessor, RAWMEN (the only $0 matches remaining in the data).
- **Wrong matches, re-pinned to the correct listing** (via `MANUAL_OVERRIDES` in
  `egs_api_enrich.py`): Control ($29.99 — rank-1 hit was an unrelated Overwolf app),
  Thimbleweed Park ($19.99 — was the free Delores spinoff).
- **Real product delisted, forced unmatched**: Hitman (2016; today's World of
  Assassination SKUs are different products), Train Sim World 2 (only TSW6 remains).
- **Correct match, bogus price**: Borderlands 2 and Borderlands: The Pre-Sequel — the
  store itself reports $0 at the *offer* level (no longer individually purchasable).
  Match kept, price nulled, noted in `egs_notes`.

### B. Low-confidence matches (score < 80)
All verified as garbage matches for games that are **genuinely absent from EGS search**
(FEZ, Hob, Hue, Pine, RiME, Sifu, Vampyr, Steep, Minit, SOMA, The Fall). Rule applied:
below-threshold matches keep provenance columns (match title/score/flag/notes) but every
substantive field (price, seller, dates, tags, …) is **nulled in the output**. The cache
keeps the raw guess. Exception: Model Builder was re-pinned to its Complete Edition
re-release (original delisted).
Borderline cases: ABZÛ→ABZU and Evoland 2→Legendary Edition confirmed fine; The Drone
Racing League Simulator confirmed correct (the listing's slug is
`the-drone-racing-league-simulator`); Football Manager 2024 (and 2020) forced unmatched —
FM main games aren't on EGS, the matcher was grabbing the FM2020 in-game editor DLC.

### B+. Token-subset audit (new, not in the original list)
`token_set_ratio` scores 100 whenever the giveaway title's words are a subset of a longer
candidate — an audit of all "confident" matches caught 8 more wrong matches the original
review missed, all re-pinned: **Rogue Legacy** (was an Assassin's Creed DLC!), The Bridge,
Thief (forced unmatched), Vampire Survivors, MudRunner, Stories Untold, Tiny Tina's
Wonderlands, Ghostwire: Tokyo, Shenmue III, Hand of Fate 2. Harmless edition-variant
matches (HUMANKIND Standard, Just Cause 4 Reloaded, Styx Deluxe, Mechanicus Standard,
Broken Sword Reforged) were left alone.

### C. The 122 unmatched titles
Skimmed all of them; the standalone-looking ones were probed against the live API.
Verdict: "no search results" almost always means **delisted from the EGS catalog**
(Little Nightmares, KOTOR I/II, Knockout City, Cultist Simulator, Horizon Chase Turbo, …),
not a matcher failure. Five were recoverable via cleaned-up queries and are now matched:
The Dungeon of Naheulbeuk (store dropped the subtitle), Encased, Bad North (Jotunn
Edition = free-update rename), Tormentor❌Punisher (store spells it "x"), Trine 4
(Definitive Edition re-release).
Scope decision: DLC/pack/unlock rows **stay in the dataset**, and a derived
`is_standalone_game` flag (606 games / 77 add-on titles) distinguishes playable games
(bundles of full games count) from in-game content. Filter on it for "real games"
analyses.

### D. The 2 `next` marker rows
Both windows (Apr 30 – May 7, 2026) completed long ago — relabeled to standard at build
time, with `was listed as upcoming ('next') at scrape time` appended to `notes`.

### E. Publisher disagreements (95 of 186)
Sampled — confirmed label noise, not a join bug: same company under different labels
(KRAFTON, Inc./Krafton, Plaion/Deep Silver, Tripwire Presents/Tripwire Interactive) or
store-publisher vs. original-publisher (Rogue Legacy: Ubisoft was actually a *wrong
match*, caught in B+ above and fixed). No action on the rest.

### Bonus: case-variant duplicate titles
`SIFU`/`Sifu`, `ARK`/`Ark: Survival Evolved`, `Remnant: From The/the Ashes` were splitting
one game into two "unique" titles. Folded via `CANONICAL_TITLES` in `build_dataset.py`;
game count went 686 → 683 (ARK now correctly shows 4 giveaways).

## Updated headline numbers
- Confident EGS matches: 550/683 titles. Total retail value (confident): **$12,114**;
  confident + standalone games only: **$12,079**. (The old $17k figure was inflated by
  the wrong matches and add-on prices removed above.)
- Methodology habit unchanged: filter price/tag analyses to `egs_meets_threshold == True`
  — and now also `is_standalone_game == True` for "real games" questions.

## Still worth human eyes (nothing urgent)
- **Wiki footnote artifacts**: some `*_wiki` credit fields carry junk like
  `13AM Games, [, a, ]` — a cleanup pass in `enrich_wiki_data.py` would fix it.
- **Metacritic matcher is unaudited**: it takes the first search result with no
  threshold (see DIAGRAM.md stage-4 table). The EGS audit caught wrong matches at 100 —
  Metacritic likely has some too. A similar plain-ratio audit would be cheap.
- **Delisted-game enrichment**: product pages sometimes still exist for delisted games
  (e.g. `borderlands-2` works) even when search fails. A slug-guess fallback could
  recover dev/publisher/description (no price) for some of the 122 unmatched — only if
  that metadata turns out to matter for the analysis.

# Comparison: Gaby Ferreira's Epic giveaway analysis

Reviewed 2026-09-10.

Sources:

- [Medium article](https://medium.com/@gabyferreirabusiness/i-paid-60-for-a-game-epic-later-gave-away-for-free-so-i-analysed-600-of-their-free-games-93002c7645f3)
- [Article's GitHub project](https://github.com/gabyferreira/epic-games-savings-analysis)
- Local context: `PROJECT_REVIEW.md`, `outputs/egdata_comparison.md`, `DATA_DICTIONARY.md`

## Short verdict

This is meaningful overlap, but not a reason to abandon the project.

The article occupies the same broad territory: a seven-year Epic giveaway corpus, launch/list
price value, release-to-giveaway lag, publisher summaries, ratings, and sequel timing. Its public
story is concise and effective. A generic version of “I collected every Epic free game and made
some charts” would now be too similar to pursue as the main contribution.

The stronger opening for this project is different: a transparent, source-reconciled analysis of
how the giveaway programme changed and what kind of library it created, with definitions that a
visitor can inspect and switch. The distinctive work is the evidence layer and the analysis
product, not another scraper or another total-value chart.

## What the article/project does

The article presents:

1. A personal hook: a €60 purchase later became a free giveaway.
2. A roughly 600-game historical corpus, assembled from a Kaggle starting point and manual checks.
3. Daily tracking for new giveaways via GitHub Actions.
4. Enrichment from CheapShark, Steam, IGDB, and Wikidata, with Levenshtein matching and manual
   cleaning.
5. A small set of memorable claims: about $12.5k of listed launch value, roughly $22.50 average
   launch price, roughly 3.6 years average release-to-free lag, and a 76/100 average rating.
6. Publisher analysis, including a weighted “Generosity Index.”
7. A sequel-promotion test using a 90-day window and an expanded one-year window.
8. A strategic interpretation: free games acquire attention and accounts, while Epic still faces
   retention and ecosystem-feature problems relative to Steam.

The visuals appear to serve the writing rather than act as a standalone application: one chart or
statistic supports each question. That is a good editorial pattern to borrow. The repository also
advertises inflation-adjusted value, seasonality, quality trends, a subscription comparison, and
automated chart/data updates, so the article is only a selected view of the project.

## Overlap: do not make these the headline

These are now crowded or too close to the article to be strong differentiators on their own:

| Idea | Assessment |
|---|---|
| Total list/launch value given away | Direct overlap. Also vulnerable to price-date and edition definitions. |
| Average price and price distribution | Direct overlap; useful as a supporting view only. |
| Number of games / annual totals | Direct overlap with the article and egdata's headline stats. |
| Average critic/user rating | Direct overlap; source and denominator matter more than the chart. |
| Average time from release to giveaway | Direct overlap. A better version would be cohort- and censoring-aware. |
| Publisher leaderboard | Direct overlap, especially a single composite generosity score. |
| “Epic uses giveaways to market sequels” | Direct overlap. The timing test can be improved, but the question is not new. |
| Basic yearly bar charts and a static dashboard | Table stakes now, not a project thesis. |

This does not mean removing these measures. Keep them where they help answer a larger question, but
avoid presenting them as discoveries merely because they have a new chart style.

## What to replicate

### 1. The personal-to-system narrative

The €60-to-free opening gives the analysis a reason to exist. A version suited to this project could
start with a concrete question such as: “If I claimed Epic's games over time, what library did I
actually acquire?” Then move from the personal case to programme-wide evidence.

### 2. One question per visual

The article has a clean rhythm: question, measure, visual, interpretation. The existing dashboard
work can adopt this more deliberately. For example:

- How did the programme change? Cadence, full games versus add-ons, repeats, and release age.
- What library did it create? Unique games, playable hours, quality-adjusted hours, and genre mix.
- How sensitive are the headlines? Toggle event/game, offer/title, content/full-game, PC/mobile,
  and current/list price versus price-at-giveaway.

### 3. A small number of memorable metrics

The article's numbers are easy to repeat. This project should also choose a compact set, but label
each one with its grain, cutoff date, source coverage, and price meaning. A “headline” is only as
trustworthy as those four pieces of context.

### 4. A falsifiable strategic question

The sequel window is a useful model for turning industry folklore into a test. More promising local
questions include whether repeat giveaways concentrate in older catalogues, whether free-game
cadence changed after the first years, and whether the mix of full games and add-ons changed over
time. These can be descriptive first; they should not be presented as causal evidence without a
stronger design.

### 5. An automated refresh loop

Daily tracking is worth copying. The current repository already has rolling raw sources and cached
enrichment, but the refresh contract needs to be made explicit: stable source snapshot, cutoff,
identity reconciliation, validation, and a report of what changed. Automation should produce an
audit trail, not only a new number.

## What this project can do better

### 1. Make grain visible instead of hiding it

The local canonical design already distinguishes event-level and game-level tables. Make that a
first-class user choice. A title, a giveaway occurrence, a distinct giveaway window, an offer, an
edition, and a content pack are not interchangeable. The article's “600 games” framing compresses
these decisions.

The important repair comes first: the independent review found that a title-only Wikipedia join
can expand 806 cleaned Sheet rows to 914. Until that is fixed, local totals should remain
provisional and should not be used to claim superior coverage.

### 2. Use stable offer identity as a reconciliation aid

The article relies heavily on title matching and manual cleaning. Your repository has the same
historical problem in its EGS enrichment, while egdata exposes offer-linked giveaway history and
stable IDs. Use that as a reconciliation source, not as unquestioned truth. Preserve the Sheet,
Wikipedia, Epic, and egdata values side by side so disagreements are inspectable.

This is a stronger data-engineering story than “we used a higher fuzzy-match threshold.”

### 3. Correct the price interpretation

The article is careful to say listed retail value is not Epic's licensing cost, but it still uses
launch/list value as the emotionally salient “savings” measure. The current repository often has a
similar problem: EGS prices are current matched-listing prices, not necessarily historical prices
at the giveaway date.

Use at least two clearly named measures:

- `current_list_price_value`: what the matched listing costs in the saved snapshot;
- `price_at_giveaway_value`: the historical price, only where price-history coverage supports it.

Show coverage and sensitivity. Never call either one Epic's cost or actual consumer savings without
additional evidence.

### 4. Treat data quality as part of the product

The article mentions “a lot of manual cleaning,” but the public story does not make each match,
override, missing value, or edition decision easy to audit. Your repository already has the raw
ingredients: match scores, manual overrides, source links, a data dictionary, validation, and a
triage explorer.

Turn those into a visible “why should I trust this?” surface:

- source and identity used for each row;
- match confidence and override reason;
- what is missing and whether missingness is structural;
- event/game/offer counts under the selected definition;
- a small disagreement queue with before/after values.

That is a real differentiator for a portfolio data project.

### 5. Go beyond average quality

“Average rating 76” is a good article statistic but a weak discovery tool. Your HLTB and rating
fields support a more useful library view: well-reviewed short games, quality-adjusted hours,
long games by genre, and the tradeoff between price, score, and time. Keep the denominator visible,
especially because current coverage is incomplete.

### 6. Replace the single publisher score with decomposed evidence

The article's 70% value / 30% average-price Generosity Index is readable but arbitrary and can
reward different publisher behaviours in opaque ways. Show volume, distinct titles, total value,
median price, repeat rate, catalogue age, and full-game share separately. If a composite remains,
make the weights interactive and show how ranks change.

### 7. Make repeats a subject, not merely a deduplication nuisance

The repository has repeated events and can preserve them explicitly. That enables questions the
article only partly addresses: which titles recur, how long until repeat, do repeats substitute
for new acquisition, and does the repeat mix change by year or platform? This is a good place for
survival-style descriptive analysis, with right-censoring called out for titles that have not yet
repeated.

## Gaps worth filling

### Highest-value gaps

1. **A reconciled historical spine.** Compare distinct offer/windows against egdata through a
   shared cutoff, retaining local provenance and explaining every missing/extra record.
2. **A defensible program-phase analysis.** Define phases such as launch, pandemic expansion,
   stabilization, and recent changes using observed cadence/mix rather than arbitrary labels.
3. **Full games versus content.** Quantify how much of the apparent library/value/hours comes from
   playable standalone games, bundles, mobile items, DLC, and packs.
4. **Contemporaneous value.** Test price-at-giveaway using price history, with explicit coverage;
   compare it to current list price so the “value” story is not time-shifted.
5. **Library utility.** Combine critic score, HLTB, genre, and mode to answer “what could a person
   actually play?” rather than only “what was the nominal price?”
6. **Sensitivity analysis.** Let the same headline change under reasonable definitions. That is more
   intellectually honest and more distinctive than defending one magic total.
7. **Source-disagreement explorer.** Make the messy cases visible. A small, well-explained table of
   wrong matches and definition conflicts may be more valuable than another polished chart.

### Lower-priority or already-covered gaps

- Another EGS catalog scraper: not worth expanding while egdata already covers offer/catalog
  identity, historical giveaways, prices, and related metadata more deeply.
- Another static “all games” gallery: your dashboard prototypes already cover this direction.
- A stronger composite publisher ranking: improve decomposed evidence first.
- Causal claims about Epic's strategy: the available observational data can support patterns and
  hypotheses, not clean causal attribution.

## A practical next release

The best next artifact is a “Giveaway Atlas” with three linked views:

1. **Programme over time:** cadence, full-game share, repeats, release age, price-at-giveaway
   coverage, and publisher concentration by year/phase.
2. **Claimed library:** unique games, playable hours, quality-adjusted hours, genre breadth, and
   short/high-rated discovery, with filters and game history.
3. **Definitions and evidence:** a toggle for event/game/offer grain plus source reconciliation,
   missingness, match confidence, and price semantics.

Use the article's editorial discipline—one question and one clear visual at a time—but make the
underlying uncertainty and definitions a visible feature. That gives the project a recognizable
relationship to the article without making it a clone.

## Bottom line

Borrow the article's hook, scope control, automated refresh, and question-led visuals. Do not make
its headline totals, average lag, publisher leaderboard, or sequel-window result your central
claim. The most defensible contribution here is a reproducible and inspectable account of the
giveaway programme: what changed, what library was created, and how much the answer changes when
the unit, identity, content type, and price definition change.


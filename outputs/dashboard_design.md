# The Giveaway Atlas — second dashboard prototype

Branch: `codex/clean-sample-dashboard`. This is an isolated design iteration;
the canonical datasets, pipeline scripts, and older explorers are unchanged.

## Why this direction

The README frames the project as a portfolio analysis and an interactive viewer.
The archived `streamlit_brainstorm_NEW.rtf` asks for a sidebar, meaningful tags,
ratings, pricing, and game lookup. `PROJECT_REVIEW.md` proposes three useful
visitor tasks: locate a game/history, compare periods, and find a well-reviewed
short game. The existing marimo work and `MARIMO_NOTES.md` provide the best
fit for the user's Python/pandas/Plotly preferences and future personal website.

The second attempt makes exploration the first screen: compact navy typography,
blue chart marks, teal weekend picks, persistent sidebar controls, and a game file
beside the table. This replaces the earlier narrative-first and unfiltered KPI
approach. All four metrics respond to the same filters as the plots and tables.
No framework migration or custom frontend application is required.

- **Discover games:** search, giveaway years, OR genre selection, main-story
  time budget, and minimum critic score. Score versus time shows every game once,
  uses a labeled logarithmic time axis, and distinguishes ≤8-hour / 80+ picks.
  Genre counts retain overlap explicitly. Table selection opens cached metadata,
  full sample history, source links, and matched-record evidence.
- **Giveaway history:** counts game/window pairs, distinguishing first and
  returning appearances in the sample. This deliberately does not pretend that
  a stratified enriched sample estimates the whole program's cadence.
- **Data & methods:** selection, coverage, grain, price meaning, source semantics,
  sample bias, and what remains unverified. These details do not dominate browsing.

The four headline values are games in view, median critic score, median main-story
hours, and median cached USD list price. Defaults are 40, 79, 13.8h, and $19.99.
Price is not historical savings or Epic's investment. Every sampled game has the
fields displayed, but cached name agreement is not independent website verification.

## Run and reproduce

From the repository root:

```bash
uv run python development/build_dashboard_sample.py
uv run marimo run development/dashboard/app.py --port 2719
```

Edit with `uv run marimo edit development/dashboard/app.py`.
The sample builder writes a parquet in `data/`, a JSON browser asset, and audit
evidence; it does not scrape or overwrite canonical data. The source sheet and
canonical input fingerprints are in `outputs/dashboard_sample_report.md`.

```bash
uv run python outputs/dashboard_checks.py
uv run python development/export_dashboard.py
uv run python -m http.server 2720 --bind 127.0.0.1 --directory outputs/dashboard_site
```

The export helper runs marimo from the notebook directory to work around its
0.23.2 relative CSS resolution issue. It checks that CSS and the exact JSON asset
are included, then packages the result into `outputs/dashboard_site.zip`.

## Hosting on a normal website

Unzip the bundle into a static directory on the user's website and serve its
`index.html` over HTTP(S). Keep the `assets/`, `public/`, and other generated files
together. Subdirectory hosting is supported by marimo's notebook-relative asset
loading. A link or ordinary iframe can integrate it into a portfolio page.
Do not publish the nonreactive `dashboard_preview.html` execution snapshot as
the interactive application.

This uses [marimo's standard WebAssembly export](https://docs.marimo.io/guides/wasm/),
with no ChatGPT/Sites dependency. The initial load fetches Python/WASM and packages
from marimo/Pyodide distribution endpoints. This is not a fully offline bundle.
The installed marimo 0.23.2 exporter bundles Pyodide 0.27.7 (confirmed in its
worker bootstrap). The [Pyodide 0.27.7 package set](https://pyodide.org/en/0.27.7/usage/packages-in-pyodide.html)
ships pandas 2.2.3. Notebook PEP 723 metadata selects that version only for
`emscripten`; native runs and all pipeline code retain pandas 3.0+ and the existing
uv lockfile. The dashboard uses dataframe operations compatible with both.

A static export supplies no access control itself. Private staging must use the
chosen host's authentication. No staging host/account has been supplied, and no
remote deployment or repository push has been performed.

## Verification and next iteration

`outputs/dashboard_checks.py` verifies Python 3.11 syntax, docstrings, identity
agreement, positive values, distinct offers/windows, exact sheet row/date
reconciliation, literal title search, OR genres, year boundaries, repeats, and
weekend filtering. It executes the whole marimo notebook in default, empty,
single-game, and history states. Captured results: `outputs/dashboard_checks.txt`.
The static export additionally checks bundled CSS and data equality.

Browser acceptance was subsequently performed in the in-app browser: inspected
the actual layout at its normal narrow viewport, tested native literal search and
the two Alien: Isolation history windows, and ran the exported WebAssembly app.
Verified default metrics, World of Goo row selection, no-result filtering, and
reset to the full sample. First-load package delivery completed; a startup message
now covers the initial runtime download. Empty genre charts show a message instead
of meaningless axes. The native browser logged an upstream marimo drawer
accessibility warning; a full accessibility/device audit remains outside this pass.
The final production host will still need its own delivery/access-control check.

Next, review this working surface with the user, then expand against the repaired
full data contract. Likely follow-ups are program-wide year comparisons and
price distributions once the complete population is trustworthy. Keep snapshot
provenance and distinct event/game grain explicit when switching inputs.

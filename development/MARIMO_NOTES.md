# marimo conventions — pinned to 0.23.2

Working notes for building interactive marimo apps in this repo (e.g. `explorer.py`).
marimo's API drifts between versions, so everything here is checked against the
**installed 0.23.2** (signatures introspected from the package, not guessed). If you bump
the version, re-introspect before trusting this.

```bash
uv run python -c "import marimo as mo; print(mo.__version__)"   # confirm the pin
```

## The one rule that bites everyone: define vs. read across cells
A UI element only drives reactivity if it's **assigned to a global variable**, and you
**read its `.value` in a *different* cell** than the one that created it. Reading `.value`
in the same cell it's defined won't update reactively.

So the app is structured as a little pipeline of cells:
1. **define** the UI elements (one cell, assign each to a global) and display them
2. **derive** the filtered DataFrame in a downstream cell that reads each `.value`
3. **render** charts/tables in further cells that read the derived frame

Display an element by making it the last expression of a cell, or interpolate it into
markdown: `mo.md(f"Year: {year_slider}")`. (3.11-safe f-strings only — no quote reuse.)

## Reactive cell model (the other gotchas)
- Cells form a DAG by variable references, **not** top-to-bottom order. Order cells for
  human reading; marimo runs them in dependency order.
- **No redefining a global** across cells — each name is assigned in exactly one cell.
  (This is why `eda.py` returns values out of cells and takes them as args.)
- Local/throwaway names can be prefixed `_` to keep them cell-private.
- Keep one concern per cell; it makes the reactive graph legible and cheap to recompute.

## UI elements we use (0.23.2 signatures — note the picky bits)
- `mo.ui.dropdown(options, value=None, *, label='', searchable=False, full_width=False)`
  — `options` is a sequence or `{label: value}` dict.
- `mo.ui.multiselect(options, value=None, *, label='', full_width=False)` — `.value` is a
  list. Good for `giveaway_type` and tag pickers.
- `mo.ui.slider(start, stop, step=None, value=None, *, label='', show_value=False, full_width=False)`
  — **`start`/`stop`, not `min`/`max`.**
- `mo.ui.range_slider(start, stop, step=None, value=None, *, label='', show_value=False)`
  — `.value` is a `(low, high)` sequence. Used for year range and price range.
- `mo.ui.switch(value=False, *, label='')` / `mo.ui.checkbox(value=False, *, label='')`
  — `.value` is a bool. The "confident matches only" toggle.
- `mo.ui.number(start=None, stop=None, step=None, value=None, *, label='')` — numeric input.
- `mo.ui.table(data, *, selection='multi', page_size=None, show_download=True, label='')`
  — accepts a DataFrame directly; paginates and gives a download button for free. Prefer
  this over `mo.md` for any row-level table the user will scan/triage.
- `mo.ui.tabs({label: content, ...}, value=None)` — top-level Explore / Triage split.
- Grouping: `mo.ui.array([...])` / `mo.ui.dictionary({...})` when a set of elements is
  built at runtime; `mo.ui.form` / `mo.ui.batch` to gate updates behind a submit button
  (we don't need gating — live filtering is the point).

## Layout & control flow
- `mo.vstack([...])` / `mo.hstack([...])` to arrange elements and outputs.
- `mo.md("...")` for prose; `mo.callout(content, kind=...)` for highlighted notes.
- `mo.stop(predicate, output=None)` — early-out a cell when a guard fails (e.g. an empty
  filtered frame): `mo.stop(df.empty, mo.md("No rows match these filters."))`.

## Plotly in marimo
Plotly is this repo's interactive viz lib. A `plotly.express` figure renders if it's the
last expression of a cell (or inside a `mo.vstack`). Wrap with `mo.ui.plotly(fig)` only if
you need selection events back — we don't, so return the figure directly, exactly as
`eda.py` already does.

## Run / export
```bash
uv run marimo edit development/explorer.py                                  # interactive
uv run marimo export html development/explorer.py -o outputs/explorer.html  # static snapshot
```
`*.html` is gitignored (see root `.gitignore`), so exported snapshots are local-only — a
remote run won't ship the HTML; regenerate it locally to eyeball. The export also doubles
as a **full-execution smoke test**: every cell must run cleanly against the real data for
the export to succeed.

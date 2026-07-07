import marimo

__generated_with = "0.23.2"
app = marimo.App(width="medium", app_title="Seven Years of Free Games")


@app.cell
def _():
    # The public-facing portfolio explorer. Unlike development/explorer.py (an
    # internal filter-and-poke workbench), this app is written for a stranger
    # arriving from a reddit/linkedin link: narrative first, hero numbers, a
    # small set of curated charts, one filter row, and a browsable table.
    #
    # Built WASM-first: data loads via mo.notebook_location()/public/ so the
    # same file runs locally (uv run marimo edit/run) and as a client-side
    # `marimo export html-wasm` deploy with no code changes. The data extract
    # is a slim 212 KB CSV cut by development/build_app_data.py — never point
    # this app at the full parquet, pyarrow is not a safe dependency in the
    # browser.
    #
    # marimo wiring follows development/MARIMO_NOTES.md (define UI globals in
    # one cell, read .value downstream). Chart styling follows a validated
    # palette + chrome token set; single-series charts wear the one accent
    # hue, text wears ink tokens, grids are solid hairlines.

    import marimo as mo
    import pandas as pd
    import plotly.express as px
    import plotly.graph_objects as go
    import plotly.io as pio

    return go, mo, pd, pio, px


@app.cell
def _(go, mo, pio):
    # theme tokens (light/dark chosen once per run from the app theme) and a
    # plotly template so every figure inherits the same chrome for free
    _FONT = 'system-ui, -apple-system, "Segoe UI", sans-serif'

    if mo.app_meta().theme == "dark":
        C = {
            "ink": "#ffffff", "sec": "#c3c2b7", "muted": "#898781",
            "grid": "#2c2c2a", "axis": "#383835", "surface": "#1a1a19",
            "accent": "#3987e5", "wash": "rgba(57,135,229,0.12)",
        }
    else:
        C = {
            "ink": "#0b0b0b", "sec": "#52514e", "muted": "#898781",
            "grid": "#e1e0d9", "axis": "#c3c2b7", "surface": "#fcfcfb",
            "accent": "#2a78d6", "wash": "rgba(42,120,214,0.10)",
        }

    _tmpl = go.layout.Template()
    _tmpl.layout = dict(
        font=dict(family=_FONT, size=13, color=C["sec"]),
        paper_bgcolor="rgba(0,0,0,0)",  # blend into the page, no chart "card"
        plot_bgcolor="rgba(0,0,0,0)",
        colorway=[C["accent"]],
        xaxis=dict(
            showgrid=False, linecolor=C["axis"], ticks="outside",
            tickcolor=C["axis"], zeroline=False, automargin=True,
            title=dict(font=dict(color=C["muted"])),
        ),
        yaxis=dict(
            gridcolor=C["grid"], showline=False, zeroline=False,
            automargin=True, title=dict(font=dict(color=C["muted"])),
        ),
        hoverlabel=dict(
            bgcolor=C["surface"], bordercolor=C["grid"],
            font=dict(family=_FONT, size=13, color=C["ink"]),
        ),
        margin=dict(t=16, r=16, b=8, l=8),
        bargap=0.35,
    )
    pio.templates["egs_portfolio"] = _tmpl
    pio.templates.default = "egs_portfolio"

    def style_fig(fig, height=340):
        """Apply shared sizing/mark chrome a template can't carry (height, rounded bar ends)."""
        fig.update_layout(height=height, barcornerradius=4, showlegend=False)
        return fig

    return C, style_fig


@app.cell
def _(mo, pd):
    # load the slim extract; notebook_location() resolves to the notebook dir
    # locally and to the site URL under WASM, so both paths just work
    _path = mo.notebook_location() / "public" / "egs_app_data.csv"
    events = pd.read_csv(str(_path), parse_dates=["from_date"])

    # game grain = first occurrence per title (enrichment is constant within
    # a title, so "first" is a faithful representative)
    _game = events.sort_values("from_date").drop_duplicates("title")

    # hero numbers describe the FULL dataset; the filter row only scopes the
    # explorer sections below it
    N_EVENTS = len(events)
    N_TITLES = int(events["title"].nunique())
    LIBRARY_VALUE = float(
        _game.loc[_game["egs_meets_threshold"], "egs_original_price_usd"].sum()
    )
    HLTB_HOURS = float(_game.loc[_game["is_standalone_game"], "hltb_main_story"].sum())
    MC_MEDIAN = float(_game["mc_criticScore"].median())

    YEAR_MIN = int(events["giveaway_year"].min())
    YEAR_MAX = int(events["giveaway_year"].max())
    DATA_THROUGH = events["from_date"].max().strftime("%B %d, %Y")
    TAG_OPTIONS = sorted(
        _game["egs_tags"].dropna().str.split(", ").explode().str.strip().unique().tolist()
    )
    return (
        DATA_THROUGH,
        HLTB_HOURS,
        LIBRARY_VALUE,
        MC_MEDIAN,
        N_EVENTS,
        N_TITLES,
        TAG_OPTIONS,
        YEAR_MAX,
        YEAR_MIN,
        events,
    )


@app.cell
def _(DATA_THROUGH, mo):
    mo.md(
        """
        # Seven years of free games

        **What the Epic Games Store's giveaway program is actually worth.**

        Since December 2018, the Epic Games Store has given away at least one
        free game almost every single week — a marketing campaign with no real
        precedent in scale or persistence. This page joins a community-tracked
        history of every giveaway with storefront prices, Metacritic scores,
        and HowLongToBeat playtimes, so you can see the whole program at once —
        and dig into any slice of it yourself.

        *Data through {through}. Sources and caveats are at the bottom of the page.*
        """.format(through=DATA_THROUGH)
    )
    return


@app.cell
def _(HLTB_HOURS, LIBRARY_VALUE, MC_MEDIAN, N_EVENTS, N_TITLES, mo):
    # the KPI row: whole-dataset numbers, deliberately NOT affected by filters
    _value = "${:,.0f}".format(LIBRARY_VALUE)
    _hours = "{:,.0f} h".format(HLTB_HOURS)
    mo.hstack(
        [
            mo.stat(value="{:,}".format(N_EVENTS), label="Giveaways", caption="since Dec 2018", bordered=True),
            mo.stat(value="{:,}".format(N_TITLES), label="Unique titles", caption="repeats not counted", bordered=True),
            mo.stat(value=_value, label="Library retail value", caption="confidently priced, one copy each", bordered=True),
            mo.stat(value=_hours, label="Time to play it all", caption="HowLongToBeat main stories", bordered=True),
            mo.stat(value="{:.0f}".format(MC_MEDIAN), label="Median Metacritic", caption="across scored titles", bordered=True),
        ],
        widths="equal", gap=0.75, wrap=True,
    )
    return


@app.cell
def _(TAG_OPTIONS, YEAR_MAX, YEAR_MIN, mo):
    # the single filter row — scopes every chart and table below it
    year_range = mo.ui.range_slider(
        start=YEAR_MIN, stop=YEAR_MAX, step=1, value=(YEAR_MIN, YEAR_MAX),
        show_value=True, label="Years",
    )
    full_games_only = mo.ui.switch(value=False, label="Full games only")
    tag_select = mo.ui.multiselect(options=TAG_OPTIONS, value=[], label="Store tags")
    title_search = mo.ui.text(placeholder="Search titles…", label="Search")
    return full_games_only, tag_select, title_search, year_range


@app.cell
def _(full_games_only, mo, tag_select, title_search, year_range):
    mo.vstack(
        [
            mo.md("## Explore the giveaways"),
            mo.hstack(
                [year_range, full_games_only, tag_select, title_search],
                justify="start", gap=1.5, wrap=True, align="end",
            ),
            mo.md(
                "*Filters apply to everything below them. “Full games only”"
                " hides DLC, add-on packs, and in-game content.*"
            ),
        ]
    )
    return


@app.cell
def _(events, full_games_only, tag_select, title_search, year_range):
    # apply the filter row to the event grain, then re-derive the game grain
    # from the surviving events so every section below agrees on the slice
    ev_f = events

    _ylo, _yhi = year_range.value
    ev_f = ev_f[ev_f["giveaway_year"].between(_ylo, _yhi)]

    if full_games_only.value:
        ev_f = ev_f[ev_f["is_standalone_game"]]

    if tag_select.value:
        _wanted = set(tag_select.value)
        _has_tag = ev_f["egs_tags"].fillna("").apply(
            lambda s: bool(_wanted & {t.strip() for t in s.split(",") if t.strip()})
        )
        ev_f = ev_f[_has_tag]

    if title_search.value.strip():
        ev_f = ev_f[ev_f["title"].str.contains(title_search.value.strip(), case=False, regex=False)]

    gm_f = (
        ev_f.sort_values("from_date")
        .groupby("title", as_index=False)
        .agg(
            giveaway_count=("title", "size"),
            first_giveaway=("from_date", "min"),
            egs_meets_threshold=("egs_meets_threshold", "first"),
            egs_original_price_usd=("egs_original_price_usd", "first"),
            egs_publisher=("egs_publisher", "first"),
            egs_tags=("egs_tags", "first"),
            mc_criticScore=("mc_criticScore", "first"),
            hltb_main_story=("hltb_main_story", "first"),
            is_standalone_game=("is_standalone_game", "first"),
        )
    )
    return ev_f, gm_f


@app.cell
def _(ev_f, gm_f, mo):
    # live summary of the current slice, so filtering always has feedback
    _priced = gm_f.loc[gm_f["egs_meets_threshold"], "egs_original_price_usd"]
    _value = "${:,.0f}".format(float(_priced.sum()))
    mo.md(
        "**{ev:,}** giveaways &nbsp;·&nbsp; **{gm:,}** unique titles"
        " &nbsp;·&nbsp; combined retail value **{val}** in this selection".format(
            ev=len(ev_f), gm=len(gm_f), val=_value
        )
    )
    return


@app.cell
def _(C, ev_f, mo, px, style_fig):
    # ---- chart 1: the cadence ----------------------------------------------
    _hdr = mo.md(
        """
        ### The weekly drumbeat

        Epic settled into a steady one-per-week rhythm early, then started
        stacking multi-game weeks and holiday blitzes on top. *(The first and
        last years are partial — the program launched mid-December 2018, and
        the data snapshot cuts off mid-2026.)*
        """
    )
    if ev_f.empty:
        _out = mo.md("*No giveaways match these filters.*")
    else:
        _per_year = (
            ev_f.groupby("giveaway_year", as_index=False)
            .agg(giveaways=("title", "size"))
        )
        _fig = px.bar(_per_year, x="giveaway_year", y="giveaways", text="giveaways")
        _fig.update_traces(
            textposition="outside", cliponaxis=False,
            textfont=dict(color=C["muted"]),
            hovertemplate="%{x}: %{y} giveaways<extra></extra>",
        )
        _fig.update_xaxes(title=None, dtick=1)
        _fig.update_yaxes(title=None, showgrid=False, showticklabels=False)
        _out = style_fig(_fig, height=300)
    mo.vstack([_hdr, _out])
    return


@app.cell
def _(C, ev_f, go, mo, style_fig):
    # ---- chart 2: cumulative library value ---------------------------------
    _hdr = mo.md(
        """
        ### The free library, priced

        If you had claimed every giveaway from day one, here is what that
        library would cost at today's store prices. Only confidently matched
        store listings are counted, and each title once — so this line is
        conservative.
        """
    )
    _claims = (
        ev_f.sort_values("from_date")
        .drop_duplicates("title")
        .loc[lambda d: d["egs_meets_threshold"] & d["egs_original_price_usd"].notna()]
    )
    if _claims.empty:
        _out = mo.md("*No priced giveaways match these filters.*")
    else:
        _claims = _claims.assign(library_value=_claims["egs_original_price_usd"].cumsum())
        _fig = go.Figure(
            go.Scatter(
                x=_claims["from_date"], y=_claims["library_value"],
                mode="lines", line=dict(width=2, color=C["accent"], shape="hv"),
                fill="tozeroy", fillcolor=C["wash"],
                customdata=_claims[["title", "egs_original_price_usd"]],
                hovertemplate=(
                    "%{x|%b %d, %Y}<br><b>+$%{customdata[1]:.2f}</b> — "
                    "%{customdata[0]}<br>library value $%{y:,.0f}<extra></extra>"
                ),
            )
        )
        # end-dot + direct label on the final value (the number the chart is about)
        _last = _claims.iloc[-1]
        _fig.add_trace(
            go.Scatter(
                x=[_last["from_date"]], y=[_last["library_value"]],
                mode="markers+text",
                marker=dict(size=9, color=C["accent"], line=dict(width=2, color=C["surface"])),
                text=["${:,.0f}".format(float(_last["library_value"]))],
                textposition="top left",
                textfont=dict(color=C["ink"], size=14),
                hoverinfo="skip",
            )
        )
        _fig.update_yaxes(title=None, tickprefix="$", tickformat=",.0f")
        _fig.update_xaxes(title=None)
        _out = style_fig(_fig, height=360)
    mo.vstack([_hdr, _out])
    return


@app.cell
def _(gm_f, mo, px, style_fig):
    # ---- chart 3: price distribution ---------------------------------------
    _hdr = mo.md(
        """
        ### What would they have cost?

        Most giveaways are games in the 10–30 dollar range, but full-priced
        titles show up more often than you might expect.
        """
    )
    _priced = gm_f[gm_f["egs_meets_threshold"] & gm_f["egs_original_price_usd"].notna()]
    if _priced.empty:
        _out = mo.md("*No priced titles match these filters.*")
    else:
        _fig = px.histogram(_priced, x="egs_original_price_usd")
        _fig.update_traces(
            xbins=dict(start=0, size=5),
            hovertemplate="$%{x} retail: %{y} titles<extra></extra>",
        )
        _fig.update_layout(bargap=0.08)
        _fig.update_xaxes(title="retail price (USD)", tickprefix="$")
        _fig.update_yaxes(title=None)
        _out = style_fig(_fig, height=300)
    mo.vstack([_hdr, _out])
    return


@app.cell
def _(C, gm_f, mo, px, style_fig):
    # ---- chart 4: what kinds of games --------------------------------------
    _hdr = mo.md(
        """
        ### What kind of games does Epic give away?

        Store tags per unique title (a game given away twelve times still
        counts once).
        """
    )
    _tags = (
        gm_f["egs_tags"].dropna().str.split(", ").explode().str.strip()
        .value_counts().head(12).reset_index()
    )
    _tags.columns = ["tag", "titles"]
    if _tags.empty:
        _out = mo.md("*No tagged titles match these filters.*")
    else:
        _fig = px.bar(
            _tags.sort_values("titles"), x="titles", y="tag",
            orientation="h", text="titles",
        )
        _fig.update_traces(
            textposition="outside", cliponaxis=False,
            textfont=dict(color=C["muted"]),
            hovertemplate="%{y}: %{x} titles<extra></extra>",
        )
        _fig.update_xaxes(title=None, showgrid=False, showticklabels=False)
        _fig.update_yaxes(title=None, gridcolor="rgba(0,0,0,0)")
        _out = style_fig(_fig, height=380)
    mo.vstack([_hdr, _out])
    return


@app.cell
def _(C, gm_f, go, mo, style_fig):
    # ---- chart 5: quality vs price -----------------------------------------
    _hdr = mo.md(
        """
        ### Are they any good?

        Every dot is one title — hover to identify it. There are genuine
        heavyweights in the free pile, not just bargain-bin filler.
        """
    )
    _scored = gm_f[
        gm_f["mc_criticScore"].notna()
        & gm_f["egs_meets_threshold"]
        & gm_f["egs_original_price_usd"].notna()
    ]
    if _scored.empty:
        _out = mo.md("*No scored titles match these filters.*")
    else:
        _fig = go.Figure(
            go.Scatter(
                x=_scored["egs_original_price_usd"], y=_scored["mc_criticScore"],
                mode="markers",
                marker=dict(
                    size=9, color=C["accent"], opacity=0.85,
                    line=dict(width=2, color=C["surface"]),
                ),
                customdata=_scored[["title", "egs_publisher"]].fillna(""),
                hovertemplate=(
                    "<b>%{customdata[0]}</b><br>Metacritic %{y} · $%{x:.2f}"
                    "<br>%{customdata[1]}<extra></extra>"
                ),
            )
        )
        _fig.update_xaxes(title="retail price (USD)", tickprefix="$")
        _fig.update_yaxes(title="Metacritic score")
        _out = style_fig(_fig, height=400)
    mo.vstack([_hdr, _out])
    return


@app.cell
def _(gm_f, mo):
    # ---- the table: every value in the charts, reachable without hovering --
    _hdr = mo.md(
        """
        ### Browse every title

        The full list behind the charts above — sortable, and downloadable
        with the button in the table header.
        """
    )
    _table = (
        gm_f.sort_values(["giveaway_count", "first_giveaway"], ascending=[False, True])
        .reset_index(drop=True)  # mo.ui.table renders the index; hide the row numbers
        .assign(first_giveaway=lambda d: d["first_giveaway"].dt.strftime("%Y-%m-%d"))
        [
            ["title", "giveaway_count", "first_giveaway", "egs_original_price_usd",
             "egs_publisher", "mc_criticScore", "hltb_main_story", "egs_tags"]
        ]
        .rename(columns={
            "title": "Title",
            "giveaway_count": "Times given",
            "first_giveaway": "First giveaway",
            "egs_original_price_usd": "Retail (USD)",
            "egs_publisher": "Publisher",
            "mc_criticScore": "Metacritic",
            "hltb_main_story": "Main story (h)",
            "egs_tags": "Store tags",
        })
    )
    mo.vstack([_hdr, mo.ui.table(_table, selection=None, page_size=10, show_download=True)])
    return


@app.cell
def _(mo):
    mo.accordion(
        {
            "Where the data comes from": mo.md(
                """
                - **Giveaway history** — a long-running community-maintained
                  spreadsheet tracking every Epic Games Store giveaway since the
                  program began in December 2018.
                - **Prices, publishers, tags** — the Epic Games Store's public
                  storefront API, matched to each title by fuzzy search with
                  manual corrections for the tricky cases.
                - **Critic scores** — Metacritic. **Playtimes** — HowLongToBeat
                  community estimates (main-story column).
                - Pipeline, cleaning decisions, and full data dictionary:
                  [github.com/dylanbay11/EGS_project](https://github.com/dylanbay11/EGS_project).
                """
            ),
            "How “retail value” is computed": mo.md(
                """
                Each title is counted **once** (repeat giveaways add nothing),
                and only when its store listing was matched with high confidence
                — about 550 of the 683 titles. Prices are the **current** full
                store price of that listing, not the price on giveaway day, and
                delisted games can't be priced at all. So the headline value is
                deliberately an *undercount* of what the program has given away.
                """
            ),
            "Known caveats": mo.md(
                """
                - Some giveaways are DLC, add-on packs, or in-game content
                  rather than full games — the **Full games only** filter
                  excludes those (77 of 683 titles).
                - Metacritic and HowLongToBeat matches are automated
                  (first-search-result with fuzzy checks); a small number may be
                  wrong, and unscored/obscure titles are absent, which biases
                  score and playtime summaries toward better-known games.
                - Wikipedia-sourced fields in the underlying dataset are not
                  shown here; see the repo for the full enriched data.
                """
            ),
        }
    )
    return


@app.cell
def _(DATA_THROUGH, mo):
    mo.md(
        """
        ---
        *Data snapshot through {through} · built with
        [marimo](https://marimo.io) and plotly ·
        [Dylan Bay](https://github.com/dylanbay11) 2026*
        """.format(through=DATA_THROUGH)
    )
    return


if __name__ == "__main__":
    app.run()

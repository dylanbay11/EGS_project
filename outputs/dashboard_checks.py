"""Check the sample's analytical contract and execute meaningful dashboard states.

Run ``uv run python outputs/dashboard_checks.py``. Uses saved data only; no
browser automation, live scraping, or changes to the canonical datasets.
"""

import ast
import importlib.util
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent


def main() -> None:
    """Validate identity, source grain, filters, medians, and empty-state execution."""
    for relative in [
        "development/build_dashboard_sample.py", "development/export_dashboard.py",
        "development/dashboard/app.py", "outputs/dashboard_checks.py",
    ]:
        tree = ast.parse((ROOT / relative).read_text(), feature_version=(3, 11))
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name != "_":
                assert ast.get_docstring(node), f"Missing docstring: {relative}:{node.name}"
    print("PASS: Python 3.11 syntax and function docstrings")

    sample = pd.read_parquet(ROOT / "data/dashboard_sample.parquet")
    assert sample.title.nunique() == 40 and len(sample) == 42
    assert not sample.duplicated(["title", "from_date", "to_date"]).any()
    games = sample.drop_duplicates("title").reset_index(drop=True)
    assert not games.duplicated(["egs_namespace", "egs_offer_id"]).any()
    for column in ["mc_title", "egs_match_title", "hltb_game_name", "title_wiki"]:
        actual = sample[column].str.casefold().str.replace(r"[^a-z0-9]", "", regex=True)
        expected = sample.title.str.casefold().str.replace(r"[^a-z0-9]", "", regex=True)
        assert actual.equals(expected), column
    assert sample.mc_criticScore.between(1, 100).all()
    assert sample.hltb_main_story.gt(0).all()
    assert sample.egs_original_price_usd.gt(0).all()
    assert sample.egs_currency.eq("USD").all()
    assert not sample.title.str.contains("BioShock|Cat Quest|Bloons|Evoland", case=False).any()

    raw = pd.read_excel(ROOT / "data/2026-04-29-gsheets.xlsx", skiprows=15)
    for column in raw.columns[:2]:
        raw[column] = pd.to_datetime(raw[column].ffill(), errors="coerce")
    for row in sample.itertuples():
        source = raw.iloc[row.source_sheet_row - 17]
        assert str(source.iloc[5]).strip() == row.title
        assert source.iloc[0] == row.from_date
        assert source.iloc[1] == row.to_date
        assert pd.isna(source.iloc[6])
    print("PASS: 40 identities, 42 unique windows, exact source-sheet row/date reconciliation")

    spec = importlib.util.spec_from_file_location("dashboard", ROOT / "development/dashboard/app.py")
    notebook = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(notebook)
    outputs, definitions = notebook.app.run()
    select = definitions["select_view"]
    events = definitions["events"]
    assert len(definitions["filtered_games"]) == 40
    assert definitions["filtered_games"].mc_criticScore.median() == 79
    assert definitions["filtered_games"].egs_original_price_usd.median() == 19.99
    assert definitions["game_table"].value.iloc[0]["Game"] == "Super Meat Boy"
    print(f"PASS: all {len(outputs)} notebook cells execute; default metrics and selected game agree")

    repeat_events, repeat_games = select(events, (2018, 2025), query="ALIEN: ISOLATION")
    assert len(repeat_events) == 2 and len(repeat_games) == 1
    assert repeat_games.iloc[0].windows_in_view == 2
    later, later_games = select(events, (2021, 2021), query="Alien: Isolation")
    assert len(later) == len(later_games) == 1
    assert later.iloc[0].sample_occurrence == 2
    short_events, short_games = select(events, (2018, 2025), max_hours=8, score_floor=80)
    assert len(short_games) > 0
    assert short_games.hltb_main_story.le(8).all() and short_games.mc_criticScore.ge(80).all()
    assert select(events, (2018, 2025), query="[")[0].empty
    for bounds in [(2018, 2018), (2025, 2025)]:
        year_events, _ = select(events, bounds)
        assert len(year_events) > 0 and year_events.giveaway_year.eq(bounds[0]).all()
    union, _ = select(events, (2018, 2025), selected_genres=["Horror", "Strategy"])
    horror, _ = select(events, (2018, 2025), selected_genres=["Horror"])
    strategy, _ = select(events, (2018, 2025), selected_genres=["Strategy"])
    assert set(union.title) == set(horror.title) | set(strategy.title)
    print(f"PASS: repeats count once per game, year boundaries, literal search, OR genres, {len(short_games)} weekend picks")

    for label, query in [("empty", "no such game exists"), ("single game", "Alien: Isolation")]:
        scoped_events, scoped_games = select(events, (2018, 2025), query=query)
        _, scoped = notebook.app.run(defs={
            "filtered_events": scoped_events, "filtered_games": scoped_games, "select_view": select,
        })
        assert len(scoped["game_table"].value) == (0 if label == "empty" else 1)
        print(f"PASS: complete {label} rendering including charts, table, metrics, and game file")
    assert notebook.app.run(defs={"view_selector": definitions["mo"].ui.tabs({
        "Discover games": "", "Giveaway history": "", "Data & methods": ""
    }, value="Giveaway history")})[1]["view_selector"].value == "Giveaway history"
    print("PASS: history view executes with its independently retained tab state")
    print("Browser/WASM execution and visual layout require a separate acceptance pass.")


if __name__ == "__main__":
    main()

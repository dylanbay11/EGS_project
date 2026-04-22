# AI Agents Rules and Reference

## Role

You are an expert Python data engineer and data analyst strong in both statistics and machine learning, appreciating the strengths of each approach. Your primary task is to assist in scraping, cleaning, and analyzing data, interacting with the Epic Games Store API, and providing visualizations, including interactive ones, of the data along with insightful analysis. 

## Environment

This repo is currently set up with a pinned python 3.13 version, and managed with uv. As such many commands usually should be of the "uv run" variety, and any suggestions for testing should follow that. I do not myself use dedicated formatting or automatic linting tools, but standard PEP8 is usually a safe bet.

## Rules and Best Practices for AI Agents and Code

### Language and formats
Python is preferred. **Never write code that does not work on version 3.11+.** Although the pinned version is 3.13, this is for local convenience, so 3.11 backward compatiblity is a must for future deployments. This repo may eventually involve R, but not currently. Markdown is preferred for documents. Data storage is preferred to be csv for initial data, arrow or parquet for final output only, intermediate data in whatever form is best. 

### Core code principles
You are an engineer who writes code for **human brains, not machines**. You favour code that is simple to understand and maintain. Remember at all times that the code you write will be processed by human brain. The brain has a very limited capacity. People can only hold ~4 chunks in their working memory at once. If there are more than four things to think about, it feels mentally taxing for us. Avoid unnecessary layers of abstractions, jumping between layers of abstractions (like many small methods/classes/modules) is mentally exhausting, linear thinking is more natural to humans. Don't abuse DRY, a little duplication is better than unnecessary dependencies!

### Comments
Don't write "WHAT" comments that just restate the line below, or are otherwise useless or superfluous. Comments are for:

- Bird's-eye overviews: a higher-level description of what a block does
- "WHY" comments: motivation behind a non-obvious choice
- Section markers: brief labels when a function shifts concern

I prefer comments in slightly more casual language. Full sentence comments, go ahead and capitalize, but I prefer in-line and after-line comments especially to start with lower case.

### Functions and returns, classes
- Prefer early returns over nested ifs, free working memory by letting the reader focus only on the happy path only.
- Don't make readers chase behavior up an inheritance chain. Prefer injecting collaborators or using plain functions composed together. 
- Avoid wrappers whose interface is more complex than their implementation, or add a shallow abstraction that mostly adds mental load without extra clarity.

### Python and tabular data (pandas) specifics
- As a reminder, do not write code unless it works in python version 3.11. That means you are strictly forbidden from using Python 3.12+ syntax features, specifically f-string quote reuse and the new type parameter syntax (PEP 695). Do not import modules or functions introduced after 3.11, such as itertools.batched.
- An R/tidy language general philosophy is how the pandas code should read where possible; to emulate that kind of heuristic, method chaining is often preferred over intermediate variable assignment, as long as it still keeps mental load manageable.
- Exceptions should be exceptional — use them for truly unexpected states, not ordinary control flow like "user not found"
- Use self-descriptive values, avoid custom mappings that require memorization.
- Use list/dict/generator comprehensions when they reduce noise — but break them into loops the moment a reader would have to pause
- Prefer | union types and Optional over silent None-returns with no type hint
- A surprising number of bugs come from forgetting that reset_index() wasn't called, or that a groupby left a MultiIndex. Either call **reset_index()** immediately after any operation that changes the index, or add a comment explaining why you're keeping a non-default index. 

### Pandas 3.0 note (CRITICAL)
This repo uses Pandas 3.0+. You must account for breaking changes and utilize new syntax:
- **No Chained Assignment:** It hard errors. Use `.loc` for mutation (e.g., `df.loc[df["col"] > 0, "col"] = 0`).
- **String Dtypes:** Strings are Arrow-backed `str`, not `object`. Checking `dtype == "object"` or `dtype == object` to find strings will break.
- **Tidy Column References:** Use `pd.col()` instead of `lambda` in methods like `.assign()`: `df.assign(name=pd.col("first") + " " + pd.col("last"))`.
- **Anti-Joins:** Use `how="left_anti"` or `"right_anti"` in `pd.merge()` directly instead of manual boolean masking.
- **Arrow:** Prefer `DataFrame.from_arrow()` for zero-copy ingestion over numpy conversions.
- Every indexing operation and method returns a **copy** (semantically). Chained assignment is **broken and silent** — it will not raise an error but will not modify the original DataFrame either. The `mode.copy_on_write` option no longer exists and will be removed in 4.0. Do not reference it.
- With `sort=False`, the result now preserves **input order** (consistent with `Series.value_counts()`). Previously it sorted by row labels. If your code depended on the old label-sorted output, add an explicit `.sort_index()`.

### Package preference
- Pandas for dataframe manipulation
- Plotly for interactive visualizations
- Seaborn for statis visualizations

## Organization of repo

Scripts and code in active development are to be placed in the development folder. 

Recent data and their derived cleaned and/or merged forms are to be placed in the data folder. 

Overview files, such as a PROGRESS.md (an ongoing checklist of TODOs), this file AGENTS.md (to orient best practices), README.md (intended to be user-facing for final release, not currently fully implemented), and similarly-scoped general repo files (such as the EGS_API_report.md which is relevant to current goals) should stay in the repo's root.

Output files, such as test scripts and test outputs, smaller-scale markdown reports, smaller visualizations, etc. are to be placed in the outputs folder. Please note that currently .gitignore includes *.html, so those outputs are purely for the benefit of myself locally for verification. This also means that any remotely executed code html outputs will not transfer via github and will need to be done locally. As this is a small scale project, pytest is overkill. However, data validation is important, and realistic edge cases should be tested.

Temporarily, the entirety of the 'epicstore_api' package source code (which is a wrapper to access the Epic Games Store API itself) is copied in its own epicstore_api folder, because I believe it can serve as a good reference. As a package wrapper it's still imported normally and has auto-generated documentation at https://epicstore-api.readthedocs.io/en/latest/ (or in the internal functions serving as the source).

### Archiving data and code

The archive folder contains code, data, and misc documents from previous versions of this repo. Most of it is for legacy purposes, as I personally dislike digging through old commit histories for deleted files, but some of it especially the scripts and info in misc can occasionally be helpful references for what was preivously tried. 

Also, due to the nature of scraping, new data sources are sometimes cut off and it is good to have fallbacks. However, at some point when the current code/data is stable, the truly old stuff will be deleted and newer stable content will be cycled in. 

Of note is the archive/misc/2026-03-Update.md, which outlines the state of things prior to the current (as of April 2026) development sprint; archive/misc/streamlit_brainstorm_NEW.rtf, which contained a vision for future objectives and visualizations; a trio of files following the pattern archive/code/old_* which contain the 'most recent' of the older generation of visualizations and scraping attempts, including a few gotchas.

### Data freshness

Ideally, I want functionality where it re-scrapes if it's been more than a day since last scrape; one successful previous scrape will be kept (base data). Data scrapes should be named YYYY-MM-DD-sourcetype. It is fine and desirable to keep only a single copy of intermediate tables/datasets. 
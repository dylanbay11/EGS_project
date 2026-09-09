# Dashboard sample evidence

Built from local caches; no live source verification or pipeline repair implied.

- Output: `data/dashboard_sample.parquet` — 42 title/window records,
  40 distinct games, 2018–2025.
- Eligible pool after source reconciliation: 122 games.
- All included titles agree across EGS, MC, HLTB, and Wikipedia after case and
  punctuation normalization. No words, edition suffixes, or sequel numerals removed.
- Reject entire titles affected by duplicated canonical/source windows, shared
  EGS IDs, conflicting displayed metadata, edition/collection naming, or unmatched
  ordinary source events. Source rows have no notes and only standard/repeat types.
- Positive USD cached list prices, MC critic scores, HLTB main-story hours, store
  tags, publisher, description, and Wikipedia developer/link required.
- Round-robin selection across first-giveaway years, deterministic SHA-256 title
  ordering within year. This is a deliberately enriched design fixture, **not a
  representative sample** for estimating the whole giveaway program.
- History is the 2018–2025 source-backed history for included games only.
  No program-wide cadence, trend, monetary savings, or Epic expenditure claims.
- Price observation dates are unavailable; prices are cached USD list prices,
  not current prices or giveaway-day values. MC platform-specific score selection
  is not recorded. HLTB hours are estimates, not personal completion guarantees.
- `outputs/dashboard_sample_audit.csv` preserves the source Excel row for each
  event and all matched titles/product IDs. This is inspectable evidence of cache
  agreement, not independent certification of the upstream websites.

## Input fingerprints

- `2026-04-29-gsheets.xlsx`: `81096d45c1bfa37b4c03472e8162c93f6c9bc5fb7026e5dcc9e4581c41d8217a`
- `egs_giveaways.parquet`: `3675e011ecf12b459950c5cc8db694b40919200105287a4d45e51acc092a6c38`

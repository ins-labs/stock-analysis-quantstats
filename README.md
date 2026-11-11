# QuantStats: explicit returns CSV risk reports

Public, reviewed, manual GitHub Actions command runner. First case is **756 invented returns**, not a stock, investment recommendation or EGX result. No data provider or broker.

## Command and persistent variable

Set repository **Settings > Secrets and variables > Actions > Variables**:

```text
ANALYSIS_COMMAND=python analyze.py --input data/synthetic-returns.csv --metadata data/synthetic-returns.metadata.json --periods-per-year 252 --rf 0 --compounding geometric --output results
```

Then manually run **Explicit returns CSV risk report** on protected `main`. This is a persistent repository Variable, not a transient dispatch input. Updating the variable does not execute it. PR events only install and run tests, never this command. Commands and results are public; never upload secrets, private portfolios or unlicensed inputs.

The parser permits only `python analyze.py` with the documented arguments, using argv with `shell=False`, never eval or shell execution. The variable is executable *configuration* controlled by repository writers. Input paths must be existing `.csv`/`.json` files below `data/` after symlink resolution. Results always go to `results/`. No arbitrary output destination, import, ticker, URL or benchmark argument. For a new dataset, use an issue branch and reviewed PR to add public input and sidecar, then update the variable and manually dispatch after acceptance.

## Financial contract

CSV header exactly `Date,Return`. Each record has an ISO `YYYY-MM-DD` and a **simple fractional return**: `0.01` means +1%, `-0.01` means -1%. This is not a price, a percent number or a log return. Unique strictly increasing dates and finite `-1 < Return < 1` are required. This bounded recipe intentionally refuses bankruptcy/-100%, +100% or larger returns, and leveraged/other series needing a separate policy. It avoids QuantStats' price-versus-return heuristics. No price conversion, split/dividend adjustment, fees, FX, benchmark or rebalancing is inferred.

At least **504 daily observations** are required for this full-report recipe. Blank/missing records, invalid dates, duplicate/out-of-order dates and NaN/Infinity are rejected, not cleaned or filled. Gaps in the date sequence are retained as supplied; no exchange-calendar or completeness check is claimed. The fixture uses invented weekdays, not an exchange session calendar.

Sidecar must include nonempty strings: `dataset_kind` (`synthetic`/`market`), `instrument`, `source`, offset-aware `as_of`, IANA `timezone`, `return_type` (exactly `simple_fractional`), `return_basis`, `frequency` (exactly `daily_observations`), `publication_rights`. Every row's date must be on/before as_of in that timezone. Metadata declares provenance; it does not verify a market provider, licensed rights, price adjustments or completeness.

Every command explicitly chooses `--periods-per-year 252` or `365`. The right annualization depends on the supplied observations, not the number of elapsed calendar days. Annual risk-free rate is explicitly **fixed at zero** in v1. Compounding is explicitly **geometric**. No benchmark and `match_dates=False`; no silent leading-row alignment.

The five exported metrics are fractional, not percent-display numbers:

| Metric | Convention |
|---|---|
| total_compounded_return | product(1+r) - 1 |
| cagr_observation_annualized | terminal wealth^(periods_per_year / observation_count) - 1, not elapsed-calendar CAGR |
| annualized_volatility_sample | sample std, ddof=1, times sqrt(periods_per_year) |
| sharpe_rf_zero | arithmetic mean / sample std times sqrt(periods_per_year), annual rf=0; undefined for zero volatility |
| max_drawdown | min(wealth / running peak - 1), including pre-first-return wealth=1 |

Non-finite exported metrics are JSON `null`/CSV blank with an explanation, not zero. Cumulative wealth overflow/underflow refuses the report. Ancillary HTML metrics and plots use pinned QuantStats conventions, not all independently formula-qualified; the five metric fields above have independent scalar tests. The tear sheet can be nondeterministic in generated timestamps/SVG identifiers; fixture and numeric outputs are deterministic within stated numerical tolerances.

## Outputs and evidence

Manual Actions artifact `returns-risk-results-<run_id>` retains 7 days:

- `returns-and-equity.csv`: Date, Return, baseline-1 compounded Wealth and Drawdown.
- `metrics.csv`, `summary.json`, `summary.txt`: five metrics, input and metadata hashes, declared provenance, dates/count, explicit parameters, package versions and financial caveats.
- `tearsheet.html`: self-contained SVG figures from the pinned QuantStats template; its external favicon removed. Fixed title identifies synthetic/market kind. Outbound human-clicked attribution link remains, not a data source.
- `installed-versions.txt`, `source-commit.txt`, `run-id.txt`, `stdout.txt`, `stderr.txt`, `exit-code.txt`: actual host and command evidence. Failed runs may have partial artifacts; only RC0 plus complete accepted outputs qualifies a result.

Runtime disables QuantStats download_returns and yfinance download/Ticker and ordinary socket connect paths. This is defense in depth for the fixed no-benchmark recipe, **not an OS firewall or a general untrusted-code sandbox**. The installation phase needs public package downloads, and yfinance remains a declared upstream dependency even though market fetching is not used.

## Acceptance and safety

1. Source/issue/branch first; independently review exact source head and dependency metadata.
2. Actual approved host PR test run with `pip check`; no authored CI/test/subprocess timeout.
3. Bind required `analyze` check to its observed GitHub Actions App, keep one independent eligible approval, stale dismissal, last-push approval, administrator enforcement, no force pushes/deletions. Do not self-approve or bypass protection.
4. Merge only after source/runtime approval, then dispatch the stored command manually on exact protected main.
5. Inspect artifact originals, hashes, row joins, scalar math, RC and stderr. Open **actual generated HTML** and inspect pixels for readable headings/tables/charts, clipping and completeness. A test pass is not HTML visual acceptance. Do not label the tool qualified until this happens.

Current release source: QuantStats **0.0.86**. See `PROVENANCE.md` and `DEPENDENCIES.json`. Source preparation itself is **not** install, test, manual analysis or visual qualification. No real-market result is claimed by the fixture. New reviewer Write/token repository access requires its own authority; a different repository's grant does not cover this one.

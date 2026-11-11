# Source and qualification provenance

Source prepared 2026-11-11 Africa/Cairo. Status: PREPARED, UNRUN. No project import, compile, test or analysis was executed during source preparation. Do not read source files, a PR or a candidate lock as evidence of an actual analysis result.

## Owning release, not main-branch assumptions

- Current PyPI release observed: QuantStats 0.0.86, Python >=3.10, Apache-2.0.
- Metadata: https://pypi.org/pypi/quantstats/json
- Project: https://pypi.org/project/quantstats/
- Published wheel actually downloaded and SHA256-verified:
  https://files.pythonhosted.org/packages/d8/46/3d9304b888c5e67e00e3ad814e06ab08b21c0386e14ba5d08daceaab9b31/quantstats-0.0.86-py3-none-any.whl
- SHA256: `4cfb157c8228cbb47681d6a81767d465fbc2bdf529643dd7e836479d2165efd6`
- Owning published files read directly: `quantstats/reports.py`, `utils.py`, `stats.py`, `report.html`, `__init__.py` and release LICENSE. `UPSTREAM-LICENSE-QuantStats.txt` is the original Apache-2.0 notice. Runner code is separately MIT.
- Upstream source navigation: https://github.com/ranaroussi/quantstats/ and https://github.com/ranaroussi/quantstats/blob/main/quantstats/reports.py . Release wheel, not mutable main, grounds wrapper decisions.

Release implementation findings:

- reports.html takes returns, benchmark=None, rf, compounded, periods_per_year, output and template_path; absent output can invoke browser/notebook behavior. We supply the file explicitly and no benchmark.
- `_prepare_returns` can reclassify an all-nonnegative series with max>1 as prices. `_prepare_prices` uses another heuristic. The explicit bounded return contract avoids both; preparation must preserve the input exactly.
- `to_excess_returns` deannualizes annual rf as `(1+rf)^(1/periods)-1`. v1 intentionally fixes rf=0; no nonzero-rate branch is exposed.
- CAGR accepts rf but intentionally does not subtract it, and uses observed count/periods years. We disclose observation-based annualization, not elapsed calendar years.
- volatility is sample std(ddof=1); Sharpe uses sample std with sqrt(periods) annualization. max_drawdown inserts a baseline for first-period loss. Independent scalar tests compare all five exported metrics.
- HTML template has an external automatic favicon and a human-clicked attribution link. The runner strips the favicon, keeps the link, supplies fixed safe title/series names and only safe generated hash/kind parameters. SVG charts are embedded. It refuses unresolved template placeholders and detected automatic external HTML resources. This is not a hostile-HTML sanitizer.

## Dependency evidence

`DEPENDENCIES.json` records **37 freshly observed current PyPI releases** across runtime/build closure, Python requirements, declared dependencies, exact release filenames, source URLs and SHA256 hashes. For CPython3.12.16 Linux x86_64, all active non-extra declared version constraints were checked against the chosen release versions. Complete closure includes yfinance even though the command does not use network data. No transitive dependency is deliberately suppressed. `requirements.txt` and `requirements-build.txt` pin those versions, not reused pins from another tool.

A metadata-compatible candidate is not an installed or runtime-compatible environment. Actual pip resolution/build/install, `pip check`, imports, tests, manual execution and HTML rendering still need the approved host. Dependency files do not claim wheel availability or runtime compatibility; if the host fails, fix via a reviewed source change, not an unrecorded install workaround. Requirements are version-pinned, not pip `--require-hashes` locked; the provenance file records release file hashes for audit, not a guarantee pip enforced those hashes.

Workflow Actions tag refs independently read from GitHub at source preparation:

- actions/checkout v4 -> `11d5960a326750d5838078e36cf38b85af677262`
- actions/setup-python v5 -> `a26af69be951a213d495a4c3e4e4022e16d87065`
- actions/upload-artifact v4 -> `ea165f8d65b6e75b540449e92b4886f43607fa02`

## First case and limits

`data/synthetic-returns.csv`: 756 invented weekday observations from 2022-01-03 through 2024-11-25. Repeat the 20-value pattern `[-.008,.004,.012,-.006,.003,-.014,.009,.007,-.002,.005,-.011,.006,.001,-.004,.008,.002,-.005,.010,-.003,.004]`, adding `((i//20)%5-2)*.0002` at index i. Fixed decimal format. Not market, EGX, benchmark or exchange-calendar evidence.

The first acceptance command explicitly uses 252 periods/year, annual rf0 and geometric compounding. All dates, input bytes/hashes, declared as_of/source/basis, package versions, command RC and run/source identity must join across actual originals. Supplemental HTML metrics are upstream conventions, not independent acceptance of every formula in the report. Actual HTML pixels must still be inspected after execution.

## Protection and authority

Issue-first branch: `feat/issue-1-returns-reports`; issue #1. Baseline main has review1, stale-review dismissal, last-push approval and administrator enforcement, force pushes and deletion disabled. Required status check must be attached only after its actual GitHub Actions App identity is observed. No eligible reviewer, token scope, approval, merge, successful host run, manual result or visual acceptance is claimed by this source packet. Separate per-repository reviewer access/token expansion is not inferred from another repository's grant.

# Progress

## Done
- All phases in PLAN.md.

## Next
- Nothing planned. Next-step ideas are in the README.

## Blockers
- None.

## Needs Abhiram
- Nothing is blocking. See "What needs me" below for optional checks.

## Morning summary

### What works
- Live load of the county's 311 data from 2021 on, incremental after the first run.
- dbt staging and mart models with data tests and a freshness check.
- SQL analysis, anomaly detection, a findings page, and a Streamlit dashboard with screenshots.
- `scripts/check.sh` passed three times in a row from fresh GitHub clones. CI is green.

### How to run it
- Everything on live data, over an hour the first time: `make all`
- Offline on generated rows, about a minute: `make sample`
- Dashboard, after `make all`: `make dashboard`
- Full check: `scripts/check.sh`

### What needs me
- **The weekly workflow has never run.** `make all`, which it calls, works locally. Its first run has no cache, so it does a full backfill. Start it from the Actions tab to test it.
- **The weekly job commits as github-actions[bot],** not as me. Decide whether that is acceptable. Those commits appear only if the job runs and the numbers change.
- **A full live run from a completely fresh clone was not done.** The live load ran in my working folder, and check.sh uses generated rows in its clones.
- **Check the judgement calls before quoting them:** the request type crosswalk, the batch closure rule, and the hotspot filter. All are in DECISIONS.md.
- **The storm list stops at 2024,** so any later Miami storm counts as unmatched. Add later events to `dbt/seeds/known_events.csv`.
- **Optional clean-up:** delete the local branch `backup/pre-rules`. It holds the earlier unpushed commits and is not on GitHub.

### Resume bullets
All numbers come from RESULTS.md.
- Consolidated 1,927,549 Miami-Dade 311 service requests covering 69 months and 7 source layers into one tested dataset, by building an incremental Python and dbt pipeline on DuckDB that reconciles two incompatible source schemas.
- Quantified service delays and a 35,815-request open backlog, finding Sidewalk requests the slowest at a 374.5-day p90, by writing SQL window-function analyses of time to close, backlog aging and repeat requests.
- Prevented false service-time conclusions, as measured by 14,132 requests in 8 administrative batch closures isolated from close-time metrics, by profiling outliers in live data and flagging same-day clean-up closures.
- Detected 146 anomalous type-weeks, with surges falling in storm windows 23% of the time against 11% of all weeks and 100% recall (26/26) on simulated +100 spikes, by building an STL and z-score model with outlier masking.

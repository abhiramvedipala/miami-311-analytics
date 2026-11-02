# Interview notes

## Phase 1: Ingestion and data model

**What I built**
- A Python loader for the county's ArcGIS 311 layers with keyset paging, retries and incremental upserts into DuckDB.
- A raw, staging and mart structure in dbt: `stg_requests`, `fct_requests`, `dim_request_type`, `dim_neighborhood`.
- dbt tests for keys, relationships, accepted values and freshness.
- A hand-written crosswalk that joins request types across the county's 2024 system change.
- An offline sample generator, so the whole pipeline can run with no network.

**Key decisions**
- *ArcGIS, why not Socrata?* The brief assumed Socrata, but that portal is retired. The ArcGIS layers are the same county data, so I did not need a fallback city.
- *Why filter on created or modified date, not created alone?* A created-date filter never sees an old request being closed, so the backlog would only ever grow.
- *Why ZIP, not municipality?* The source has no neighborhood field, and most rows share one municipality. ZIP is the finest area on all rows.
- *Why store raw rows as JSON?* Both schemas load unchanged and dbt handles the differences. It costs storage, but a schema change cannot break the load.

**Hardest problem**
The data looks like one dataset but is two. On 2024-08-11 the county changed systems: every field was renamed, status codes changed (`LOCKED`, `DUP` and `WIP` became `Closed` and `Open`), and request labels share no taxonomy. Older layers also stopped receiving updates, so their open tickets are not real backlog. I found this by profiling each layer before building, then handled it in staging, the crosswalk and the `is_backlog` flag.

**Likely questions**
1. *How do incremental loads work?* Each layer stores a watermark, the newest created or modified time seen. The next run asks for rows at or after that time, minus a two-day lookback, and upserts them by request id. The watermark is saved only after a layer finishes, so an interrupted load restarts that layer safely.
2. *Why keyset paging instead of offsets?* Each page asks for ObjectId greater than the last one seen. The cost stays flat as the table grows, and rows shifting between requests cannot cause skips or repeats within a stable layer.
3. *How do you handle API failures?* Requests retry with exponential backoff, five attempts in total. ArcGIS can return HTTP 200 with an error in the body, so the code inspects the body too. A status-only check would treat those errors as empty results and silently lose data.
4. *What do your dbt tests catch?* Duplicate or missing keys, orphaned foreign keys, negative durations, and unmapped status values. Unknown statuses become `unknown`, which fails accepted values, so a new source code breaks the build rather than dropping out of metrics.
5. *Why DuckDB rather than a warehouse?* One analyst, one file, no server or account, and fast columnar queries at this size. The trade-off is one writer at a time, so a multi-user setup would move to a warehouse. The dbt models would mostly carry over.

**Files to open**
`src/ingest.py`, `dbt/models/staging/stg_requests.sql`, `dbt/models/marts/fct_requests.sql`, `dbt/seeds/request_type_crosswalk.csv`, `tests/test_ingest.py`

## Phase 2: SQL analysis

**What I built**
- Six questions in `analysis/*.sql`, each stating its question in its first line.
- Median and p90 time to close by type and ZIP, using window functions.
- Month-over-month volume, backlog aging, repeat-request hotspots and weekday/hour seasonality.
- A runner that writes headline findings to `RESULTS.md`, with each section hashed so hand edits fail verification.

**Key decisions**
- *Why p90 as well as median?* The median shows the typical case. The p90 shows how bad slow cases get, which is what generates complaints.
- *Why a 500 closed request minimum?* Without it, a rare type with a few old tickets tops every list.
- *Why measure backlog age at the newest row, not today?* Results stay reproducible and do not drift with the run date.
- *Why not count old-system open rows?* Those layers stopped getting updates, so an open status there may just be stale.

**Hardest problem**
Keeping the numbers honest rather than getting the SQL to run. Time to close only exists for closed requests, which understates waits, especially recently. A partial latest month reads as a collapse in volume. Old-system open rows would inflate the backlog. Each needed an explicit rule, and the first two are stated as limits or handled in the query.

**Likely questions**
1. *Why window functions for the percentiles?* `quantile_cont(...) OVER (PARTITION BY ...)` keeps the row-level input and lets me compute count, median and p90 over one named window. A `GROUP BY` would also work and is what I would use if nothing else needed the window; the ranking on top uses `rank()` either way.
2. *How do you define a repeat request?* The same type at the same rounded coordinates, about 11 metres, within 30 days of the previous one, found with `lag()`. Some repeats are normal, such as bulky waste pickups, so this finds places to investigate rather than proving a failure.
3. *How did you handle time zones?* The source stores UTC epochs. Staging converts to America/New_York, including daylight saving, so hourly patterns reflect local behaviour.
4. *What is the survivorship problem here?* Recent requests that closed quickly appear in the data while slow ones are still open. So recent medians look better than they are. A survival model such as Kaplan-Meier would handle this properly, and that is my next step.
5. *How do you know the SQL is right?* Tests run each query on a small mart with answers known by construction, such as 600 requests taking 1 to 600 days, where the median must be 300.5. Duplicates planted with extreme values prove the filters work.

**Files to open**
`analysis/01_close_time_by_type.sql`, `analysis/05_repeat_hotspots.sql`, `src/run_analysis.py`, `src/results.py`, `tests/test_analysis.py`

## Phase 3: Anomaly detection

**What I built**
- Weekly volume per request type, with an STL seasonal and trend baseline.
- Residual z-scores, flagged at an absolute value of 3.5 or more.
- A plain-English note for each flag, and a match against storms and federal holidays.
- A chance baseline, so the match rate can be judged fairly.
- A validation script that plants spikes in simulated series and measures recall and false flags.

**Key decisions**
- *Why report a chance baseline?* Storm windows and holidays cover a large share of all weeks, so a match rate alone flatters the model. It only means something above the baseline.
- *Why only crosswalked types?* A renamed label creates a false level shift at the system change. I also drop flags within two weeks of that date.
- *Why not IsolationForest or Prophet?* STL is explainable to a non-technical reader as expected versus actual, needs no training, and was what the brief called for.
- *Why load from 2021?* The validation table shows recall rising with history, so I extended the load rather than accept weak detection.

**Hardest problem**
Robust STL hid the biggest spikes, which are the storms I most wanted to find. A very large spike leaks into its week-of-year group on the first pass, the whole group gets zero weight, and STL falls back to the raw value, so the spike becomes "seasonal". A +100 spike was caught while a +200 spike vanished. I found it by testing many spike sizes rather than one. The fix masks outliers with a rolling median, refits, then scores the original series against the clean fit. Masking with the fitted value did not work, because that value was itself polluted.

**Likely questions**
1. *Why not use the standard deviation of the residuals for z?* With only a few yearly cycles, STL fits ordinary weeks almost exactly, so residual spread is too small and everything gets flagged. I estimate noise from the median absolute deviation of week-to-week changes divided by the square root of two, which does not depend on the fit.
2. *How did you validate it with no labels?* I planted spikes at known weeks in simulated series with fixed seeds, then measured recall and false flags by spike size and history length. That tests the method, while the event match checks real data. The numbers are in the validation section of `RESULTS.md`.
3. *What does the match rate tell you?* It tells you how often flags coincide with a listed event, compared with how often any week would by chance. It does not prove cause, and the event list is incomplete, so unmatched flags may still be real.
4. *What are the method's weak spots?* Small spikes near the noise level are often missed, as the validation table shows. A sustained shift goes into the trend rather than being flagged. Low-volume types are skipped.
5. *How would you run this in production?* Score new weeks against a baseline fitted on past data only, because refitting on all data lets future weeks influence past scores. Then route flags to the responsible department and track which ones were useful, so the threshold can be tuned.

**Files to open**
`src/anomaly.py`, `src/validate_anomaly.py`, `tests/test_anomaly.py`, `dbt/seeds/known_events.csv`

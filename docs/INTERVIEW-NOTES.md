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

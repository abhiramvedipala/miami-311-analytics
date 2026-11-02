# Miami-Dade 311 service analytics

I turned Miami-Dade County's public 311 records into a tested pipeline, SQL analysis, anomaly detection and a dashboard.

[![CI](https://github.com/abhiramvedipala/miami-311-analytics/actions/workflows/ci.yml/badge.svg)](https://github.com/abhiramvedipala/miami-311-analytics/actions/workflows/ci.yml)

## Problem

Miami-Dade publishes every 311 service request, but as separate yearly layers with two incompatible schemas. That makes simple questions hard for county managers, journalists and residents: where do people wait longest, what is stuck in the backlog, where do problems keep coming back, and which weeks were truly unusual? This project answers them from one tested dataset.

Plain-language findings are in [docs/findings.md](docs/findings.md).

## Demo

![Overview](docs/overview.png)
![Time to close](docs/time_to_close.png)
![Anomalies](docs/anomalies.png)

## Architecture

```mermaid
flowchart LR
    A[ArcGIS 311 layers] -->|paged, retried, incremental| B[src/ingest.py]
    B --> C[(DuckDB raw)]
    C --> D[dbt staging]
    D --> E[(dbt mart: fct_requests, dim_request_type, dim_neighborhood)]
    E --> F[analysis/*.sql]
    E --> G[src/anomaly.py: STL and z-scores]
    F --> H[RESULTS.md and docs/findings.md]
    G --> H
    E --> I[Streamlit dashboard]
    G --> I
```

The loader pages through the county's layers and upserts rows into a raw DuckDB table as JSON. dbt maps the two source schemas to shared columns in staging, then builds a fact table and two dimensions, with tests that fail the build on bad data. SQL files answer the analysis questions, and the anomaly script scores weekly volumes. Scripts write every reported number to `RESULTS.md`, and the dashboard reads the same mart and the same SQL files.

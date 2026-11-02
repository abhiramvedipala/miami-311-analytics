# Plan

- [x] 0. Setup: git, GitHub repo, `.gitignore`, `.env.example`, Python env, confirm data source
- [ ] 1. Ingestion: paged, retrying, incremental loader into DuckDB; dbt staging, `fct_requests`, `dim_request_type`, `dim_neighborhood`; dbt tests and freshness
- [ ] 2. SQL analysis: `analysis/*.sql` and a script that writes headline findings to `RESULTS.md`
- [ ] 3. Anomaly detection: weekly volume per type, STL baseline, residual z-score flags, top 10 weeks with notes, known-event match rate
- [ ] 4. Dashboard: Streamlit app and 3 Playwright PNG screenshots in `docs/`
- [ ] 5. Automation: GitHub Actions CI and weekly cron, `docs/findings.md`
- [ ] 6. Finish: README, fresh-clone check, `RESULTS.md` from real runs, Morning summary in `PROGRESS.md`, all pushed

PY := .venv/bin/python
DBT := .venv/bin/dbt
DBT_ARGS := --project-dir dbt --profiles-dir dbt
SAMPLE_ENV := DUCKDB_PATH=$${DUCKDB_PATH:-data/sample.duckdb} RESULTS_PATH=$${RESULTS_PATH:-data/sample_RESULTS.md}

.PHONY: setup all sample ingest transform report test dashboard screenshots

# One command: install, download live data, build, analyse.
all: setup ingest transform report

setup: .venv/.ready

.venv/.ready: requirements.txt
	uv venv --python 3.12 --allow-existing .venv
	VIRTUAL_ENV=.venv uv pip install -q -r requirements.txt
	touch $@

ingest: setup
	$(PY) src/ingest.py

transform: setup
	$(DBT) build $(DBT_ARGS)
	$(DBT) source freshness $(DBT_ARGS)

report: setup
	$(PY) src/report_ingestion.py
	$(PY) src/run_analysis.py
	$(PY) src/anomaly.py
	$(PY) src/validate_anomaly.py
	$(PY) src/write_findings.py

# The same pipeline on generated rows: no network, about a minute.
sample: setup
	$(SAMPLE_ENV) $(PY) src/sample_data.py
	$(SAMPLE_ENV) $(DBT) build $(DBT_ARGS)
	$(SAMPLE_ENV) $(DBT) source freshness $(DBT_ARGS)
	$(SAMPLE_ENV) $(PY) src/report_ingestion.py
	$(SAMPLE_ENV) $(PY) src/run_analysis.py
	$(SAMPLE_ENV) $(PY) src/anomaly.py

test: setup
	$(PY) -m pytest -q

dashboard: setup
	.venv/bin/streamlit run dashboard/app.py

# Starts the dashboard on the live database, saves PNGs to docs/, stops it again.
screenshots: setup
	.venv/bin/playwright install chromium
	.venv/bin/streamlit run dashboard/app.py --server.headless true --server.port 8501 & APP=$$!; \
	$(PY) scripts/screenshots.py; STATUS=$$?; kill $$APP; exit $$STATUS

import sys
from pathlib import Path

import duckdb
import pytest

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT / "src"))

FACTS = """
CREATE SCHEMA raw; CREATE SCHEMA mart;
CREATE TABLE raw.service_requests AS SELECT 'data_311_2025' AS source_layer;
CREATE TABLE mart.dim_request_type AS SELECT * FROM (VALUES
    ('p', 'Pothole', true), ('m', 'Mosquito', true)) t(request_type_key, request_type, spans_both_systems);
CREATE TABLE mart.dim_neighborhood AS SELECT * FROM (VALUES
    (33101, '33101 (MIAMI)'), (33102, '33102 (DORAL)')) t(neighborhood_key, neighborhood);
-- 600 potholes taking 1..600 days in 33101, 600 mosquito requests taking 1 day in 33102.
CREATE TABLE mart.fct_requests AS
SELECT 'p' AS request_type_key, 33101 AS neighborhood_key, TIMESTAMP '2025-03-03 09:00:00' + INTERVAL (i) MINUTE AS created_at,
       i::double AS days_to_close, false AS is_duplicate, false AS is_backlog, 25.7 AS latitude, -80.2 AS longitude
FROM range(1, 601) r(i)
UNION ALL
SELECT 'm', 33102, TIMESTAMP '2025-04-30 10:00:00', 1.0, false, false, 25.8 + i / 1000.0, -80.3 FROM range(600) r(i)
UNION ALL  -- Duplicates must not count.
SELECT 'p', 33101, TIMESTAMP '2025-04-30 11:00:00', 9999.0, true, false, 25.7, -80.2 FROM range(5)
UNION ALL  -- Backlog: 10 days old and 400 days old, measured at the newest row.
SELECT 'm', 33102, TIMESTAMP '2025-04-20 10:00:00', NULL, false, true, 25.9, -80.1
UNION ALL
SELECT 'm', 33102, TIMESTAMP '2024-03-26 10:00:00', NULL, false, true, 25.9, -80.0;
ALTER TABLE mart.fct_requests ADD COLUMN is_bulk_close BOOLEAN DEFAULT false;
ALTER TABLE mart.fct_requests ADD COLUMN closed_at TIMESTAMP;
"""


@pytest.fixture
def small_db(tmp_path, monkeypatch):
    """A tiny mart with answers known by construction."""
    path = tmp_path / "small.duckdb"
    con = duckdb.connect(str(path))
    con.execute(FACTS)
    con.close()
    monkeypatch.setenv("DUCKDB_PATH", str(path))
    monkeypatch.setenv("RESULTS_PATH", str(tmp_path / "RESULTS.md"))
    return path

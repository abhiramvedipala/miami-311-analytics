import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

import duckdb

import ingest

ROOT = Path(__file__).parent.parent
DAY_MS = 86_400_000
JAN_2026_MS = 1767244003000  # 2026-01-01 05:06:43 UTC, which is 00:06:43 in Miami


def new_row(number, label="Pothole or Roadway Defect", status="Open", created=JAN_2026_MS, closed=None):
    return (
        "data_311_2026", f"N{number}", created, created,
        json.dumps({
            "Service_Request_Number": f"N{number}", "Subject": label, "Status": status, "Priority": "Standard",
            "Municipality": "MIAMI", "Zip_Code": 33127, "Created_Date": created, "Closed_Date": closed,
        }),
        datetime.now(timezone.utc).replace(tzinfo=None),
    )


def old_row(number, status="OPEN", city="City_of_Cutler_Bay"):
    return (
        "data_311_2023", f"O{number}", JAN_2026_MS, JAN_2026_MS,
        json.dumps({
            "ticket_id": f"O{number}", "issue_type": "POTHOLE", "ticket_status": status, "sr_priority": "EMERGNCY",
            "location_city": city, "zip_code": 33189.0, "ticket_created_date_time": JAN_2026_MS,
        }),
        datetime.now(timezone.utc).replace(tzinfo=None),
    )


def test_models_unify_both_schemas_and_flag_batches(tmp_path, monkeypatch):
    path = tmp_path / "models.duckdb"
    monkeypatch.setenv("DUCKDB_PATH", str(path))
    con = ingest.connect()
    # 250 tickets 100 days old closing on one day form a batch; a lone old closure does not.
    batch_close = JAN_2026_MS + 100 * DAY_MS
    batch = [new_row(i, status="Closed", closed=batch_close) for i in range(250)]
    rows = batch + [
        new_row(1000),
        new_row(1001, status="Closed", closed=JAN_2026_MS + 40 * DAY_MS),
        new_row(1002, status="Closed (Duplicate)", closed=JAN_2026_MS + DAY_MS),
        old_row(1),
        old_row(2, status="DUP"),
    ]
    ingest.upsert(con, rows)
    ingest.save_watermark(con, "data_311_2026", datetime.now(timezone.utc).replace(tzinfo=None))
    con.close()

    dbt = Path(sys.executable).parent / "dbt"
    build = subprocess.run(
        [dbt, "build", "--project-dir", "dbt", "--profiles-dir", "dbt"],
        cwd=ROOT, env=os.environ, capture_output=True, text=True,
    )
    assert build.returncode == 0, build.stdout[-3000:]

    con = duckdb.connect(str(path), read_only=True)
    facts = con.execute("SELECT * FROM mart.fct_requests").df().set_index("request_id")
    types = con.execute("SELECT count(*) FROM mart.dim_request_type").fetchone()[0]
    con.close()

    assert types == 1  # POTHOLE and the new label share one type through the crosswalk
    assert str(facts.loc["N1000"].created_at) == "2026-01-01 00:06:43"  # UTC became Miami time
    assert facts.loc["N1000"].is_backlog
    assert not facts.loc["O1"].is_backlog  # old-system open rows are stale
    assert facts.loc["O1"].municipality == "CUTLER BAY"
    assert facts.loc["O1"].priority == "High"
    assert facts.loc["O2"].is_duplicate
    assert facts.loc["N1002"].is_duplicate
    assert facts.loc["N0"].is_bulk_close
    assert not facts.loc["N1001"].is_bulk_close
    assert round(facts.loc["N1001"].days_to_close) == 40

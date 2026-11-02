import pytest
import requests

import ingest


class FakeResponse:
    def __init__(self, payload):
        self.payload = payload

    def raise_for_status(self):
        pass

    def json(self):
        return self.payload


class FakeSession:
    def __init__(self, payloads):
        self.payloads = list(payloads)
        self.calls = []

    def get(self, url, params, timeout):
        self.calls.append(params)
        item = self.payloads.pop(0)
        if isinstance(item, Exception):
            raise item
        return FakeResponse(item)


def test_retries_http_failures_and_error_bodies():
    session = FakeSession([requests.ConnectionError("down"), {"error": {"code": 500}}, {"ok": True}])
    assert ingest.get_json(session, "url", {}, sleep=lambda _: None) == {"ok": True}


def test_gives_up_after_max_attempts():
    session = FakeSession([{"error": {"code": 500}}] * ingest.MAX_ATTEMPTS)
    with pytest.raises(ValueError):
        ingest.get_json(session, "url", {}, sleep=lambda _: None)


def test_paging_advances_past_last_object_id_until_empty():
    session = FakeSession([
        {"features": [{"attributes": {"ObjectId": 5}}, {"attributes": {"ObjectId": 9}}]},
        {"features": []},
    ])
    pages = list(ingest.fetch_pages(session, "layer", "1=1"))
    assert len(pages) == 1
    assert "ObjectId > 9" in session.calls[1]["where"]


def test_where_includes_modified_rows_and_lookback():
    where = ingest.build_where(ingest.NEW_FIELDS, 1767225600000)  # 2026-01-01 UTC
    assert where == (
        "Created_Date >= TIMESTAMP '2025-12-30 00:00:00' OR Last_Modified >= TIMESTAMP '2025-12-30 00:00:00'"
    )
    assert ingest.build_where(ingest.NEW_FIELDS, None) == "1=1"


def test_selects_new_year_layers_and_skips_old_ones():
    names = ["data_311_2022", "data_311_2023", "data_311_2024_Aug_Dec", "data_311_2031", ingest.OLD_SCHEMA_2024, "other"]
    assert ingest.select_layers(names, 2023) == sorted(
        ["data_311_2023", "data_311_2024_Aug_Dec", "data_311_2031", ingest.OLD_SCHEMA_2024]
    )


def test_incremental_upsert_replaces_instead_of_duplicating(tmp_path, monkeypatch):
    monkeypatch.setenv("DUCKDB_PATH", str(tmp_path / "t.duckdb"))
    con = ingest.connect()
    row = {"Service_Request_Number": "1", "Created_Date": 1, "Last_Modified": 1, "Status": "Open"}
    ingest.upsert(con, ingest.to_records("layer", [row], ingest.NEW_FIELDS, "2026-01-01"))
    ingest.upsert(con, ingest.to_records("layer", [{**row, "Status": "Closed", "Last_Modified": 2}], ingest.NEW_FIELDS, "2026-01-02"))
    assert con.execute("SELECT count(*), max(modified_ms) FROM raw.service_requests").fetchone() == (1, 2)


def test_rows_without_id_are_dropped():
    assert ingest.to_records("layer", [{"Created_Date": 1}], ingest.NEW_FIELDS, "2026-01-01") == []

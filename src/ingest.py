"""Load Miami-Dade 311 requests from ArcGIS into DuckDB (raw.service_requests).

Usage: python src/ingest.py [--full]

The first run backfills every layer. Later runs fetch only rows created or
modified since each layer's watermark, then upsert them by request id.
"""
import argparse
import json
import os
import re
import time
from datetime import datetime, timedelta, timezone

import duckdb
import requests

BASE_URL = "https://services.arcgis.com/8Pc9XBTAsYuxx9Ny/arcgis/rest/services"
START_YEAR = int(os.getenv("START_YEAR", "2021"))
PAGE_SIZE = 1000  # the server's maxRecordCount
MAX_ATTEMPTS = 5
LOOKBACK = timedelta(days=2)  # re-read a little to cover late edits and clock skew

# The county changed 311 systems on 2024-08-11, and the field names changed with it.
OLD_FIELDS = ("ticket_id", "ticket_created_date_time", "ticket__last_update_date_time")
NEW_FIELDS = ("Service_Request_Number", "Created_Date", "Last_Modified")
OLD_SCHEMA_2024 = "311_Service_Requests_-_Miami-Dade_County_-_2024_-_Jan_-_Aug"

DDL = """
CREATE SCHEMA IF NOT EXISTS raw;
CREATE TABLE IF NOT EXISTS raw.service_requests (
    source_layer VARCHAR NOT NULL,
    request_id VARCHAR NOT NULL,
    created_ms BIGINT,
    modified_ms BIGINT,
    attributes JSON NOT NULL,
    loaded_at TIMESTAMP NOT NULL,
    PRIMARY KEY (source_layer, request_id)
);
CREATE TABLE IF NOT EXISTS raw.ingest_state (
    source_layer VARCHAR PRIMARY KEY,
    watermark_ms BIGINT NOT NULL,
    completed_at TIMESTAMP NOT NULL
);
"""


def db_path():
    return os.getenv("DUCKDB_PATH", "data/miami311.duckdb")


def connect():
    path = db_path()
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    con = duckdb.connect(path)
    con.execute(DDL)
    return con


def get_json(session, url, params, sleep=time.sleep):
    """GET with backoff. ArcGIS reports many failures as HTTP 200 with an error body."""
    for attempt in range(1, MAX_ATTEMPTS + 1):
        try:
            response = session.get(url, params=params, timeout=90)
            response.raise_for_status()
            payload = response.json()
            if "error" in payload:
                raise ValueError(f"ArcGIS error: {payload['error']}")
            return payload
        except (requests.RequestException, ValueError) as error:
            if attempt == MAX_ATTEMPTS:
                raise
            print(f"  attempt {attempt} failed ({error}), retrying")
            sleep(2**attempt)


def select_layers(names, start_year=START_YEAR):
    """Pick layers by name, so a new data_311_YYYY layer is picked up automatically."""
    layers = []
    for name in names:
        match = re.fullmatch(r"data_311_(\d{4})(_Aug_Dec)?", name)
        if name == OLD_SCHEMA_2024 or (match and int(match[1]) >= start_year):
            layers.append(name)
    return sorted(set(layers))


def layer_fields(session, layer):
    """Return (id, created, modified) field names for a layer."""
    meta = get_json(session, f"{BASE_URL}/{layer}/FeatureServer/0", {"f": "json"})
    names = {field["name"] for field in meta["fields"]}
    for fields in (NEW_FIELDS, OLD_FIELDS):
        if set(fields) <= names:
            return fields
    raise ValueError(f"{layer}: unrecognised schema {sorted(names)}")


def build_where(fields, watermark_ms):
    if watermark_ms is None:
        return "1=1"
    since = datetime.fromtimestamp(watermark_ms / 1000, timezone.utc) - LOOKBACK
    literal = since.strftime("TIMESTAMP '%Y-%m-%d %H:%M:%S'")
    return f"{fields[1]} >= {literal} OR {fields[2]} >= {literal}"


def fetch_pages(session, layer, where):
    """Yield pages of attribute dicts using keyset paging on ObjectId."""
    last_id = 0
    while True:
        payload = get_json(
            session,
            f"{BASE_URL}/{layer}/FeatureServer/0/query",
            {
                "where": f"({where}) AND ObjectId > {last_id}",
                "outFields": "*",
                "orderByFields": "ObjectId",
                "resultRecordCount": PAGE_SIZE,
                "returnGeometry": "false",
                "f": "json",
            },
        )
        rows = [feature["attributes"] for feature in payload.get("features", [])]
        if not rows:
            return
        yield rows
        last_id = rows[-1]["ObjectId"]


def to_records(layer, rows, fields, loaded_at):
    """Shape API rows for the raw table. Rows without a request id cannot be upserted."""
    id_field, created_field, modified_field = fields
    return [
        (layer, str(row[id_field]), row.get(created_field), row.get(modified_field), json.dumps(row), loaded_at)
        for row in rows
        if row.get(id_field)
    ]


def upsert(con, records):
    con.executemany("INSERT OR REPLACE INTO raw.service_requests VALUES (?, ?, ?, ?, ?, ?)", records)


def save_watermark(con, layer, loaded_at):
    """Only a finished layer gets a watermark, so an interrupted backfill restarts that layer."""
    con.execute(
        """
        INSERT OR REPLACE INTO raw.ingest_state
        SELECT ?, max(greatest(created_ms, coalesce(modified_ms, created_ms))), ?
        FROM raw.service_requests WHERE source_layer = ?
        HAVING count(*) > 0
        """,
        [layer, loaded_at, layer],
    )


def load_layer(con, session, layer, full=False):
    """Load one layer and return the number of rows received."""
    fields = layer_fields(session, layer)
    state = con.execute(
        "SELECT watermark_ms FROM raw.ingest_state WHERE source_layer = ?", [layer]
    ).fetchone()
    where = build_where(fields, None if full or state is None else state[0])
    print(f"{layer}: where {where}")

    received = 0
    loaded_at = datetime.now(timezone.utc).replace(tzinfo=None)
    for rows in fetch_pages(session, layer, where):
        upsert(con, to_records(layer, rows, fields, loaded_at))
        received += len(rows)
        if received % 50000 == 0:
            print(f"  {received:,} rows")
    save_watermark(con, layer, loaded_at)
    print(f"{layer}: received {received:,} rows")
    return received


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--full", action="store_true", help="ignore watermarks and re-read every layer")
    args = parser.parse_args()

    con = connect()
    session = requests.Session()
    services = get_json(session, BASE_URL, {"f": "json"})["services"]
    layers = select_layers(service["name"] for service in services)
    received = sum(load_layer(con, session, layer, args.full) for layer in layers)
    total = con.execute("SELECT count(*) FROM raw.service_requests").fetchone()[0]
    print(f"Received {received:,} rows. raw.service_requests now holds {total:,} rows.")
    con.close()


if __name__ == "__main__":
    main()

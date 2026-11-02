"""Fill raw.service_requests with generated rows so the pipeline runs offline.

Rows use both real source schemas. They are made up: nothing here is a finding.
A flood spike is planted in the week of Hurricane Milton for the anomaly check.

Usage: python src/sample_data.py
"""
import json
import random
from datetime import date, datetime, timedelta, timezone

from ingest import connect, save_watermark, upsert

CUTOVER = date(2024, 8, 11)
FIRST_WEEK = date(2021, 1, 4)
WEEKS = 300
SPIKE_WEEK = date(2024, 10, 7)
TYPES = [  # old label, new label, department, weekly requests, days to close
    ("BULKY TRASH REQUEST BY APPOINTMENT", "Schedule Bulky Waste Pickup", "Solid Waste Management", 30, 12),
    ("MOSQUITO INSPECTION REQUEST", "Mosquito Inspection Request", "Solid Waste Management", 16, 4),
    ("POTHOLE", "Pothole or Roadway Defect", "Transportation and Public Works", 10, 30),
    ("DRAIN CLOGGED / CLEANING", "Flooding or Drainage Issue", "Transportation and Public Works", 8, 45),
    ("DEAD ANIMAL PICKUP MD", "Dead Animal Pickup", "Animal Services", 6, 2),
]
AREAS = [(33157, "UNINCORPORATED MIAMI-DADE"), (33165, "UNINCORPORATED MIAMI-DADE"), (33127, "MIAMI"), (33056, "MIAMI GARDENS")]


def weekly_count(rng, week_index, week_start, base):
    seasonal = 1 + 0.3 * ((week_start.timetuple().tm_yday / 365 * 2 - 1) ** 2)
    spike = 6 if week_start == SPIKE_WEEK else 1
    return max(1, round(base * seasonal * spike * rng.uniform(0.9, 1.1)))


def make_row(rng, number, created, type_row, new_system):
    old_label, new_label, department, _, close_days = type_row
    zip_code, municipality = rng.choice(AREAS)
    is_open = rng.random() < 0.05
    closed = None if is_open else created + timedelta(days=rng.expovariate(1 / close_days))
    created_ms = int(created.timestamp() * 1000)
    closed_ms = int(closed.timestamp() * 1000) if closed else None
    latitude, longitude = 25.75 + rng.uniform(-0.2, 0.2), -80.3 + rng.uniform(-0.1, 0.1)
    if new_system:
        return {
            "Service_Request_Number": f"S-{number}", "Subject": new_label, "Department": department,
            "Status": "Open" if is_open else "Closed", "Priority": "Standard", "Municipality": municipality,
            "Zip_Code": zip_code, "Method_Received": "API - Web", "Created_Date": created_ms,
            "Last_Modified": closed_ms or created_ms, "Closed_Date": closed_ms,
            "Latitude": latitude, "Longitude": longitude, "ObjectId": number,
        }
    city = {"MIAMI": "City_of_Miami", "MIAMI GARDENS": "City_of_Miami_Gardens"}.get(municipality, "Miami_Dade_County")
    return {
        "ticket_id": f"S-{number}", "issue_type": old_label, "case_owner_description": department,
        "ticket_status": "OPEN" if is_open else "CLOSED", "sr_priority": "STANDARD", "location_city": city,
        "zip_code": float(zip_code), "method_received": "WEB", "ticket_created_date_time": created_ms,
        "ticket__last_update_date_time": closed_ms or created_ms, "ticket_closed_date_time": closed_ms,
        "latitude": latitude, "longitude": longitude, "ObjectId": number,
    }


def main():
    rng = random.Random(311)
    loaded_at = datetime.now(timezone.utc).replace(tzinfo=None)
    records = {"sample_old": [], "sample_new": []}
    number = 0
    for week_index in range(WEEKS):
        week_start = FIRST_WEEK + timedelta(weeks=week_index)
        new_system = week_start >= CUTOVER
        layer = "sample_new" if new_system else "sample_old"
        for type_row in TYPES:
            for _ in range(weekly_count(rng, week_index, week_start, type_row[3])):
                number += 1
                created = datetime(week_start.year, week_start.month, week_start.day, tzinfo=timezone.utc) + timedelta(
                    days=rng.randrange(7), hours=rng.randrange(12, 23), minutes=rng.randrange(60)
                )
                row = make_row(rng, number, created, type_row, new_system)
                modified = row.get("Last_Modified") or row.get("ticket__last_update_date_time")
                records[layer].append((layer, f"S-{number}", int(created.timestamp() * 1000), modified, json.dumps(row), loaded_at))
    con = connect()
    con.execute("DELETE FROM raw.service_requests")
    for layer, rows in records.items():
        upsert(con, rows)
        save_watermark(con, layer, loaded_at)
    print(f"Wrote {number:,} sample rows")
    con.close()


if __name__ == "__main__":
    main()

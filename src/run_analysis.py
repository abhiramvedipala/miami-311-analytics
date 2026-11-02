"""Run every analysis/*.sql and write headline findings to RESULTS.md.

Usage: python src/run_analysis.py
"""
from pathlib import Path

from ingest import connect
from results import data_source, write_section

ANALYSIS_DIR = Path(__file__).parent.parent / "analysis"


def question(path):
    return path.read_text().splitlines()[0].removeprefix("-- Question: ")


def run_all(con):
    """Return {file stem: dataframe} for every analysis file."""
    return {path.stem: con.execute(path.read_text()).df() for path in sorted(ANALYSIS_DIR.glob("*.sql"))}


def build_body(frames):
    areas = frames["02_close_time_by_neighborhood"].head(3)
    types = frames["01_close_time_by_type"]
    backlog = frames["04_backlog_aging"]
    worst = types.iloc[0]
    busiest = frames["06_weekday_hour"].sort_values("requests", ascending=False).iloc[0]
    months = frames["03_monthly_volume"]
    batches = frames["07_bulk_closures"]

    area_rows = "\n".join(
        f"| {row.neighborhood} | {row.median_days} | {row.p90_days} | {row.closed_requests:,} |"
        for row in areas.itertuples()
    )
    backlog_rows = "\n".join(
        f"| {row.age_bucket} | {row.open_requests:,} | {row.share_pct}% |" for row in backlog.itertuples()
    )
    return f"""
- Backlog (open new-system requests): **{int(backlog.open_requests.sum()):,}**
- Worst p90 type: **{worst.request_type}**, {worst.p90_days} days at p90 and {worst.median_days} at median ({worst.closed_requests:,} closed requests)
- Busiest slot: {busiest.weekday} at {busiest.hour}:00 Miami time ({busiest.requests:,} requests)
- Batch closures left out of close times: {int(batches.requests.sum()):,} requests across {len(batches)} type-days
- Complete months covered: {len(months)}; highest {months.requests.max():,}, lowest {months.requests.min():,}

3 slowest neighborhoods by median days to close (at least 500 closed requests):

| Neighborhood | Median days | P90 days | Closed requests |
|---|---|---|---|
{area_rows}

Backlog aging:

| Age | Open requests | Share |
|---|---|---|
{backlog_rows}
"""


def main():
    con = connect()
    frames = run_all(con)
    for path in sorted(ANALYSIS_DIR.glob("*.sql")):
        print(f"{path.stem}: {question(path)} ({len(frames[path.stem])} rows)")
    write_section("analysis", build_body(frames), "python src/run_analysis.py", data_source(con))
    con.close()


if __name__ == "__main__":
    main()

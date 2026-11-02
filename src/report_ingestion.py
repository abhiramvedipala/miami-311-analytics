"""Write row counts and date coverage to RESULTS.md. Usage: python src/report_ingestion.py"""
from ingest import connect
from results import data_source, write_section


def build_body(con):
    raw = con.execute("SELECT count(*) FROM raw.service_requests").fetchone()[0]
    fact, first, last, months = con.execute(
        """
        SELECT count(*), min(created_at)::date, max(created_at)::date,
               count(DISTINCT date_trunc('month', created_at))
        FROM mart.fct_requests
        """
    ).fetchone()
    layers = con.execute(
        "SELECT source_layer, count(*) FROM raw.service_requests GROUP BY 1 ORDER BY 1"
    ).fetchall()
    rows = "\n".join(f"| {layer} | {count:,} |" for layer, count in layers)
    return (
        f"- Raw rows loaded: **{raw:,}**\n"
        f"- Unique requests in `mart.fct_requests`: **{fact:,}**\n"
        f"- Coverage: {first} to {last} ({months} calendar months)\n\n"
        f"| Source layer | Rows |\n|---|---|\n{rows}\n"
    )


def main():
    con = connect()
    write_section("ingestion", build_body(con), "make all", data_source(con))
    con.close()


if __name__ == "__main__":
    main()

"""Miami-Dade 311 dashboard. Usage: streamlit run dashboard/app.py"""
import os
from pathlib import Path

import altair as alt
import duckdb
import streamlit as st

DB_PATH = os.getenv("DUCKDB_PATH", "data/miami311.duckdb")
ANALYSIS_DIR = Path(__file__).parent.parent / "analysis"
TOP_N = 15


def query(sql, params=None):
    con = duckdb.connect(DB_PATH, read_only=True)
    try:
        return con.execute(sql, params or []).df()
    finally:
        con.close()


def analysis(name):
    return query((ANALYSIS_DIR / f"{name}.sql").read_text())


def bar_chart(frame, label, title):
    """Horizontal bars of median days, with p90 alongside in the table below."""
    chart = (
        alt.Chart(frame.head(TOP_N))
        .mark_bar()
        .encode(
            x=alt.X("median_days:Q", title="Median days to close"),
            y=alt.Y(f"{label}:N", sort="-x", title=None, axis=alt.Axis(labelLimit=320, labelOverlap=False)),
            tooltip=[label, "median_days", "p90_days", "closed_requests"],
        )
        .properties(title=title, height=TOP_N * 24)
    )
    st.altair_chart(chart, width="stretch")


st.set_page_config(page_title="Miami-Dade 311", layout="wide")
st.title("Miami-Dade 311 service requests")

overview, close_times, backlog, anomalies = st.tabs(["Overview", "Time to close", "Backlog", "Anomalies"])

with overview:
    kpis = query(
        """
        SELECT count(*) AS requests, count(*) FILTER (is_backlog) AS open_requests,
               median(days_to_close) FILTER (NOT is_bulk_close) AS median_days,
               quantile_cont(days_to_close, 0.9) FILTER (NOT is_bulk_close) AS p90_days,
               strftime(min(created_at), '%Y-%m-%d') AS first_day, strftime(max(created_at), '%Y-%m-%d') AS last_day
        FROM mart.fct_requests WHERE NOT is_duplicate
        """
    ).iloc[0]
    columns = st.columns(4)
    columns[0].metric("Requests", f"{int(kpis.requests):,}")
    columns[1].metric("Open backlog", f"{int(kpis.open_requests):,}")
    columns[2].metric("Median days to close", f"{kpis.median_days:.1f}")
    columns[3].metric("P90 days to close", f"{kpis.p90_days:.1f}")
    st.caption(f"Requests created {kpis.first_day} to {kpis.last_day}. Duplicates excluded; close times also exclude batch clean-up closures.")
    monthly = analysis("03_monthly_volume")
    st.altair_chart(
        alt.Chart(monthly)
        .mark_line()
        .encode(x=alt.X("month:T", title=None), y=alt.Y("requests:Q", title="Requests per month"))
        .properties(title="Monthly volume", height=340),
        width="stretch",
    )
    st.caption("The county changed 311 systems on 2024-08-11, so levels before and after are not fully comparable.")

with close_times:
    st.caption("Closed requests only, in groups with at least 500, without batch clean-up closures. Slowest 15 shown.")
    by_type = analysis("01_close_time_by_type").sort_values("median_days", ascending=False)
    by_area = analysis("02_close_time_by_neighborhood")
    left, right = st.columns(2)
    with left:
        bar_chart(by_type, "request_type", "By request type")
    with right:
        bar_chart(by_area, "neighborhood", "By neighborhood (ZIP)")
    st.dataframe(by_type, hide_index=True, width="stretch")

with backlog:
    aging = analysis("04_backlog_aging")
    st.metric("Open requests", f"{int(aging.open_requests.sum()):,}")
    st.altair_chart(
        alt.Chart(aging)
        .mark_bar()
        .encode(
            x=alt.X("age_bucket:N", sort=alt.SortField("sort_key"), title="Age", axis=alt.Axis(labelAngle=0)),
            y=alt.Y("open_requests:Q", title="Open requests"),
            tooltip=["age_bucket", "open_requests", "share_pct"],
        )
        .properties(height=360),
        width="stretch",
    )
    st.caption("New-system requests only: old-system layers stopped receiving status updates.")

with anomalies:
    flags = query(
        """
        SELECT strftime(week_start, '%Y-%m-%d') AS week_start, request_type, round(z, 1) AS z, requests, round(expected) AS expected,
               event, note
        FROM mart.anomalies ORDER BY abs(z) DESC
        """
    )
    st.dataframe(flags, hide_index=True, width="stretch", height=320)
    if flags.empty:
        st.info("No anomalous weeks flagged.")
    else:
        labels = [f"{row.week_start} · {row.request_type}" for row in flags.itertuples()]
        chosen = flags.iloc[labels.index(st.selectbox("Map one flagged week", labels))]
        points = query(
            """
            SELECT facts.latitude, facts.longitude
            FROM mart.fct_requests AS facts
            JOIN mart.dim_request_type AS types USING (request_type_key)
            WHERE types.request_type = ? AND strftime(date_trunc('week', facts.created_at), '%Y-%m-%d') = ?
              AND facts.latitude IS NOT NULL AND facts.longitude IS NOT NULL AND NOT facts.is_duplicate
            """,
            [chosen.request_type, chosen.week_start],
        )
        st.write(chosen.note)
        st.map(points, height=360)

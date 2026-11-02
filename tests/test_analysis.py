import run_analysis
from ingest import connect


def frames():
    con = connect()
    result = run_analysis.run_all(con)
    con.close()
    return result


def test_every_query_states_its_question():
    for path in run_analysis.ANALYSIS_DIR.glob("*.sql"):
        assert path.read_text().startswith("-- Question: ")


def test_close_time_percentiles_and_ranking_exclude_duplicates(small_db):
    types = frames()["01_close_time_by_type"]
    worst = types.iloc[0]
    assert worst.request_type == "Pothole"
    assert worst.closed_requests == 600
    assert worst.median_days == 300.5
    assert worst.p90_days == 540.1


def test_slowest_neighborhood_comes_first(small_db):
    assert frames()["02_close_time_by_neighborhood"].iloc[0].neighborhood == "33101 (MIAMI)"


def test_backlog_buckets_use_age_at_newest_row(small_db):
    backlog = frames()["04_backlog_aging"]
    assert dict(zip(backlog.age_bucket, backlog.open_requests)) == {"0-30 days": 1, "Over 365 days": 1}


def test_partial_latest_month_is_dropped(small_db):
    con = connect()
    con.execute("INSERT INTO mart.fct_requests SELECT 'm', 33102, TIMESTAMP '2025-05-02 10:00:00', 1.0, false, false, 25.0, -80.0")
    months = run_analysis.run_all(con)["03_monthly_volume"]
    con.close()
    assert str(months.month.max())[:7] == "2025-04"


def test_repeats_within_30_days_are_counted_at_one_point(small_db):
    top = frames()["05_repeat_hotspots"].iloc[0]
    assert top.request_type == "Pothole"
    assert top.repeats_within_30_days == 599


def test_weekday_hour_uses_busiest_slot(small_db):
    busiest = frames()["06_weekday_hour"].sort_values("requests", ascending=False).iloc[0]
    assert busiest.weekday == "Wednesday" and busiest.hour == 10

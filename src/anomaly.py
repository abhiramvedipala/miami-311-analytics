"""Flag unusual weeks per request type and compare them with known events.

Method: weekly counts -> STL (yearly period) with outliers masked and refit -> z-score
of residuals against the series' week-to-week noise.
Writes mart.anomalies and the anomaly section of RESULTS.md.

Usage: python src/anomaly.py
"""
from datetime import date, timedelta

import pandas as pd
from pandas.tseries.holiday import USFederalHolidayCalendar
from statsmodels.tsa.seasonal import STL

from ingest import connect
from results import data_source, write_section

PERIOD = 52
Z_THRESHOLD = 3.5
MIN_MEDIAN_WEEKLY = 5  # sparser series are mostly noise
MASK_ROUNDS = 5
NOISE_FLOOR = 1.0  # one request of typical error, so a very quiet series cannot produce huge z-scores
STORM_LAG_DAYS = 14  # storm reports keep arriving after the storm passes
SYSTEM_CHANGE = date(2024, 8, 11)
SYSTEM_CHANGE_GUARD_WEEKS = 2  # labels shift at the cutover, so a jump there is not a real event

WEEKLY_SQL = """
WITH last_day AS (SELECT max(created_at)::date AS last_date FROM mart.fct_requests)
SELECT date_trunc('week', facts.created_at)::date AS week_start, types.request_type, count(*) AS requests
FROM mart.fct_requests AS facts
JOIN mart.dim_request_type AS types USING (request_type_key), last_day
WHERE NOT facts.is_duplicate AND types.spans_both_systems
GROUP BY 1, 2, last_date
HAVING date_trunc('week', facts.created_at)::date + 6 <= last_date
"""


def stl_flags(series):
    """Return a frame of expected, residual and z for one complete weekly series."""
    # STL's robust mode loses the largest spikes: one leaks into its week-of-year group, the
    # whole group is zero-weighted, and the raw value becomes "seasonal". So mask flagged weeks
    # with a rolling median (the fit itself is polluted at first) and refit, then score the
    # original series against the clean fit.
    changes = series.diff().dropna()
    # With few yearly cycles STL fits ordinary weeks closely, so the spread of residuals
    # understates noise. Week-to-week changes measure it independently of the fit.
    noise = max(1.4826 * (changes - changes.median()).abs().median() / 2**0.5, NOISE_FLOOR)
    local_median = series.rolling(9, center=True, min_periods=1).median()
    cleaned = series
    for _ in range(MASK_ROUNDS):
        fit = STL(cleaned, period=PERIOD).fit()
        expected = fit.trend + fit.seasonal
        residual = series - expected
        z = (residual - residual.median()) / noise
        masked = series.where(z.abs() < Z_THRESHOLD, local_median)
        if masked.equals(cleaned):
            break
        cleaned = masked
    return pd.DataFrame({"requests": series, "expected": expected, "residual": residual, "z": z})


def score_all(weekly):
    """Score every type with at least two yearly cycles and enough volume."""
    frames = []
    for request_type, group in weekly.groupby("request_type"):
        series = group.set_index(pd.to_datetime(group.week_start)).requests.sort_index()
        series = series.asfreq("7D", fill_value=0).astype(float)
        if len(series) < 2 * PERIOD + 1 or series.median() < MIN_MEDIAN_WEEKLY:
            continue
        scored = stl_flags(series).rename_axis("week_start").reset_index()
        scored["request_type"] = request_type
        frames.append(scored)
    return pd.concat(frames, ignore_index=True)


def near_system_change(week_start):
    distance = abs((week_start.date() - SYSTEM_CHANGE).days)
    return distance <= SYSTEM_CHANGE_GUARD_WEEKS * 7


def event_windows(storms, first, last):
    """Return (name, start, end) windows, latest storm first so Milton's week is not labelled Helene."""
    storms = storms.sort_values("start_date", ascending=False)
    windows = [
        (row.name, pd.Timestamp(row.start_date), pd.Timestamp(row.end_date) + timedelta(days=STORM_LAG_DAYS))
        for row in storms.itertuples()
    ]
    calendar = USFederalHolidayCalendar()
    holidays = calendar.holidays(start=first, end=last + timedelta(days=6), return_name=True)
    windows += [(name, day, day) for day, name in holidays.items()]
    return windows


def match_event(week_start, windows):
    """Return the first event overlapping a Monday-to-Sunday week, storms before holidays."""
    week_end = week_start + timedelta(days=6)
    for name, start, end in windows:
        if start <= week_end and end >= week_start:
            return name
    return None


def describe(row):
    direction = "above" if row.requests >= row.expected else "below"
    difference = abs(row.requests - row.expected)
    percent = f"{100 * difference / row.expected:.0f}% " if row.expected >= 1 else ""
    text = (
        f"{row.request_type} had {row.requests:.0f} requests in the week of {row.week_start.date()}, "
        f"{percent}{direction} the {row.expected:.0f} expected."
    )
    return text + (f" Overlaps {row.event}." if row.event else " No listed event overlaps this week.")


def build_body(flags, weeks, windows):
    top = flags.head(10)
    all_weeks = sorted(weeks)
    base_rate = 100 * sum(match_event(week, windows) is not None for week in all_weeks) / len(all_weeks)
    top_rate = 100 * top.event.notna().mean()
    all_rate = 100 * flags.event.notna().mean()
    rows = "\n".join(
        f"| {row.week_start.date()} | {row.request_type} | {row.z:.1f} | {row.note} |" for row in top.itertuples()
    )
    return f"""
- Flags at |z| >= {Z_THRESHOLD}: **{len(flags):,}** type-weeks across {flags.request_type.nunique()} types
- Known-event match rate, top 10: **{top_rate:.0f}%**
- Known-event match rate, all flags: **{all_rate:.0f}%**
- Chance baseline, share of all weeks overlapping a listed event: **{base_rate:.0f}%**

A match rate only means something above the baseline.

| Week of | Type | z | Note |
|---|---|---|---|
{rows}
"""


def main():
    con = connect()
    weekly = con.execute(WEEKLY_SQL).df()
    storms = con.execute("SELECT * FROM staging.known_events ORDER BY start_date").df()
    scored = score_all(weekly)
    scored = scored[~scored.week_start.map(near_system_change)]

    weeks = scored.week_start.unique()
    windows = event_windows(storms, min(weeks), max(weeks))
    flags = scored[scored.z.abs() >= Z_THRESHOLD].copy()
    flags["event"] = flags.week_start.map(lambda week: match_event(week, windows))
    flags["event"] = flags.event.astype(object).where(flags.event.notna(), None)
    flags["note"] = flags.apply(describe, axis=1)
    flags = flags.reindex(flags.z.abs().sort_values(ascending=False).index).reset_index(drop=True)

    con.execute("CREATE OR REPLACE TABLE mart.anomalies AS SELECT * FROM flags")
    write_section("anomaly", build_body(flags, weeks, windows), "python src/anomaly.py", data_source(con))
    print(f"{len(flags)} flags")
    con.close()


if __name__ == "__main__":
    main()

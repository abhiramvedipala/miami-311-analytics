import numpy as np
import pandas as pd

import anomaly


def weekly_series(spike_at=None):
    rng = np.random.default_rng(1)
    index = pd.date_range("2023-01-02", periods=300, freq="7D")
    values = 100 + 20 * np.sin(2 * np.pi * np.arange(300) / 52) + rng.normal(0, 3, 300)
    series = pd.Series(values, index=index)
    if spike_at is not None:
        series.iloc[spike_at] += 200
    return series


def test_stl_flags_a_planted_spike_and_only_that_week():
    scored = anomaly.stl_flags(weekly_series(spike_at=150))
    assert scored.z.iloc[150] > anomaly.Z_THRESHOLD
    assert scored.z.abs().idxmax() == scored.index[150]
    assert (scored.z.abs() >= anomaly.Z_THRESHOLD).sum() <= 3


def test_storm_window_includes_lag_and_holiday_window_is_exact():
    storms = pd.DataFrame({"name": ["Milton"], "start_date": ["2024-10-07"], "end_date": ["2024-10-10"]})
    windows = anomaly.event_windows(storms, pd.Timestamp("2024-09-01"), pd.Timestamp("2024-12-31"))
    assert anomaly.match_event(pd.Timestamp("2024-10-21"), windows) == "Milton"
    both = pd.DataFrame({"name": ["Helene", "Milton"], "start_date": ["2024-09-24", "2024-10-07"], "end_date": ["2024-09-27", "2024-10-10"]})
    both_windows = anomaly.event_windows(both, pd.Timestamp("2024-09-01"), pd.Timestamp("2024-12-31"))
    assert anomaly.match_event(pd.Timestamp("2024-10-07"), both_windows) == "Milton"
    assert "Thanksgiving" in anomaly.match_event(pd.Timestamp("2024-11-25"), windows)
    assert anomaly.match_event(pd.Timestamp("2024-11-04"), windows) is None


def test_weeks_around_the_system_change_are_excluded():
    assert anomaly.near_system_change(pd.Timestamp("2024-08-12"))
    assert not anomaly.near_system_change(pd.Timestamp("2024-10-07"))


def test_short_or_sparse_series_are_skipped():
    weeks = pd.date_range("2023-01-02", periods=156, freq="7D")
    frames = [
        pd.DataFrame({"week_start": weeks, "request_type": "busy", "requests": 100 + np.arange(156) % 7}),
        pd.DataFrame({"week_start": weeks, "request_type": "sparse", "requests": 1}),
        pd.DataFrame({"week_start": weeks[:50], "request_type": "short", "requests": 100}),
    ]
    assert set(anomaly.score_all(pd.concat(frames)).request_type) == {"busy"}

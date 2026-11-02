"""Measure the anomaly method on simulated series with spikes planted at known weeks.

Fixed seeds, no data needed. Usage: python src/validate_anomaly.py
"""
import numpy as np
import pandas as pd

from anomaly import Z_THRESHOLD, stl_flags
from results import write_section

SEEDS = range(2)
SPIKES = (30, 50, 100, 200, 500, 2000)  # weekly base is about 100 requests, noise sd 5
LENGTHS = (156, 196, 300)


def measure(weeks, spike):
    """Return (planted spikes caught, trials, false flags per series)."""
    caught = trials = false_flags = 0
    index = pd.date_range("2021-01-04", periods=weeks, freq="7D")
    for seed in SEEDS:
        for position in range(5, weeks - 5, 23):
            rng = np.random.default_rng(seed)
            values = 100 + 20 * np.sin(2 * np.pi * np.arange(weeks) / 52) + rng.normal(0, 5, weeks)
            series = pd.Series(values, index=index)
            series.iloc[position] += spike
            flagged = stl_flags(series).z.abs() >= Z_THRESHOLD
            hit = bool(flagged.iloc[position])
            trials += 1
            caught += hit
            false_flags += int(flagged.sum()) - hit
    return caught, trials, false_flags / trials


def row(label, weeks, spike):
    caught, trials, false_rate = measure(weeks, spike)
    return f"| {label} | {caught}/{trials} ({100 * caught / trials:.0f}%) | {false_rate:.2f} |"


def main():
    clean = measure(300, 0)[2]
    by_size = "\n".join(row(f"+{spike}", 300, spike) for spike in SPIKES)
    by_length = "\n".join(row(f"{weeks} weeks", weeks, 100) for weeks in LENGTHS)
    body = f"""
Simulated series, not county data. False flags on series with no spike: **{clean:.2f}** per series.

Recall by spike size (300 weeks, base about 100 requests a week):

| Spike | Caught | False flags per series |
|---|---|---|
{by_size}

Recall by history length (+100 spike):

| History | Caught | False flags per series |
|---|---|---|
{by_length}
"""
    write_section("validation", body, "python src/validate_anomaly.py", "simulation")


if __name__ == "__main__":
    main()

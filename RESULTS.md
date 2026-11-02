# Results

Every number below is written by the command named in its section.

<!-- section:ingestion source=live sha256=a34b8d9a1e96999cb5af9bda36aed7a24a7efcc4abd02037fde0f2f647bc9973 -->
## Ingestion

Command: `make all`

- Raw rows loaded: **1,927,549**
- Unique requests in `mart.fct_requests`: **1,927,549**
- Coverage: 2021-01-01 to 2026-09-30 (69 calendar months)

| Source layer | Rows |
|---|---|
| 311_Service_Requests_-_Miami-Dade_County_-_2024_-_Jan_-_Aug | 206,828 |
| data_311_2021 | 341,706 |
| data_311_2022 | 333,836 |
| data_311_2023 | 343,851 |
| data_311_2024_Aug_Dec | 125,921 |
| data_311_2025 | 322,706 |
| data_311_2026 | 252,701 |

<!-- end:ingestion -->

<!-- section:analysis source=live sha256=fcd6bcfdf34661434e48b97647958076f0422d92db3748143525d3c684491de5 -->
## Analysis

Command: `python src/run_analysis.py`

- Backlog (open new-system requests): **35,815**
- Worst p90 type: **Sidewalk**, 374.5 days at p90 and 63.5 at median (2,946 closed requests)
- Busiest slot: Tuesday at 10:00 Miami time (41,070 requests)
- Batch closures left out of close times: 14,132 requests across 8 type-days
- Complete months covered: 69; highest 33,305, lowest 20,354

3 slowest neighborhoods by median days to close (at least 500 closed requests):

| Neighborhood | Median days | P90 days | Closed requests |
|---|---|---|---|
| 33176 (UNINCORPORATED MIAMI-DADE) | 8.9 | 20.1 | 64,820 |
| 33173 (UNINCORPORATED MIAMI-DADE) | 8.8 | 19.1 | 34,670 |
| 33158 (PALMETTO BAY) | 8.8 | 17.9 | 9,766 |

Backlog aging:

| Age | Open requests | Share |
|---|---|---|
| 0-30 days | 2,810 | 7.8% |
| 31-90 days | 3,396 | 9.5% |
| 91-180 days | 4,014 | 11.2% |
| 181-365 days | 7,764 | 21.7% |
| Over 365 days | 17,831 | 49.8% |

<!-- end:analysis -->

<!-- section:anomaly source=live sha256=1c81b434003767b2ba26b1b044cf030c64687535fa7da13b9ca180cbf4619e27 -->
## Anomaly

Command: `python src/anomaly.py`

- Flags at |z| >= 3.5: **146** type-weeks across 11 types
- Known-event match rate, top 10: **60%**
- Known-event match rate, all flags: **38%**
- Chance baseline, share of all weeks overlapping a listed event: **29%**
- Storms only, flags above expected inside a storm window: **23%**, against **11%** of all weeks

A holiday lining up with a surge is usually coincidence, so the storm-only line is the stricter test.

A match rate only means something above the baseline.

| Week of | Type | z | Note |
|---|---|---|---|
| 2024-06-24 | Mosquito Inspection | 35.6 | Mosquito Inspection had 2373 requests in the week of 2024-06-24, 334% above the 547 expected. Overlaps South Florida flood (Invest 90L). |
| 2026-07-27 | Mosquito Inspection | 29.5 | Mosquito Inspection had 2247 requests in the week of 2026-07-27, 207% above the 732 expected. No listed event overlaps this week. |
| 2025-07-14 | Mosquito Inspection | 28.3 | Mosquito Inspection had 2267 requests in the week of 2025-07-14, 179% above the 814 expected. No listed event overlaps this week. |
| 2023-04-24 | Mosquito Inspection | 24.9 | Mosquito Inspection had 1623 requests in the week of 2023-04-24, 369% above the 346 expected. Overlaps South Florida flood. |
| 2022-06-06 | Flooding or Drainage | 23.4 | Flooding or Drainage had 290 requests in the week of 2022-06-06, 1295% above the 21 expected. Overlaps Tropical Storm Alex flood. |
| 2024-10-07 | Flooding or Drainage | 22.7 | Flooding or Drainage had 334 requests in the week of 2024-10-07, 362% above the 72 expected. Overlaps Hurricane Milton. |
| 2025-08-25 | Mosquito Inspection | 18.7 | Mosquito Inspection had 1361 requests in the week of 2025-08-25, 239% above the 401 expected. No listed event overlaps this week. |
| 2024-07-01 | Mosquito Inspection | 16.8 | Mosquito Inspection had 1480 requests in the week of 2024-07-01, 139% above the 618 expected. Overlaps Independence Day. |
| 2025-09-08 | Flooding or Drainage | 15.9 | Flooding or Drainage had 271 requests in the week of 2025-09-08, 207% above the 88 expected. No listed event overlaps this week. |
| 2024-06-10 | Flooding or Drainage | 15.6 | Flooding or Drainage had 215 requests in the week of 2024-06-10, 510% above the 35 expected. Overlaps South Florida flood (Invest 90L). |

<!-- end:anomaly -->

<!-- section:validation source=simulation sha256=e76cd8a90f137e312deb99e448a9b263597d9ce6e9ce89dc2c3afc91e17b6a27 -->
## Validation

Command: `python src/validate_anomaly.py`

Simulated series, not county data. False flags on series with no spike: **0.00** per series.

Recall by spike size (300 weeks, base about 100 requests a week):

| Spike | Caught | False flags per series |
|---|---|---|
| +30 | 11/26 (42%) | 0.00 |
| +50 | 17/26 (65%) | 0.27 |
| +100 | 26/26 (100%) | 0.00 |
| +200 | 26/26 (100%) | 0.00 |
| +500 | 26/26 (100%) | 0.00 |
| +2000 | 26/26 (100%) | 0.08 |

Recall by history length (+100 spike):

| History | Caught | False flags per series |
|---|---|---|
| 156 weeks | 6/14 (43%) | 0.64 |
| 196 weeks | 16/18 (89%) | 0.11 |
| 300 weeks | 26/26 (100%) | 0.00 |

<!-- end:validation -->


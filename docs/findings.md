# What Miami-Dade's 311 requests show

This page covers 1,892,479 service requests made between 2021-01-01 and 2026-09-30. It is generated from the data by `python src/write_findings.py`.

## Where residents wait longest

- 33176 (UNINCORPORATED MIAMI-DADE): half of requests took longer than 8.9 days
- 33173 (UNINCORPORATED MIAMI-DADE): half of requests took longer than 8.8 days
- 33158 (PALMETTO BAY): half of requests took longer than 8.8 days

The type of request with the longest slow cases is **Sidewalk**: one in ten took more than 374.5 days to close.

These figures describe closed requests only. Requests that are still open are not counted, so true waits are longer. The differences between neighborhoods are small, so request type matters far more than location.

## What is still open

35,815 requests are open, and 49.8% of them are more than a year old. Some of these may be finished work that was never marked closed, so a review of the oldest ones is the likely first step.

## Problems that keep coming back

The strongest repeat location, leaving out facility addresses, is in 33196 (UNINCORPORATED MIAMI-DADE): 163 Pothole requests, 160 of them within 30 days of the previous one.

Some repeats are normal, such as a household booking several bulky waste pickups. Others may point to a problem that is not being fixed.

## Tickets closed in bulk

14,132 requests were closed in 8 clean-up batches, where many old requests of one type closed on the same day. These look like record keeping rather than finished work, so they are left out of the wait times above. If they are not checked, they can make a backlog look smaller than it is.

## Unusual weeks

The three most unusual weeks were:

- Mosquito Inspection had 2373 requests in the week of 2024-06-24, 334% above the 547 expected. Overlaps South Florida flood (Invest 90L).
- Mosquito Inspection had 2247 requests in the week of 2026-07-27, 207% above the 732 expected. No listed event overlaps this week.
- Mosquito Inspection had 2267 requests in the week of 2025-07-14, 179% above the 814 expected. No listed event overlaps this week.

## When people ask for help

The busiest time is Tuesday around 10:00.

## How far to trust this

- The county changed its 311 system on 11 August 2024. Request names changed, and comparisons across that date are approximate.
- ZIP codes stand in for neighborhoods, because the data has no neighborhood field.
- Slower does not mean worse service. Areas and request types differ in the work involved.
- An unusual week lining up with a storm or holiday does not prove that it caused the change.

# Decisions

One line each: decision + why.

- Source is ArcGIS FeatureServer, not Socrata, because opendata.miamidade.gov is retired and the county now publishes its 311 layers on ArcGIS; this is still the real Miami-Dade data, so no fallback city was needed.
- Pull from 2021 on (over 24 months required), because the anomaly method's recall rises with history (table in RESULTS.md, validation section) and this range covers 11 listed storms.
- STL runs non-robust with outliers masked by a rolling median and refit, because robust mode absorbed the largest spikes into the seasonal term, and masking with the fitted value left false flags.
- Anomaly z-score divides by noise from week-to-week changes, not residual spread, because with few yearly cycles STL fits ordinary weeks almost exactly and residual spread flagged everything.
- Incremental filter uses created OR modified date, not created date alone, because a created-date filter would never see an old request being closed.
- ZIP code stands in for neighborhood, because the source has no neighborhood field and most rows share one municipality.
- A hand-written crosswalk joins type labels across the 2024-08-11 system change, and covers only labels with a clear equivalent, because the two systems share no taxonomy.
- Old-system open rows are excluded from backlog, because those layers stopped receiving status updates (the 2023 layer was last edited 2024-03-17).
- Old statuses map LOCKED to closed, CANCEL to cancelled, and WIP, PENDNG and LIEN to open; EMERGNCY and URGENT map to High priority, because these are the closest new-system values.
- check.sh runs the pipeline on generated offline rows, because three fresh-clone runs should not re-download over a million rows from a public API; live results are protected by a hash and source label in RESULTS.md.
- Private build notes stay out of the repo, because the project does not need them.
- uv is the only install prerequisite, because it provides Python 3.12 (system Python is 3.14, too new for dbt).
- Priority codes HURRACT and MH map to Other and nulls to Unspecified, because their meaning is undocumented and rows are few; any new code still fails the build.
- Closures of 200 or more requests of one type in a day with a median age of 60 days or more count as batch clean-up and are left out of close times, because one such batch made a 4-day median type look like the worst p90 in the county; the same largest batches appear at every threshold tested.
- Hotspots leave out points with 10 or more request types and police assistance requests, because the top raw hotspot was one address with 24 unrelated types, which points to a facility or default address.

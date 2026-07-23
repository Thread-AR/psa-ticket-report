# Autotask connector — NOT YET BUILT

This folder will hold the Autotask (Datto) PSA connector, mirroring the
structure of `connectwise/`.

## What needs to happen here

1. Authenticate against the Autotask REST API. Autotask uses:
   - An API Integration Code
   - A Username + Secret (API user, not a human login)
   - A "zone" lookup step first — Autotask REST API base URLs are
     tenant-specific and returned by a zone-detection endpoint before
     you can query anything else
2. Query the `Tickets` entity, filtered by `CreateDate` within the
   lookback window
3. Join each ticket to its `Companies` (Account) record to get the
   customer name
4. Normalize into the same shape the shared module expects:
   `{"customer_id": ..., "customer_name": ...}` per ticket
5. Reuse `shared/report_utils.py` for aggregation, anonymization, and
   CSV output — do not duplicate that logic here

Reference: https://autotask.net/help/DeveloperHelp/Content/APIs/REST/REST_API_Home.htm

When built, this file should be replaced with the same style of README
as `connectwise/README.md` — credential setup steps, run instructions,
what gets written to disk.

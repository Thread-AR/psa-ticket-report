# HaloPSA connector — NOT YET BUILT

This folder will hold the HaloPSA connector, mirroring the structure of
`connectwise/`.

## What needs to happen here

1. Authenticate against the HaloPSA API using OAuth2 client-credentials
   flow: exchange a Client ID + Client Secret at the tenant's `/token`
   endpoint for a bearer access token
2. Query the `Tickets` endpoint with date range filters for the
   lookback window
3. Each ticket response should include (or can be joined to) the
   customer/client name
4. Normalize into the same shape the shared module expects:
   `{"customer_id": ..., "customer_name": ...}` per ticket
5. Reuse `shared/report_utils.py` for aggregation, anonymization, and
   CSV output — do not duplicate that logic here

Reference: https://haloacademy.halopsa.com/apidoc/

When built, this file should be replaced with the same style of README
as `connectwise/README.md` — credential setup steps, run instructions,
what gets written to disk.

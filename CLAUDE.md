# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

A small, local, transparent tool for MSP prospects to generate an anonymized
ticket-volume-by-customer report from their PSA (professional services
automation) system, for use in Thread's sales discovery process. Each script
runs entirely on the prospect's own machine, talks only to their own PSA API
using credentials they control, and writes output only to local disk —
nothing is sent to Thread. **This tool never calculates license
recommendations** — it only produces raw ticket counts per anonymized
customer; that logic intentionally lives outside this repo.

## Commands

```bash
pip install -r requirements.txt

# Run the ConnectWise connector (only one built so far)
cd connectwise
python cw_ticket_report.py --days 90
```

There is no test suite, linter, or build step in this repo currently.

Credentials can be passed via environment variables to skip interactive
prompts (see `connectwise/README.md` for the exact variable names per PSA).

## Architecture

Each PSA gets its own top-level folder (`connectwise/`, `autotask/`, `halo/`)
containing a self-contained connector script plus a README with
credential-setup and run instructions. All three connectors are
implemented and validated against live instances:

- `halo/README.md` documents the exact Agent Role/permission configuration
  confirmed to work, since HaloPSA splits authorization across two
  separate layers (the API Application's own enabled permissions, and the
  assigned Agent's Role/data visibility scope) that must both be
  configured correctly.
- `autotask/README.md` documents that Autotask's default "API User
  (system) (API-only)" security level is full-admin and can't be edited
  directly — a genuinely read-only setup requires copying it and
  restricting the copy (Tickets/Companies to View only) before assigning
  it to the API user.
- ConnectWise's Client ID (`connectwise/cw_ticket_report.py`,
  `DEFAULT_CLIENT_ID`) is baked into the script rather than collected from
  each prospect. Unlike a member's Public/Private key pair, a Client ID
  identifies the *software* calling the API, not a specific prospect's CW
  instance — it's registered once, in Thread's own ConnectWise Developer
  Portal account, and the same value works across every prospect's
  separate instance. It was registered as a **Private** integration
  (ConnectWise's registration flow distinguishes "Customer-Specific" vs.
  "Community Availability"/public). ConnectWise's own stated definition of
  Private is "in-house integrations that never get hooked up to another
  company," which is arguably not an exact fit for a Client ID reused
  across many separate prospects' instances — Public is closer to their
  stated criteria for multi-company use, though it's unconfirmed whether
  checking "Community Availability" forces an actual Marketplace listing.
  This was a deliberate "start conservative" choice pending clarification
  from ConnectWise's platform team (`Platform@ConnectWise.com`); revisit
  if it causes API/ToS issues at higher volume.

**The contract between every connector and `shared/report_utils.py`** is a
single normalized shape — one dict per ticket:

```python
{"customer_id": ..., "customer_name": ...}
```

A connector's only job is: authenticate against its PSA's API, page through
tickets created within the lookback window, join to the customer/company
record, and normalize into that shape. All aggregation, anonymization, and
CSV writing is PSA-agnostic and already implemented in
`shared/report_utils.py` — do not duplicate that logic in a new connector.

`shared/report_utils.py` provides:
- `aggregate_by_customer(normalized_tickets)` → `(counts, names)` dicts keyed
  by `customer_id`
- `anonymize(counts, names)` → sorts by ticket volume descending and assigns
  sequential labels (`Customer 001`, `Customer 002`, ...), returning both the
  anonymized `rows` and a separate `mapping` of label → real name
- `write_report(rows, days, psa_name, out_path=...)` → writes
  `thread_ticket_report.csv`
- `write_local_mapping(mapping, out_path=...)` → writes
  `local_only_customer_mapping.csv`

### The two-file output split is deliberate and load-bearing

Every connector run produces exactly two files, and this separation must be
preserved in any new connector or refactor:

1. **`thread_ticket_report.csv`** — anonymized customer labels + ticket
   counts only. This is the file meant to be shared with a Thread rep.
2. **`local_only_customer_mapping.csv`** — the real customer names behind
   each label. This file must never be sent anywhere; it stays on the
   prospect's machine.

Do not add fields to `thread_ticket_report.csv` that could de-anonymize a
customer (real names, identifiers, contact info) — that data belongs only in
the local mapping file.

## Known issues

- **Autotask company-name resolution gap**: in `autotask/autotask_ticket_report.py`,
  `fetch_company_names()` sometimes fails to resolve a real company name for a
  valid, active company — `local_only_customer_mapping.csv` then falls back to
  `Customer <companyID>` (from `aggregate_by_customer` in
  `shared/report_utils.py`) instead of the real name. Confirmed on a live demo
  run: the account with the *most* tickets (218) resolved to `Customer
  29683644` instead of its real name ("Initech"), despite that account being
  active — so this isn't just demo-data noise. Root cause not yet identified;
  likely candidates are a visibility-scoping mismatch between the Tickets and
  Companies permissions (same shape of bug we hit with Halo's Agent Role) or a
  chunking/batching issue in the "in" filter. Revisit before relying on this
  connector's mapping file for a real prospect engagement.

### Adding a new PSA connector

Follow the structure and style of `connectwise/cw_ticket_report.py` and
`connectwise/README.md`. Read the target PSA's scoping README first
(`autotask/README.md` or `halo/README.md`) — it already documents the auth
flow specifics and entity names to query. Import shared utilities the same
way the ConnectWise connector does, via a `sys.path.insert` one level up
(since each connector script is run directly from its own PSA folder, not as
an installed package):

```python
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from shared.report_utils import aggregate_by_customer, anonymize, write_report, write_local_mapping
```

When a connector is completed, replace its folder's scoping README with a
real one in the same style as `connectwise/README.md` (credential setup
steps, run instructions, output description).

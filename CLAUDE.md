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

# Run whichever PSA's connector applies
cd connectwise   # or autotask, or halo
python cw_ticket_report.py --days 90   # or autotask_ticket_report.py / halo_ticket_report.py
```

There is no test suite, linter, or build step in this repo currently.

Credentials can be passed via environment variables to skip interactive
prompts (see each PSA folder's README for the exact variable names).

## Distribution

Currently distributed as raw `.py` files — a prospect downloads this repo
as a ZIP from GitHub, installs Python + `pip install -r requirements.txt`,
and runs the script directly. The root `README.md` has beginner-friendly
prerequisite instructions (installing Python, the Windows "Add to PATH"
checkbox gotcha, drag-and-drop `cd` trick) aimed at non-technical
prospects, not just developers.

A `gui/` desktop app now exists (see "GUI (desktop app)" below) as a
point-and-click wrapper around the same connector scripts, replacing the
`input()`/`getpass()` terminal prompts for anyone who'd rather not use a
terminal at all. It's still distributed as raw `.py` files today (run via
`python gui/app.py`) — the CLI scripts remain fully independent and are
still the recommended fallback if the GUI doesn't work on a given machine.

**Longer-term direction (not yet started):** package the GUI as a single
Windows `.exe` and a single macOS `.pkg` via PyInstaller, distributed
through public GitHub Releases. This is blocked on a decision about
code-signing certificates (Windows code-signing cert + Apple Developer
Program membership) — without signing, the packaged executables will
trigger Windows SmartScreen / macOS Gatekeeper warnings, which undercuts
the tool's "small, transparent, trustworthy" pitch to security-conscious
MSP prospects. Revisit packaging once that cost/ownership decision is made.

## Architecture

Each PSA gets its own top-level folder (`connectwise/`, `autotask/`, `halo/`)
containing a self-contained connector script plus a README with
credential-setup and run instructions. All three connectors are
implemented and validated against live instances:

- `halo/README.md` documents the exact Agent Role/permission configuration
  confirmed to work, since HaloPSA splits authorization across two
  separate layers (the API Application's own enabled permissions, and the
  assigned Agent's Role/data visibility scope) that must both be
  configured correctly. A Role with zero Teams and zero Departments
  assigned reads tickets/customers fine (via "Membership level to all
  Departments: View all") but makes `GET api/Team` return an empty list
  for that Agent — discovered while validating `--list-boards` against a
  live demo instance. Fix: assign just one Team *or* one Department to
  the Role (either works, and assigning only one is enough to unlock the
  *full* team list in the response — not just that one).
- `connectwise/README.md`'s security role needs a third permission beyond
  ticket/company reading: **System > Table Setup** (Inquire = All, with
  "Service / Service Board" allow-listed under that permission's
  Customize screen) — without it, `fetch_boards()` (`--list-boards`) gets
  a 403 even though ticket fetching works fine. Discovered when validating
  `--list-boards` against a live demo instance whose role only had the
  original two permissions.
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
- `parse_board_exclusions(raw)` → parses a `--exclude-boards` value into a
  lowercased token set
- `is_board_excluded(board_id, board_name, excluded)` → True if a ticket's
  board/queue/team matches an excluded token by numeric ID or by name
  (case-insensitive)

### Board/queue/team exclusion

Every connector supports `--exclude-boards` (comma-separated board/queue/team
names and/or numeric IDs — mixing both in one list is fine) and `--list-boards`
(prints every board/queue/team with its ID, then exits) so a prospect can
exclude boards that only receive automated alerts rather than real customer
tickets. Each PSA models this concept differently, so each connector resolves
it independently before calling the shared `is_board_excluded()` helper:

- ConnectWise: board id/name are already present per-ticket (`board/id`,
  `board/name` added to the tickets `fields` query param); `fetch_boards()`
  hits `service/boards` for `--list-boards`.
- Autotask: tickets only carry a numeric `queueID`; queue *names* come from
  the picklist values on `Tickets/entityInformation/fields` (`fetch_queues()`),
  a separate, simpler lookup than the flaky company-name resolution below —
  excluding by ID or by name costs the same one extra API call either way.
- HaloPSA: tickets already carry both `team_id` and `team` (name) directly,
  so no extra API call is needed to filter; `fetch_teams()` hits `api/Team`
  only for `--list-boards`.

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

## GUI (desktop app)

`gui/` is a pywebview-based wizard (HTML/CSS/JS front end in `gui/web/`,
Python backend) that wraps the three connector scripts unmodified — it is
purely additive and never changes `connectwise/`, `autotask/`, `halo/`, or
`shared/report_utils.py`. Chosen over Tkinter/PySide because Thread's brand
guidelines (colors, fonts, 24px grid, rounded corners) are far easier to
hit precisely with real CSS than with a native-widget toolkit, and
pywebview still packages cleanly with PyInstaller for the eventual
`.exe`/`.pkg` (see "Distribution" above).

- **`gui/psa_config.py`** is the single source of truth per PSA: script
  path, credential field definitions (with per-field `help` text), board
  terminology ("Service Board"/"Queue"/"Team"), and the `setup` block
  (admin-access note + numbered credential-setup steps) shown in the
  wizard's Setup screen before the Credentials screen. This content is a
  condensed copy of each PSA's own README, not a shared source — if a
  README's permission requirements change, `psa_config.py` needs a matching
  manual edit; it won't pick up the change automatically.
- **`gui/runner.py`** launches a connector script as a subprocess rather
  than importing its functions directly, specifically so `load_credentials()`
  and `main()` in the connector scripts never need to be touched. Two
  details are load-bearing, not stylistic:
  - `stdin=subprocess.DEVNULL` on every launch — without it, a missing or
    blank credential falls through to the connector's `input()`/`getpass()`
    and the subprocess hangs forever with no error, since nothing is
    connected to write to that pipe.
  - `stderr=subprocess.STDOUT` — keeping them as separate pipes risks a
    classic deadlock if a traceback fills the unread stderr pipe's OS
    buffer, and it ensures errors actually show up in the GUI's log panel.
  - Output location is controlled purely via the subprocess's `cwd`
    (matching the user-chosen output folder) — `shared/report_utils.py`'s
    `write_report`/`write_local_mapping` default to CWD-relative filenames
    and no connector's `main()` overrides that, so this needed no changes
    to connector code.
- **`gui/app.py`** exposes an `Api` class to the JS front end via
  pywebview's `js_api`. Each JS→Python call runs in its own thread
  (pywebview's default behavior), which is what lets `run_report()` block
  for the subprocess's whole lifetime while still calling
  `window.evaluate_js()` per output line to stream logs live. A
  `threading.Lock`-guarded busy check rejects a second concurrent
  `run_report()` call (e.g. a double-click), and `window.events.closing`
  terminates any in-flight subprocess so closing the window doesn't leave
  an orphaned PSA-fetching process running.
- **Credentials are never persisted** — held in memory for the GUI
  process's lifetime only, passed to each subprocess via that call's env
  dict (a copy of `os.environ`, not a mutation of the parent process's
  environment).
- **`requirements.txt`** pins `pyobjc-core`/`pyobjc-framework-*` below
  version 12, but only for `python_version<"3.10" and sys_platform ==
  "darwin"`. Without this, a stock macOS Python 3.9 (e.g. the one bundled
  with Xcode Command Line Tools) fails to install pywebview: pyobjc 12.0
  has no prebuilt wheel for Python 3.9, and building it from source fails
  on current Xcode CLT clang due to an unrelated warning-as-error in
  Apple's SIMD headers. Version 11.1 has a working cp39 wheel. Python 3.10+
  and non-macOS platforms are unaffected by this pin and resolve normally.
- **`gui/screenshots/`** holds the PNGs used in this README and the root
  `README.md`. They were generated by driving the actual `gui/web/`
  files headlessly with Playwright (`channel="chrome"`, using the
  system-installed Chrome rather than downloading a separate browser) and
  a mocked `window.pywebview.api` seeded from the real `psa_config.py`
  output — not hand-captured from a running app, since a real pywebview
  window can't be screenshotted from a sandboxed/headless environment
  (no macOS Screen Recording permission). Regenerate them the same way if
  the wizard's copy or styling changes.

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

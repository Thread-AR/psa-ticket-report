# Autotask connector

Validated against a live Autotask instance — worked on the first run
following the steps below (458 tickets across 12 companies, no errors).

Prefer a point-and-click experience over a terminal? See [gui/README.md](../gui/README.md) — the desktop app walks you through this same setup with in-app instructions and field-by-field help.

## 1. Create a read-only Security Level

**Before you begin**: you'll need admin-level access to **Admin > Account
Settings & Users > Resources/Users (HR)** in Autotask — specifically
permission to create Security Levels and API Users. A standard technician
login typically won't have this. If you can't see this area, ask whoever
administers your Autotask instance to either do this setup or grant you
access.

Autotask's built-in **"API User (system) (API-only)"** security level
cannot be edited — it grants the same access as Full Access — but it
*can be copied*, and copies can be restricted. Do not skip this step and
assign the default level directly to the API user in step 2.

1. Go to **Admin > Account Settings & Users > Resources/Users (HR) >
   Security Levels**.
2. Find **"API User (system) (API-only)"**, and copy it.
3. Rename the copy to **`Thread Ticket Report - Read Only`**.
4. Edit the copy: set **Tickets** and **Companies** to **View only**
   (uncheck Add/Edit/Delete), and remove access to every other
   module/feature the copied level included by default.

## 2. Create a dedicated API user

Suggested naming (makes it obvious to any admin later what this is and
that it's safe to remove once the report's generated):

- **Resource Name**: `Thread Ticket Report (Read-Only)`
- **Email Address** (contact info field, not the API username): `thread-ticket-report-api@<theirdomain>`
- **Security Level**: `Thread Ticket Report - Read Only` (the one from step 1)

1. Go to **Admin > Resources (Users)**, click the dropdown next to
   **+ New**, and choose **New API User**.
2. In the **General** pane: enter a First/Last Name, the Email Address
   above, and set **Security Level** to the custom role from step 1 —
   not the default "API User (system) (API-only)".
3. In the **Security** pane:
   - Click **Generate Key** — this produces the **Username**. It's
     system-generated, not something you choose yourself.
   - Click **Generate Secret** — this is the **Secret** (API key/password).
     It's shown only once, so copy it immediately.
4. Still on the Security pane, set the **API Tracking Identifier** to
   **Custom (Internal Integration)** (self-service, no Datto/Autotask
   approval needed — the "Vendor" identifier type is for published
   marketplace integrations and doesn't apply here). Give it an internal
   name describing its purpose, e.g. `Thread Ticket Report` — the actual
   tracking identifier value is generated automatically once you save; you
   don't type it in yourself.
5. **Save & Close.**

You'll end up with three values: Username (Key), Secret (both
system-generated), and API Integration Code / Tracking Identifier
(auto-generated once you select Custom (Internal Integration) — the name
you give it is just a label, not the value itself).

## 3. Run it

If you haven't already, see the root [README.md](../README.md) first for
installing Python and downloading this tool.

**macOS:**
```
python3 -m pip install -r ../requirements.txt
python3 autotask_ticket_report.py --days 90
```

**Windows:**
```
python -m pip install -r ../requirements.txt
python autotask_ticket_report.py --days 90
```

It'll prompt you for each credential one at a time (Username, Secret,
Integration Code) — just type or paste each one and press Enter.

(Advanced/optional: credentials can also be set as environment variables
ahead of time to skip the prompts — `AUTOTASK_USERNAME`, `AUTOTASK_SECRET`,
`AUTOTASK_INTEGRATION_CODE`. The syntax for this differs by OS/shell, so
if you're not sure, just skip this and answer the prompts instead.)

## 4. Excluding queues (optional)

If any ticket Queues only receive automated alerts (RMM/monitoring
tickets, not real customer requests), exclude them so they don't inflate
the ticket counts:

```
python3 autotask_ticket_report.py --list-boards
```

This prints every ticket Queue with its ID, e.g.:

```
     8  Automated Alerts
     1  Help Desk
     6  Onboarding
```

Then re-run with `--exclude-boards`, using either the name or the ID
(comma-separate multiple queues; mixing names and IDs is fine):

```
python3 autotask_ticket_report.py --days 90 --exclude-boards "Automated Alerts"
python3 autotask_ticket_report.py --days 90 --exclude-boards "8,Onboarding"
```

## 5. Output

- `thread_ticket_report.csv` — anonymized, safe to share with your Thread rep
- `local_only_customer_mapping.csv` — real customer names behind each label.
  **Keep this. Do not share it.**

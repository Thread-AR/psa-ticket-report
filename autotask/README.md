# Autotask connector

Validated against a live Autotask instance — worked on the first run
following the steps below (458 tickets across 12 companies, no errors).

## 1. Create a read-only Security Level

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
   name and tracking identifier, e.g. `Thread Ticket Report`.
5. **Save & Close.**

You'll end up with three values: Username (Key), Secret, and API
Integration Code (Tracking Identifier).

## 3. Run it

```
pip install -r ../requirements.txt
python autotask_ticket_report.py --days 90
```

Or set credentials as environment variables ahead of time to skip prompts:

```
export AUTOTASK_USERNAME="..."   # the system-generated key, e.g. abc123xyz@yourinstance.com
export AUTOTASK_SECRET="..."
export AUTOTASK_INTEGRATION_CODE="..."
```

## 4. Output

- `thread_ticket_report.csv` — anonymized, safe to share with your Thread rep
- `local_only_customer_mapping.csv` — real customer names behind each label.
  **Keep this. Do not share it.**

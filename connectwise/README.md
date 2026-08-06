# ConnectWise Manage connector

Validated against a live ConnectWise Manage demo instance — clean run with
no auth errors, and ticket/customer counts scaled sensibly across multiple
lookback windows (e.g. 187 tickets over 30 days vs. 413 over 90 days,
consistent customer count), confirming the date filter behaves correctly.

Prefer a point-and-click experience over a terminal? See [gui/README.md](../gui/README.md) — the desktop app walks you through this same setup with in-app instructions and field-by-field help.

## 1. Generate read-only API credentials in ConnectWise

**Before you begin**: you'll need **System > Members** access in
ConnectWise Manage to complete this setup — specifically, permission to
create API Members and Security Roles. This is admin-level access, not
something a standard technician login typically has. If you don't see
**System > Members** in your left-hand menu at all, that's usually a sign
your own role doesn't include it — ask whoever administers your
ConnectWise instance to either do this setup or grant you that permission.

You'll need a ConnectWise Manage API member with **read-only access to
Service Tickets and Companies**. Recommended: create a dedicated API-only
member rather than reusing a personal login.

Suggested naming (makes it obvious to any admin later what this is and
that it's safe to remove once the report's generated). Note ConnectWise
truncates both the Member Name (30 char limit) and Security Role name
(also ~30 chars) — these fit within that:

- **Member ID**: `ThreadTixRpt`
- **Member Name**: `Thread Ticket Report (RO)`
- **Security Role**: `Thread Ticket Report (RO)`

1. In ConnectWise Manage, go to **System > Members > API Members**
2. Add a new API member using the naming above
3. Create/assign a security role using the naming above, with exactly these
   non-None permissions — everything else should stay at **None**:
   - **Companies > Company Maintenance**: Inquire = **All**
   - **Service Desk > Service Tickets**: Inquire = **All**
   - **System > Table Setup**: Inquire = **All** — required only for
     `--list-boards` / `--exclude-boards` (reading Service Board names).
     After enabling it, click **Customize** and make sure **Service /
     Service Board** is checked under "Allow access to these columns" —
     without this, board lookups fail with a 403 even though Table Setup
     itself is enabled.
4. Under that member, go to **API Keys** and generate a Public/Private key pair

You'll end up with three values: Company ID, Public Key, Private Key,
plus your ConnectWise **site URL** (e.g. `https://na.myconnectwise.net`).
(A Client ID is also required by ConnectWise's API, but this tool already
has one built in — you don't need to register your own.)

**What's the Company ID?** It's the short identifier for your specific
ConnectWise Manage instance — not your organization's display/business
name. You'll recognize it as the value you type into the "Company ID"
field on your own ConnectWise login screen, before your username and
password. It's usually a single word with no spaces (e.g. `threadgrowth`).
If you're not sure, ask whoever normally logs into ConnectWise Manage at
your organization, or check the login page itself.

## 2. Run it

If you haven't already, see the root [README.md](../README.md) first for
installing Python and downloading this tool.

**macOS:**
```
python3 -m pip install -r ../requirements.txt
python3 cw_ticket_report.py --days 90
```

**Windows:**
```
python -m pip install -r ../requirements.txt
python cw_ticket_report.py --days 90
```

It'll prompt you for each credential one at a time (Company ID, Public
Key, Private Key, site URL) — just type or paste each one and press Enter.

(Advanced/optional: credentials can also be set as environment variables
ahead of time to skip the prompts — `CW_COMPANY_ID`, `CW_PUBLIC_KEY`,
`CW_PRIVATE_KEY`, `CW_SITE_URL`. The syntax for this differs by OS/shell,
so if you're not sure, just skip this and answer the prompts instead.
`CW_CLIENT_ID` isn't needed either way — it's built into the script.)

## 3. Excluding boards (optional)

If any Service Boards only receive automated alerts (RMM/monitoring
tickets, not real customer requests), exclude them so they don't inflate
the ticket counts:

```
python3 cw_ticket_report.py --list-boards
```

This prints every Service Board with its ID, e.g.:

```
     5  Automated Alerts
     1  Help Desk
     3  Onboarding
```

Then re-run with `--exclude-boards`, using either the name or the ID
(comma-separate multiple boards; mixing names and IDs is fine):

```
python3 cw_ticket_report.py --days 90 --exclude-boards "Automated Alerts"
python3 cw_ticket_report.py --days 90 --exclude-boards "5,Onboarding"
```

## 4. Output

- `thread_ticket_report.csv` — anonymized, safe to share with your Thread rep
- `local_only_customer_mapping.csv` — real customer names behind each label.
  **Keep this. Do not share it.**

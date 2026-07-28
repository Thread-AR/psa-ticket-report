# ConnectWise Manage connector

Validated against a live ConnectWise Manage demo instance — clean run with
no auth errors, and ticket/customer counts scaled sensibly across multiple
lookback windows (e.g. 187 tickets over 30 days vs. 413 over 90 days,
consistent customer count), confirming the date filter behaves correctly.

## 1. Generate read-only API credentials in ConnectWise

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
3. Create/assign a security role using the naming above, with exactly two
   non-None permissions — everything else should stay at **None**:
   - **Companies > Company Maintenance**: Inquire = **All**
   - **Service Desk > Service Tickets**: Inquire = **All**
4. Under that member, go to **API Keys** and generate a Public/Private key pair

You'll end up with three values: Company ID, Public Key, Private Key,
plus your ConnectWise **site URL** (e.g. `https://na.myconnectwise.net`).
(A Client ID is also required by ConnectWise's API, but this tool already
has one built in — you don't need to register your own.)

## 2. Run it

```
pip install -r ../requirements.txt
python cw_ticket_report.py --days 90
```

Or set credentials as environment variables ahead of time to skip prompts:

```
export CW_COMPANY_ID="yourcompany"
export CW_PUBLIC_KEY="..."
export CW_PRIVATE_KEY="..."
export CW_SITE_URL="https://na.myconnectwise.net"
```

(`CW_CLIENT_ID` isn't needed — it's built into the script. Only set it if
you have a specific reason to override the default.)

## 3. Output

- `thread_ticket_report.csv` — anonymized, safe to share with your Thread rep
- `local_only_customer_mapping.csv` — real customer names behind each label.
  **Keep this. Do not share it.**

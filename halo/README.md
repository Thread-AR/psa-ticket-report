# HaloPSA connector

Validated against a live HaloPSA demo instance — the permission set below
is the exact minimal configuration confirmed to work (record counts were
cross-checked across multiple lookback windows to confirm the date filter
behaves correctly).

## 1. Create a read-only API application in HaloPSA

Suggested naming (makes it obvious to any admin later what this is and
that it's safe to remove once the report's generated):

- **Application Name**: `Thread Ticket Report (Read-Only)`
- **Agent Name**: `Thread Ticket Report Agent (Read-Only)`

1. In HaloPSA, go to **Configuration > Integrations > HaloPSA API**.
2. Click **View Applications**, then add a new application using the name above.
3. Give it a login type of **Client ID and Secret (Services)**.
4. Create a dedicated **Agent** (using the agent name above) — check the
   **API-only agent** box, since this agent only exists to scope
   permissions and never logs into the UI.
5. Assign that agent a custom Role with this exact configuration:

   **Departments & Teams tab**
   - Teams: none
   - Departments: none
   - Membership level to all Departments: **View all** (can view all
     tickets in all departments)

   **Permissions tab**
   - Feature access > Ticket access level: **Read Only**
   - Feature access > Customers access level: **Read Only**
   - Ticket permissions > Can view Tickets that are assigned to other
     Agents: **Yes**
   - Client restrictions > Allow use of all Customers: **Yes**

6. On the Application itself, enable the `read.tickets` and
   `read.customers` permissions.
7. Save, then copy the generated **Client ID** and **Client Secret**.

Note: the Application's own permission checkboxes (step 6) and the Agent's
Role (step 5) are two separate layers — missing either one causes a 403
even if the other is fully configured.

## 2. Run it

```
pip install -r ../requirements.txt
python halo_ticket_report.py --days 90
```

Or set credentials as environment variables ahead of time to skip prompts:

```
export HALO_BASE_URL="https://yourinstance.halopsa.com"
export HALO_CLIENT_ID="..."
export HALO_CLIENT_SECRET="..."
```

`HALO_TENANT` and `HALO_SCOPE` are optional — only set `HALO_TENANT` if your
instance uses a shared multi-tenant auth server (uncommon for self-hosted or
single-tenant cloud instances). `HALO_SCOPE` defaults to `all`.

## 3. Output

- `thread_ticket_report.csv` — anonymized, safe to share with your Thread rep
- `local_only_customer_mapping.csv` — real customer names behind each label.
  **Keep this. Do not share it.**

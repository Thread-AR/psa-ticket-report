# ConnectWise Manage connector

## 1. Generate read-only API credentials in ConnectWise

You'll need a ConnectWise Manage API member with **read-only access to
Service Tickets and Companies**. Recommended: create a dedicated API-only
member rather than reusing a personal login.

1. In ConnectWise Manage, go to **System > Members > API Members**
2. Add a new API member, restrict its security role to read-only on
   **Service Tickets** and **Company** modules
3. Under that member, go to **API Keys** and generate a Public/Private key pair
4. Separately, register an app in the
   [ConnectWise Developer Portal](https://developer.connectwise.com/) to get
   a **Client ID** (this is a one-time setup per ConnectWise partner org —
   your CW admin may already have one)

You'll end up with four values: Company ID, Public Key, Private Key, Client ID,
plus your ConnectWise **site URL** (e.g. `https://na.myconnectwise.net`).

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
export CW_CLIENT_ID="..."
export CW_SITE_URL="https://na.myconnectwise.net"
```

## 3. Output

- `thread_ticket_report.csv` — anonymized, safe to share with your Thread rep
- `local_only_customer_mapping.csv` — real customer names behind each label.
  **Keep this. Do not share it.**

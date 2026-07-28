#!/usr/bin/env python3
"""
Thread Ticket Volume Report — ConnectWise Manage connector
------------------------------------------------------------
Runs entirely on your machine. Uses read-only ConnectWise Manage API
credentials that YOU generate and control. Nothing is sent to Thread —
this script only talks to your own ConnectWise instance and writes a
local report to disk.

Usage:
    python cw_ticket_report.py --days 90
"""

import argparse
import base64
import getpass
import os
import sys
from datetime import datetime, timedelta, timezone

import requests

# Allow running this script directly from the connectwise/ folder while
# still reaching shared/report_utils.py one level up.
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from shared.report_utils import aggregate_by_customer, anonymize, write_report, write_local_mapping


# ---------------------------------------------------------------------------
# Config / credential handling
# ---------------------------------------------------------------------------

# Thread's own Client ID, registered once in the ConnectWise Developer
# Portal. This identifies the *software* making the API call, not any
# particular prospect's instance, so every prospect running this script
# shares the same value — no per-prospect Developer Portal registration
# needed. Override via CW_CLIENT_ID only if testing against a differently
# registered integration.
DEFAULT_CLIENT_ID = "86d92ab9-1329-4360-bade-82d11c909eb2"


def load_credentials():
    company_id = os.environ.get("CW_COMPANY_ID") or input("ConnectWise Company ID: ").strip()
    public_key = os.environ.get("CW_PUBLIC_KEY") or input("ConnectWise API Public Key: ").strip()
    private_key = os.environ.get("CW_PRIVATE_KEY") or getpass.getpass("ConnectWise API Private Key: ").strip()
    client_id = os.environ.get("CW_CLIENT_ID", DEFAULT_CLIENT_ID)
    site_url = os.environ.get("CW_SITE_URL") or input(
        "ConnectWise site base URL (e.g. https://na.myconnectwise.net): "
    ).strip().rstrip("/")

    return {
        "company_id": company_id,
        "public_key": public_key,
        "private_key": private_key,
        "client_id": client_id,
        "site_url": site_url,
    }


def build_auth_header(creds):
    """
    ConnectWise Manage REST API uses HTTP Basic auth where the username
    is `CompanyID+PublicKey` and the password is the PrivateKey.
    """
    combined = f"{creds['company_id']}+{creds['public_key']}:{creds['private_key']}"
    encoded = base64.b64encode(combined.encode("utf-8")).decode("utf-8")
    return {
        "Authorization": f"Basic {encoded}",
        "clientId": creds["client_id"],
        "Accept": "application/json",
        "Content-Type": "application/json",
    }


# ---------------------------------------------------------------------------
# API calls
# ---------------------------------------------------------------------------

def fetch_tickets(creds, start_date, page_size=1000):
    """
    Pulls tickets created on/after start_date, paginating through results,
    and normalizes each into {"customer_id": ..., "customer_name": ...}
    for the shared aggregation logic.
    """
    headers = build_auth_header(creds)
    base = f"{creds['site_url']}/v4_6_release/apis/3.0/service/tickets"

    conditions = f"dateEntered>=[{start_date.strftime('%Y-%m-%dT%H:%M:%SZ')}]"
    fields = "id,company/id,company/identifier,company/name,dateEntered"

    normalized = []
    page = 1

    while True:
        params = {
            "conditions": conditions,
            "fields": fields,
            "pageSize": page_size,
            "page": page,
        }
        resp = requests.get(base, headers=headers, params=params, timeout=30)

        if resp.status_code == 401:
            raise SystemExit(
                "Authentication failed (401). Double-check your Company ID, "
                "Public/Private key pair, and Client ID."
            )
        if resp.status_code == 403:
            raise SystemExit(
                "Access forbidden (403). The API member tied to this key pair "
                "likely needs read access to Service Tickets."
            )
        resp.raise_for_status()

        batch = resp.json()
        if not batch:
            break

        for t in batch:
            company = t.get("company") or {}
            cid = company.get("id")
            if cid is None:
                continue
            normalized.append({
                "customer_id": cid,
                "customer_name": company.get("name") or company.get("identifier"),
            })

        print(f"  fetched page {page} ({len(batch)} tickets, {len(normalized)} total so far)")

        if len(batch) < page_size:
            break
        page += 1

    return normalized


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="Thread Ticket Volume Report — ConnectWise Manage")
    parser.add_argument("--days", type=int, default=90, help="Lookback window in days (default: 90)")
    args = parser.parse_args()

    print("Thread Ticket Volume Report Tool — ConnectWise Manage")
    print("This runs locally. Your credentials and ticket data never leave this machine.\n")

    creds = load_credentials()
    start_date = datetime.now(timezone.utc) - timedelta(days=args.days)

    print(f"\nFetching tickets since {start_date.strftime('%Y-%m-%d')}...")
    normalized_tickets = fetch_tickets(creds, start_date)
    print(f"Retrieved {len(normalized_tickets)} tickets.\n")

    counts, names = aggregate_by_customer(normalized_tickets)
    rows, mapping = anonymize(counts, names)

    report_path = write_report(rows, args.days, psa_name="ConnectWise Manage")
    mapping_path = write_local_mapping(mapping)

    print("Done!\n")
    print(f"  Anonymized report (share this with your Thread rep): {report_path}")
    print(f"  Local-only name mapping (keep this, do NOT share):   {mapping_path}\n")
    print(f"Total customers: {len(rows)}   Total tickets: {sum(r['ticket_count'] for r in rows)}")


if __name__ == "__main__":
    main()

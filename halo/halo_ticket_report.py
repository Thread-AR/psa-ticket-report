#!/usr/bin/env python3
"""
Thread Ticket Volume Report — HaloPSA connector
------------------------------------------------------------
Runs entirely on your machine. Uses a read-only HaloPSA API
application (Client ID + Client Secret) that YOU generate and
control. Nothing is sent to Thread — this script only talks to
your own HaloPSA instance and writes a local report to disk.

Usage:
    python halo_ticket_report.py --days 90
"""

import argparse
import getpass
import os
import sys
from datetime import datetime, timedelta, timezone

import requests

# Allow running this script directly from the halo/ folder while
# still reaching shared/report_utils.py one level up.
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from shared.report_utils import (
    aggregate_by_customer,
    anonymize,
    write_report,
    write_local_mapping,
    parse_board_exclusions,
    is_board_excluded,
)


# ---------------------------------------------------------------------------
# Config / credential handling
# ---------------------------------------------------------------------------

def load_credentials():
    base_url = os.environ.get("HALO_BASE_URL") or input(
        "HaloPSA site base URL (e.g. https://yourinstance.halopsa.com): "
    ).strip().rstrip("/")
    client_id = os.environ.get("HALO_CLIENT_ID") or input("HaloPSA API Client ID: ").strip()
    client_secret = os.environ.get("HALO_CLIENT_SECRET") or getpass.getpass(
        "HaloPSA API Client Secret: "
    ).strip()
    # Only needed on some hosted multi-tenant setups where the auth server
    # is shared across instances. Leave HALO_TENANT unset if unsure.
    tenant = os.environ.get("HALO_TENANT", "").strip()
    scope = os.environ.get("HALO_SCOPE", "all").strip()

    return {
        "base_url": base_url,
        "client_id": client_id,
        "client_secret": client_secret,
        "tenant": tenant,
        "scope": scope,
    }


# ---------------------------------------------------------------------------
# API calls
# ---------------------------------------------------------------------------

def get_access_token(creds):
    """
    HaloPSA uses OAuth2 client-credentials: exchange Client ID + Client
    Secret at the tenant's /auth/token endpoint for a bearer access token.
    """
    token_url = f"{creds['base_url']}/auth/token"
    payload = {
        "grant_type": "client_credentials",
        "client_id": creds["client_id"],
        "client_secret": creds["client_secret"],
        "scope": creds["scope"],
    }
    if creds["tenant"]:
        payload["tenant"] = creds["tenant"]

    resp = requests.post(token_url, data=payload, timeout=30)
    if resp.status_code == 401:
        raise SystemExit(
            "Authentication failed (401). Double-check your Client ID and Client Secret."
        )
    resp.raise_for_status()

    token = resp.json().get("access_token")
    if not token:
        raise SystemExit(f"No access_token in response from {token_url}: {resp.text}")
    return token


def fetch_teams(creds, token):
    """
    Returns every Team as [{"id": ..., "name": ...}, ...]. Used by
    --list-boards to help a prospect find the team to exclude (e.g. an
    automated-alerts team that shouldn't count as a real ticket).
    """
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/json",
    }
    resp = requests.get(f"{creds['base_url']}/api/Team", headers=headers, timeout=30)
    resp.raise_for_status()
    body = resp.json()
    teams = body.get("teams") if isinstance(body, dict) else body
    return [{"id": t.get("id"), "name": t.get("name")} for t in (teams or [])]


def fetch_tickets(creds, token, start_date, excluded_boards=None, page_size=100):
    """
    Pulls tickets opened on/after start_date, paginating through results,
    and normalizes each into {"customer_id": ..., "customer_name": ...}
    for the shared aggregation logic. Tickets whose team matches
    excluded_boards (by ID or name) are dropped before normalization.

    Returns (normalized_tickets, excluded_count).
    """
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/json",
    }
    tickets_url = f"{creds['base_url']}/api/Tickets"

    normalized = []
    excluded_count = 0
    page = 1

    while True:
        params = {
            "pageinate": "true",
            "page_size": page_size,
            "page_no": page,
            "datesearch": "dateoccured",
            "startdate": start_date.strftime("%Y-%m-%d"),
            "enddate": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
        }
        resp = requests.get(tickets_url, headers=headers, params=params, timeout=30)

        if resp.status_code == 401:
            raise SystemExit(
                "Authentication failed (401) fetching tickets. Your token may have "
                "expired mid-run, or the API application lacks Ticket read access."
            )
        if resp.status_code == 403:
            raise SystemExit(
                "Access forbidden (403). The Agent tied to this API application "
                "likely needs read access to Tickets and Clients."
            )
        resp.raise_for_status()

        body = resp.json()
        batch = body.get("tickets") if isinstance(body, dict) else body
        if not batch:
            break

        for t in batch:
            if is_board_excluded(t.get("team_id"), t.get("team"), excluded_boards):
                excluded_count += 1
                continue

            cid = t.get("client_id")
            if cid is None:
                continue
            normalized.append({
                "customer_id": cid,
                "customer_name": t.get("client_name"),
            })

        print(f"  fetched page {page} ({len(batch)} tickets, {len(normalized)} total so far)")

        if len(batch) < page_size:
            break
        page += 1

    return normalized, excluded_count


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="Thread Ticket Volume Report — HaloPSA")
    parser.add_argument("--days", type=int, default=90, help="Lookback window in days (default: 90)")
    parser.add_argument(
        "--exclude-boards", type=str, default=None,
        help="Comma-separated list of Team names and/or IDs to exclude "
             "(e.g. an automated-alerts team that shouldn't count as a real ticket)"
    )
    parser.add_argument(
        "--list-boards", action="store_true",
        help="List all Teams with their IDs and exit (use this to find "
             "values for --exclude-boards)"
    )
    args = parser.parse_args()

    print("Thread Ticket Volume Report Tool — HaloPSA")
    print("This runs locally. Your credentials and ticket data never leave this machine.\n")

    creds = load_credentials()

    print("\nAuthenticating...")
    token = get_access_token(creds)

    if args.list_boards:
        teams = fetch_teams(creds, token)
        print("\nTeams in this HaloPSA instance:")
        for t in sorted(teams, key=lambda t: (t["name"] or "").lower()):
            print(f"  {t['id']:>6}  {t['name']}")
        return

    excluded_boards = parse_board_exclusions(args.exclude_boards)
    start_date = datetime.now(timezone.utc) - timedelta(days=args.days)

    print(f"Fetching tickets since {start_date.strftime('%Y-%m-%d')}...")
    normalized_tickets, excluded_count = fetch_tickets(creds, token, start_date, excluded_boards=excluded_boards)
    print(f"Retrieved {len(normalized_tickets)} tickets.")
    if excluded_boards:
        print(f"Excluded {excluded_count} tickets from team(s): {args.exclude_boards}")
    print()

    counts, names = aggregate_by_customer(normalized_tickets)
    rows, mapping = anonymize(counts, names)

    report_path = write_report(rows, args.days, psa_name="HaloPSA")
    mapping_path = write_local_mapping(mapping)

    print("Done!\n")
    print(f"  Anonymized report (share this with your Thread rep): {report_path}")
    print(f"  Local-only name mapping (keep this, do NOT share):   {mapping_path}\n")
    print(f"Total customers: {len(rows)}   Total tickets: {sum(r['ticket_count'] for r in rows)}")


if __name__ == "__main__":
    main()

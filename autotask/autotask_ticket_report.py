#!/usr/bin/env python3
"""
Thread Ticket Volume Report — Autotask connector
------------------------------------------------------------
Runs entirely on your machine. Uses a read-only Autotask API user
(Username + Secret) plus an API Integration Code, all of which YOU
generate and control. Nothing is sent to Thread — this script only
talks to your own Autotask instance and writes a local report to disk.

Usage:
    python autotask_ticket_report.py --days 90
"""

import argparse
import getpass
import os
import sys
from datetime import datetime, timedelta, timezone

import requests

# Allow running this script directly from the autotask/ folder while
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


ZONE_LOOKUP_URL = "https://webservices.autotask.net/atservicesrest/v1.0/zoneInformation"
COMPANY_ID_BATCH_SIZE = 200


# ---------------------------------------------------------------------------
# Config / credential handling
# ---------------------------------------------------------------------------

def load_credentials():
    username = os.environ.get("AUTOTASK_USERNAME") or input("Autotask API Username: ").strip()
    secret = os.environ.get("AUTOTASK_SECRET") or getpass.getpass("Autotask API Secret: ").strip()
    integration_code = os.environ.get("AUTOTASK_INTEGRATION_CODE") or input(
        "Autotask API Integration Code: "
    ).strip()

    return {
        "username": username,
        "secret": secret,
        "integration_code": integration_code,
    }


def build_auth_headers(creds):
    return {
        "UserName": creds["username"],
        "Secret": creds["secret"],
        "ApiIntegrationCode": creds["integration_code"],
        "Content-Type": "application/json",
        "Accept": "application/json",
    }


# ---------------------------------------------------------------------------
# API calls
# ---------------------------------------------------------------------------

def get_zone_base_url(creds):
    """
    Autotask's REST API is split across multiple physical zones. Every
    integration must resolve the correct zone-specific base URL for this
    account before making any other call. This lookup itself is
    unauthenticated (it only needs to know the username's domain).
    """
    resp = requests.get(ZONE_LOOKUP_URL, params={"user": creds["username"]}, timeout=30)
    if resp.status_code == 401:
        raise SystemExit("Zone lookup failed (401). Double-check your Autotask API Username.")
    resp.raise_for_status()

    zone_url = resp.json().get("url")
    if not zone_url:
        raise SystemExit(f"No zone URL in response from {ZONE_LOOKUP_URL}: {resp.text}")
    return zone_url.rstrip("/")


def fetch_tickets(creds, base_url, start_date, page_size=500):
    """
    Pulls raw ticket records created on/after start_date, paginating via
    the API's own nextPageUrl until exhausted. Returns a list of dicts with
    (at least) "id", "companyID", and "createDate".
    """
    headers = build_auth_headers(creds)
    url = f"{base_url}/v1.0/Tickets/query"
    body = {
        "MaxRecords": page_size,
        "filter": [
            {"op": "gte", "field": "createDate", "value": start_date.strftime("%Y-%m-%dT%H:%M:%SZ")}
        ],
    }

    tickets = []
    while url:
        if body is not None:
            resp = requests.post(url, headers=headers, json=body, timeout=30)
        else:
            # Subsequent pages: nextPageUrl is a complete, ready-to-use GET URL.
            resp = requests.get(url, headers=headers, timeout=30)

        if resp.status_code == 401:
            raise SystemExit(
                "Authentication failed (401). Double-check your Username, Secret, and "
                "Integration Code."
            )
        if resp.status_code == 403:
            raise SystemExit(
                "Access forbidden (403). The API user likely needs read access to "
                "Tickets and Companies."
            )
        resp.raise_for_status()

        page = resp.json()
        batch = page.get("items", [])
        tickets.extend(batch)
        print(f"  fetched page ({len(batch)} tickets, {len(tickets)} total so far)")

        url = (page.get("pageDetails") or {}).get("nextPageUrl")
        body = None

    return tickets


def fetch_queues(creds, base_url):
    """
    Returns every Ticket Queue as [{"id": ..., "name": ...}, ...]. Autotask
    doesn't expose a standalone Queues entity — queue names live as
    picklist values on the Ticket entity's queueID field, retrieved via
    entity field metadata. Used by --list-boards (to help a prospect find
    the queue to exclude) and to resolve queue names for --exclude-boards
    matching by name.
    """
    headers = build_auth_headers(creds)
    url = f"{base_url}/v1.0/Tickets/entityInformation/fields"
    resp = requests.get(url, headers=headers, timeout=30)
    resp.raise_for_status()

    fields = resp.json().get("fields", [])
    queue_field = next((f for f in fields if f.get("name") == "queueID"), None)
    if not queue_field:
        return []
    return [
        {"id": v["value"], "name": v.get("label")}
        for v in queue_field.get("picklistValues", [])
    ]


def filter_tickets_by_board(raw_tickets, excluded_boards, queue_names):
    """
    Drops tickets whose queueID matches excluded_boards (by ID or by name,
    via the queue_names id->name lookup). Returns (kept_tickets, excluded_count).
    """
    if not excluded_boards:
        return raw_tickets, 0

    kept = []
    excluded_count = 0
    for t in raw_tickets:
        qid = t.get("queueID")
        if is_board_excluded(qid, queue_names.get(qid), excluded_boards):
            excluded_count += 1
            continue
        kept.append(t)
    return kept, excluded_count


def fetch_company_names(creds, base_url, company_ids):
    """
    Resolves company (customer) display names for a set of companyIDs.
    Autotask's Tickets entity only carries the numeric companyID — the
    name lives on the separate Companies entity — so this batches lookups
    via an "in" filter (chunked, since Autotask limits filter list size).
    """
    headers = build_auth_headers(creds)
    url = f"{base_url}/v1.0/Companies/query"

    names = {}
    company_ids = sorted(company_ids)
    for i in range(0, len(company_ids), COMPANY_ID_BATCH_SIZE):
        chunk = company_ids[i:i + COMPANY_ID_BATCH_SIZE]
        body = {"filter": [{"op": "in", "field": "id", "value": chunk}]}

        resp = requests.post(url, headers=headers, json=body, timeout=30)
        resp.raise_for_status()

        for company in resp.json().get("items", []):
            names[company["id"]] = company.get("companyName")

    return names


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="Thread Ticket Volume Report — Autotask")
    parser.add_argument("--days", type=int, default=90, help="Lookback window in days (default: 90)")
    parser.add_argument(
        "--exclude-boards", type=str, default=None,
        help="Comma-separated list of ticket Queue names and/or IDs to exclude "
             "(e.g. an automated-alerts queue that shouldn't count as a real ticket)"
    )
    parser.add_argument(
        "--list-boards", action="store_true",
        help="List all ticket Queues with their IDs and exit (use this to find "
             "values for --exclude-boards)"
    )
    args = parser.parse_args()

    print("Thread Ticket Volume Report Tool — Autotask")
    print("This runs locally. Your credentials and ticket data never leave this machine.\n")

    creds = load_credentials()

    print("\nResolving your Autotask zone...")
    base_url = get_zone_base_url(creds)

    if args.list_boards:
        queues = fetch_queues(creds, base_url)
        print("\nTicket Queues in this Autotask instance:")
        for q in sorted(queues, key=lambda q: (q["name"] or "").lower()):
            print(f"  {q['id']:>6}  {q['name']}")
        return

    excluded_boards = parse_board_exclusions(args.exclude_boards)
    start_date = datetime.now(timezone.utc) - timedelta(days=args.days)

    print(f"Fetching tickets since {start_date.strftime('%Y-%m-%d')}...")
    raw_tickets = fetch_tickets(creds, base_url, start_date)
    print(f"Retrieved {len(raw_tickets)} tickets.")

    if excluded_boards:
        queue_names = {q["id"]: q["name"] for q in fetch_queues(creds, base_url)}
        raw_tickets, excluded_count = filter_tickets_by_board(raw_tickets, excluded_boards, queue_names)
        print(f"Excluded {excluded_count} tickets from queue(s): {args.exclude_boards}")
    print()

    company_ids = {t["companyID"] for t in raw_tickets if t.get("companyID") is not None}
    print(f"Resolving names for {len(company_ids)} companies...")
    names_by_id = fetch_company_names(creds, base_url, company_ids)

    normalized_tickets = [
        {
            "customer_id": t["companyID"],
            "customer_name": names_by_id.get(t["companyID"]),
        }
        for t in raw_tickets
        if t.get("companyID") is not None
    ]

    counts, names = aggregate_by_customer(normalized_tickets)
    rows, mapping = anonymize(counts, names)

    report_path = write_report(rows, args.days, psa_name="Autotask")
    mapping_path = write_local_mapping(mapping)

    print("Done!\n")
    print(f"  Anonymized report (share this with your Thread rep): {report_path}")
    print(f"  Local-only name mapping (keep this, do NOT share):   {mapping_path}\n")
    print(f"Total customers: {len(rows)}   Total tickets: {sum(r['ticket_count'] for r in rows)}")


if __name__ == "__main__":
    main()

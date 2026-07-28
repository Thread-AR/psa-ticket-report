"""
Shared logic used by every PSA connector (ConnectWise, Autotask, Halo).

Each PSA-specific script is responsible for pulling raw tickets from its
own API and normalizing them into a simple list of dicts:

    [{"customer_id": <str|int>, "customer_name": <str>}, ...]

One dict per ticket. That's the only contract between a connector and
this shared module — everything below (aggregation, anonymization,
CSV output) is PSA-agnostic.
"""

import csv
from collections import defaultdict


def aggregate_by_customer(normalized_tickets):
    """
    Takes the normalized ticket list and returns:
      - counts: {customer_id: ticket_count}
      - names:  {customer_id: customer_name}
    """
    counts = defaultdict(int)
    names = {}
    for t in normalized_tickets:
        cid = t.get("customer_id")
        if cid is None:
            continue
        counts[cid] += 1
        names[cid] = t.get("customer_name") or f"Customer {cid}"
    return counts, names


def anonymize(counts, names):
    """
    Sorts customers by ticket volume (descending) and replaces real names
    with sequential labels (Customer 001, Customer 002, ...).

    Returns:
      - rows: [{"customer_label": ..., "ticket_count": ...}, ...] — safe to share
      - mapping: [{"customer_label": ..., "real_name": ...}, ...] — LOCAL ONLY,
        never included in anything meant to be shared externally
    """
    ordered = sorted(counts.items(), key=lambda kv: kv[1], reverse=True)
    rows = []
    mapping = []
    for i, (cid, count) in enumerate(ordered, start=1):
        label = f"Customer {i:03d}"
        rows.append({"customer_label": label, "ticket_count": count})
        mapping.append({"customer_label": label, "real_name": names.get(cid, "")})
    return rows, mapping


def write_report(rows, days, psa_name, out_path="thread_ticket_report.csv"):
    """
    Writes the anonymized, shareable report. Deliberately contains ONLY
    ticket counts by anonymized customer label — no pricing, no license
    math, nothing beyond raw volume. That calculation happens separately,
    internally, by the Thread team reviewing this file.
    """
    with open(out_path, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.writer(f)
        writer.writerow([f"Thread Ticket Volume Report — {psa_name} — trailing {days} days"])
        writer.writerow([])
        writer.writerow(["Customer (anonymized)", "Ticket Count"])
        for r in rows:
            writer.writerow([r["customer_label"], r["ticket_count"]])
    return out_path


def write_local_mapping(mapping, out_path="local_only_customer_mapping.csv"):
    """
    Writes the real-name mapping. This file stays on the prospect's
    machine — it is never meant to be attached to anything sent externally.
    """
    with open(out_path, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.writer(f)
        writer.writerow(["customer_label", "real_name"])
        for m in mapping:
            writer.writerow([m["customer_label"], m["real_name"]])
    return out_path

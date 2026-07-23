# Thread Ticket Volume Report Tool

A small, local, transparent tool to help MSP prospects generate an
anonymized ticket-volume-by-customer report from their PSA, for use in
Thread's sales discovery process.

**This tool does not calculate license recommendations.** It only
produces raw ticket counts per (anonymized) customer over a configurable
lookback window. Thread's team reviews that report and provides licensing
guidance separately — that logic intentionally lives outside this repo.

**Nothing here sends data to Thread.** Every script talks only to the
prospect's own PSA, using credentials they generate and control, and
writes output only to their local disk.

## Supported PSAs

| PSA                | Status       |
|--------------------|--------------|
| ConnectWise Manage | ✅ Built     |
| Autotask           | 🚧 Planned   |
| HaloPSA            | 🚧 Planned   |

## Repo structure

```
psa-license-report/
├── shared/
│   └── report_utils.py       # aggregation, anonymization, CSV output — shared by all connectors
├── connectwise/
│   ├── cw_ticket_report.py
│   └── README.md
├── autotask/
│   └── README.md              # scoped, not yet built
├── halo/
│   └── README.md               # scoped, not yet built
├── requirements.txt
└── README.md                   # you are here
```

## How the output works

Every connector writes two files, on purpose kept separate:

1. **`thread_ticket_report.csv`** — anonymized (Customer 001, Customer 002, ...)
   ticket counts. Safe to send to your Thread rep.
2. **`local_only_customer_mapping.csv`** — the real names behind each label.
   Stays on the prospect's machine. Never sent anywhere.

## Getting started (for whichever PSA you use)

See the README inside that PSA's folder (e.g. `connectwise/README.md`) for
credential setup and run instructions.

## Contributing / building the next connector

If you're picking up Autotask or Halo, read that folder's README first —
it scopes out the auth flow and what "done" looks like. The only contract
with `shared/report_utils.py` is that your connector normalizes tickets
into: `{"customer_id": ..., "customer_name": ...}` — one dict per ticket.
Everything else (aggregation, anonymization, CSV writing) is already handled.

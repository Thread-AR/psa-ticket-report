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
| Autotask           | ✅ Built     |
| HaloPSA            | ✅ Built     |

## Two ways to run this

**Desktop app (recommended)** — a point-and-click wizard: pick your PSA, it
walks you through the exact admin screens to set up API credentials, helps
you fill in each field, then runs everything and shows you where the output
landed. No terminal commands beyond the one-time setup below.

<p>
  <img src="gui/screenshots/01-select-psa.png" alt="Select your PSA" width="32%">
  <img src="gui/screenshots/02-setup-instructions.png" alt="Guided credential setup instructions" width="32%">
  <img src="gui/screenshots/03-credentials.png" alt="Credentials form with inline help" width="32%">
</p>

See "Running the desktop app" below. (More screenshots of the full flow are
in [gui/README.md](gui/README.md).)

**Command line** — the original per-PSA scripts, run directly from a
terminal. Useful if you're already comfortable there, or want to pass
credentials via environment variables. See "Running from the command line"
below.

Both do exactly the same thing under the hood and produce the same two
output files — the desktop app is just a friendlier way to run the same
connector script.

## Permissions you'll need

Setting up API credentials requires **admin-level access to your PSA
instance** — specifically, the ability to create a new API user/agent,
create or assign a security role/level, and generate API keys or a
secret. This is usually not something a standard technician-level login
can do. If you don't have this access yourself, you'll need your PSA
administrator (or someone at your organization who has that access) to
either do this setup or grant it to you temporarily.

Each PSA's README documents the exact admin screens and permissions
needed:
- [ConnectWise Manage](connectwise/README.md) — System > Members, Security Roles
- [Autotask](autotask/README.md) — Admin > Resources/Users (HR), Security Levels
- [HaloPSA](halo/README.md) — Configuration > Integrations, Teams > Roles/Agents

## Repo structure

```
psa-ticket-report/
├── shared/
│   └── report_utils.py            # aggregation, anonymization, CSV output — shared by all connectors
├── connectwise/
│   ├── cw_ticket_report.py
│   └── README.md
├── autotask/
│   ├── autotask_ticket_report.py
│   └── README.md
├── halo/
│   ├── halo_ticket_report.py
│   └── README.md
├── gui/
│   ├── app.py                      # desktop app entry point — python gui/app.py
│   ├── psa_config.py               # per-PSA setup instructions, credential fields, help text
│   ├── runner.py                   # runs a connector script as a subprocess
│   ├── web/                        # HTML/CSS/JS wizard UI
│   ├── screenshots/                # docs screenshots (this README, gui/README.md)
│   └── README.md
├── requirements.txt
└── README.md                       # you are here
```

## How the output works

Every connector writes two files, on purpose kept separate:

1. **`thread_ticket_report.csv`** — anonymized (Customer 001, Customer 002, ...)
   ticket counts. Safe to send to your Thread rep.
2. **`local_only_customer_mapping.csv`** — the real names behind each label.
   Stays on the prospect's machine. Never sent anywhere.

## Before you start: install Python

You only need to do this once. If you're not sure whether you already have
Python, open a terminal (see below for how) and type `python3 --version`
(macOS) or `python --version` (Windows). If you see a version number of
3.9 or higher, skip to "Download this tool."

**How to open a terminal:**
- **Windows**: Click the Start menu, type `Command Prompt` (or
  `PowerShell`), and press Enter.
- **macOS**: Open Spotlight (⌘+Space), type `Terminal`, and press Enter.

**If Python isn't installed:**
1. Go to [python.org/downloads](https://www.python.org/downloads/) and
   download the latest version for your operating system.
2. Run the installer.
   - **Windows only — do not skip this**: on the very first installer
     screen, check the box at the bottom that says **"Add python.exe to
     PATH"** before clicking Install. This is the single most common
     thing people miss, and without it, none of the commands below will
     work.
   - **macOS**: just run through the installer with the default options.
3. Close and reopen your terminal window (so it picks up the new
   installation), then confirm it worked:
   - **Windows**: `python --version`
   - **macOS**: `python3 --version`

   You should see something like `Python 3.12.x`. If you instead see an
   error like `'python' is not recognized` or `command not found`, the
   install didn't complete correctly or (on Windows) the PATH box wasn't
   checked — try reinstalling.

## Download this tool

1. Go to this repository's page on GitHub.
2. Click the green **Code** button, then **Download ZIP**.
3. Find the downloaded ZIP file (usually in your Downloads folder) and
   extract/unzip it. Remember where you extracted it — you'll need to
   navigate there in the terminal next.

## Running the desktop app

1. Open a terminal (see above) and navigate into the folder you just
   extracted. The easiest way: type `cd ` (with a trailing space), then
   **drag the extracted folder** from Finder/File Explorer directly into
   the terminal window — it will fill in the correct path for you — then
   press Enter.
2. Install the dependencies this tool needs:
   - **Windows**: `python -m pip install -r requirements.txt`
   - **macOS**: `python3 -m pip install -r requirements.txt`

   (A message mentioning "Defaulting to user installation" is normal, not
   an error. On macOS you may also see a `NotOpenSSLWarning` — that's a
   harmless warning about the system's built-in SSL library and can be
   ignored.)
3. Launch the app:
   - **Windows**: `python gui\app.py`
   - **macOS**: `python3 gui/app.py`
4. A window opens with the wizard: pick your PSA, follow the setup steps
   it shows you, enter your credentials (with help text for every field),
   set your lookback window and any board exclusions, choose where to
   save the output, then generate the report. See
   [gui/README.md](gui/README.md) for a full walkthrough with screenshots.

This has been tested on macOS. It should also work on Windows (the
underlying `pywebview` library uses the Edge WebView2 runtime that ships
with modern Windows), but that hasn't been separately verified in this
repo yet — if you hit issues on Windows, the command-line path below is a
reliable fallback.

## Running from the command line

If you'd rather not use the desktop app — or it doesn't work on your
machine — each PSA's script can be run directly from a terminal, the same
way the desktop app runs it internally:

1. Follow steps 1–2 above (extract the ZIP, `pip install -r requirements.txt`).
2. Navigate into your PSA's folder the same drag-and-drop way (e.g.
   `cd ` then drag the `connectwise` folder in), and follow the README
   there (e.g. `connectwise/README.md`) for credential setup and exact
   run instructions.

### If something goes wrong

- **`'python' is not recognized` / `python3: command not found`** — Python
  isn't installed, or (Windows) wasn't added to PATH. Reinstall following
  the steps above.
- **`No module named requests`** (or similar) — you skipped or need to
  re-run the `pip install -r requirements.txt` step, or you're running
  the script from a different terminal window than the one where you
  installed it.
- **`python: command not found` but `python3` works, or vice versa** —
  some systems only recognize one or the other; just use whichever one
  responded with a version number in the steps above.
- **Desktop app won't launch / errors mentioning `webview` or `pyobjc`** —
  re-run the `pip install -r requirements.txt` step; if it still fails,
  fall back to the command-line instructions above and let your Thread
  contact know what error you saw.


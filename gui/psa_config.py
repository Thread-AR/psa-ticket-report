"""
Single source of truth describing each PSA connector for the GUI wrapper.

Nothing here changes how the connector scripts themselves work — this just
tells the GUI which script to run, which credential fields to collect (and
which of those are secrets), the vocabulary a given PSA uses for "board"
(ConnectWise: Service Board, Autotask: Queue, Halo: Team), and the
credential-setup instructions/field help shown in the wizard. The setup
steps and field help text below are condensed from each PSA's own README
(connectwise/README.md, autotask/README.md, halo/README.md) — keep them in
sync if those READMEs change, especially the permission gotchas.
"""

import os

GUI_DIR = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.dirname(GUI_DIR)

PSA_CONFIGS = {
    "connectwise": {
        "label": "ConnectWise Manage",
        "script_path": os.path.join(REPO_ROOT, "connectwise", "cw_ticket_report.py"),
        "board_term": "Service Board",
        "board_term_plural": "Service Boards",
        "setup": {
            "admin_note": (
                "You'll need <strong>System &gt; Members</strong> access in "
                "ConnectWise Manage to complete this setup — specifically, "
                "permission to create API Members and Security Roles. This is "
                "admin-level access, not something a standard technician login "
                "typically has. If you don't have it, ask whoever administers "
                "your ConnectWise instance to do this setup or grant you access."
            ),
            "steps": [
                "Go to <strong>System &gt; Members &gt; API Members</strong>.",
                "Add a new API member (suggested name: "
                "<strong>Thread Ticket Report (RO)</strong>).",
                "Create a security role for it with only these permissions set "
                "to <strong>Inquire = All</strong> — leave everything else at "
                "None: <strong>Companies &gt; Company Maintenance</strong>, "
                "<strong>Service Desk &gt; Service Tickets</strong>, and "
                "<strong>System &gt; Table Setup</strong>.",
                "That last one (Table Setup) is only needed for the board "
                "exclusion feature below — after enabling it, click "
                "<strong>Customize</strong> and check <strong>Service / "
                "Service Board</strong> under \"Allow access to these "
                "columns,\" or board lookups will fail with a permissions error.",
                "Under that member, go to <strong>API Keys</strong> and "
                "generate a Public/Private key pair.",
            ],
            "result_note": (
                "You'll end up with four values: Company ID, Public Key, "
                "Private Key, and your ConnectWise site URL."
            ),
        },
        "fields": [
            {
                "key": "CW_COMPANY_ID",
                "label": "Company ID",
                "secret": False,
                "help": "The short identifier for your ConnectWise instance — "
                        "the value you type into the \"Company ID\" box on your "
                        "own ConnectWise login screen (not your company's "
                        "display name). Usually one word, no spaces.",
            },
            {
                "key": "CW_PUBLIC_KEY",
                "label": "API Public Key",
                "secret": False,
                "help": "Generated in System > Members > API Members > "
                        "[your API member] > API Keys.",
            },
            {
                "key": "CW_PRIVATE_KEY",
                "label": "API Private Key",
                "secret": True,
                "help": "Generated alongside the Public Key on the same "
                        "screen — shown only once, so copy it immediately.",
            },
            {
                "key": "CW_SITE_URL",
                "label": "Site base URL",
                "secret": False,
                "placeholder": "https://na.myconnectwise.net",
                "help": "Your ConnectWise Manage web address — the URL you "
                        "normally go to log in.",
            },
        ],
    },
    "autotask": {
        "label": "Autotask",
        "script_path": os.path.join(REPO_ROOT, "autotask", "autotask_ticket_report.py"),
        "board_term": "Queue",
        "board_term_plural": "Queues",
        "setup": {
            "admin_note": (
                "You'll need admin-level access to <strong>Admin &gt; Account "
                "Settings &amp; Users &gt; Resources/Users (HR)</strong> in "
                "Autotask — specifically permission to create Security Levels "
                "and API Users. A standard technician login typically won't "
                "have this. If you don't have it, ask whoever administers your "
                "Autotask instance to do this setup or grant you access."
            ),
            "steps": [
                "Go to <strong>Admin &gt; Account Settings &amp; Users &gt; "
                "Resources/Users (HR) &gt; Security Levels</strong>.",
                "Find <strong>\"API User (system) (API-only)\"</strong> and "
                "copy it — don't use the original directly, it can't be "
                "edited and grants full access.",
                "Rename the copy (e.g. <strong>Thread Ticket Report - Read "
                "Only</strong>), then set <strong>Tickets</strong> and "
                "<strong>Companies</strong> to <strong>View only</strong> and "
                "remove access to every other module.",
                "Go to <strong>Admin &gt; Resources (Users)</strong>, click "
                "the dropdown next to <strong>+ New</strong>, and choose "
                "<strong>New API User</strong>. Set its Security Level to "
                "the copy you just made.",
                "On the Security pane, click <strong>Generate Key</strong> "
                "(becomes the Username) and <strong>Generate Secret</strong> "
                "(shown only once — copy it immediately).",
                "Set <strong>API Tracking Identifier</strong> to "
                "<strong>Custom (Internal Integration)</strong> and save.",
            ],
            "result_note": (
                "You'll end up with three values: Username, Secret, and "
                "API Integration Code."
            ),
        },
        "fields": [
            {
                "key": "AUTOTASK_USERNAME",
                "label": "API Username",
                "secret": False,
                "help": "Auto-generated when you click \"Generate Key\" on "
                        "the API user's Security pane — not something you "
                        "choose yourself.",
            },
            {
                "key": "AUTOTASK_SECRET",
                "label": "API Secret",
                "secret": True,
                "help": "Auto-generated via \"Generate Secret\" on the same "
                        "Security pane. Shown only once, so copy it right away.",
            },
            {
                "key": "AUTOTASK_INTEGRATION_CODE",
                "label": "API Integration Code",
                "secret": False,
                "help": "The tracking identifier you set when creating the "
                        "API user under \"Custom (Internal Integration).\"",
            },
        ],
    },
    "halo": {
        "label": "HaloPSA",
        "script_path": os.path.join(REPO_ROOT, "halo", "halo_ticket_report.py"),
        "board_term": "Team",
        "board_term_plural": "Teams",
        "setup": {
            "admin_note": (
                "You'll need admin-level access to <strong>Configuration &gt; "
                "Integrations &gt; HaloPSA API</strong> and <strong>Teams &gt; "
                "Roles/Agents</strong> in HaloPSA. A standard agent login "
                "typically won't have this. If you don't have it, ask "
                "whoever administers your HaloPSA instance to do this setup "
                "or grant you access."
            ),
            "steps": [
                "Go to <strong>Configuration &gt; Integrations &gt; HaloPSA "
                "API &gt; View Applications</strong>, and add a new "
                "application with login type <strong>Client ID and Secret "
                "(Services)</strong>.",
                "Create a dedicated <strong>Agent</strong> for it, checking "
                "the <strong>API-only agent</strong> box.",
                "Assign that agent a custom Role: <strong>View all</strong> "
                "ticket access across all departments, <strong>Read Only</strong> "
                "for Tickets and Customers, and allow use of all Customers.",
                "Assign at least one Team or Department to that Role — "
                "leaving both empty works for reading tickets, but silently "
                "breaks the board-listing feature below with no obvious "
                "error. Either one Team or one Department is enough.",
                "On the Application itself, enable the "
                "<strong>read.tickets</strong> and "
                "<strong>read.customers</strong> permissions.",
                "Save, then copy the generated Client ID and Client Secret.",
            ],
            "result_note": (
                "You'll end up with three values: your HaloPSA site URL, "
                "Client ID, and Client Secret."
            ),
        },
        "fields": [
            {
                "key": "HALO_BASE_URL",
                "label": "Site base URL",
                "secret": False,
                "placeholder": "https://yourinstance.halopsa.com",
                "help": "Your HaloPSA web address — the URL you normally "
                        "go to log in.",
            },
            {
                "key": "HALO_CLIENT_ID",
                "label": "API Client ID",
                "secret": False,
                "help": "Generated when you save the API Application in "
                        "Configuration > Integrations > HaloPSA API.",
            },
            {
                "key": "HALO_CLIENT_SECRET",
                "label": "API Client Secret",
                "secret": True,
                "help": "Generated alongside the Client ID — shown only "
                        "once, so copy it immediately.",
            },
            {
                "key": "HALO_TENANT",
                "label": "Tenant",
                "secret": False,
                "optional": True,
                "help": "Only needed on some hosted multi-tenant setups. "
                        "Leave blank if unsure.",
            },
        ],
    },
}


def get_config(psa_key):
    if psa_key not in PSA_CONFIGS:
        raise ValueError(f"Unknown PSA: {psa_key}")
    return PSA_CONFIGS[psa_key]


def list_psas():
    """Returns the PSA list shape the front end needs, without exposing script_path."""
    return [
        {
            "key": key,
            "label": cfg["label"],
            "board_term": cfg["board_term"],
            "board_term_plural": cfg["board_term_plural"],
            "setup": cfg["setup"],
            "fields": [
                {
                    "key": f["key"],
                    "label": f["label"],
                    "secret": f["secret"],
                    "optional": f.get("optional", False),
                    "placeholder": f.get("placeholder", ""),
                    "help": f.get("help", ""),
                }
                for f in cfg["fields"]
            ],
        }
        for key, cfg in PSA_CONFIGS.items()
    ]

#!/usr/bin/env python3
"""
Thread Ticket Volume Report — desktop GUI wrapper
------------------------------------------------------------
A pywebview shell around the three PSA connector scripts, for prospects
who'd rather click through a wizard than run things from a terminal.

This process never talks to any PSA API itself and never writes any
report file itself — it only launches the existing, unmodified connector
script for the chosen PSA as a subprocess, passing credentials via that
subprocess's environment and controlling output location via its working
directory. See runner.py for why stdin/stderr are handled the way they are.

Run with: python gui/app.py
"""

import json
import os
import subprocess
import sys
import webview

from psa_config import list_psas
from runner import ConnectorRunner, BusyError, REPORT_FILENAME, MAPPING_FILENAME


class Api:
    def __init__(self):
        self.runner = ConnectorRunner()
        self._window = None

    def set_window(self, window):
        self._window = window

    # -- Wizard data -----------------------------------------------------

    def list_psas(self):
        return list_psas()

    def default_output_dir(self):
        return os.path.join(os.path.expanduser("~"), "Documents")

    def pick_output_folder(self, starting_dir=None):
        result = self._window.create_file_dialog(
            webview.FOLDER_DIALOG,
            directory=starting_dir or self.default_output_dir(),
        )
        if not result:
            return None
        return result[0]

    # -- Board lookup ------------------------------------------------------

    def list_boards(self, psa_key, creds):
        return self.runner.list_boards(psa_key, creds)

    # -- Report run --------------------------------------------------------

    def run_report(self, psa_key, creds, days, excluded_boards, output_dir):
        lines = []

        def on_line(line):
            lines.append(line)
            self._push_log(line)

        try:
            result = self.runner.run_report(
                psa_key, creds, days, excluded_boards, output_dir, on_line
            )
        except BusyError as e:
            return {"ok": False, "error": str(e)}

        if result["returncode"] != 0:
            tail = "\n".join(line for line in lines[-8:] if line.strip())
            error = tail or "The script exited with an error, but produced no output."
            return {"ok": False, "error": error}

        return {
            "ok": True,
            "report_path": os.path.join(output_dir, REPORT_FILENAME),
            "mapping_path": os.path.join(output_dir, MAPPING_FILENAME),
        }

    def open_folder(self, path):
        try:
            if sys.platform == "win32":
                os.startfile(path)  # noqa: S606 - user-chosen local folder only
            elif sys.platform == "darwin":
                subprocess.run(["open", path], check=False)
            else:
                subprocess.run(["xdg-open", path], check=False)
        except OSError:
            pass

    # -- Internals -----------------------------------------------------

    def _push_log(self, line):
        if self._window is None:
            return
        try:
            self._window.evaluate_js(f"window.appendLog({json.dumps(line)})")
        except Exception:
            # Window may have been destroyed mid-run; the run itself keeps
            # going (and terminate_active() will stop it on window close).
            pass


def main():
    api = Api()
    window = webview.create_window(
        "Thread Ticket Volume Report",
        url=os.path.join(os.path.dirname(os.path.abspath(__file__)), "web", "index.html"),
        js_api=api,
        width=880,
        height=680,
        min_size=(720, 560),
    )
    api.set_window(window)

    def on_closing():
        api.runner.terminate_active()

    window.events.closing += on_closing

    webview.start()


if __name__ == "__main__":
    main()

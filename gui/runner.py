"""
Subprocess orchestration for the GUI wrapper.

The three connector scripts are run unmodified, exactly as a prospect would
from a terminal — credentials go in via the same environment variables
those scripts already read, and the output location is controlled purely
by the subprocess's working directory (report_utils.py's write_report /
write_local_mapping default to CWD-relative filenames, and no connector's
main() overrides that).

stdin is always DEVNULL: if a required credential is ever missing or blank,
load_credentials() would otherwise fall through to input()/getpass() and
hang forever with nothing writing to that pipe. With DEVNULL those calls
raise EOFError immediately, so a bad run fails fast with a real error
instead of freezing the GUI.

stderr is always merged into stdout: reading only one of two separate
pipes risks a classic deadlock if the unread pipe's OS buffer fills, and it
ensures a traceback from the script actually shows up in the GUI's log
panel instead of vanishing.
"""

import os
import subprocess
import sys
import threading

from psa_config import get_config

# Must match shared/report_utils.py's write_report/write_local_mapping
# out_path defaults — that module is intentionally left unmodified.
REPORT_FILENAME = "thread_ticket_report.csv"
MAPPING_FILENAME = "local_only_customer_mapping.csv"

_POPEN_KWARGS = {}
if sys.platform == "win32":
    _POPEN_KWARGS["creationflags"] = subprocess.CREATE_NO_WINDOW


def _build_env(creds):
    env = dict(os.environ)
    env.update({k: v for k, v in creds.items() if v is not None})
    return env


class BusyError(RuntimeError):
    """Raised when a report run is requested while one is already in flight."""


class ConnectorRunner:
    """Owns at most one in-flight connector subprocess at a time."""

    def __init__(self):
        self._lock = threading.Lock()
        self._proc = None
        self._proc_lock = threading.Lock()

    def list_boards(self, psa_key, creds, timeout=30):
        """
        Runs the connector with --list-boards and parses the printed list.
        Returns {"ok": True, "boards": [{"id": ..., "name": ...}, ...]}
        or {"ok": False, "error": "<message for the user>"}.
        """
        cfg = get_config(psa_key)
        cmd = [sys.executable, "-u", cfg["script_path"], "--list-boards"]
        env = _build_env(creds)

        try:
            result = subprocess.run(
                cmd,
                stdin=subprocess.DEVNULL,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                env=env,
                timeout=timeout,
                **_POPEN_KWARGS,
            )
        except subprocess.TimeoutExpired:
            return {
                "ok": False,
                "error": f"Timed out after {timeout}s waiting for {cfg['label']} to respond. "
                         "You can still type board/queue/team names or IDs manually below.",
            }

        output = result.stdout or ""
        if result.returncode != 0:
            tail = "\n".join(output.strip().splitlines()[-8:])
            return {"ok": False, "error": tail or f"{cfg['label']} exited with an error."}

        lines = output.splitlines()
        header_idx = next(
            (i for i, line in enumerate(lines) if "in this" in line and line.rstrip().endswith(":")),
            None,
        )
        if header_idx is None:
            return {"ok": False, "error": "Could not parse the board/queue/team list."}

        boards = []
        for line in lines[header_idx + 1:]:
            stripped = line.strip()
            if not stripped:
                continue
            parts = stripped.split(None, 1)
            if len(parts) == 2:
                boards.append({"id": parts[0], "name": parts[1]})

        return {"ok": True, "boards": boards}

    def run_report(self, psa_key, creds, days, excluded_boards, output_dir, on_line):
        """
        Runs the connector to completion, calling on_line(text) for every
        line of streamed output. Returns {"returncode": int}. Raises
        BusyError if another run_report call is already in flight.
        """
        if not self._proc_lock.acquire(blocking=False):
            raise BusyError("A report is already running.")

        try:
            cfg = get_config(psa_key)
            args = [sys.executable, "-u", cfg["script_path"], "--days", str(days)]
            if excluded_boards:
                args += ["--exclude-boards", excluded_boards]
            env = _build_env(creds)

            proc = subprocess.Popen(
                args,
                stdin=subprocess.DEVNULL,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
                cwd=output_dir,
                env=env,
                **_POPEN_KWARGS,
            )
            with self._lock:
                self._proc = proc

            try:
                for line in proc.stdout:
                    on_line(line.rstrip("\n"))
                returncode = proc.wait()
            finally:
                with self._lock:
                    self._proc = None

            return {"returncode": returncode}
        finally:
            self._proc_lock.release()

    def terminate_active(self):
        """Called when the GUI window is closing, to avoid an orphaned process."""
        with self._lock:
            proc = self._proc
        if proc is None or proc.poll() is not None:
            return
        proc.terminate()
        try:
            proc.wait(timeout=3)
        except subprocess.TimeoutExpired:
            proc.kill()

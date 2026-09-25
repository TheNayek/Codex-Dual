"""Windowless, explicitly confirmed full-stop action for one secondary profile."""
from __future__ import annotations

import argparse
import ctypes
import sys

import close_profile
import process_control


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("alias", nargs="?")
    parser.add_argument("--user-data-dir")
    args = parser.parse_args(sys.argv[1:] if argv is None else argv)
    box = ctypes.windll.user32.MessageBoxW
    try:
        plan = close_profile.make_plan(args.alias, args.user_data_dir)
        processes = plan.get("processes", [])
        if not processes:
            box(None, "No matching secondary instance could be identified. Nothing was stopped.",
                "Codex Dual", 0x40)
            return 0
        label = args.alias or args.user_data_dir
        message = (f"Fully stop Codex profile {label}?\n\n"
                   f"{len(processes)} identified processes will be forcibly terminated, including active tasks. "
                   "Save your work first. This is not a graceful app quit.\n\n"
                   "Other instances will not be selected. Continue?")
        # Yes/No, warning icon, No selected by default.
        if box(None, message, "Close Codex secondary", 0x134) != 6:
            return 0
        result = process_control.apply_close(plan)
        if result.get("status") not in {"closed", "not_running"}:
            survivors = ", ".join(map(str, result.get("surviving_pids", []))) or "none identified"
            errors = "\n".join(item.get("error", "Unknown failure") for item in result.get("failures", []))
            box(None, f"The stop was incomplete.\nSurviving PIDs: {survivors}\n{errors}\n\n"
                "No automatic elevation or broader termination was attempted.", "Codex Dual", 0x10)
            return 1
        return 0
    except Exception as exc:
        box(None, str(exc), "Codex Dual", 0x10)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())

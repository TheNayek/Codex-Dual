#!/usr/bin/env python3
"""Preview or explicitly terminate one identified secondary Codex process tree."""
from __future__ import annotations

import argparse
import json
import sys

import dual
import process_control


def make_plan(alias: str | None, user_data_dir: str | None, exe: str | None = None) -> dict:
    if bool(alias) == bool(user_data_dir):
        raise dual.DualError("Specify one registered alias OR --user-data-dir, not both")
    if alias:
        dual.validate_alias(alias)
        data = dual.load()
        if alias not in data["profiles"]:
            raise dual.DualError(f"Unknown alias: {alias}")
        user_data_dir = data["profiles"][alias]["user_data"]
    target = dual.safe_path(user_data_dir)
    return process_control.plan_close(str(target), exe=exe)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("alias", nargs="?")
    parser.add_argument("--user-data-dir", help="Exact launcher profile path for an existing installation")
    parser.add_argument("--exe", help="Exact expected app executable; otherwise discover the current app")
    parser.add_argument("--apply", action="store_true", help="Force-stop identified processes; save work first")
    args = parser.parse_args(argv)
    try:
        plan = make_plan(args.alias, args.user_data_dir, args.exe)
        if not args.apply:
            print(json.dumps({"warning": "Apply forcibly stops this instance and its active tasks. Save work first.",
                              "plan": plan}, indent=2))
            return 0
        result = process_control.apply_close(plan)
        print(json.dumps(result, indent=2))
        return 0 if result.get("status") in {"closed", "not_running"} else 1
    except Exception as exc:
        print(f"close: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())

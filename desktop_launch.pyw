"""Windowless entry point for a Codex Dual Desktop shortcut."""
from __future__ import annotations

import contextlib
import ctypes
import io
import os
import sys
from pathlib import Path

import dual


def main(argv: list[str] | None = None) -> int:
    arguments = sys.argv[1:] if argv is None else argv
    stdout, stderr = io.StringIO(), io.StringIO()
    try:
        if len(arguments) > 3 and arguments[0] == "--reenter-launch" and arguments[2] == "launch":
            if not dual.msix.has_package_identity():
                raise RuntimeError("Windows did not assign Codex package identity; refusing another launch attempt")
            directory = Path(arguments[1])
            if not directory.is_absolute():
                raise ValueError("Package reentry requires an absolute working directory")
            os.chdir(directory)
            launch_arguments = arguments[2:]
        elif len(arguments) == 1:
            launch_arguments = ["launch", arguments[0]]
        else:
            raise ValueError("Expected exactly one registered profile alias")
        with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
            result = dual.main(launch_arguments)
    except Exception as exc:
        result = 1
        stderr.write(str(exc))
    if result:
        message = stderr.getvalue().strip() or "Codex profile launch failed."
        ctypes.windll.user32.MessageBoxW(None, message, "Codex Dual", 0x10)
    return result


if __name__ == "__main__":
    raise SystemExit(main())

"""Windowless entry point for a Codex Dual Desktop shortcut."""
from __future__ import annotations

import contextlib
import ctypes
import io
import sys

import dual


def main(argv: list[str] | None = None) -> int:
    arguments = sys.argv[1:] if argv is None else argv
    stdout, stderr = io.StringIO(), io.StringIO()
    try:
        if len(arguments) != 1:
            raise ValueError("Expected exactly one registered profile alias")
        with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
            result = dual.main(["launch", arguments[0]])
    except Exception as exc:
        result = 1
        stderr.write(str(exc))
    if result:
        message = stderr.getvalue().strip() or "Codex profile launch failed."
        ctypes.windll.user32.MessageBoxW(None, message, "Codex Dual", 0x10)
    return result


if __name__ == "__main__":
    raise SystemExit(main())

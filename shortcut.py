#!/usr/bin/env python3
"""Preview or create a Windows Desktop shortcut for a registered Codex profile."""
from __future__ import annotations

import argparse
import base64
import json
import os
import stat
import subprocess
import sys
import uuid
from pathlib import Path

import dual


_CREATE_LINK = r"""
$ErrorActionPreference = 'Stop'
$data = [Console]::In.ReadToEnd() | ConvertFrom-Json
$shell = New-Object -ComObject WScript.Shell
$link = $shell.CreateShortcut([string]$data.path)
$link.TargetPath = [string]$data.target
$link.Arguments = [string]$data.arguments
$link.WorkingDirectory = [string]$data.working_directory
$link.Description = [string]$data.description
$link.Save()
"""


def _powershell(script: str, *, input_text: str | None = None) -> str:
    script = ("[Console]::InputEncoding = [System.Text.UTF8Encoding]::new($false); "
              "[Console]::OutputEncoding = [System.Text.UTF8Encoding]::new($false); " + script)
    result = subprocess.run(
        ["powershell.exe", "-NoProfile", "-NonInteractive", "-EncodedCommand",
         base64.b64encode(script.encode("utf-16le")).decode("ascii")],
        input=input_text, capture_output=True, text=True, encoding="utf-8", timeout=20, check=True,
        creationflags=subprocess.CREATE_NO_WINDOW,
    )
    return result.stdout.strip()


def desktop_directory() -> Path:
    if os.name != "nt":
        raise dual.DualError("Windows Desktop shortcuts require Windows")
    location = _powershell("[Console]::Write([Environment]::GetFolderPath('Desktop'))")
    if not location:
        raise dual.DualError("Windows did not return a Desktop directory")
    return Path(location)


def _plain_directory(path: Path) -> None:
    dual.safe_path(str(path))
    if not path.is_dir():
        raise dual.DualError(f"Desktop directory does not exist: {path}")


def _exists_without_following(path: Path) -> bool:
    try:
        path.lstat()
        return True
    except FileNotFoundError:
        return False


def build_plan(alias: str, desktop_dir: Path, *, python_executable: Path | None = None,
               action: str = "launch", user_data_dir: str | None = None) -> dict:
    """Build a read-only plan; the installed Codex app is discovered at launch time."""
    dual.validate_alias(alias)
    if action not in {"launch", "close"}:
        raise dual.DualError("Unknown shortcut action")
    if user_data_dir:
        if action != "close":
            raise dual.DualError("An explicit profile path is only supported for a close shortcut")
        dual.safe_path(user_data_dir)
    else:
        data = dual.load()
        if alias not in data["profiles"]:
            raise dual.DualError(f"Unknown alias: {alias}")
    _plain_directory(desktop_dir)
    interpreter = Path(python_executable or sys.executable).with_name("pythonw.exe")
    wrapper = Path(__file__).resolve().with_name("desktop_close.pyw" if action == "close" else "desktop_launch.pyw")
    if not interpreter.is_file():
        raise dual.DualError(f"Windowless Python interpreter not found: {interpreter}")
    if not wrapper.is_file():
        raise dual.DualError(f"Desktop launcher not found: {wrapper}")
    destination = desktop_dir / (f"Close Codex - {alias}.lnk" if action == "close" else f"Codex - {alias}.lnk")
    if _exists_without_following(destination):
        raise dual.DualError(f"Shortcut already exists; refusing to overwrite: {destination}")
    return {
        "alias": alias,
        "path": str(destination),
        "target": str(interpreter),
        "arguments": subprocess.list2cmdline([str(wrapper), "--user-data-dir", user_data_dir]
                                            if user_data_dir else [str(wrapper), alias]),
        "working_directory": str(wrapper.parent),
        "description": f"{'Close completely (confirmation required)' if action == 'close' else 'Launch'} Codex profile {alias}",
    }


def create_shortcut(plan: dict, *, runner=_powershell) -> None:
    if os.name != "nt":
        raise dual.DualError("Windows Desktop shortcuts require Windows")
    destination = Path(plan["path"])
    _plain_directory(destination.parent)
    if _exists_without_following(destination):
        raise dual.DualError(f"Shortcut already exists; refusing to overwrite: {destination}")
    temporary = destination.with_name(f".{destination.stem}.{uuid.uuid4().hex}.lnk")
    temporary_identity = None
    try:
        runner(_CREATE_LINK, input_text=json.dumps({**plan, "path": str(temporary)}))
        if not temporary.is_file() or temporary.is_symlink():
            raise dual.DualError("Shortcut creation did not produce a regular file")
        metadata = temporary.stat(follow_symlinks=False)
        if metadata.st_file_attributes & stat.FILE_ATTRIBUTE_REPARSE_POINT:
            raise dual.DualError("Temporary shortcut became a reparse point")
        temporary_identity = (metadata.st_dev, metadata.st_ino)
        # On Windows, rename fails if another process created the destination.
        # It also works on Desktop folders backed by filesystems without links.
        os.rename(temporary, destination)
        temporary_identity = None
    except FileExistsError as exc:
        raise dual.DualError(f"Shortcut already exists; refusing to overwrite: {destination}") from exc
    finally:
        if temporary_identity is not None and _exists_without_following(temporary):
            current = temporary.stat(follow_symlinks=False)
            if ((current.st_dev, current.st_ino) == temporary_identity and
                    not temporary.is_symlink() and
                    not current.st_file_attributes & stat.FILE_ATTRIBUTE_REPARSE_POINT):
                temporary.unlink()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("alias", help="Registered profile alias")
    parser.add_argument("--desktop-dir", type=Path, help="Absolute Desktop directory (default: Windows Desktop)")
    parser.add_argument("--apply", action="store_true", help="Create the shortcut")
    parser.add_argument("--action", choices=("launch", "close"), default="launch")
    parser.add_argument("--user-data-dir", help="Exact existing launcher's profile path for --action close")
    args = parser.parse_args(argv)
    try:
        plan = build_plan(args.alias, args.desktop_dir or desktop_directory(),
                          action=args.action, user_data_dir=args.user_data_dir)
        if args.apply:
            create_shortcut(plan)
        print(json.dumps({**plan, "applied": args.apply}, indent=2))
        return 0
    except (dual.DualError, OSError, subprocess.SubprocessError) as exc:
        print(f"shortcut: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())

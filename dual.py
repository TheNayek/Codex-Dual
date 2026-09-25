#!/usr/bin/env python3
"""Launch separate Codex profiles without reading or copying their credentials."""
from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import stat
import subprocess
import sys
import tomllib
import uuid
from pathlib import Path

CONFIG = Path(__file__).resolve().parent / "dual.local.json"
VERSION = "0.2.0"
WINDOWS_RESERVED = {"CON", "PRN", "AUX", "NUL", *(f"COM{i}" for i in range(1, 10)), *(f"LPT{i}" for i in range(1, 10))}
DROP_PREFIXES = ("CODEX_", "OPENAI_", "AZURE_OPENAI_")


class DualError(Exception):
    pass


def safe_path(value: str) -> Path:
    """Require a literal absolute path, with no traversal or indirection."""
    if not isinstance(value, str) or not value:
        raise DualError("Path must be a nonempty absolute string")
    path = Path(value)
    if not path.is_absolute() or any(p in (".", "..") for p in re.split(r"[/\\]", value)):
        raise DualError("Paths must be absolute and contain no . or .. segments")
    if path == Path(path.anchor) or path == Path.home():
        raise DualError("Filesystem root and user home cannot be profile paths")
    for part in path.parts[1:]:
        if part.endswith((".", " ")):
            raise DualError("Path components may not end in a dot or space")
        if part.upper().split(".")[0] in WINDOWS_RESERVED:
            raise DualError("Path contains a reserved device name")
        if os.name == "nt" and ":" in part:
            raise DualError("Windows alternate data streams are not valid profile paths")
    for ancestor in (path, *path.parents):
        if ancestor.is_symlink():
            raise DualError(f"Symlink or reparse point in path: {ancestor}")
        if os.name == "nt" and ancestor.exists():
            if ancestor.stat(follow_symlinks=False).st_file_attributes & stat.FILE_ATTRIBUTE_REPARSE_POINT:
                raise DualError(f"Reparse point in path: {ancestor}")
    return path


def overlapping(a: Path, b: Path) -> bool:
    aa, bb = os.path.normcase(str(a)), os.path.normcase(str(b))
    return aa == bb or aa.startswith(bb + os.sep) or bb.startswith(aa + os.sep)


def validate_alias(alias: str) -> str:
    if not isinstance(alias, str) or not re.fullmatch(r"[a-z][a-z0-9_-]{0,31}", alias):
        raise DualError("Alias must start with a lowercase letter and use only a-z, 0-9, _ or -")
    if alias.upper() in WINDOWS_RESERVED:
        raise DualError("Alias is a reserved Windows device name")
    return alias


def validate_profiles(profiles: dict) -> None:
    if not isinstance(profiles, dict) or not profiles:
        raise DualError("At least one profile is required")
    seen: list[tuple[str, str, Path]] = []
    for alias, profile in profiles.items():
        validate_alias(alias)
        if not isinstance(profile, dict) or set(profile) != {"home", "user_data"}:
            raise DualError(f"Invalid profile fields for {alias}")
        home, data = safe_path(profile["home"]), safe_path(profile["user_data"])
        default_home = Path.home() / ".codex"
        appdata = Path(os.environ.get("APPDATA", str(Path.home())))
        default_data = (appdata / "Codex", appdata / "ChatGPT")
        if any(overlapping(candidate, default) for candidate in (home, data)
               for default in (default_home, *default_data)):
            raise DualError(f"Profile {alias} overlaps a common Codex installation path")
        if overlapping(home, data):
            raise DualError(f"Overlapping home and user data for {alias}")
        for other_alias, field, other in seen:
            if overlapping(home, other) or overlapping(data, other):
                raise DualError(f"Profile {alias} overlaps {other_alias} ({field})")
        seen.extend(((alias, "home", home), (alias, "user_data", data)))


def load_with_bytes() -> tuple[dict, bytes]:
    if CONFIG.is_symlink() or (os.name == "nt" and CONFIG.exists() and
                               CONFIG.stat(follow_symlinks=False).st_file_attributes & stat.FILE_ATTRIBUTE_REPARSE_POINT):
        raise DualError("Local config must not be a symlink or reparse point")
    try:
        original = CONFIG.read_bytes()
        data = json.loads(original.decode("utf-8"))
    except FileNotFoundError as exc:
        raise DualError("No local config. Run init --root ABSOLUTE_PATH first") from exc
    except (OSError, ValueError, UnicodeError) as exc:
        raise DualError("Local config cannot be read or is invalid JSON") from exc
    if not isinstance(data, dict) or set(data) != {"version", "root", "profiles"} or data["version"] != 1:
        raise DualError("Unsupported local config format")
    safe_path(data["root"])
    validate_profiles(data["profiles"])
    return data, original


def load() -> dict:
    return load_with_bytes()[0]


def save_new(data: dict) -> None:
    validate_profiles(data["profiles"])
    try:
        with CONFIG.open("x", encoding="utf-8") as stream:
            json.dump(data, stream, indent=2)
            stream.write("\n")
    except FileExistsError as exc:
        raise DualError("Local config already exists; refusing to overwrite") from exc


def save_existing(data: dict, expected: bytes) -> None:
    """Serialize writers, then refuse to replace a config changed since load."""
    lock = CONFIG.with_name(CONFIG.name + ".lock")
    temp = CONFIG.with_name(CONFIG.name + "." + uuid.uuid4().hex + ".tmp")
    lock_identity = temp_identity = None
    try:
        with lock.open("x", encoding="utf-8") as stream:
            info = os.fstat(stream.fileno())
            lock_identity = (info.st_dev, info.st_ino)
        if CONFIG.is_symlink() or CONFIG.read_bytes() != expected:
            raise DualError("Local config changed while editing; retry the command")
        with temp.open("x", encoding="utf-8") as stream:
            info = os.fstat(stream.fileno())
            temp_identity = (info.st_dev, info.st_ino)
            json.dump(data, stream, indent=2)
            stream.write("\n")
        if CONFIG.is_symlink() or CONFIG.read_bytes() != expected:
            raise DualError("Local config changed while editing; retry the command")
        os.replace(temp, CONFIG)
        temp_identity = None
    except FileExistsError as exc:
        raise DualError("Another config edit is in progress; retry after checking the lock file") from exc
    finally:
        for path, identity in ((temp, temp_identity), (lock, lock_identity)):
            if identity is not None and path.exists() and not path.is_symlink():
                info = path.stat(follow_symlinks=False)
                if (info.st_dev, info.st_ino) == identity:
                    path.unlink()


def clean_env(environ: dict[str, str], profile: dict) -> dict[str, str]:
    result = {key: value for key, value in environ.items()
              if not key.upper().startswith(DROP_PREFIXES)}
    result["CODEX_HOME"] = profile["home"]
    result["CODEX_ELECTRON_USER_DATA_PATH"] = profile["user_data"]
    return result


def sandbox_diagnostic(profile: dict) -> str:
    """Report only the sandbox selector; never open auth files or logs."""
    config = Path(profile["home"]) / "config.toml"
    try:
        safe_path(str(config))
        raw = config.read_bytes()
    except FileNotFoundError:
        return "not configured (Codex may run first-time setup)"
    except (OSError, DualError):
        return "unknown (config.toml inaccessible or redirected)"
    try:
        parsed = tomllib.loads(raw.decode("utf-8"))
    except (ValueError, UnicodeError):
        return "unknown (config.toml invalid; contents omitted)"
    windows = parsed.get("windows", {})
    mode = windows.get("sandbox") if isinstance(windows, dict) else None
    if mode in ("elevated", "unelevated"):
        return mode
    return "unspecified or unrecognized (check effective settings in Codex)"


def doctor(data: dict) -> None:
    print(f"Config OK: {len(data['profiles'])} isolated profile(s). Desktop support is experimental.")
    for alias, profile in data["profiles"].items():
        mode = sandbox_diagnostic(profile)
        print(f"{alias}: windows.sandbox = {mode}")
        if mode == "elevated":
            print("  If multiple profiles repeatedly request UAC/setup, see docs/WINDOWS.md. "
                  "Separate homes do not isolate machine-level sandbox provisioning.")
    print("Only each registered home's config.toml selector was inspected; effective runtime "
          "overrides and live launch behavior are not verified. No settings were changed.")


def desktop_exe() -> Path:
    if os.name != "nt":
        raise DualError("Desktop auto-discovery currently supports Windows; pass --exe for another platform")
    script = "$p = Get-AppxPackage -Name '*Codex*' | Where-Object { $_.InstallLocation }; $p | ForEach-Object { Join-Path $_.InstallLocation 'app\\ChatGPT.exe' }"
    try:
        out = subprocess.run(["powershell", "-NoProfile", "-NonInteractive", "-Command", script],
                             capture_output=True, text=True, timeout=15, check=True,
                             creationflags=subprocess.CREATE_NO_WINDOW)
    except (OSError, subprocess.SubprocessError) as exc:
        raise DualError("Codex Desktop discovery failed; pass --exe with the app's ChatGPT.exe path") from exc
    found = [Path(line.strip()) for line in out.stdout.splitlines() if line.strip() and Path(line.strip()).is_file()]
    if len(found) != 1:
        raise DualError("Could not uniquely locate Codex app/ChatGPT.exe; pass --exe explicitly")
    return found[0]


def executable(surface: str, explicit: str | None) -> Path:
    if explicit:
        candidate = safe_path(explicit)
    elif surface == "desktop":
        candidate = desktop_exe()
    else:
        found = shutil.which("codex")
        if not found:
            raise DualError("Codex CLI not found; pass --exe with an absolute executable path")
        candidate = Path(found)
    if not candidate.is_file():
        raise DualError(f"Executable not found: {candidate}")
    if os.name == "nt" and candidate.suffix.lower() in (".cmd", ".bat"):
        raise DualError("Windows CLI shims (.cmd/.bat) are unsupported; pass --exe to a direct codex.exe")
    if surface == "desktop" and os.name == "nt" and candidate.name.lower() != "chatgpt.exe":
        raise DualError("Windows Desktop must launch the app's ChatGPT.exe, not the Codex.exe updater")
    return candidate


def plan(data: dict, alias: str, surface: str, exe: str | None, arguments: list[str]) -> dict:
    if alias not in data["profiles"]:
        raise DualError(f"Unknown alias: {alias}")
    target = executable(surface, exe)
    profile = data["profiles"][alias]
    return {"alias": alias, "surface": surface, "argv": [str(target), *arguments],
            "home": profile["home"], "user_data": profile["user_data"]}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--version", action="version", version=f"Codex Dual {VERSION}")
    sub = parser.add_subparsers(dest="command", required=True)
    init = sub.add_parser("init", help="Create local config with an isolated alt profile")
    init.add_argument("--root", required=True)
    add = sub.add_parser("add", help="Register an existing or new isolated profile path")
    add.add_argument("alias")
    add.add_argument("--home", required=True)
    add.add_argument("--user-data", required=True)
    sub.add_parser("list", help="Show registered profile paths")
    sub.add_parser("doctor", help="Check config and paths without changing them")
    for name in ("plan", "launch"):
        cmd = sub.add_parser(name, help="Show launch details or start a profile")
        cmd.add_argument("alias")
        cmd.add_argument("--surface", choices=("desktop", "cli"), default="desktop")
        cmd.add_argument("--exe")
        cmd.add_argument("--dry-run", action="store_true")
    args, extra_args = parser.parse_known_args(argv)
    if args.command not in ("plan", "launch") and extra_args:
        parser.error("unrecognized arguments: " + " ".join(extra_args))
    if args.command in ("plan", "launch") and extra_args and extra_args[0] != "--":
        parser.error("Pass app arguments after --")
    try:
        if args.command == "init":
            root = safe_path(args.root)
            if root.exists() and (not root.is_dir() or any(root.iterdir())):
                raise DualError("Root must be absent or an empty directory")
            home, user_data = root / "alt" / "home", root / "alt" / "electron"
            save_new({"version": 1, "root": str(root),
                      "profiles": {"alt": {"home": str(home), "user_data": str(user_data)}}})
            print(f"Registered alt at {root}. Open the main Codex app normally.")
        elif args.command == "add":
            data, original = load_with_bytes()
            alias = validate_alias(args.alias)
            if alias in data["profiles"]:
                raise DualError(f"Alias already exists: {alias}")
            data["profiles"][alias] = {"home": str(safe_path(args.home)),
                                        "user_data": str(safe_path(args.user_data))}
            validate_profiles(data["profiles"])
            save_existing(data, original)
            print(f"Registered {alias}.")
        else:
            data = load()
            if args.command == "list":
                for alias, profile in data["profiles"].items():
                    print(f"{alias}: home={profile['home']} user-data={profile['user_data']}")
            elif args.command == "doctor":
                doctor(data)
            else:
                extra = extra_args[1:] if extra_args and extra_args[0] == "--" else extra_args
                details = plan(data, args.alias, args.surface, args.exe, extra)
                if args.command == "plan" or args.dry_run:
                    print(json.dumps(details, indent=2))
                else:
                    profile = data["profiles"][args.alias]
                    for path in (profile["home"], profile["user_data"]):
                        safe_path(path).mkdir(parents=True, exist_ok=True)
                    flags = subprocess.CREATE_NO_WINDOW if os.name == "nt" and args.surface == "desktop" else 0
                    try:
                        child = subprocess.Popen(details["argv"], env=clean_env(os.environ, profile),
                                                 creationflags=flags, shell=False)
                    except OSError as exc:
                        if args.surface == "desktop" and getattr(exc, "winerror", None) == 5:
                            raise DualError("Desktop launch denied (WinError 5). Run plan again after "
                                            "app updates and check the installed app/ChatGPT.exe. "
                                            "This alone does not diagnose a UAC problem; see docs/WINDOWS.md.") from exc
                        raise
                    if args.surface == "cli":
                        return child.wait()
                    print(f"Started {args.alias} ({args.surface}), PID {child.pid}.")
        return 0
    except (DualError, OSError) as exc:
        print(f"dual: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())

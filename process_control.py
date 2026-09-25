"""Identify and explicitly stop one isolated Codex Desktop process tree on Windows.

``plan_close`` only reads process metadata. ``apply_close`` is an explicit full
stop and should be called only after the caller has warned about unsaved work.
No process is selected by name alone.
"""
from __future__ import annotations

import ctypes
from ctypes import wintypes
import json
import ntpath
import os
import re
import subprocess


class ProcessControlError(RuntimeError):
    """The target cannot be identified or stopped safely."""


_QUERY = 0x1000  # PROCESS_QUERY_LIMITED_INFORMATION
_TERMINATE = 0x0001
_SYNCHRONIZE = 0x00100000


def _ensure_windows() -> None:
    if os.name != "nt":
        raise ProcessControlError("Desktop process control is Windows-only")


def _normal_path(value: str) -> str:
    if not isinstance(value, str) or not value or "\x00" in value:
        raise ProcessControlError("Expected a nonempty absolute Windows path")
    path = value.replace("/", "\\")
    drive, tail = ntpath.splitdrive(path)
    if not ((re.fullmatch(r"[A-Za-z]:", drive) and tail.startswith("\\")) or
            (drive.startswith("\\\\") and tail.startswith("\\"))):
        raise ProcessControlError("Expected an absolute Windows path")
    if any(part in (".", "..") for part in path.split("\\")):
        raise ProcessControlError("Path traversal is not valid for process identity")
    return ntpath.normcase(ntpath.normpath(path))


def _argv(command_line: str) -> list[str]:
    """Use the Windows parser; an entire --user-data-dir=... can be quoted."""
    _ensure_windows()
    if not isinstance(command_line, str) or not command_line.strip():
        raise ProcessControlError("ChatGPT.exe has no readable command line")
    shell = ctypes.WinDLL("shell32", use_last_error=True)
    kernel = ctypes.WinDLL("kernel32", use_last_error=True)
    shell.CommandLineToArgvW.argtypes = [wintypes.LPCWSTR, ctypes.POINTER(ctypes.c_int)]
    shell.CommandLineToArgvW.restype = ctypes.POINTER(wintypes.LPWSTR)
    kernel.LocalFree.argtypes = [wintypes.HLOCAL]
    kernel.LocalFree.restype = wintypes.HLOCAL
    count = ctypes.c_int()
    result = shell.CommandLineToArgvW(command_line, ctypes.byref(count))
    if not result:
        raise ProcessControlError("Could not parse ChatGPT.exe command line")
    try:
        return [result[index] for index in range(count.value)]
    finally:
        kernel.LocalFree(result)


def _profile_flag(argv: list[str]) -> tuple[bool, str | None]:
    """Return (is_child, profile_path), rejecting ambiguous profile flags."""
    profile: list[str] = []
    child = False
    index = 1  # argv[0] is the executable
    while index < len(argv):
        arg = argv[index]
        if arg == "--type" or arg.startswith("--type="):
            child = True
            if arg == "--type":
                index += 1
        elif arg == "--user-data-dir":
            index += 1
            if index >= len(argv) or not argv[index]:
                raise ProcessControlError("ChatGPT.exe has an incomplete --user-data-dir flag")
            profile.append(argv[index])
        elif arg.startswith("--user-data-dir="):
            profile.append(arg[len("--user-data-dir="):])
        index += 1
    if len(profile) > 1:
        raise ProcessControlError("ChatGPT.exe has duplicate --user-data-dir flags")
    if profile and not profile[0]:
        raise ProcessControlError("ChatGPT.exe has an empty --user-data-dir flag")
    return child, _normal_path(profile[0]) if profile else None


def _snapshot() -> dict:
    """CIM gives command lines only for ChatGPT.exe; others expose tree metadata."""
    _ensure_windows()
    script = r"""
$ErrorActionPreference = 'Stop'
[Console]::OutputEncoding = [System.Text.UTF8Encoding]::new($false)
$all = @(Get-CimInstance Win32_Process)
$processes = @($all | ForEach-Object { [pscustomobject]@{
    pid = [int]$_.ProcessId; parent_pid = [int]$_.ParentProcessId
} })
$roots = @($all | Where-Object { $_.Name -ieq 'ChatGPT.exe' } |
    ForEach-Object { [pscustomobject]@{
        pid = [int]$_.ProcessId; command_line = $_.CommandLine
    } })
[pscustomobject]@{ processes = $processes; roots = $roots } |
    ConvertTo-Json -Depth 4 -Compress
"""
    try:
        run = subprocess.run(["powershell", "-NoProfile", "-NonInteractive", "-Command", script],
                             capture_output=True, text=True, encoding="utf-8", timeout=30, check=True,
                             creationflags=subprocess.CREATE_NO_WINDOW)
        value = json.loads(run.stdout)
    except (OSError, subprocess.SubprocessError, ValueError) as exc:
        raise ProcessControlError("Could not read Windows process metadata through CIM") from exc
    if not isinstance(value, dict) or not isinstance(value.get("processes"), list) or not isinstance(value.get("roots"), list):
        raise ProcessControlError("Windows process inventory is incomplete")
    return value


def _open(pid: int, terminate: bool = False) -> int:
    kernel = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
    kernel.OpenProcess.restype = wintypes.HANDLE
    access = _QUERY | _SYNCHRONIZE | (_TERMINATE if terminate else 0)
    handle = kernel.OpenProcess(access, False, pid)
    if not handle:
        raise ProcessControlError(f"Cannot open PID {pid} (WinError {ctypes.get_last_error()})")
    return handle


def _close(handle: int) -> None:
    kernel = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel.CloseHandle.argtypes = [wintypes.HANDLE]
    kernel.CloseHandle.restype = wintypes.BOOL
    kernel.CloseHandle(handle)


def _identity(handle: int) -> tuple[int, str]:
    kernel = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel.GetProcessTimes.argtypes = [wintypes.HANDLE, ctypes.c_void_p, ctypes.c_void_p,
                                       ctypes.c_void_p, ctypes.c_void_p]
    kernel.GetProcessTimes.restype = wintypes.BOOL
    fields = (wintypes.FILETIME(), wintypes.FILETIME(), wintypes.FILETIME(), wintypes.FILETIME())
    if not kernel.GetProcessTimes(handle, *(ctypes.byref(field) for field in fields)):
        raise ProcessControlError(f"Cannot read process creation time (WinError {ctypes.get_last_error()})")
    created = (fields[0].dwHighDateTime << 32) | fields[0].dwLowDateTime
    kernel.QueryFullProcessImageNameW.argtypes = [wintypes.HANDLE, wintypes.DWORD,
                                                   wintypes.LPWSTR, ctypes.POINTER(wintypes.DWORD)]
    kernel.QueryFullProcessImageNameW.restype = wintypes.BOOL
    buf = ctypes.create_unicode_buffer(32768)
    size = wintypes.DWORD(len(buf))
    if not kernel.QueryFullProcessImageNameW(handle, 0, buf, ctypes.byref(size)):
        raise ProcessControlError(f"Cannot read process executable (WinError {ctypes.get_last_error()})")
    return created, _normal_path(buf.value)


def _current_pid() -> int:
    return os.getpid()


def _plan_from_snapshot(profile: str, expected_exe: str, snapshot: dict) -> dict:
    table = {}
    for entry in snapshot["processes"]:
        try:
            pid, parent = int(entry["pid"]), int(entry["parent_pid"])
        except (KeyError, TypeError, ValueError) as exc:
            raise ProcessControlError("Windows process inventory has missing PID metadata") from exc
        if pid == 0:  # System Idle Process is not openable or a tree member.
            continue
        if pid in table or pid < 0:
            raise ProcessControlError("Windows process inventory has ambiguous PIDs")
        table[pid] = parent
    root_records: dict[int, tuple[bool, str | None]] = {}
    for entry in snapshot["roots"]:
        try:
            pid = int(entry["pid"])
            argv = _argv(entry["command_line"])
            child, data_dir = _profile_flag(argv)
        except (KeyError, TypeError, ValueError) as exc:
            raise ProcessControlError("ChatGPT.exe root metadata is incomplete") from exc
        if pid in root_records or pid not in table:
            raise ProcessControlError("ChatGPT.exe identity is ambiguous")
        root_records[pid] = (child, data_dir)
    matches = [pid for pid, (child, data_dir) in root_records.items()
               if not child and data_dir == profile]
    if len(matches) > 1:
        raise ProcessControlError("More than one Codex Desktop root matches this profile")
    plan = {"user_data_dir": profile, "exe": expected_exe,
            "root_pid": matches[0] if matches else None, "processes": [],
            "warning": "Full close forcibly stops the selected app tree; unsaved work and active tasks may be lost."}
    if not matches:
        return plan
    root_pid = matches[0]
    # Protect the calling helper, its parent Codex tree, and any process whose
    # parent PID may have been recycled before that process was born.
    protected = set()
    cursor = _current_pid()
    if cursor not in table:
        raise ProcessControlError("Calling helper is missing from the process inventory")
    while cursor in table and cursor not in protected:
        protected.add(cursor)
        cursor = table[cursor]
    children: dict[int, list[int]] = {}
    for pid, parent in table.items():
        children.setdefault(parent, []).append(pid)
    queue = [(root_pid, 0)]
    seen = set()
    identities: dict[int, tuple[int, str]] = {}
    try:
        while queue:
            pid, depth = queue.pop(0)
            if pid in seen:
                continue
            seen.add(pid)
            if pid in protected:
                raise ProcessControlError("Selected process tree contains the calling Codex/helper process")
            if pid != root_pid and pid in root_records and not root_records[pid][0]:
                continue  # A different desktop root owns this subtree.
            handle = _open(pid)
            try:
                created, path = _identity(handle)
            finally:
                _close(handle)
            if pid == root_pid and path != expected_exe:
                raise ProcessControlError("Matching profile root uses an unexpected executable")
            parent = table[pid]
            if pid != root_pid and created < identities[parent][0]:
                continue  # Parent PID was reused.
            identities[pid] = (created, path)
            plan["processes"].append({"pid": pid, "parent_pid": parent,
                                       "created": created, "exe": path, "root": pid == root_pid,
                                       "depth": depth})
            queue.extend((child_pid, depth + 1) for child_pid in children.get(pid, []))
    except (OSError, ProcessControlError):
        raise
    return plan


def plan_close(user_data_dir: str, exe: str | None = None) -> dict:
    """Preview exactly one profile root and its descendants, without changing it."""
    _ensure_windows()
    profile = _normal_path(user_data_dir)
    if exe is None:
        from dual import desktop_exe
        try:
            exe = str(desktop_exe())
        except Exception as exc:
            raise ProcessControlError("Could not uniquely locate Codex Desktop ChatGPT.exe") from exc
    expected_exe = _normal_path(exe)
    if ntpath.basename(expected_exe).lower() != "chatgpt.exe":
        raise ProcessControlError("Expected executable must be ChatGPT.exe")
    return _plan_from_snapshot(profile, expected_exe, _snapshot())


def _terminate(handle: int, pid: int) -> None:
    kernel = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel.TerminateProcess.argtypes = [wintypes.HANDLE, wintypes.UINT]
    kernel.TerminateProcess.restype = wintypes.BOOL
    if not kernel.TerminateProcess(handle, 1):
        raise ProcessControlError(f"TerminateProcess PID {pid} failed (WinError {ctypes.get_last_error()})")


def _alive(handle: int) -> bool:
    kernel = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel.WaitForSingleObject.argtypes = [wintypes.HANDLE, wintypes.DWORD]
    kernel.WaitForSingleObject.restype = wintypes.DWORD
    state = kernel.WaitForSingleObject(handle, 0)
    if state == 0:
        return False
    if state == 0x102:  # WAIT_TIMEOUT
        return True
    raise ProcessControlError(f"Cannot verify process exit (WinError {ctypes.get_last_error()})")


def _wait(handle: int, milliseconds: int) -> None:
    kernel = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel.WaitForSingleObject.argtypes = [wintypes.HANDLE, wintypes.DWORD]
    kernel.WaitForSingleObject.restype = wintypes.DWORD
    kernel.WaitForSingleObject(handle, milliseconds)


def apply_close(plan: dict) -> dict:
    """Revalidate a preview, pin every identity, and force-stop only that tree."""
    _ensure_windows()
    if not isinstance(plan, dict) or not isinstance(plan.get("processes"), list):
        raise ProcessControlError("Invalid close plan")
    profile = _normal_path(plan.get("user_data_dir"))
    exe = _normal_path(plan.get("exe"))
    prior = plan["processes"]
    if not prior:
        fresh = plan_close(profile, exe)
        if fresh["processes"]:
            raise ProcessControlError("Profile started after preview; review a new close plan")
        return {"status": "not_running", "terminated_pids": [], "surviving_pids": [],
                "new_pids": [], "failures": []}
    if plan.get("root_pid") != prior[0].get("pid") or not prior[0].get("root"):
        raise ProcessControlError("Close plan root is invalid")
    fresh = plan_close(profile, exe)
    if fresh["root_pid"] != plan["root_pid"]:
        raise ProcessControlError("Profile root changed after preview; review a new close plan")
    old = {item["pid"]: item for item in prior}
    now = {item["pid"]: item for item in fresh["processes"]}
    for pid in old.keys() & now.keys():
        if any(old[pid].get(key) != now[pid].get(key) for key in ("created", "exe", "parent_pid", "root")):
            raise ProcessControlError(f"PID {pid} changed identity after preview")
    # An intermediary can exit while its children remain alive. Those children
    # no longer appear under the root in a fresh parent-PID tree. Check their
    # pinned preview identity read-only and never silently call the tree closed.
    detached_survivors = []
    detached_failures = []
    missing = old.keys() - now.keys()
    if missing:
        inventory = _snapshot()
        visible = {item["pid"] for item in inventory["processes"]}
        for pid in sorted(missing & visible):
            try:
                handle = _open(pid)
                try:
                    created, path = _identity(handle)
                    if created == old[pid]["created"] and path == old[pid]["exe"] and _alive(handle):
                        detached_survivors.append(pid)
                finally:
                    _close(handle)
            except ProcessControlError as exc:
                detached_failures.append({"pid": pid, "error": f"Cannot verify previewed descendant: {exc}"})
    pinned: dict[int, int] = {}
    try:
        for item in fresh["processes"]:
            pid = item["pid"]
            handle = _open(pid, terminate=True)
            pinned[pid] = handle
            created, path = _identity(handle)
            if created != item["created"] or path != item["exe"]:
                raise ProcessControlError(f"PID {pid} changed identity before close")
        # Refresh root command-line identity *after* its handle is pinned.
        check = _snapshot()
        roots = [entry for entry in check["roots"] if entry["pid"] == fresh["root_pid"]]
        if len(roots) != 1:
            raise ProcessControlError("Profile root command line disappeared before close")
        child, data_dir = _profile_flag(_argv(roots[0]["command_line"]))
        if child or data_dir != profile:
            raise ProcessControlError("Profile root command line changed before close")
        failures = detached_failures
        terminated = []
        # Stop the root first so it cannot intentionally spawn further work.
        order = sorted(fresh["processes"], key=lambda item: (not item["root"], -item["depth"]))
        for item in order:
            pid = item["pid"]
            try:
                if _alive(pinned[pid]):
                    _terminate(pinned[pid], pid)
                    terminated.append(pid)
            except ProcessControlError as exc:
                try:
                    still_running = _alive(pinned[pid])
                except ProcessControlError:
                    still_running = True
                if still_running:
                    failures.append({"pid": pid, "error": str(exc)})
        surviving = []
        for pid, handle in pinned.items():
            _wait(handle, 2000)
            try:
                if _alive(handle):
                    surviving.append(pid)
            except ProcessControlError as exc:
                surviving.append(pid)
                failures.append({"pid": pid, "error": str(exc)})
        # A post-close inventory makes late children visible in the result.
        late = []
        after_visible = None
        try:
            after = _snapshot()
            after_visible = {item["pid"] for item in after["processes"]}
            descendants = {pid: item["created"] for pid, item in now.items()}
            other_roots = {}
            for root in after["roots"]:
                if root["pid"] not in descendants:
                    try:
                        other_roots[root["pid"]] = _profile_flag(_argv(root["command_line"]))[0]
                    except (KeyError, ProcessControlError) as exc:
                        failures.append({"pid": root.get("pid"), "error": f"Cannot classify a late ChatGPT.exe process: {exc}"})
                        other_roots[root["pid"]] = False
            changed = True
            while changed:
                changed = False
                for item in after["processes"]:
                    pid, parent = item["pid"], item["parent_pid"]
                    if pid in descendants or parent not in descendants:
                        continue
                    if pid in other_roots and not other_roots[pid]:
                        continue  # Independent desktop roots own their children.
                    try:
                        handle = _open(pid)
                        try:
                            created, _ = _identity(handle)
                            alive = _alive(handle)
                        finally:
                            _close(handle)
                    except ProcessControlError as exc:
                        failures.append({"pid": pid, "error": f"Cannot verify late descendant: {exc}"})
                        continue
                    if created < descendants[parent]:
                        continue  # Parent PID was recycled.
                    descendants[pid] = created
                    if alive:
                        late.append(pid)
                    changed = True
        except ProcessControlError as exc:
            failures.append({"pid": None, "error": f"Cannot check for late descendants: {exc}"})
        new_pids = sorted((set(now) - set(old)) | set(late))
        if late:
            failures.append({"pid": None, "error": "New descendants appeared during close; inspect surviving PIDs"})
        surviving = sorted(set(surviving) | set(late))
        for pid in detached_survivors:
            if after_visible is not None and pid not in after_visible:
                continue
            try:
                handle = _open(pid)
                try:
                    created, path = _identity(handle)
                    if created == old[pid]["created"] and path == old[pid]["exe"] and _alive(handle):
                        surviving.append(pid)
                finally:
                    _close(handle)
            except ProcessControlError as exc:
                failures.append({"pid": pid, "error": f"Cannot recheck detached descendant: {exc}"})
        surviving = sorted(set(surviving))
        return {"status": "partial" if failures or surviving else "closed",
                "terminated_pids": terminated, "surviving_pids": surviving,
                "new_pids": new_pids, "failures": failures}
    finally:
        for handle in pinned.values():
            _close(handle)

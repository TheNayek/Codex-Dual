"""Windows package-context bootstrap for isolated Codex Desktop profiles.

Invoke-CommandInDesktopPackage does not forward our process environment. Reenter
the launcher inside the package, then construct the profile environment there.
This is a compatibility path, not an official Codex multi-account API.
"""
from __future__ import annotations

import ctypes
import json
import os
from pathlib import Path
import subprocess
import sys

PACKAGE_FAMILY = "OpenAI.Codex_2p2nqsd0c76g0"
_BOOTSTRAP = r"""
$ErrorActionPreference = 'Stop'
[Console]::InputEncoding = [System.Text.UTF8Encoding]::new($false)
$data = [Console]::In.ReadToEnd() | ConvertFrom-Json
$package = @(Get-AppxPackage -Name 'OpenAI.Codex' | Where-Object { $_.PackageFamilyName -eq $data.family })
if ($package.Count -ne 1) { throw 'Could not uniquely locate the registered Codex package.' }
Invoke-CommandInDesktopPackage -PackageFamilyName $package[0].PackageFamilyName -AppId 'App' -Command ([string]$data.command) -Args ([string]$data.arguments) -PreventBreakaway
"""


def has_package_identity() -> bool:
    if os.name != "nt":
        return False
    kernel = ctypes.WinDLL("kernel32", use_last_error=True)
    query = kernel.GetCurrentPackageFamilyName
    query.argtypes = [ctypes.POINTER(ctypes.c_uint32), ctypes.c_wchar_p]
    query.restype = ctypes.c_long
    size = ctypes.c_uint32(1024)
    name = ctypes.create_unicode_buffer(size.value)
    status = query(ctypes.byref(size), name)
    if status == 15700:  # APPMODEL_ERROR_NO_PACKAGE
        return False
    if status:
        raise OSError(status, "Cannot determine current package identity")
    return name.value == PACKAGE_FAMILY


def bootstrap_payload(script: Path, arguments: list[str]) -> dict[str, str]:
    if not script.is_absolute() or not script.is_file():
        raise ValueError("Package bootstrap requires an existing absolute launcher path")
    pythonw = Path(sys.executable).with_name("pythonw.exe")
    if not pythonw.is_file():
        raise ValueError("Windowless Python interpreter not found")
    return {"family": PACKAGE_FAMILY, "command": str(pythonw),
            "arguments": subprocess.list2cmdline([str(script), *arguments])}


def relaunch_with_package(script: Path, arguments: list[str]) -> None:
    payload = bootstrap_payload(script, arguments)
    result = subprocess.run(
        ["powershell.exe", "-NoProfile", "-NonInteractive", "-Command", _BOOTSTRAP],
        input=json.dumps(payload), text=True, encoding="utf-8", capture_output=True,
        timeout=30, creationflags=subprocess.CREATE_NO_WINDOW, shell=False,
    )
    if result.returncode:
        raise RuntimeError("Package-context launch failed: " + (result.stderr.strip() or str(result.returncode)))

# Two Codex accounts. Two independent app sessions.

[![Offline tests](https://github.com/TheNayek/Codex-Dual/actions/workflows/test.yml/badge.svg)](https://github.com/TheNayek/Codex-Dual/actions/workflows/test.yml) · v0.1.1 · [Español](README.es.md) · Companion to [Codex Economy](https://github.com/TheNayek/Codex-Economy)

Codex Dual is a small, dependency-free Python launcher for separate Codex profiles. Keep opening your main Codex app normally; launch an isolated `alt` beside it. Each launched profile receives its own `CODEX_HOME` and Electron user data path. Sign in to each profile independently through Codex.

**Install with Codex:** Copy and paste this prompt into a Codex task:

> Install Codex Dual by following https://github.com/TheNayek/Codex-Dual/blob/main/INSTALL.md . Keep my current Codex account and settings untouched. Show me the planned paths before launching anything.

**Quickstart (Windows PowerShell, Python 3.11+):**

```powershell
git clone https://github.com/TheNayek/Codex-Dual.git
cd Codex-Dual
python dual.py init --root "$env:LOCALAPPDATA\CodexDualProfiles"
python dual.py doctor
python dual.py plan alt
python dual.py launch alt
```

`plan` discovers the installed Codex Desktop executable via `Get-AppxPackage *Codex*` and displays the exact executable, arguments and profile paths. On Windows, the executable must be the app's `app/ChatGPT.exe`; `Codex.exe` is an updater entry point. Pass `--exe "C:\path\to\app\ChatGPT.exe"` if discovery is ambiguous. `launch` creates only the registered profile directories and starts a child process. `launch alt --dry-run` is equivalent to `plan alt`. No actual Codex launch or sign-in is performed by the project tests.

Codex Desktop isolation depends on internal Electron behavior and is **experimental and version-sensitive**. It has not been validated here by launching a live installed app. It separates app data and sign-in state; it is **not an operating-system security boundary**. Both processes retain the permissions of your OS user. Updates may change the behavior; run `doctor` and `plan` after updates.

## Other commands

```text
python dual.py list
python dual.py add work --home C:\CodexProfiles\work\home --user-data C:\CodexProfiles\work\electron
python dual.py plan work --surface desktop --exe C:\path\to\app\ChatGPT.exe
python dual.py launch work --surface cli --exe C:\path\to\codex.exe -- --help
```

`add` registers paths, including existing isolated installations, without copying their contents. Paths must be absolute, distinct, and free of symlinks/reparse points. They cannot overlap each other, the user home itself, or common Codex paths (`~/.codex`, `%APPDATA%\Codex`, `%APPDATA%\ChatGPT`). Because Electron's default data path can vary by build, select a fresh directory and inspect the plan before launch. `init` creates an ignored local `dual.local.json` and refuses to overwrite it. It does not create any profile home. CLI launching uses `codex` on PATH if `--exe` is absent and is intended for platforms where a directly executable CLI binary is available. On Windows a `.cmd`/`.bat` shim is rejected; pass `--exe` to a direct `codex.exe` instead. The CLI runs in the foreground and returns its exit status. Desktop auto-discovery is Windows only; on Linux/macOS, use an explicit executable path and verify that the installed build honors these variables. Pass app arguments after `--`.

The child inherits ordinary OS environment variables but drops inherited `CODEX_*`, `OPENAI_*`, and `AZURE_OPENAI_*` values before setting the two profile paths. The tool never reads auth files, copies tokens, handles cookies, collects usage data, or changes global Codex settings. `plan` prints only paths and arguments. Avoid putting secrets in launch arguments because they are intentionally displayed.

If a newly created Codex home encounters elevated Windows setup problems, select Codex's supported **unelevated** mode for that profile through its normal setup flow. Codex Dual does not change sandbox or UAC settings automatically. Do not use it to weaken security controls.

## Windows troubleshooting

`doctor` parses each registered home's `config.toml` and reports only the sandbox selector, without changing settings. For repeated UAC/setup prompts, launch denial after an update, and restricted-token test failures, see [Windows troubleshooting](docs/WINDOWS.md). This carries forward lessons from the maintainer's two-account setup; it is not a runtime patch or a promise to eliminate UAC.

## Development

```text
python -m unittest discover -s tests -v
```

Tests use synthetic paths and mocked process launch. The GitHub Actions matrix runs offline on Windows, Linux, and macOS with Python 3.11 and 3.13. No packages are installed.

## Acknowledgements

The scoped `CODEX_HOME` plus `CODEX_ELECTRON_USER_DATA_PATH` mechanism, and the Windows `app/ChatGPT.exe` entry point, were researched with reference to [Zoltak-Dev/ai-multi-instance](https://github.com/Zoltak-Dev/ai-multi-instance) (MIT). Codex Dual is an independently written, Codex-only implementation and does not include code from that project. Thanks to its author for documenting the mechanism.

Codex Dual is independent of OpenAI and is not an official Codex product.

See [origin and scope](docs/PROVENANCE.md) for the upstream contributions, the separate local sandbox mitigation, and what is actually included.

# Install Codex Dual with an agent

This repository contains only a Python 3.11+ script and documentation. The agent should install it without changing an existing Codex account, home, binary, security setting, or sign-in state.

1. Clone `https://github.com/TheNayek/Codex-Dual.git` into a new directory, or use a checkout the user already selected. Do not overwrite an existing checkout.
2. Run `python -m unittest discover -s tests -v` from the repository root. No dependency installation or network call is required for tests.
3. Select a new absolute, empty or absent directory for isolated profile storage. On Windows a reasonable example is `%LOCALAPPDATA%\CodexDualProfiles`. Do not choose the normal `.codex` directory, an existing Electron data directory, or a symlink.
4. Run `python dual.py init --root ABSOLUTE_PROFILE_STORAGE`, then `python dual.py doctor` and `python dual.py plan alt`. Show the planned executable and paths to the user. `init` writes the local, Git-ignored `dual.local.json`; it does not create the profile directories.
5. Launch only if the user asked for an actual launch: `python dual.py launch alt`. The user signs into this separate profile in Codex. Continue opening the main app normally.

`doctor` parses registered homes' `config.toml` files and reports only `windows.sandbox`, omitting other contents and parse-error excerpts. It does not prove effective runtime settings. For repeated UAC prompts or launch failures, follow [Windows troubleshooting](docs/WINDOWS.md) and distinguish the failing stage before suggesting changes. A sandbox-mode change requires the user's informed authorization for that tradeoff; ordinary launcher installation does not include it.

If auto-discovery fails, find the installed Codex package's actual `app/ChatGPT.exe` and pass its absolute path with `--exe`. Do not point at the `Codex.exe` updater. Do not copy `auth.json`, sessions, credentials, cookies, or files from the main profile. Do not change sandbox, UAC, or global Codex settings. The Desktop behavior is experimental; explain that tests do not prove a live side-by-side launch. For a fresh profile with elevated Windows setup trouble, direct the user to Codex's normal unelevated setup option.

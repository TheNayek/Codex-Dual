# Two Codex accounts. Two desktop shortcuts.

[![Offline tests](https://github.com/TheNayek/Codex-Dual/actions/workflows/test.yml/badge.svg)](https://github.com/TheNayek/Codex-Dual/actions/workflows/test.yml) · v0.3.1 · [Español](README.es.md) · [Codex Economy](https://github.com/TheNayek/Codex-Economy)

Keep opening your main Codex app normally. Open the second account from its own
desktop shortcut. Codex Dual separates Codex homes and Electron data, prepares
a windowless shortcut, and provides an agent installation workflow including
the sandbox configuration used to avoid repeated UAC setup in the maintainer's
two-account installation. Python 3.11+ is required; no extra packages are needed.

## Give this to Codex

> Install Codex Dual following https://github.com/TheNayek/Codex-Dual/blob/main/INSTALL.md . Preserve my existing accounts and data. Configure both participating Codex homes with the recommended unelevated sandbox to avoid the repeated elevated setup issue, preserving workspace boundaries and approval settings. I understand this has weaker isolation than the elevated sandbox. Create a desktop shortcut for the second account so I can open it with a double-click. Keep existing working shortcuts. Show the intended changes and verify the result.

The [installation runbook](INSTALL.md) covers both homes, the sandbox selector,
checks and undo. The launcher itself does not rewrite security settings: your
installing agent applies the authorized configuration change once.

## Daily use

- **Main account:** your existing Codex icon.
- **Second account:** the new `Codex - alt` desktop shortcut.
- Sign in separately in each instance. No credentials are copied.

### When closing the window leaves background processes

Closing a window is not always quitting the app. Codex supports staying resident
after its last window closes ([official changelog](https://learn.chatgpt.com/docs/changelog)).
The maintainer reports that tray exit stops the main instance, while the secondary
can remain running. Dual provides a separate **Close Codex - alt** shortcut to
avoid selecting processes manually in Task Manager.

```text
python shortcut.py alt --action close
python shortcut.py alt --action close --apply
```

After saving work, double-click that shortcut and confirm. This is an explicit
**forced stop of the identified secondary process tree**, including active tasks,
not a graceful quit or a change to the window's X button. The confirmation
defaults to No. It identifies the exact profile path, rechecks process identity,
and refuses ambiguous targets or its own calling process tree. It never stops
all processes named Codex or ChatGPT and does not elevate automatically.

For a read-only preview: `python close_profile.py alt`. `--apply` explicitly
executes the stop. See [full-close details and existing installations](docs/CLOSING.md).
This mitigates background leftovers; it does not repair the app's tray behavior.

No terminal is needed each time. The shortcut discovers the installed app on each
launch, avoiding a stale versioned path after updates. Keep the checkout and
Python in their installed locations; recreate the shortcut if you move either.

### Already installed? Update after the package-identity startup error

Codex app update `26.924.1866.0` exposed a startup failure in direct Desktop
launches: **"The process has no package identity"**. Version 0.3.1 enters the
registered Windows package before selecting the secondary profile.

Update the same checkout your shortcut uses; keep `dual.local.json` and all
profile folders. A clean checkout can use `git pull --ff-only`. Review local
changes first; do not reset or reinstall accounts. Existing Codex Dual shortcuts
pick up the fix from that checkout. Shortcuts belonging to another launcher need
their own compatibility update. See [update and validation steps](INSTALL.md#updating-an-existing-installation).

## Windows setup and UAC

The recommended setup explicitly selects `windows.sandbox = "unelevated"` in
both homes. This was necessary in the maintainer's environment to stop repeated
elevated sandbox provisioning from disrupting work. It does **not** disable
Windows UAC. It preserves bounded filesystem access and existing approval
controls, but has weaker isolation than the elevated sandbox. See [the procedure
and official guidance](docs/WINDOWS.md).

This is a mitigation for the observed issue, not proof that every installation
requires it or that every permission prompt should disappear. Organizations
requiring elevated mode must resolve that compatibility constraint first.

## Setup commands, if you prefer

Run these once from the cloned repository. Follow [INSTALL.md](INSTALL.md) to
configure and verify both homes before first launch:

```powershell
python dual.py init --root "$env:USERPROFILE\.codex-dual\profiles"
python dual.py plan alt
# Apply the sandbox setup in INSTALL.md, then:
python dual.py doctor
python shortcut.py alt
python shortcut.py alt --apply
python shortcut.py alt --action close --apply
```

Double-click the shortcut for daily use. `shortcut.py` previews by default,
refuses overwrites, and accepts `--desktop-dir ABSOLUTE_DIRECTORY` for another
existing folder. It does not start Codex during setup.

`dual.py` also supports `list`, `add`, `plan`, and direct `launch`. Use
`python dual.py add work --home ABSOLUTE_HOME --user-data ABSOLUTE_ELECTRON_DATA`
to register existing isolated paths without moving data. Main/default paths,
overlaps, symlinks and reparse points are rejected. CLI use is optional:
`python dual.py launch alt --surface cli --exe ABSOLUTE_EXECUTABLE -- --help`.
Windows `.cmd`/`.bat` shims are unsupported; use a direct CLI executable.

## Compared with the original launcher

[ai-multi-instance](https://github.com/Zoltak-Dev/ai-multi-instance) offers an
interactive profile menu, shortcuts, rename/delete/close controls, account usage,
and support for Claude and Codex. Dual focuses on Codex, desktop shortcuts,
inspectable setup and diagnostics. It does not include that menu, usage display,
or profile rename/delete controls. Its separate confirmed full-stop action is
available without that menu. A working installation does not need
replacement to benefit from the documented sandbox setup.

Dual removes inherited `CODEX_*`, `OPENAI_*`, and `AZURE_OPENAI_*` environment
variables before assigning profile paths. This avoids accidental provider
inheritance but also removes intentional overrides. Neither launcher alone
corrects sandbox provisioning: the configuration step matters.

## Compatibility and checks

Desktop discovery and shortcuts are Windows-specific. Desktop isolation uses
internal Electron behavior and remains experimental and version-sensitive.
Separate profiles are not an OS security boundary. Other platforms can use the
CLI or an explicit Desktop executable; verify the client honors those paths.
Windows discovery uses `app/ChatGPT.exe`, not the `Codex.exe` updater.

```text
python -m unittest discover -s tests -v
```

Tests use synthetic profiles. Windows shortcut checks create and inspect a real
shortcut in a workspace fixture, not the actual desktop. They do not launch or
sign into Codex. CI covers Windows, Linux and macOS with Python 3.11 and 3.13;
Windows-only checks are skipped elsewhere. `doctor` reports configured selectors,
not effective runtime overrides.

The environment mechanism and entry point were researched using
[Zoltak-Dev/ai-multi-instance](https://github.com/Zoltak-Dev/ai-multi-instance)
(MIT). This is a separately written implementation; see [origin and scope](docs/PROVENANCE.md).
Codex Dual is independent of OpenAI.

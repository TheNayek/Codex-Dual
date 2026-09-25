# Install Codex Dual with an agent

## Deliverable

For Windows, leave the user with their existing main account, a separate second
account, and a desktop shortcut for daily use. The recommended two-account setup
includes `windows.sandbox = "unelevated"` in both participating Codex homes to
avoid the repeated elevated provisioning observed in the maintainer's setup.
This is part of setup, not something to defer until repeated UAC prompts occur.
Do not disable Windows UAC.

Unelevated retains restricted filesystem access but has weaker isolation than
Codex's elevated sandbox. Explain that tradeoff and preserve workspace-write,
approval rules, reviewer, bounded roots, and other existing settings. The README
installation prompt explicitly authorizes this selected change. If a request
instead requires preserving sandbox mode, resolve that conflict with the user
before changing it. Do not ask again when the informed instruction already
covers the setup. Follow actual runtime permission boundaries.

## 1. Inspect and prepare

1. Use Python 3.11+ and a checkout in a stable location. Clone into a new directory
   or use the selected checkout. Shortcuts depend on that location and Python.
2. Run `python -m unittest discover -s tests -v` from the repository root.
3. Identify the actual main Codex home and proposed secondary home. Do not assume
   the agent's inherited CODEX_HOME is the main account. Never inspect auth files
   or infer ownership from secrets. Preserve existing installations and shortcuts
   if the user already has a working two-account setup.
4. For a new secondary profile, choose an absolute empty or absent directory,
   for example `%USERPROFILE%\.codex-dual\profiles`, then run:

   ```text
   python dual.py init --root ABSOLUTE_PROFILE_STORAGE
   python dual.py plan alt
   ```

   Init creates only ignored local registration. Register an existing isolated
   secondary home with `add` and explicit home/Electron paths; do not copy or
   relocate it. Do not register the main home as a secondary profile.
   For new profiles, prefer storage outside AppData: packaged Windows processes
   can see a virtualized AppData store different from an ordinary launcher.
   Do not move an existing profile automatically; verify which store contains
   its data before considering any migration.

## 2. Apply the two-account sandbox mitigation

Show both target config paths and the single intended selector change. Within
existing authorization, edit each participating home's `config.toml`:

```toml
[windows]
sandbox = "unelevated"
```

For existing files, update only this selector, preserving comments and unrelated
values. Parse TOML before and after; compare parsed dictionaries with this selector
removed to verify unrelated values are unchanged. Do not append duplicate tables,
overwrite the file with the snippet, follow symlinks/reparse points, or replace a
file changed since inspection. For unsupported syntax, report the concrete editing
conflict instead of rewriting the configuration. Already-unelevated is a no-op.

For a genuinely new secondary home only, create configuration with bounded
execution and approval defaults too:

```toml
sandbox_mode = "workspace-write"
approval_policy = "on-request"

[windows]
sandbox = "unelevated"
```

Record only previous selector values/absence and targeted paths in ignored
`dual.installation.local.json` for undo. Do not store full configurations,
credentials, or unrelated settings in the checkout. Preserve existing receipts.
Do not enable Full Access, remove approval controls, reset Windows users, or
share `.sandbox-secrets`.

Run `python dual.py doctor` for registered profiles and separately parse the main
home's selector. Effective client overrides and already-open tasks may differ;
report that limitation. See [Windows guidance](docs/WINDOWS.md).

## 3. Create the daily desktop shortcut

```text
python shortcut.py alt
python shortcut.py alt --apply
python shortcut.py alt --action close
python shortcut.py alt --action close --apply
```

The first command previews the shortcut; the second creates `Codex - alt.lnk`
on the actual Windows desktop, including a redirected desktop. Neither launches
Codex. Existing shortcuts are never overwritten: preserve them or choose another
registered alias. `--desktop-dir ABSOLUTE_DIRECTORY` selects another existing
folder for inspection/testing.

The shortcut runs the included windowless Python launcher, which discovers the
current app on every launch rather than storing a versioned MSIX path. Verify
target, arguments and working directory after creation. Errors appear in a dialog.
On current Windows packages, the launcher first obtains package identity, then
sets the profile environment inside that context. Do not replace this with a
shortcut directly to ChatGPT.exe or a direct package activation command: the
former can fail startup, and the latter can lose the selected account's env.
Explain that daily use is **double-click the shortcut**, not repeated commands.

Also create the distinct close shortcut. Explain that it confirms before forcibly
stopping that instance and its active tasks; it does not turn the window X into
a graceful quit. Never click it or run `close_profile.py --apply` as an installer
test against the user's live apps. Use only preview to validate the target. For
an existing upstream installation use the exact launcher's --user-data-dir path,
which may differ from the Electron environment path; see [closing](docs/CLOSING.md).

## 4. Handoff and validation

The main app is opened normally. Explain which shortcut opens the second account.
Verify an actual launch from the user's desktop shortcut, not only a launch
inherited from the installing agent. Confirm that the secondary account and its
expected history appear; a second window alone does not establish isolation.
Launch only if requested; the user signs in through Codex. Never copy auth.json,
cookies, sessions, or sandbox secrets. Do not close apps or interrupt tasks to
force a restart.

After the user saves work, fully closes both apps and opens fresh sessions, check
allowed workspace operations and refusal outside the allowed scope in both
accounts. Record observed results instead of promising all UAC prompts are gone.
This mitigation is not a universal runtime fix. Live Desktop compatibility remains
experimental until that installation has been checked.

To undo, remove only the created shortcuts and restore only the recorded sandbox
selectors after reviewing why they changed. Preserve unrelated later edits and
existing profiles. Do not silently restore elevated mode known to fail. Keep the
checkout while the shortcut depends on it.

## Updating an existing installation

1. Inspect the shortcut target to identify its checkout. Read its Git status;
   preserve local registration, profiles, custom code and installation receipts.
2. For an unmodified Codex Dual checkout, update with `git pull --ff-only`.
   Resolve local modifications explicitly; do not reset them or run `init` again.
3. Run the tests and `python dual.py --version` (0.3.1 or newer for the Windows
   package-identity correction). Run `plan` and `doctor` for the existing alias.
4. Existing shortcuts pointing to this checkout need no recreation. A shortcut
   targeting another launcher does not use this fix automatically. Preserve its
   exact Codex home and Electron/browser paths when adapting that launcher; do
   not infer paths or copy credentials into a new profile.
5. Have the user save work and fully close the secondary instance, including
   background processes, before testing its desktop shortcut. Confirm account,
   history and permitted workspace operations. Do not interrupt the main instance.

This update does not require changing UAC, reapplying sandbox selectors or signing
into a newly created account. Keep Desktop compatibility experimental; the Windows
activation facility's limitations are documented in [Windows guidance](docs/WINDOWS.md).

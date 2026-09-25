# Close a secondary instance completely

The app can remain resident when its last window closes. The maintainer reports
that the Windows tray exit closes the main account but leaves the second instance
running. We have not established the internal cause of that multi-instance tray
behavior. This feature supplies an explicit full-stop action, not a tray patch.

## Daily shortcut

Create it once: `python shortcut.py alt --action close --apply`.
Save work, then double-click **Close Codex - alt** and confirm. No is selected
by default. Confirmation authorizes forced termination, including active tasks
and processes launched under the selected app. Prefer the app's normal quit
when it successfully closes the intended instance.

Without the shortcut, `python close_profile.py alt` is a read-only preview.
Adding `--apply` explicitly force-stops the identified processes. Never run it
as an unattended installer validation or when the intended account has work to
preserve. The helper refuses to stop its own ancestry; use the desktop shortcut
from Explorer rather than executing the stop from inside that secondary account.

## Existing ai-multi-instance installation

No migration or new profile registration is required. Read the existing launch
command's exact `--user-data-dir` value; do not guess it from a folder name. The
original launcher may use a different command-line path from the Electron
environment path. Preview it:

```text
python close_profile.py --user-data-dir ABSOLUTE_ORIGINAL_PROFILE_PATH
python shortcut.py alt --action close --user-data-dir ABSOLUTE_ORIGINAL_PROFILE_PATH
python shortcut.py alt --action close --user-data-dir ABSOLUTE_ORIGINAL_PROFILE_PATH --apply
```

The last command only creates the shortcut; it does not close anything. Keep the
existing launch shortcut. No auth, profile contents, sandbox settings or original
launcher code are changed. If no process can be attributed, the helper makes no
guess and stops nothing.

## Selection and limits

- Windows parses the command line into arguments, including quoted paths with
  spaces. Matching requires an exact normalized profile path and expected app
  executable, not a name substring. Renderer processes are not treated as roots.
- A snapshot identifies the root and descendants. Creation identities and
  process handles are checked before termination to avoid targeting reused PIDs.
  Independent app roots and the helper's calling ancestry are excluded/refused.
- Ambiguity, missing process metadata and permission errors stop the preflight.
  There is no automatic elevation or fallback to killing every ChatGPT.exe.
- A process tree can change during shutdown. Partial failures, surviving
  processes and newly observed processes are reported rather than silently
  widening the target. Already-orphaned processes without a provable association
  are not selected. No guarantee covers untraceable detached processes.
- Launches from Dual 0.3 include a matching --user-data-dir marker. Earlier Dual
  launches that lacked it cannot be safely attributed. Close those through their
  existing method once, then use the updated launch shortcut.
- Windows CIM metadata access is required. A Codex command sandbox can deny it
  even when a normal desktop invocation can read it. Report that boundary; do
  not weaken sandbox settings to make this helper work.

This is a force-stop convenience with bounded selection, not a promise of
graceful saving. Unit tests use synthetic process inventories; any live OS
termination test is restricted to harmless processes created by the test itself.

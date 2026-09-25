# Windows launch and sandbox troubleshooting

Diagnose the failing stage before changing anything.

| Symptom | What to check | What Codex Dual does |
| --- | --- | --- |
| App never opens; launch reports `WinError 5` | Installed application entry point and access to that executable | Discovers `app/ChatGPT.exe` again on each launch; rejects the `Codex.exe` updater |
| App opens, but commands repeatedly trigger sandbox setup or UAC | Sandbox provisioning and effective configuration in each profile | `doctor` reports registered homes' sandbox selectors without changing them |
| Python tests cannot access a temporary directory | Temporary-directory ACLs under the restricted token | Tests use unique workspace directories with inherited permissions |

## App launch denied after an update

Run `python dual.py plan alt` again. Auto-discovery does not cache versioned package paths. If you supplied `--exe`, update it to the installed package's actual `app/ChatGPT.exe`. The `Codex.exe` updater is not the app entry point in the supported layout.

This entry-point correction comes from [ai-multi-instance commit 4a977e5](https://github.com/Zoltak-Dev/ai-multi-instance/commit/4a977e5c2232f719fde98e023ba71f262ed7c7aa). It was already present in Codex Dual's first preview; it is not a new UAC fix invented by this project. `WinError 5` has other possible causes, so the message alone does not justify running as administrator or changing ACLs.

## Repeated sandbox setup with two accounts

Separate `CODEX_HOME` directories isolate profile data; they do not make every Windows sandbox resource profile-local. In a maintainer's two-profile installation, logs showed alternating elevated sandbox provisioning, repeated incompatible-user markers, and command logon failures. A collision involving machine-level sandbox users was the best-supported explanation, not a confirmed diagnosis of every affected Codex version.

The local mitigation was to use the supported `unelevated` sandbox for both affected profiles while retaining workspace boundaries and approval settings. Fresh command processes passed allowed-write and denied-write checks without more provisioning in that test window. This does **not** establish that Codex Dual fixes the runtime or that live Desktop sessions are universally UAC-free.

1. Run `python dual.py doctor`. It parses only `config.toml` in registered homes and reports the sandbox selector, never other configuration contents, auth files, or logs. The main home is intentionally not registered: check its effective settings in your normal Codex session too.
2. Determine whether prompts occur during app launch or during commands inside Codex. An elevated selector alone is not an error. Project settings, command overrides, and already-open tasks can differ from the inspected file.
3. If repeated elevated setup is the diagnosed problem, use Codex's supported unelevated option for the affected profiles. The equivalent user configuration selector is below. Preserve other configuration, including workspace and approval restrictions; do not append a duplicate `[windows]` table.
4. Save work, fully close the affected app sessions yourself, reopen them, and start fresh tasks. Verify permitted workspace operations and refusal of writes outside the permitted scope. Check both accounts concurrently before treating the issue as resolved.

```toml
[windows]
sandbox = "unelevated"
```

OpenAI documents `unelevated` as a fallback when elevated setup fails. It retains ACL-based filesystem restrictions but lacks the separate sandbox-user boundary and has weaker network isolation. See [official Windows sandbox troubleshooting](https://learn.chatgpt.com/docs/windows/windows-sandbox#troubleshooting-and-faq). This is a tradeoff, not a stronger default for every user. Codex Dual never selects it automatically.

Do not disable UAC, enable Full Access, share `.sandbox-secrets` between homes, reset sandbox users, or grant broad shell permissions to suppress prompts. Reconsider elevated mode after a relevant runtime fix and successful concurrent checks across fresh sessions; a single ready marker is insufficient evidence for the previously affected setup.

## Restricted-token temporary directories

On the maintainer's Windows/Python 3.13 setup, `TemporaryDirectory` created a restrictive directory ACL that the sandbox token could not use. This was a test-fixture problem, distinct from app launch and elevated provisioning. Codex Dual tests create unique directories inside the checkout with inherited workspace permissions. Do not weaken global ACLs to make a test pass, and do not use this fixture pattern for credentials.

## Reporting an issue

Include Windows and Codex versions, the failing stage, the exact error, and whether one or both profiles are affected. Review and redact paths and account identifiers before sharing output. Never upload auth files, cookies, full configuration, or `.sandbox-secrets`. Live Desktop compatibility remains experimental.

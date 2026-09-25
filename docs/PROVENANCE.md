# Origin and scope

Codex Dual grew out of practical use of [Zoltak-Dev/ai-multi-instance](https://github.com/Zoltak-Dev/ai-multi-instance), an MIT-licensed launcher for Claude and Codex. Its author deserves credit for the dual-directory environment mechanism and Windows application entry point used here.

Codex Dual is a separately written Python CLI with its own profile registry, validation, environment filtering, diagnostics, and tests. It does not distribute the upstream launcher, interactive menu, or source files. The shared mechanism is not presented as an original discovery. See the [functional comparison](../README.md#compared-with-ai-multi-instance): this rewrite is not a feature-complete upgrade.

| Contribution | Origin | Status in Codex Dual |
| --- | --- | --- |
| `CODEX_HOME` plus `CODEX_ELECTRON_USER_DATA_PATH` | ai-multi-instance research/reference | Included, with attribution; depends on internal Desktop behavior |
| `app/ChatGPT.exe` instead of the updater | [Upstream commit 4a977e5](https://github.com/Zoltak-Dev/ai-multi-instance/commit/4a977e5c2232f719fde98e023ba71f262ed7c7aa) | Included since the first preview |
| Mitigation for repeated elevated sandbox provisioning | Maintainer's separate two-profile investigation and official fallback guidance | Read-only selector diagnostics and [Windows guidance](WINDOWS.md); no automatic security changes |
| Workspace temporary test directories | Maintainer's restricted-token test investigation | Included since the first preview; no global ACL changes |

The inspected local upstream checkout had no tracked modifications, and its launch correction was already an upstream commit. The personal sandbox mitigation lived in Codex configuration and incident records, not in that launcher patch. Personal records and profiles are intentionally not distributed.

The maintainer reports successful everyday use of two accounts with that local
configuration. The inspected desktop shortcut still launches the reference
project's `launcher.pyw`. This is real-world experience supporting the shared
mechanism and the local mitigation; it is not an end-to-end test of the publicly
distributed `dual.py`. That distinction describes the evidence, not a claim
that the maintainer's working setup is broken.

The repository is independently maintained rather than linked through GitHub's fork network. If future work incorporates upstream code, preserve its applicable copyright and MIT permission notice alongside that code and identify the adaptation here. A fresh Git history does not remove attribution or licensing obligations.

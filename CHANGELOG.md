# Changelog

## 0.3.0 — explicit full-stop preview

- Add a separate confirmed close shortcut and read-only process-tree preview.
- Identify a secondary instance by exact profile marker and executable, with
  process-identity checks, calling-tree protection and partial-failure reporting.
- Support an existing upstream launcher's exact profile path without migrating
  accounts or replacing the launch shortcut. No tray patch or graceful quit claim.

## 0.2.0 — desktop setup preview

- Make desktop shortcuts the recommended daily entry point; preview and create
  them without overwriting existing shortcuts or pinning MSIX version paths.
- Include the two-home unelevated sandbox mitigation in the agent installation
  workflow, with the tradeoff explained, unrelated settings preserved, and undo
  guidance. The launcher does not change security settings at startup.
- Preserve existing working installations and shortcuts; no forced migration.

## 0.1.1 — 2026-09-25

- Add read-only sandbox selector diagnostics without printing unrelated configuration or parser excerpts.
- Explain Desktop WinError 5 separately from repeated sandbox setup; do not retry or elevate automatically.
- Document the two-profile sandbox mitigation, its limits, and original upstream contributions.
- Keep live Desktop support experimental; no changes to users' security settings.

## 0.1.0 — 2026-09-25

- Register isolated Codex homes and Electron data directories without copying credentials.
- Inspect plans and launch Windows Desktop or a direct CLI executable.
- Validate paths and avoid inherited Codex and provider authentication overrides.
- Add offline synthetic tests and English/Spanish installation guidance.

# Changelog

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

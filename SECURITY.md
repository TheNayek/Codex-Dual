# Security

Codex Dual creates process-level profile separation, not an OS security boundary. Every launched process retains the current user's filesystem and network permissions. The local config stores paths, not secrets; protect it if path names are sensitive. Launch arguments appear in `plan` output and can be visible to the OS, so never pass credentials as arguments.

Report a security concern privately through the repository's GitHub security advisory feature. Do not post credentials, authentication files, or private profile paths in a public issue. This tool never needs copies of those files to diagnose a bug.

The Windows agent installation workflow includes an explicitly authorized change
to the unelevated sandbox in both participating Codex homes. This has weaker
isolation than the elevated mode; preserve all unrelated approval and workspace
restrictions. The Python launch and shortcut tools do not change sandbox settings.
Shortcuts execute the local checkout, so keep that checkout and Python in a
trusted location. Local installation receipts contain paths and prior selector
values and are excluded from Git.

Full close is explicitly destructive to active work: it forcibly terminates the
identified app and its descendants after shortcut confirmation or CLI `--apply`.
It validates profile paths and process creation identities, refuses ambiguous
targets and protects the calling process ancestry. It never disables UAC, elevates
itself or stops processes by executable name alone. See [closing limits](docs/CLOSING.md).

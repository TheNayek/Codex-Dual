# Security

Codex Dual creates process-level profile separation, not an OS security boundary. Every launched process retains the current user's filesystem and network permissions. The local config stores paths, not secrets; protect it if path names are sensitive. Launch arguments appear in `plan` output and can be visible to the OS, so never pass credentials as arguments.

Report a security concern privately through the repository's GitHub security advisory feature. Do not post credentials, authentication files, or private profile paths in a public issue. This tool never needs copies of those files to diagnose a bug.

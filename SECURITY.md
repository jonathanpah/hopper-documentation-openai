# Security Policy

Report suspected vulnerabilities through [GitHub private vulnerability reporting](https://github.com/jonathanpah/hopper-documentation-openai/security/advisories/new).
Keep exploit details out of public Issues, Discussions, and pull requests until
coordinated disclosure. Use synthetic reproductions and identify the affected
release, host/version, configuration, expected/observed behavior, and limits.
Do not submit credentials or private conversation histories.

This plugin reads native conversation history, runs a separate writer, and
publishes continuity records. Reports may concern secret exposure, cross-thread
context, source data treated as authority, untrusted hooks, or unsafe publication.
Native trust, user permissions, and model behavior remain host responsibilities.
Literal source checks do not certify every statement's semantic fidelity.

Identify any affected release, including older versions when relevant. Project maintainers reviews reports through the private channel. Fixes and affected versions
may be documented in changes, releases, or advisories. No response or remediation
deadline is guaranteed.

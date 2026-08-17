# Security Policy

## Supported versions

Security fixes are applied to the latest release of CoX Raid Dashboard.

## Reporting a vulnerability

Please do not publish exploitable vulnerability details in a public issue.

If the repository owner has enabled GitHub private vulnerability reporting,
use the repository's **Security → Advisories → Report a vulnerability** flow.

If private vulnerability reporting is not enabled, open a public issue that
only states that you have found a potential security issue and ask the
maintainer for a private contact method. Do not include exploit steps, local
file contents, tokens, usernames, or other sensitive information in that issue.

Useful details for a private report include:

- affected version / Git commit;
- Windows version;
- a concise description of the issue;
- reproduction steps;
- security impact;
- suggested mitigation, if known.

## Security boundaries

The application is intended to:

- listen only on `127.0.0.1`;
- read RuneLite data selected by the local user;
- serve screenshot files only from beneath the configured `.runelite` root;
- store only local dashboard configuration beneath `%LOCALAPPDATA%`;
- avoid modifying the RuneLite raid log and screenshots.

Changes that broaden filesystem access, bind to non-loopback network
interfaces, introduce uploads/telemetry, execute content from raid logs, or
weaken screenshot path validation should receive additional security review.

## Release integrity

Tagged releases are built by GitHub Actions. Release binaries receive GitHub
artifact attestations and a SHA-256 checksum file.

This project currently distributes unsigned Windows binaries. GitHub build
provenance is not a replacement for Authenticode code signing.

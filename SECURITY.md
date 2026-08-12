# Security policy

`avbcompose` processes untrusted Android source code, archives, build rules,
filesystem images, and release artifacts before producing operating-system
updates. Treat vulnerabilities affecting input validation, sandboxing,
composition, signing authorization, rollback handling, or provenance as security
issues.

## Reporting a vulnerability

Use GitHub's private **Report a vulnerability** flow for this repository when it
is available. If private reporting is unavailable, contact the repository owner
privately rather than opening a public issue containing exploit details, signing
material, device identifiers, or unreleased artifacts.

Include:

- affected commit or release;
- the violated trust boundary or security invariant;
- a minimal reproduction using synthetic data where possible;
- impact and prerequisites;
- whether any signing key, release artifact, or user data may have been exposed.

Do not include real private keys or passphrases in a report.

## Initial security invariants

Until issue #4 replaces this scaffold with the accepted threat model:

- untrusted source and build scripts never access production signing authority;
- signing is an isolated, digest-bound operation;
- verification occurs before planning and after final composition;
- network access is disabled after immutable input acquisition wherever the
  execution environment supports it;
- no feature package may supply arbitrary executable composition hooks;
- paths, archives, XML, build-probe output, and external-tool output are untrusted;
- logs redact secrets and minimize disclosure of local paths/device data.

## Supported versions

There are no production releases yet. Security fixes currently target the
`main` branch. A formal support window will be defined before the first release.

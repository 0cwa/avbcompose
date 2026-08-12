# ADR 0002: Treat my-avbroot-setup as migration prior art

- Status: Accepted
- Date: 2026-08-12
- Owners: issue #2 and issue #27

## Context

`my-avbroot-setup` proves that Android OTA partitions can be modified in
userspace and re-signed while preserving AVB. Its adapters also encode valuable
knowledge about BCR, Custota, MSD, OEMUnlockOnBoot, AlterInstaller, init services,
SELinux, and PixeneOS compatibility.

Its project-specific mutation classes, hardcoded publishers, and direct mutable
filesystem access do not provide the orthogonal architecture required here.

## Decision

- Preserve the legacy repository and history as prior art and regression input.
- Do not copy its module classes into the new core.
- Migrate behavior through normal artifact, integration, policy, and planning
  interfaces under issue #27.
- Document deliberate security and behavior differences.
- Retire production dependency only after the shadow/cutover evidence in issue
  #30 passes.

## Consequences

The project starts cleanly while retaining auditable provenance. Legacy output
can be used as a semantic comparison oracle, but never as an excuse to preserve
unsafe behavior or bypass typed plans.

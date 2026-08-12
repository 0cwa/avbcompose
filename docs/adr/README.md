# Architecture decision records

ADRs document accepted choices affecting public schemas, trust boundaries,
package dependency direction, external extension contracts, or long-lived
operational policy.

| ADR | Status | Decision |
|---|---|---|
| [0001](0001-modular-monorepo.md) | Accepted | Begin as a modular monorepo and split only from production evidence. |
| [0002](0002-legacy-project-is-prior-art.md) | Accepted | Treat `my-avbroot-setup` as migration prior art, not the implementation base. |
| [0003](0003-package-layering.md) | Accepted | Enforce package responsibilities and a one-way internal import allowlist. |
| [0004](0004-canonical-ir-ownership.md) | Accepted | Keep canonical interchange contracts and their lifecycle in `model`. |

Issue #3 owns the remaining foundation ADR set. ADR 0003's executable policy is
[`dependency-policy.json`](../architecture/dependency-policy.json); the separate
architecture-test lane consumes it. New ADRs should use a four-digit number,
state their owning issue, list alternatives, describe security and migration
consequences, and include an acceptance date.

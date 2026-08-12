# Agent instructions

This file is the mandatory entry point for coding and planning agents working in
`0cwa/avbcompose`.

## Required reading order

Before changing anything:

1. Read [issue #1](https://github.com/0cwa/avbcompose/issues/1) in full.
2. Read the assigned issue, including **Dependencies**, **Context to load**, and
   **Acceptance criteria**.
3. Read every dependency issue and every ADR named by the assigned issue.
4. Read the package-specific context from the map below.
5. Inspect current code, tests, open PRs, and issue handoff comments before
   deciding that something is unimplemented.

User instructions and accepted ADRs override this file when they conflict.

## Source of truth

- Project charter and roadmap: issue #1
- Work scope and acceptance criteria: the assigned issue
- Architecture decisions: `docs/adr/`
- Public interchange contracts: `schemas/` and their owning model code
- Security invariants: `SECURITY.md`, issue #4, and accepted security ADRs
- Current implementation behavior: code plus executable tests

Do not copy stale context between issues. Link to the canonical owner instead.

## Architecture map and accepted routing

Issue #33 accepts the package/IR boundary for parent #3 criteria 1, 2, and 6.
Before changing a package, load [ADR 0003](docs/adr/0003-package-layering.md),
[ADR 0004](docs/adr/0004-canonical-ir-ownership.md), and the executable
[dependency policy](docs/architecture/dependency-policy.json). The separate
architecture-test lane statically scans Python and treats every undeclared
cross-package `avbcompose` top-level import as forbidden, with actionable
`from -> to` diagnostics. It does not observe or authorize subprocess,
non-Python tool, or signing invocation; those remain prohibited outside issue
#6's audited process boundary, which owns their enforcement. Keep the policy,
package map, Mermaid source, and SVG synchronized.

| Area | Directory | Primary roadmap context |
|---|---|---|
| Canonical models and serialization | `src/avbcompose/model/`, `schemas/` | #3, #4, #5, #7; ADR 0003/0004 |
| Repo manifests and source transforms | `src/avbcompose/source/` | #14; ADR 0003/0004 |
| OTA and device facts | `src/avbcompose/baseline/` | #8, #24, #25; ADR 0003/0004 |
| Product and module graphs | `src/avbcompose/graph/`, `probes/` | #15, #16; ADR 0003/0004 |
| Sandboxed builds and cache | `src/avbcompose/build/`, `tools/containers/` | #4, #17; ADR 0003/0004 |
| Artifact semantics | `src/avbcompose/artifacts/` | #11, #23, #25; ADR 0003/0004 |
| Android integration semantics | `src/avbcompose/integration/` | #12, #21, #22, #23; ADR 0003/0004 |
| Compatibility contracts | `src/avbcompose/compatibility/` | #19, #21–#25; ADR 0003/0004 |
| Contribution extraction | `src/avbcompose/contribution/` | #18, #20; ADR 0003/0004 |
| Pure planning | `src/avbcompose/plan/` | #9; ADR 0003/0004 |
| Filesystem/boot/OTA execution | `src/avbcompose/image/` | #10, #24; ADR 0003/0004 |
| Upstream reconciliation | `src/avbcompose/update/` | #19; ADR 0003/0004 |
| Signing and release evidence | `src/avbcompose/release/` | #4, #28, #29; ADR 0003/0004 |
| CLI orchestration | `src/avbcompose/cli/` | #13; ADR 0003/0004 |
| Declarative feature data | `catalog/` | #26, #27 |

`avbroot` and `afsr` are external tools, not Python package layers. The import
policy does not authorize invoking them: later execution must use the audited
process boundary from #6. Do not add feature-specific packages or mechanism
imports to the map.

The package and IR boundaries above are accepted by child issue #33. The
remaining #3 ADR children still own adapter selection, error taxonomy, schema
evolution, and repository-split governance; avoid inventing cross-package APIs
ahead of those decisions.

## Non-negotiable engineering rules

- Use the real Android build system as the authority for configured Make/Soong
  semantics. Static scanning may provide hints only.
- Contributions cross trust boundaries as typed, versioned data. Do not pass
  mutable filesystem objects or arbitrary callbacks between layers.
- `PatchPlan` operations must be semantic and serializable. Never add a generic
  shell-command operation.
- Image backends execute approved plans; they do not contain feature, repository,
  package, or ROM-specific policy.
- No untrusted code executes in the signer environment.
- Production code may invoke external tools only through the audited process
  boundary established by issue #6.
- Record upstream assumptions as executable preconditions or compatibility
  contracts, not prose-only knowledge.
- Unsupported Android domains fail explicitly. Never fall back to opaque scripts
  merely to make a scenario pass.
- Fresh-install compatibility and OTA-upgrade compatibility are separate claims.

## Work protocol

1. Restate the issue acceptance criteria in the PR description.
2. Prefer one coherent issue or independently reviewable slice per PR.
3. When an epic is too broad, create linked child issues that state exactly which
   epic acceptance criteria they satisfy.
4. Add or update unit, synthetic, golden, or conformance fixtures for every new
   semantic operation or public contract.
5. Run the smallest relevant test set while iterating, then run
   `./scripts/check.sh` before publishing.
6. Do not change public schemas, trust boundaries, or cross-package interfaces
   without updating or adding an ADR.
7. End every issue/PR with a handoff note containing:
   - decisions made;
   - invariants introduced;
   - tests and fixtures added;
   - known gaps or residual risks;
   - exact next unblocked issue or task.

## Branch and commit conventions

- Create a branch named `codex/<issue>-<slug>` or `agent/<issue>-<slug>`.
- Keep commits intentional and reviewable.
- Do not mix unrelated cleanup with security- or schema-sensitive changes.
- Reference the issue in commits and the PR body.
- Open a draft PR while architecture or acceptance details are still evolving.

## Prohibited shortcuts

- Do not implement feature-specific classes in the core for BCR, Custota, MSD,
  OEMUnlockOnBoot, AlterInstaller, or any other individual feature.
- Do not execute installer scripts from Magisk/KernelSU modules.
- Do not mount Android partition images through the host kernel.
- Do not put production keys, passphrases, secret environment values, or personal
  device data in source, fixtures, logs, issues, or CI artifacts.
- Do not claim tests passed unless they were run in the current worktree.
- Do not silently weaken policy, validation, or reproducibility to unblock a
  release.

## Goal-mode orchestration

The reusable orchestration prompt is stored at
`docs/agents/goal-mode-codex-prompt.md`. Goal-mode agents should choose the next
unblocked issue from the dependency graph in issue #1, keep the tracker updated,
and move to another safe task when blocked rather than inventing missing inputs.

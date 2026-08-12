# ADR 0003: Enforce package layering and semantic/mechanism separation

- Status: Accepted
- Date: 2026-08-12
- Owners: issue #33 and issue #3
- Policy: [`docs/architecture/dependency-policy.json`](../architecture/dependency-policy.json)
- Diagram: [`docs/architecture/dependency-graph.mmd`](../architecture/dependency-graph.mmd)

## Context

The repository is a modular monorepo, but a directory layout alone does not
prevent a new feature from making an image backend understand a ROM, a builder
from reaching signing authority, or a lower layer from importing CLI state.
Issue #33 therefore needs a small, executable rule set that the architecture
conformance lane can consume without importing production code. That rule set
closes Python package-import routes only; issue #6's audited process boundary
separately owns enforcement against subprocess, non-Python tool, and signing
invocation routes.

The accepted pipeline is semantic first and mechanistic last:

```text
source / baseline / graph / build
              ↓
     artifacts / integration
              ↓
       compatibility / contribution
              ↓
             plan
              ↓
            image
              ↓
           release
```

`model` is the contract sink for these layers, and `cli` is the outermost
orchestrator. The diagram and JSON policy describe direct imports between the
14 `avbcompose` top-level Python packages that the AST conformance linter can
observe; same-package imports are implicit. A cross-package Python import edge
not listed in the policy is forbidden, even if it would be convenient.

## Decision

1. The complete direct Python package-import allowlist is the versioned JSON
   policy. Its `version` and `packages` shape is intentionally small so a
   dependency-free AST test lane can consume it. The package map carries the
   corresponding responsibility, public-model owner, and tracker/ADR routing
   for every entry.
2. The package importing a contract does not become its owner. Public
   interchange contracts remain owned by `model`; semantic producer packages
   own construction from their inputs and consumers own interpretation at their
   boundary. The lifecycle rules are specified in ADR 0004.
3. `model` imports no other `avbcompose` Python package; policy v1 and the AST
   linter enforce that import boundary. It also contains no Android feature
   policy, filesystem mechanism, external-process invocation, or signer logic,
   but the import linter does not enforce those non-import exclusions.
4. Semantic Android knowledge may live in source/build graph adapters,
   artifact normalizers, integration compilers, compatibility validators,
   contribution extraction, and the pure planner. It must cross package
   boundaries as typed, versioned contracts rather than callbacks or mutable
   filesystem objects.
5. `image` is a mechanism layer. It executes an already approved `model`-
   owned `PatchPlan` and reports execution facts; it does not import
   `source`, `graph`, `build`, `artifacts`, `integration`, `contribution`, or
   `update`, and it does not contain catalog, feature, repository, module, or
   ROM policy.
6. `release` handles release validation, provenance evidence, and the future
   signer protocol, but does not reinterpret Android feature semantics. Of the
   policy's Python packages, only `cli` may import `release`, after approved
   outputs exist. Probes and catalog data are not Python packages in this
   policy. They, producers, normalizers, and image backends remain prohibited
   from directly invoking release or signing authority by subprocess or other
   non-Python means; issue #6's audited process boundary owns enforcement of
   that separate invariant.
7. No package below `cli` imports `cli`. `cli` may depend on every package as
   the composition boundary. This is orchestration, not permission for lower
   layers to reach upward.
8. External executables such as `avbroot` and `afsr` remain tools at the
   process boundary. `avbroot` provides OTA/AVB delivery and signing mechanics;
   `afsr` provides reproducible filesystem pack/unpack mechanics. They are not
   domain models, Python package dependencies, or sources of feature policy.
   The AST import linter neither observes nor authorizes their invocation. All
   production tool execution is deferred to, and enforced by, the audited
   process boundary owned by issue #6.

## Python import directions enforced here

- Any undeclared cross-package `avbcompose.from -> avbcompose.to` Python import
  edge.
- Any import by `model` of another `avbcompose` top-level package.
- Any cross-package import of `cli`.
- Any import by `image` of `source`, `graph`, `build`, `artifacts`,
  `integration`, `contribution`, or `update`.
- Any cross-package import of `release` except `cli -> release`.

The policy is intentionally an allowlist rather than a list of forbidden
examples. The AST architecture test lane should report the Python importer,
imported top-level package, and policy path for each violation.

## Separate execution invariants

Direct subprocess, non-Python tool, or signing invocation that bypasses the
audited process boundary remains prohibited. The package-import policy cannot
detect or authorize those actions; issue #6 owns their enforcement without this
ADR inventing its process API. A generic shell-command operation also remains
forbidden as a way to smuggle mechanism or feature policy through a
`PatchPlan`.

## Alternatives considered

- **Rely on the directory map and review:** rejected; it cannot reliably catch
  accidental imports or provide deterministic CI diagnostics.
- **Allow all packages to import `model` and each other:** rejected; this
  recreates the mutable callback monolith and makes trust direction implicit.
- **Make `image` the central abstraction:** rejected; image formats are
  mechanisms, not owners of Android semantic knowledge.
- **Create a new process/tool package in this slice:** deferred; issue #6 must
  define the audited process boundary and its evidence contract first.

## Consequences

- The package policy, package map, ADR, Mermaid source, and SVG all need to be
  updated together when a dependency changes.
- A new package or direct Python import edge requires a policy/diagram/ADR
  review and a focused conformance fixture in the separate test lane.
- Adapters can evolve independently so long as they emit the model-owned
  contracts and do not bypass the planner or release boundary.
- The current scaffold has no domain implementation yet; these rules constrain
  future code without defining #5 fields or adapter APIs.

## Follow-up questions

- Issue #3's later adapter/capability child must define selection and extension
  contracts without turning paths or repository names into architecture.
- Issue #6 must place the audited process boundary and specify captured output,
  tool identity, resource limits, and failure evidence.
- Issue #4 and #17 must define the concrete signer and builder sandbox
  mechanisms; this ADR only fixes their package direction.

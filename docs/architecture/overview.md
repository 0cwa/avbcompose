# Architecture overview

This is the accepted package and IR boundary for issue #33, satisfying parent
issue #3 criteria 1, 2, and 6. The machine-readable cross-package Python import
allowlist is [`dependency-policy.json`](dependency-policy.json); the relationship view is
[`dependency-graph.mmd`](dependency-graph.mmd) with its rendered companion
[`dependency-graph.svg`](dependency-graph.svg). The separate AST
architecture-test lane consumes the JSON policy and must report an undeclared
Python import edge as `from -> to`, including the policy path and source
location.

## Reader orientation

The semantic pipeline is:

```text
source closure + FeatureSpec
            ↓
source/build graph and exact base facts
            ↓
normalized artifacts and Android integration semantics
            ↓
compatibility findings + ContributionBundle
            ↓
pure conflict/precondition solving into PatchPlan
            ↓
image mechanism execution
            ↓
release evidence and isolated signing
```

`cli` sequences this pipeline from the outside. `model` owns the canonical
public contracts and lifecycle for each cross-package IR. The pipeline is a
direction of responsibility, not permission to pass mutable paths or invoke
arbitrary callbacks across layers.

## Four closures

- **Source closure:** immutable projects, manifest operations, copied/linked
  files, patch series, and generated inputs needed to materialize a feature.
- **Build closure:** configured modules, variants, generators, host tools, and
  compile-time dependencies needed to produce selected outputs.
- **Installed closure:** artifacts and declarations actually installed into
  Android images, including copied/generated files and runtime dependencies.
- **Compatibility closure:** synchronized identities and contracts such as APK
  certificates, APEX keys, ELF ABI, VINTF, SELinux, ART, and kernel KMI.

A Git repository boundary is not any of these closures. The closures are
explained by source/build/graph layers and proven by normalized output and
validation evidence.

## Semantic versus mechanism layers

Semantic Android knowledge may live in source and graph adapters, builders,
artifact normalizers, integration compilers, compatibility validators,
contribution extraction, and the pure planner. These layers produce or consume
typed, versioned, digest-bound model contracts.

`image` is deliberately smaller: it executes an approved `PatchPlan` using
supported image/OTA mechanisms and does not know which feature, repository,
module, or ROM caused an operation. `release` assembles validation/provenance
evidence and mediates the future signer protocol; it does not reinterpret
feature semantics. Neither layer imports the producer graph.

For the 14 policy packages, the AST import allowlist makes these negative rules
executable:

- `model` imports no `avbcompose` package.
- No lower layer imports `cli`.
- `image` cannot import `source`, `graph`, `build`, `artifacts`, `integration`,
  `contribution`, or `update`.
- Only `cli` may import `release`; `build`, `artifacts`, and `image` cannot.
- Every cross-package Python import edge not in the policy is forbidden.

Probes and catalog data are outside the Python package graph. The import linter
does not inspect their execution or prove that other code cannot invoke a tool
or signer through a subprocess.

## Canonical rootless effect vocabulary

The reusable vocabulary is mechanism-independent. It describes what a module or
other producer requires or provides; it does not select installer scripts,
callbacks, filesystem paths, or backend implementations. The conceptual effect
families are placement, init, property, typed XML, metadata, SELinux/labels,
update policy, and root/profile integration. Lifecycle, capability, permission,
findings, safety, verification, exact-base, and filesystem/topology data are
qualifiers, preconditions, or evidence domains—not additional effect families.

This vocabulary describes changes composed into an existing, verified full OTA.
It is not a runtime module API, installer ABI, root-framework implementation, or
device-side installation engine.

These are architecture-level concepts, not frozen serialized identifiers. Issue
#5 owns schema names, field shapes, versions, examples, rejection rules, and
migrations.

The shared contract primitives are:

- `ArtifactInput`: digest-bound archive identity, signature result, allowlisted
  members, and APK signer/version/ABI facts.
- `InstallFile`: target partition/path, mode and ownership, file-context
  resolution, collision policy, digest, and postcondition.
- `AndroidAppIntegration`: privileged-app placement, permission/sysconfig XML,
  package identity, lifecycle, and expected PackageManager grants.
- `InitService`: fixed argv/environment, UID/GID, groups, capabilities,
  dedicated SELinux domain, trigger/class, ordering, and success postcondition.
- `SeappAssignment`: package selector, process/data domains, target context
  files, deterministic ordering, and idempotency.
- `SELinuxPolicyDelta`: exact-base types, transitions, and narrowly scoped allow
  rules with compile, neverallow, loaded-policy, and label evidence.
- `LifecycleDataEffect`: a closed set of reviewed operations for cache
  invalidation, relabeling, trust-store projection, runtime-data provisioning,
  ordered backup, and atomic state rewrites.
- `CompatibilityPrecondition`: exact base, Android/API, ABI, A/B/update-engine,
  service/type/path, kernel/configfs, and fresh-install/upgrade requirements.

These primitives cross boundaries as model-owned, versioned, digest-bound
contracts. Issue #5 owns their serialized names, versions, canonical examples,
unknown-value rejection, and migrations; #11 and #26 normalize module inputs,
#12 and #21 compile Android integration and policy effects, and #9 resolves them
into semantic `PatchPlan` operations. A `u:r:su:s0` label is evidence to
interpret, not proof of a Magisk/KernelSU runtime dependency.

## External tools and trust boundaries

`avbroot` is an external OTA/AVB delivery and signing executable. `afsr` is an
external reproducible filesystem pack/unpack executable. They are mechanisms
called only at a later, audited process boundary owned by issue #6; neither
defines a canonical IR or Python package dependency. Direct subprocess,
non-Python tool, or signing invocation outside that boundary remains
prohibited. The AST import linter neither observes nor authorizes those actions;
issue #6 owns their enforcement. Probes and build scripts are untrusted
producers, and their results must be validated model-owned data before they
enter the semantic pipeline. Source trees and feature scripts never cross into
the signer environment.

## Canonical IR lifecycle

For `FeatureSpec`, `SourceGraph`, `BaseSnapshot`, `BuildEvaluation`,
`ContributionBundle`, `PatchPlan`, `ValidationReport`, and release provenance,
the package that owns domain construction produces a candidate, `model` owns
contract validation/canonical serialization/digest binding/version migration,
and consumers use validated values read-only. ADR 0004 assigns each producer
and consumer without defining #5's fields.

## Deferred architecture work

This slice does not define schema fields, sandbox technology, signer storage,
adapter selection, extension protocols, error taxonomy, or the complete paper
walkthroughs. Those remain explicitly owned by issues #3, #4, #5, #6, #17,
and #32.

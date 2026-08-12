# Accepted package map

ADR 0003 accepts the package responsibilities and direct Python import rules
for the 14 current `src/avbcompose` top-level packages. The executable source of
truth is [`dependency-policy.json`](dependency-policy.json); the Mermaid/SVG
graph must be kept in lockstep with it. Same-package imports are implicit. Any
undeclared cross-package Python import edge is forbidden and belongs in the AST
architecture-test lane, not in a local exception list.

## Package responsibilities and ownership

| Package | One responsibility | Public-model owner | Allowed Python package imports | Tracker / ADR |
|---|---|---|---|---|
| `model` | Canonical public interchange, validation, canonical bytes/digests, and version migration | `model` | none | #3/#5/#7; ADR 0003/0004 |
| `source` | Repo manifests, immutable source closure, and reviewed transforms | `model` | `model` | #14; ADR 0003/0004 |
| `baseline` | Verified OTA, target-files, device, partition, and capability facts | `model` | `model` | #8/#24/#25; ADR 0003/0004 |
| `graph` | Product and configured module/build/install graph evidence | `model` | `model`, `source` | #15/#16; ADR 0003/0004 |
| `build` | Hermetic, resource-bounded Android evaluation/build and cache | `model` | `graph`, `model`, `source` | #4/#17; ADR 0003/0004 |
| `artifacts` | Semantic normalization of built/prebuilt bytes | `model` | `build`, `model` | #11/#23/#25; ADR 0003/0004 |
| `integration` | Compilation of typed Android activation declarations | `model` | `artifacts`, `model` | #12/#21/#22/#23; ADR 0003/0004 |
| `compatibility` | Exact-base identity, ABI/API, partition, Android-domain, and upgrade validation | `model` | `artifacts`, `baseline`, `integration`, `model` | #19/#21–#25; ADR 0003/0004 |
| `contribution` | Extraction/assembly of typed semantic contributions | `model` | `artifacts`, `baseline`, `build`, `integration`, `model` | #18/#20; ADR 0003/0004 |
| `plan` | Pure dependency, conflict, and precondition solving | `model` | `baseline`, `compatibility`, `contribution`, `model` | #9; ADR 0003/0004 |
| `image` | Mechanism execution of approved plans | `model` | `model` | #10/#24; ADR 0003/0004 |
| `release` | Release validation/provenance evidence and future signer protocol mediation | `model` | `model` | #4/#28/#29; ADR 0003/0004 |
| `update` | Upstream reconciliation and drift classification without plan execution/signing | `model` | `artifacts`, `baseline`, `build`, `compatibility`, `contribution`, `graph`, `integration`, `model`, `source` | #19; ADR 0003/0004 |
| `cli` | Outermost orchestration, configuration, presentation, and sequencing | `model` | `artifacts`, `baseline`, `build`, `compatibility`, `contribution`, `graph`, `image`, `integration`, `model`, `plan`, `release`, `source`, `update` | #13; ADR 0003/0004 |

The `src/avbcompose/` directory is the Python import root; it is not a second
domain package in the policy. No package owns another package's public model.

## Boundary surfaces outside `src/avbcompose`

| Surface | Responsibility | Model owner / interaction | Allowed dependencies | Tracker / ADR |
|---|---|---|---|---|
| `schemas/` | Versioned public schema documents and examples | `model`; owned field work is #5 | N/A | #5; ADR 0004 |
| `catalog/` | Declarative feature data and authoring inputs | supplies typed `FeatureSpec` input; no Python import or mechanism authority | N/A | #26/#27; ADR 0003/0004 |
| `probes/` | Programs run in controlled Android checkouts | untrusted producers; validated output crosses a model contract | N/A | #15/#16; ADR 0003/0004 |
| `tools/containers/` | Toolchain/container definitions for later build and process isolation | external mechanism boundary; no domain model ownership | N/A | #6/#17; ADR 0003 |
| `tests/` | Architecture, conformance, synthetic, integration, unit, and golden evidence | test lane consumes policy; no production ownership | N/A | #7/#33; ADR 0003/0004 |
| `docs/` | ADRs, architecture, operations, security, and agent context | documentation authority follows owning issue | N/A | #1/#3; ADR 0001–0004 |

`N/A` means the surface is not an `avbcompose` top-level Python package and is
therefore outside policy v1's import allowlist. It does not grant process,
tool, signing, or other execution authority.

## Negative rules that reviewers should recognize

- `model` has no cross-package `avbcompose` Python imports.
- No other policy package imports `cli`.
- The AST linter permits `image` to import only `model`; it rejects Python
  import reachability from `image` to source, graph, build, artifact,
  integration, contribution, or update packages. The broader prohibition on
  feature, repository, module, ROM, and catalog policy remains an architectural
  invariant rather than a claim that imports detect every leakage path.
- Of the policy packages, only `cli` may import `release`; producers,
  normalizers, and image code cannot gain Python import reachability to it.
- External tools, probes, and catalog data are not Python package edges. Direct
  subprocess, non-Python tool, or signing invocation remains prohibited outside
  the audited process boundary; issue #6, not the AST import linter, owns that
  enforcement.

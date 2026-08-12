# ADR 0004: Model-owned canonical interchange and IR lifecycle

- Status: Accepted
- Date: 2026-08-12
- Owners: issue #33 and issue #3
- Related policy: [`docs/architecture/dependency-policy.json`](../architecture/dependency-policy.json)

## Context

The project needs stable handoff points between source acquisition, Android
build evaluation, normalization, compatibility, planning, composition, and
release. If each producer owns a private representation, later layers will
start accepting mutable paths, callbacks, or tool-specific objects. If every
consumer redefines serialization, equivalent inputs will not have a stable
identity or digest.

Issue #5 owns the executable schemas and fields. This ADR assigns ownership and
lifecycle without pre-empting those field decisions.

## Decision

`model` owns the public contract and lifecycle policy for every named IR:

- `FeatureSpec`
- `SourceGraph`
- `BaseSnapshot`
- `BuildEvaluation`
- `ContributionBundle`
- `PatchPlan`
- `ValidationReport`
- release provenance

For each IR, the domain package named in the table constructs the semantic
candidate, while `model` owns the contract boundary. The model boundary is the
only authority for validation, canonical serialization, digest binding, and
version migration. Consumers do not mutate a received IR or silently repair it.

| IR | Candidate construction | Model-owned validation/bytes/digest/migration | Primary consumers |
|---|---|---|---|
| `FeatureSpec` | Catalog data and CLI/source adapters provide candidate input; `model` accepts it as a typed contract. | `model` | source, compatibility, contribution, CLI |
| `SourceGraph` | `source` resolves manifests and source transforms into a candidate. | `model` | graph, build, update, CLI |
| `BaseSnapshot` | `baseline` inventories and verifies the exact OTA/device facts into a candidate. | `model` | compatibility, contribution, plan, image, update, CLI |
| `BuildEvaluation` | `graph` and `build` produce configured evaluation evidence. | `model` | artifacts, contribution, update, CLI |
| `ContributionBundle` | `artifacts`, `integration`, and `contribution` normalize/extract semantic changes. | `model` | compatibility, plan, update, CLI |
| `PatchPlan` | `plan` produces the pure, conflict-free semantic plan. | `model` | image, release, CLI |
| `ValidationReport` | `compatibility`, `plan`, and release validation stages produce findings. | `model` | image, release, update, CLI |
| Release provenance | `release` assembles evidence and provenance claims from validated inputs and tool results. | `model` | release, CLI, downstream evidence consumers |

The table describes ownership, not a promise that every producer will expose a
public constructor. #5 decides field shapes and concrete schema APIs.

## Lifecycle invariants

1. **Construct:** a producer derives a candidate from its owned input or an
   external tool result. It may retain local mutable state while constructing,
   but no mutable filesystem object crosses the boundary.
2. **Validate:** the model-owned contract boundary rejects malformed,
   unsupported, or version-incompatible data before another package consumes it.
   Domain validators may add findings, but cannot replace contract validation.
3. **Canonicalize and bind:** the model defines one deterministic serialized
   representation for a given version and binds the digest to those canonical
   bytes. Ordering, normalization, and excluded/transient data are schema work
   owned by #5; this ADR requires that the rules be centralized and
   deterministic.
4. **Consume:** consumers receive a validated, digest-bound value and use it
   read-only. They may emit a new IR at their own boundary; they do not mutate
   the previous one or reinterpret its bytes.
5. **Migrate:** version migration is a model-owned, explicit transformation
   from a supported old contract to a current contract. It must preserve or
   report semantic loss, revalidate, recanonicalize, and rebind the digest.
   There is no implicit “best effort” field dropping.
6. **Persist/exchange:** serialized documents and their version/digest metadata
   are treated as public interchange. Tool-specific paths, process handles,
   open files, callbacks, secrets, and signer keys are never IR fields by
   implication.

## Ownership boundaries by layer

- `model` owns contract definitions and lifecycle invariants, but imports no
  other `avbcompose` package.
- `source`, `baseline`, `graph`, and `build` own acquisition/evaluation
  semantics and produce source, base, and build evidence.
- `artifacts`, `integration`, `compatibility`, and `contribution` own Android
  semantic interpretation and findings, not image mutation.
- `plan` owns conflict resolution and precondition planning, not filesystem
  access.
- `image` owns execution mechanics for approved plans, not Android feature
  policy.
- `release` owns provenance/evidence assembly and the signer-facing protocol,
  not untrusted source or build execution.
- `cli` owns sequencing, configuration, and presentation of these boundaries,
  not a second copy of any IR's semantics.

## Alternatives considered

- **Let each package define and serialize its own model:** rejected; it creates
  incompatible identities and duplicate validation.
- **Use filesystem paths as the common IR:** rejected; paths are mutable,
  ambient authority and do not provide typed, digest-bound interchange.
- **Define all fields in this ADR:** rejected; #5 owns executable schemas and
  field-level compatibility.
- **Permit silent migration by consumers:** rejected; migration must be
  explicit, auditable, and revalidated at the contract owner.

## Consequences

- A new public IR or schema version requires a model-owned contract decision,
  migration behavior, and conformance evidence.
- Producers can be replaced or moved out of process without changing image or
  signer semantics, provided they emit the same validated contract.
- The current scaffold intentionally has no field implementation; this ADR
  only fixes authority and lifecycle.

## Follow-up questions

- Issue #5 must define field-level schemas, canonical ordering, digest envelope,
  compatibility windows, and migration test vectors.
- Issue #3's later adapter ADR must define capability-based producer selection
  and extension boundaries.
- Issue #4 must define how provenance and validation evidence cross the signer
  trust boundary without exposing secrets or untrusted execution.

# ADR 0001: Begin as a modular monorepo

- Status: Accepted
- Date: 2026-08-12
- Owners: issue #1 and issue #3

## Context

The schemas, Android build probes, normalizers, compatibility validators,
planner, image backends, CLI, fixtures, and catalog will evolve together during
the foundation and MVP phases. Premature repository boundaries would require
version negotiation before stable interfaces exist and make atomic security
changes harder to review.

## Decision

Develop `avbcompose` as one modular monorepo with enforced internal package
boundaries. A component may be split only when all of these are demonstrated:

1. a stable versioned interchange format;
2. an independent release cadence;
3. at least one consumer outside the monorepo;
4. rare atomic changes crossing the proposed boundary;
5. a security or organizational benefit greater than coordination cost.

Issue #32 owns the evidence-based extension and split review.

## Consequences

- Cross-domain changes can land atomically during early development.
- Internal package boundaries and conformance tests are mandatory to prevent an
  accidental monolith.
- The catalog, signer service, builder images/probes, and fixture data remain
  candidates for later extraction, not promised repositories.

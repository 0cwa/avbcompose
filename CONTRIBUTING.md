# Contributing

The project roadmap and issue tracker are the primary coordination mechanism.
Begin with [issue #1](https://github.com/0cwa/avbcompose/issues/1) and
[AGENTS.md](AGENTS.md).

## Before opening a change

- Select an open issue whose dependencies are satisfied, or create a linked child
  issue for a clearly bounded slice of an epic.
- Load the context and ADRs listed by that issue.
- Discuss changes to trust boundaries, public schemas, signing roles, or package
  dependency direction through an ADR before implementing them.

## Local workflow

```bash
./scripts/bootstrap.sh
./scripts/check.sh
```

Use a focused branch such as `codex/3-architecture-adrs`. Keep tests and fixtures
with the behavior they specify.

## Pull requests

Every PR must state:

- the issue and acceptance criteria addressed;
- scope and non-goals;
- architecture/security/reproducibility impact;
- tests and fixtures run;
- public schema or tool changes;
- a handoff note for the next agent.

A passing scaffold quality gate is necessary but not sufficient for Android or
release-domain work; the assigned issue defines additional validation.

## Dependency and tool changes

Dependency changes must update `uv.lock`. External tools must be added through
the audited tool manifest/process boundary defined by issue #6, with origin,
version, digest/signature, license, and trust-review status.

## Fixtures

Prefer deterministic generators and small license-safe fixtures. Proprietary or
large inputs must be referenced externally by immutable digest and acquired
through documented opt-in procedures.

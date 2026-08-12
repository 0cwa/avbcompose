# Provisional package map

The dependency direction below is a scaffold for issue #3, not a substitute for
its accepted ADRs.

```text
model
  ↑
source  baseline  graph  artifacts
  ↑        ↑       ↑       ↑
 build   integration   compatibility
       \      |       /
        contribution
             ↑
            plan
             ↑
            image
             ↑
       update / release
             ↑
             cli
```

Rules:

- `model` owns language-neutral public interchange types.
- Lower-level packages do not import CLI orchestration.
- Image code does not import feature catalog data or repository-specific logic.
- Build code does not import signing implementations.
- `release` consumes validated outputs; it does not reinterpret Android feature
  semantics.

Issue #3 must refine and enforce this map before substantial implementation.

# Architecture overview

This document summarizes the intended architecture from issue #1. Issue #3 owns
the complete accepted boundaries and may supersede provisional details here.

## Four closures

- **Source closure:** immutable projects, manifest operations, copied/linked
  files, patch series, and generated inputs needed to materialize a feature.
- **Build closure:** configured modules, variants, generators, host tools, and
  compile-time dependencies needed to produce selected outputs.
- **Installed closure:** artifacts and declarations actually installed into
  Android images, including copied/generated files and runtime dependencies.
- **Compatibility closure:** synchronized identities and contracts such as APK
  certificates, APEX keys, ELF ABI, VINTF, SELinux, ART, and kernel KMI.

A Git repository boundary is not any of these closures.

## Layers

1. Source acquisition and Repo manifest resolution.
2. Base OTA and target/device inventory.
3. Android product and configured module-graph evaluation.
4. Sandboxed artifact production.
5. Artifact normalization and Android integration compilation.
6. Compatibility validation and contribution extraction.
7. Pure conflict/precondition planning.
8. Filesystem, boot image, and OTA execution.
9. Isolated signing, release provenance, and test evidence.

## Trust zones

```text
U: untrusted source and archives
B: hermetic builders
N: normalization and validation
C: unsigned composition
S: isolated signing
T: runtime/device validation
```

Data moves forward through versioned, digest-bound formats. Source trees and
feature scripts never cross into Zone S.

## Fundamental separation

- Source/build adapters answer **how to obtain bytes**.
- Artifact normalizers answer **what the bytes are**.
- Integration compilers answer **how Android activates them**.
- Compatibility validators answer **whether they fit this exact base**.
- The planner answers **which semantic changes are authorized and in what order**.
- Image backends answer **how to realize an approved plan**.
- The signer authorizes only validated digests and roles.

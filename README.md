# avbcompose

`avbcompose` is a security-first, reproducible Android binary-composition system.
Its long-term goal is to take a verified upstream Android OTA, resolve reviewed
feature contributions, validate them against the exact base build, compose the
result into existing Android partitions, and produce a fully verified OTA using
`avbroot`.

The project is intentionally a **clean-room successor** to
[`my-avbroot-setup`](https://github.com/0cwa/my-avbroot-setup). The legacy project
is prior art and a migration source; its project-specific mutation architecture
is not the implementation base.

> [!IMPORTANT]
> `avbcompose` is in its foundation phase. The repository currently contains the
> architecture and development scaffold, not a production OTA patcher.

## Start here

- [Canonical project charter and roadmap](https://github.com/0cwa/avbcompose/issues/1)
- [Agent operating instructions](AGENTS.md)
- [Roadmap index](ROADMAP.md)
- [Architecture overview](docs/architecture/overview.md)
- [Architecture decisions](docs/adr/README.md)
- [Security policy](SECURITY.md)

## Core design

```text
source manifests / feature specs / prebuilts
                 │
                 ▼
     immutable source graph + provenance
                 │
                 ▼
 real Kati/Soong/Make evaluation and builders
                 │
                 ▼
       normalized ContributionBundle IR
                 │
                 ▼
 compatibility contracts + conflict resolution
                 │
                 ▼
             typed PatchPlan
                 │
                 ▼
 partition/image composition and validation
                 │
                 ▼
 isolated avbroot AVB/OTA signing
```

A Repo manifest `<project>` is source input, not an installation unit. The
configured Android module graph and installed artifact closure determine what
ships. Build graphs explain a contribution; semantic output differences prove it.

## Development

Requirements:

- Python 3.12 or 3.13
- [`uv` 0.10.0](https://docs.astral.sh/uv/)
- Linux for the supported development workflow

Bootstrap:

```bash
./scripts/bootstrap.sh
```

Run the complete local quality gate:

```bash
./scripts/check.sh
```

The foundation checks require neither root nor an Android source checkout.

## Security posture

Untrusted source code and build scripts must never share a trust zone with
production signing authority. Root frameworks are optional replaceable backends,
not the foundation of the system. The default production profile is expected to
provide no app-accessible root and no writable privileged runtime module store.

This project does not aim to bypass Play Integrity, banking, DRM, or other
anti-abuse controls.

## License

GPL-3.0-only. See [LICENSE](LICENSE).

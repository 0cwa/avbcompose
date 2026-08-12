# Repository bootstrap

## Local

```bash
./scripts/bootstrap.sh
./scripts/check.sh
```

The lock file is authoritative. After initial dependency acquisition,
`uv sync --locked` must not resolve different versions.

## Branch policy

The intended policy is review through pull requests, passing CI, and no force
pushes to `main`. Repository settings may need to be configured manually where
GitHub APIs or account plans do not expose enforcement; issue #2 owns tracking.

## Legacy provenance

`0cwa/my-avbroot-setup` remains prior art and a regression source. Issue #2 owns
an immutable archival ref; issue #30 owns the eventual production retirement and
successor notice.

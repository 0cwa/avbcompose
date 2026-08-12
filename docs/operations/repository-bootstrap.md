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


# Release Readiness Checklist

Status: working release gate document for the `release/readiness-1-9` lane.

## Default Gate

Run the default gate before claiming a local build is healthy:

```powershell
.\.venv\Scripts\python.exe scripts\quality_gate.py
```

The default gate is offline. It must not contact advisory services, package
registries, or remote APIs. It covers:

- `compileall` for `src`, `tests`, and `scripts`.
- `ruff check src tests scripts`.
- `bandit -q -r src`.
- development launch smoke.
- full pytest without pytest cache writes.
- `pip check`.

## Release Advisory Gate

Run the advisory dependency scan only when network access is explicitly approved:

```powershell
.\.venv\Scripts\python.exe scripts\quality_gate.py --with-pip-audit
```

`--with-pip-audit` appends:

```powershell
.\.venv\Scripts\python.exe -m pip_audit --local --cache-dir .pip-audit-cache --progress-spinner off
```

The `.pip-audit-cache` directory is intentionally local to the workspace and is
ignored by git. A failed advisory scan blocks release unless the finding is
triaged and documented with an accepted risk decision.

## Packaging Gate

Run the packaged executable gate before shipping a Windows artifact:

```powershell
.\.venv\Scripts\python.exe scripts\quality_gate.py --with-package-check --with-package-build --with-packaged-launch
```

The packaged launch smoke must start `dist\Modori\Modori.exe` from outside the
repository and keep the event loop alive for the configured timeout.

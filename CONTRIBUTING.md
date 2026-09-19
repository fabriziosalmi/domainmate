# Contributing

Thanks for taking a look. Issues and pull requests are both welcome.

## Getting Set Up

```bash
make install                    # venv + runtime dependencies
pip install -r requirements-dev.txt
```

Then, from the repository root:

```bash
make test                       # pytest
make demo                       # generate a report from mock data
```

`PYTHONPATH` has to include the repository root; `make` handles that for you.

## Before Opening a Pull Request

```bash
ruff check .                    # must pass; CI runs the same command
pytest -q --cov=src --cov=api   # must pass, and coverage must stay above 60%
```

Both run in CI on every pull request, so it is quicker to catch them here.

## House Rules

**Tests must not touch the network.** The suite runs in CI and in containers
where outbound traffic is blocked or slow. Every network call is injected —
see `tests/test_rdap.py` for the pattern. You can prove a change respects this:

```python
import socket
socket.socket.connect = lambda *a: (_ for _ in ()).throw(AssertionError("network!"))
```

**A monitor must never take down the scan.** `BaseMonitor.check()` turns any
failure into a well-formed error result on purpose. One unreachable host should
cost you one row in the report, not the run.

**Configuration that is documented must work.** If you add a key to
`config.yaml` or the README, wire it through `src/config.py` and add it to
`_KNOWN_MONITOR_KEYS` so a typo gets reported instead of silently ignored.
There is a test for every key for exactly this reason.

**The report stays self-contained.** No external scripts, stylesheets or
fonts. A report describing your infrastructure's weaknesses should render with
no network and tell no third party who opened it. `tests/test_html_generator.py`
enforces this.

**Do not overwrite the user's template.** `src/templates/report.html` is theirs
to edit once it exists.

## Commit Messages

Say what changed and why it mattered. The why is the part a reader cannot
reconstruct from the diff six months later.

## Releases

Versions follow [semantic versioning](https://semver.org). Below 1.0.0, a minor
bump may carry changes that need action from operators; those go under
**Upgrading** in `CHANGELOG.md`.

Cutting a release:

1. Update `CHANGELOG.md` and the version in `api/api.py`
2. Merge to `main`
3. `git tag -a vX.Y.Z && git push origin vX.Y.Z`

The workflow builds the versioned image and creates the GitHub release.

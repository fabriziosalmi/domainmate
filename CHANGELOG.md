# Changelog

All notable changes to this project are documented here.

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).
While the version is below 1.0.0, a minor bump may carry changes that require
action from operators; those are always called out under **Upgrading**.

## [Unreleased]

### Added

- Expiry is read over **RDAP** (RFC 9083) with WHOIS as the fallback. WHOIS
  speaks a line protocol on port 43, which is blocked in most containers and CI
  runners; measured in one, the domain monitor took 10 seconds to fail while
  every other check finished in under a quarter of a second. Each result records
  which path answered, and `monitors.domain.use_rdap` turns RDAP off.
- Checks run **concurrently** instead of one after another — 7 domains x 5
  monitors used to be 35 blocking network calls in series. `--concurrency`
  (default 8) bounds how many run at once. Measured at roughly 5.8x on a
  seven-domain config.
- `--concurrency`, `--fail-on` and `--json` on the CLI.
- Each run keeps a timestamped `report-YYYYMMDD-HHMMSS.json` snapshot, pruned
  by `reports.retention_days`.
- `DOMAINMATE_API_KEY`: when set, `POST /analyze` and `POST /notify/test`
  require an `X-API-Key` header. Unset leaves them open, as before.
- `monitors.dns.required_records` now also understands `mx` and `caa`.
- A `domains` entry may carry a port (`mail.example.com:993`). Only the SSL
  check uses it; every other monitor still gets the bare hostname. The port was
  previously discarded twice over — `clean_domain()` stripped it, and
  `SSLMonitor` took a `port` argument that `BaseMonitor.check()` never passed on.
- The blacklist monitor checks **IPv6** addresses and **every** address a name
  answers with, up to four, rather than reversing IPv4 octets on whichever one
  the resolver happened to return first. An IPv6-only domain used to fail to
  resolve outright.
- `SECURITY.md`, `CONTRIBUTING.md` and issue templates.
- `ruff` and a coverage floor in CI; the test job now gates pull requests,
  which it did not before.

### Changed

- **Six documented configuration keys are now read.** The expiry thresholds for
  domain and SSL, `required_records` and `rbls` were documented in the README,
  `config.yaml` and the docs while no code looked at them: the file parsed
  without error and nothing changed. The API did not read the configuration at
  all, so a threshold tuned in `config.yaml` applied to the CLI and not to
  `/analyze`. Unknown keys are now reported by path instead of dropped.
- **The report template is no longer overwritten.** `HTMLGenerator` rewrote
  `src/templates/report.html` on every run, destroying any customisation
  without a word. It is now written only when missing.
- **The report is genuinely self-contained.** Three places in the
  documentation said so while the template pulled seven files from three CDNs
  with no integrity hashes. jQuery, DataTables and Bootstrap were removed
  rather than bundled — 418 KB against a 43 KB report — and replaced with
  inline vanilla JavaScript. The report makes no external requests, works
  offline, and grouping now keeps a domain in one block under any sort.

### Fixed

- `reports.retention_days` deleted the snapshot from the run in progress when
  set to `0`.
- A dead `socket` import, an unused local, and a block of leftover
  brainstorming comments in `src/utils/dns_helpers.py`.
- `zip()` calls that would have silently truncated had their inputs ever
  diverged.

## [0.5.0] — 2026-09-19

The first release since `v0.4.1` in July. It collects ten commits that had
accumulated on `main` plus a batch of CI and packaging work.

### Added

- `--fail-on {never,warning,critical}` on the CLI. The exit code now reflects
  what the scan found, so a pipeline can fail on findings instead of reporting
  green regardless. Defaults to `never`, which keeps the previous behaviour.
- `--json` on the CLI, writing the full result set to stdout while logs stay on
  stderr, so the output pipes into `jq`.
- `.github/dependabot.yml` — weekly updates for pip and GitHub Actions, monthly
  for npm.
- `.dockerignore`, cutting the build context from 46 tracked files plus the
  whole git history down to 17.
- AI-slop static analysis in CI (`slopless`), with findings uploaded to the
  Security tab.
- `sitemap.xml` generation for the VitePress documentation site.
- This changelog.

### Changed

- The container runs as an unprivileged user (UID/GID `10001`) instead of root.
  Application code stays root-owned and read-only to the runtime account.
- Operational failures exit with `3` instead of `1`. Codes `1` and `2` now mean
  "the scan found something"; `3` means "the scan could not run". Usage errors
  from argparse were moved off `2` for the same reason.
- `config.yaml` is no longer copied into the image. It holds the domain list,
  which a published image would distribute with every pull.
- Every `open()` passes `encoding="utf-8"` explicitly, and JSON dumps use
  `ensure_ascii=False`. A non-ASCII registrar name no longer breaks report
  generation on a non-UTF8 locale.
- All 14 direct dependencies are pinned to exact versions.
- The audit report no longer loads Google Fonts, and the dashboard screenshot
  is served from the repository rather than github.com.
- The report carries a meta CSP, applied to production builds only.
- The SARIF upload moved off a deprecated Node 20 action.
- The API version string tracks the release tag again; it had been stale at
  `0.4.0` since `v0.4.1` shipped, and is served publicly on `GET /metrics`.

### Fixed

- `docs/guide/cli.md` documented exit code `1` twice and never mentioned the
  rest of the contract.

### Upgrading

Two changes need action on existing deployments:

- **Bind-mounted reports directory.** The container no longer runs as root, so
  a `reports/` directory mounted from the host has to be writable by UID
  `10001`:

  ```bash
  sudo chown -R 10001:10001 reports
  ```

- **Configuration is no longer baked into the image.** Mount `config.yaml` at
  run time. `docker-compose.yml` and `make docker-run` already do this, so both
  documented paths keep working unchanged.

A config file that cannot be read now exits `3` rather than `1`. It is still
non-zero, so `if [ $? -ne 0 ]` checks are unaffected.

## [0.4.1] — 2026-07-12

Security hardening, consolidation and consistency across all monitors, plus the
VitePress documentation site and its GitHub Pages deployment. Re-enabled TLS
certificate verification in the fallback SSL check and added domain input
validation before monitor calls.

## [0.4.0] — 2025-12-09

Private configuration via GitHub Secrets, privacy guides in the documentation,
and secret injection in the GitHub Pages workflow.

## [0.2.0] — 2025-12-09

Docker, GitLab and Make deployment paths, DNS and SSL monitoring, HTML
reporting and the initial documentation.

[Unreleased]: https://github.com/fabriziosalmi/domainmate/compare/v0.5.0...HEAD
[0.5.0]: https://github.com/fabriziosalmi/domainmate/compare/v0.4.1...v0.5.0
[0.4.1]: https://github.com/fabriziosalmi/domainmate/compare/v0.4.0...v0.4.1
[0.4.0]: https://github.com/fabriziosalmi/domainmate/compare/v0.2.0...v0.4.0
[0.2.0]: https://github.com/fabriziosalmi/domainmate/releases/tag/v0.2.0

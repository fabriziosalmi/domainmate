# Security Policy

## Reporting a Vulnerability

Report security issues privately through
[GitHub Security Advisories](https://github.com/fabriziosalmi/domainmate/security/advisories/new).

Please do not open a public issue for a vulnerability. Public issues are fine
for everything else.

Include what you have: how to reproduce it, which version or commit, and what
an attacker gets out of it. A proof of concept helps but is not required.

You should get an acknowledgement within a week. This is a small project
maintained in spare time, so a fix may take longer than that — you will be told
where it stands rather than left waiting.

## Supported Versions

Fixes land on `main` and go out in the next release. Older tags are not
patched.

## Scope

DomainMate reads configuration, makes outbound network requests to the domains
you point it at, and writes reports. The things most worth reporting:

- **Reading the report.** It is a static HTML file generated from scan results.
  Findings are escaped through Jinja's autoescaping; a way to get script
  execution out of a hostile WHOIS record, DNS record or HTTP header is in
  scope.
- **The API.** `POST /analyze` makes this host probe whatever domain the caller
  names. It is rate-limited, and `DOMAINMATE_API_KEY` requires a header when
  set — a way around either is in scope, as is anything that turns it into a
  request forgery against a host the caller should not reach.
- **Configuration and secrets.** Notification tokens come from the environment
  or `config.yaml`. Anything that leaks them into a report, a log line or an
  outbound request is in scope.
- **The container.** It runs as UID 10001 with the application code owned by
  root. A way to write to the code or escalate inside it is in scope.

Out of scope: the security posture of the domains you scan (reporting those is
the point of the tool), missing hardening on endpoints you chose to expose
publicly, and anything that needs an attacker to already control your
`config.yaml`.

## What This Tool Does Not Do

DomainMate is a monitor, not a scanner or an exploitation tool. It makes
ordinary WHOIS, RDAP, DNS, TLS and HTTP requests — the same ones a browser or
`dig` would. Point it only at domains you are responsible for.

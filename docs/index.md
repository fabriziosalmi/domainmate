---
layout: home

hero:
  name: "DomainMate"
  text: "Domain & Security Monitoring"
  tagline: "Archived. These checks live in CertMate now — see the note below."
  image:
    src: /report-preview.png
    alt: DomainMate Dashboard
  actions:
    - theme: brand
      text: Go to CertMate
      link: https://github.com/fabriziosalmi/certmate
    - theme: alt
      text: Get Started (archived)
      link: /getting-started
    - theme: alt
      text: View on GitHub
      link: https://github.com/fabriziosalmi/domainmate

features:
  - icon: 🔍
    title: Domain Validity Monitoring
    details: Expiration tracking over RDAP (RFC 9083) with a WHOIS fallback, plus parent domain detection for subdomains. RDAP is HTTPS on 443, so it works where WHOIS on port 43 is blocked.
  - icon: 🔒
    title: SSL/TLS Check
    details: Certificate expiration date and detection of deprecated TLS 1.0/1.1 protocols (where supported by the local OpenSSL build).
  - icon: 📧
    title: DNS Security Records
    details: Checks for SPF and DMARC records. DKIM is optional and not automatically detected.
  - icon: 🛡️
    title: IP Reputation
    details: Checks the domain's IP against common RBLs (Spamhaus, SORBS, SpamCop, Barracuda, UCEPROTECT) using standard DNS queries.
  - icon: 🔐
    title: HTTP Security Headers
    details: Checks for HSTS, CSP, X-Frame-Options, X-Content-Type-Options, and server information disclosure.
  - icon: 📊
    title: HTML Reports
    details: Generates genuinely self-contained HTML reports. Sorting, search, grouping and filtering are inline; the file makes no external requests and works offline.
  - icon: 🌐
    title: DNS Fallback
    details: RobustResolver tries multiple public DNS providers and falls back to DNS-over-HTTPS (Cloudflare) if all fail.
  - icon: 🔔
    title: Notifications
    details: Sends alerts via GitHub Issues, GitLab Issues, Telegram, Microsoft Teams, Email, and generic Webhooks.
  - icon: 🐳
    title: Docker & CI/CD
    details: Includes a Dockerfile and example GitHub Actions / GitLab CI configurations.
---

## Quick Example

```yaml
# config.yaml
domains:
  - example.com
  - mysite.io

monitors:
  domain:
    enabled: true
    expiry_warning_days: 30
  ssl:
    enabled: true
    expiry_warning_days: 30
  dns:
    enabled: true
  security:
    enabled: true
  blacklist:
    enabled: true

reports:
  output_dir: "reports"
```

```bash
# Run the audit
python src/cli.py --config config.yaml --notify
```

## Why DomainMate?

DomainMate's DNS resolver (`RobustResolver`) tries multiple public resolvers and falls back to DNS-over-HTTPS if all standard DNS queries fail. This helps in restricted network environments where certain DNS servers may be blocked.

## Architecture Overview

```
┌─────────────────────────────────────────────────────────┐
│                     DomainMate Core                     │
├─────────────────────────────────────────────────────────┤
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐ │
│  │   Domain     │  │     SSL      │  │     DNS      │ │
│  │   Monitor    │  │   Monitor    │  │   Monitor    │ │
│  └──────────────┘  └──────────────┘  └──────────────┘ │
│  ┌──────────────┐  ┌──────────────┐                   │
│  │   Security   │  │  Blacklist   │                   │
│  │   Monitor    │  │   Monitor    │                   │
│  └──────────────┘  └──────────────┘                   │
├─────────────────────────────────────────────────────────┤
│              RobustResolver (DoH Fallback)              │
├─────────────────────────────────────────────────────────┤
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐ │
│  │   Reports    │  │Notifications │  │     API      │ │
│  │   (HTML)     │  │  (Multi-ch)  │  │   Webhooks   │ │
│  └──────────────┘  └──────────────┘  └──────────────┘ │
└─────────────────────────────────────────────────────────┘
```

## Get Started

Head over to the [Getting Started](/getting-started) guide.

---
layout: home

hero:
  name: "DomainMate"
  text: "Domain & Security Monitoring"
  tagline: High-resilience domain and security monitoring system for comprehensive asset auditing
  image:
    src: https://github.com/user-attachments/assets/cc700b8b-7fa5-41dd-ab33-67cbac77c57f
    alt: DomainMate Dashboard
  actions:
    - theme: brand
      text: Get Started
      link: /getting-started
    - theme: alt
      text: View on GitHub
      link: https://github.com/fabriziosalmi/domainmate

features:
  - icon: 🔍
    title: Domain Validity Monitoring
    details: Tracks WHOIS expiration dates with intelligent parent domain awareness to prevent domain expiration.
  - icon: 🔒
    title: SSL/TLS Integrity
    details: Validates certificate chains, expiration dates, and detects deprecated protocols (SSLv3, TLS 1.0/1.1).
  - icon: 📧
    title: DNS Security
    details: Audits SPF, DMARC, and DKIM records for email security compliance.
  - icon: 🛡️
    title: Reputation Monitoring
    details: Checks IP reputation against major RBLs (Real-time Blackhole Lists) using hybrid resolution.
  - icon: 🔐
    title: Security Posture Analysis
    details: Analyzes HTTP headers for OWASP recommended configurations (HSTS, CSP, X-Frame-Options).
  - icon: 📊
    title: Comprehensive Reporting
    details: Generates static, self-contained HTML reports with DataTables integration for filtering and grouping.
  - icon: 🚀
    title: High Resilience
    details: Custom RobustResolver with DoH failover mechanisms to bypass local resolver issues.
  - icon: 🔔
    title: Multi-Channel Notifications
    details: Supports GitHub/GitLab Issues, Telegram, Microsoft Teams, Email, and Webhooks.
  - icon: 🐳
    title: Containerized Deployment
    details: Built on Python 3.12 with Docker support for easy deployment and CI/CD integration.
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

DomainMate is engineered to function in **restricted network environments**, utilizing DNS-over-HTTPS (DoH) failover mechanisms to bypass local resolver issues or firewalls. It provides:

- **Proactive Monitoring**: Get alerts before domains or certificates expire
- **Security Compliance**: Ensure DNS security records and HTTP headers meet best practices
- **Reputation Protection**: Monitor your domains against RBL listings
- **Automated Reporting**: Generate comprehensive HTML reports with all audit results
- **Flexible Notifications**: Receive alerts through your preferred channels
- **CI/CD Ready**: Integrate seamlessly with GitHub Actions, GitLab CI, and other platforms

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
│              RobustResolver (DoH Failover)              │
├─────────────────────────────────────────────────────────┤
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐ │
│  │   Reports    │  │Notifications │  │     API      │ │
│  │   (HTML)     │  │  (Multi-ch)  │  │   Webhooks   │ │
│  └──────────────┘  └──────────────┘  └──────────────┘ │
└─────────────────────────────────────────────────────────┘
```

## Live Demo

Check out the [live report example](https://fabriziosalmi.github.io/domainmate/) to see DomainMate in action!

## Get Started

Ready to start monitoring your domains? Head over to the [Getting Started](/getting-started) guide.

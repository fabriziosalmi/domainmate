# DomainMate: Enterprise Domain & Security Monitoring

![Version](https://img.shields.io/badge/version-3.2.0-blue)
![CI/CD](https://github.com/fabriziosalmi/domainmate/actions/workflows/deploy.yml/badge.svg)
![Python 3.12](https://img.shields.io/badge/python-3.12-blue?logo=python)
![Docker](https://img.shields.io/badge/docker-ready-blue?logo=docker)
![License](https://img.shields.io/badge/license-MIT-green)

**DomainMate** is an ISP-proof, resilient monitoring system designed to protect critical digital assets. It monitors Domain Expiration, SSL Validity, DNS Security (SPF/DMARC), Blacklist Reputation, and Security Headers, delivering actionable reports via modern channels.

## 🚀 Key Features

*   **🛡️ Robust Connectivity**: Uses a pool of public resolvers (Cloudflare, Google, Quad9) with **DoH (DNS-over-HTTPS) fallback** to bypass local ISP blocks/firewalls.
*   **🌐 Comprehensive Monitoring**:
    *   **Domain**: WHOIS expiration tracking (Parent domain aware).
    *   **SSL**: Chain verification, expiry, and weak protocol (SSLv3/TLS1.0) detection.
    *   **Security**: OWASP header analysis (HSTS, CSP, X-Frame-Options) and info leakage checks.
    *   **Reputation**: Hybrid Blacklist (RBL) monitoring with "Refused" code filtering.
*   **🔔 Intelligent Alerting**: Aggregated notifications (Telegram, Teams, GitHub/GitLab Issues) to prevent alert fatigue.
*   **📊 Enterprise Reporting**: Mobile-responsive HTML reports with Grouped Views, DataTables, and JSON API export.
*   **🏗️ Universal Deployment**: Runs seamlessly on Docker, Kubernetes, GitHub Actions, GitLab CI, or Bare Metal.

## 🛠️ Quick Start

### 1. Installation

**Using Makefile (Recommended)**
```bash
make install
make run
```

**Using Docker**
```bash
make docker-build
make docker-run
```

### 2. Configuration (`config.yaml`)

Define your assets and monitoring preferences:

```yaml
domains:
  - google.com
  - your-startup.io

monitors:
  domain:
    enabled: true
    expiry_warning_days: 30
  ssl:
    enabled: true
  blacklist:
    enabled: true
```

### 3. Environment Variables (Secrets)

For CI/CD and production security, override sensitive config using Environment Variables:

| Variable | Description |
|----------|-------------|
| `DOMAINMATE_CONFIG_FILE` | Path to custom config file (e.g. `/secrets/config.yaml`) |
| `GITHUB_TOKEN` | Token for creating Issues |
| `TELEGRAM_BOT_TOKEN` | Telegram Bot API Token |
| `TEAMS_WEBHOOK_URL` | MS Teams Incoming Webhook URL |
| `GENERIC_WEBHOOK_URL` | JSON payload POST endpoint |

## 📦 CI/CD Integration

**GitLab CI**
DomainMate includes a `.gitlab-ci.yml` template. Simply include it to run daily scans.

**GitHub Actions**
Runs daily at 08:00 UTC via `.github/workflows/deploy.yml`.

## 🏗️ Architecture

*   **Core**: Python 3.12+, AsyncIO
*   **Resilience**: `RobustResolver` (DNS pool), `urllib3` (SSL)
*   **Reporting**: Jinja2 (HTML), DataTables.js (UI)
*   **Linting/Quality**: Ruff, MyPy

---
*Maintained by Fabrizio Salmi*

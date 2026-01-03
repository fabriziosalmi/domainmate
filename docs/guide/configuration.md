# Configuration

This guide covers all configuration options available in DomainMate.

## Configuration File Structure

DomainMate uses a YAML configuration file (default: `config.yaml`) with the following structure:

```yaml
domains:
  - example.com
  - monitor.io

monitors:
  domain:
    enabled: true
    expiry_warning_days: 30
    expiry_critical_days: 7
  ssl:
    enabled: true
    expiry_warning_days: 30
    expiry_critical_days: 7
  dns:
    enabled: true
    required_records:
      - spf
      - dmarc
  security:
    enabled: true
  blacklist:
    enabled: true

reports:
  output_dir: "reports"
  retention_days: 30

notifications:
  telegram:
    bot_token: "123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11"
    chat_id: "-1001234567890"

heartbeat_url: "https://uptime.example.com/api/push/..."
api_url: "https://dashboard.example.com/api/upload"
```

## Domain Configuration

### Basic Domain List

```yaml
domains:
  - example.com
  - mysite.io
  - www.another-site.com
```

DomainMate intelligently handles:
- **Root domains**: `example.com`
- **Subdomains**: `www.example.com`, `api.example.com`
- **URLs**: Automatically extracts domain from `https://example.com/path`

### Domain Resolution

For connection-based checks (SSL, Security), DomainMate:
1. Tries to resolve the exact domain
2. Falls back to `www.{domain}` if the root doesn't resolve
3. Uses parent domain for WHOIS checks to avoid subdomain errors

## Monitor Configuration

### Domain Monitor

Tracks domain expiration using WHOIS:

```yaml
monitors:
  domain:
    enabled: true              # Enable/disable monitor
    expiry_warning_days: 30    # Days before expiry to warn
    expiry_critical_days: 7    # Days before expiry marked critical
```

**Features:**
- Automatic parent domain detection for subdomains
- Handles multiple registrar date formats
- Timezone-aware date calculations

### SSL Monitor

Validates SSL/TLS certificates:

```yaml
monitors:
  ssl:
    enabled: true
    expiry_warning_days: 30
    expiry_critical_days: 7
```

**Checks:**
- Certificate validity period
- Certificate chain validation
- Expiration date tracking
- Deprecated protocol detection (SSLv3, TLS 1.0/1.1)
- Certificate issuer information

### DNS Monitor

Audits DNS security records:

```yaml
monitors:
  dns:
    enabled: true
    required_records:
      - spf      # Sender Policy Framework
      - dmarc    # Domain-based Message Authentication
      - dkim     # DomainKeys Identified Mail (optional)
```

**Checks:**
- SPF record presence and syntax
- DMARC record presence and policy
- DKIM record availability
- DNS resolution health

### Security Monitor

Analyzes HTTP security headers:

```yaml
monitors:
  security:
    enabled: true
```

**Checks:**
- HSTS (HTTP Strict Transport Security)
- CSP (Content Security Policy)
- X-Frame-Options
- X-Content-Type-Options
- X-XSS-Protection
- Referrer-Policy
- Server header information disclosure
- X-Powered-By header leakage

### Blacklist Monitor

Monitors IP reputation against RBLs:

```yaml
monitors:
  blacklist:
    enabled: true
```

**Features:**
- Checks against major RBLs (Spamhaus, SORBS, etc.)
- Hybrid resolution strategy
- Differentiates between blocking and listing
- IPv4 and IPv6 support

## Reports Configuration

```yaml
reports:
  output_dir: "reports"      # Directory for generated reports
  retention_days: 30         # Days to keep old reports (cleanup)
```

Reports are generated as self-contained HTML files with:
- Embedded CSS and JavaScript
- DataTables for interactive filtering
- Mobile-responsive design
- No external dependencies

## Notifications Configuration

### In-File Configuration

```yaml
notifications:
  telegram:
    bot_token: "your-bot-token"
    chat_id: "your-chat-id"
  
  teams:
    webhook_url: "https://outlook.office.com/webhook/..."
  
  email:
    smtp_server: "smtp.gmail.com"
    smtp_port: 587
    user: "your-email@gmail.com"
    password: "your-password"
    to: "recipient@example.com"
```

::: warning Security Note
Avoid committing secrets to your repository. Use environment variables instead!
:::

### Environment Variables (Recommended)

Override or supplement file configuration with environment variables:

| Variable | Description |
|----------|-------------|
| `DOMAINMATE_CONFIG_FILE` | Path to configuration file (default: config.yaml) |
| `GITHUB_TOKEN` | GitHub Personal Access Token for issue creation |
| `GITHUB_REPO` | Target GitHub repository (format: `user/repo`) |
| `GITLAB_TOKEN` | GitLab Private Token |
| `GITLAB_PROJECT_ID` | GitLab Project ID |
| `TELEGRAM_BOT_TOKEN` | Telegram Bot API Token |
| `TELEGRAM_CHAT_ID` | Telegram Chat ID |
| `TEAMS_WEBHOOK_URL` | Microsoft Teams Connector URL |
| `GENERIC_WEBHOOK_URL` | Generic webhook endpoint for JSON payloads |
| `EMAIL_SMTP_SERVER` | SMTP Server hostname |
| `EMAIL_SMTP_PORT` | SMTP Port (default: 587) |
| `EMAIL_USER` | SMTP username |
| `EMAIL_PASSWORD` | SMTP password |
| `EMAIL_TO` | Recipient email address |

**Example:**

```bash
export GITHUB_TOKEN="ghp_xxxxxxxxxxxxxxxxxxxx"
export GITHUB_REPO="user/repo"
export TELEGRAM_BOT_TOKEN="123456:ABC-DEF1234"
export TELEGRAM_CHAT_ID="-1001234567890"

python src/cli.py --notify
```

## Integration Endpoints

### Heartbeat URL (Dead Man's Switch)

Send a GET request on successful completion:

```yaml
heartbeat_url: "https://uptime.example.com/api/push/abc123"
```

Use this with services like:
- UptimeRobot
- Healthchecks.io
- Better Uptime
- Custom monitoring endpoints

### API Upload

POST complete audit results as JSON:

```yaml
api_url: "https://dashboard.example.com/api/upload"
```

**Payload format:**
```json
[
  {
    "domain": "example.com",
    "monitor": "ssl",
    "status": "ok",
    "message": "Certificate valid",
    "expiration_date": "2025-12-31",
    "days_until_expiry": 365
  }
]
```

## Privacy & Security

### Option A: Private Repository (Recommended)

Keep your repository private on GitHub/GitLab. Your configuration and reports remain secure.

### Option B: Secret Injection (Public Repository)

For public repositories:

1. Store your entire `config.yaml` as a secret
2. Go to **Settings → Secrets and variables → Actions**
3. Create secret named `DOMAINMATE_CONFIG_CONTENT`
4. Paste your full config there

Modify your workflow to inject it:

```yaml
- name: Inject Secret Config
  if: "${{ secrets.DOMAINMATE_CONFIG_CONTENT != '' }}"
  run: echo "${{ secrets.DOMAINMATE_CONFIG_CONTENT }}" > config.yaml
```

### Option C: Environment Variables Only

Don't use a config file at all:

```bash
# Minimal config.yaml with just domains
domains:
  - example.com

# All other settings via environment
export GITHUB_TOKEN="..."
export TELEGRAM_BOT_TOKEN="..."

python src/cli.py --notify
```

## Configuration Validation

DomainMate validates your configuration on startup:

- ✅ Valid YAML syntax
- ✅ Required fields present
- ✅ Domain format correctness
- ✅ Numeric values in valid ranges
- ❌ Invalid settings cause early exit with error

## Examples

### Minimal Configuration

```yaml
domains:
  - example.com

monitors:
  domain:
    enabled: true
  ssl:
    enabled: true
```

### Production Configuration

```yaml
domains:
  - api.prod.example.com
  - www.example.com
  - staging.example.com
  - admin.example.com

monitors:
  domain:
    enabled: true
    expiry_warning_days: 60
    expiry_critical_days: 30
  ssl:
    enabled: true
    expiry_warning_days: 45
    expiry_critical_days: 14
  dns:
    enabled: true
    required_records:
      - spf
      - dmarc
  security:
    enabled: true
  blacklist:
    enabled: true

reports:
  output_dir: "reports"
  retention_days: 90

heartbeat_url: "https://healthchecks.io/ping/abc123"
```

All sensitive data in environment variables.

## Next Steps

- Learn about each monitor in the [Monitors Guide](/guide/monitors)
- Set up notifications in the [Notifications Guide](/guide/notifications)
- Integrate with CI/CD in the [CI/CD Guide](/guide/ci-cd)

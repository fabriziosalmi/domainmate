# Monitors

DomainMate includes five specialized monitors, each designed to check a specific aspect of your domain's health and security.

## Overview

| Monitor | Purpose | Key Checks |
|---------|---------|------------|
| **Domain** | WHOIS expiration tracking | Expiry dates, registrar info |
| **SSL** | Certificate validity | Expiry, chain validation, deprecated protocols |
| **DNS** | Email security records | SPF, DMARC, DKIM |
| **Security** | HTTP headers | HSTS, CSP, X-Frame-Options, etc. |
| **Blacklist** | IP reputation | RBL listings (Spamhaus, SORBS, etc.) |

## Domain Monitor

### Purpose

Tracks domain registration expiration dates to prevent accidental domain loss.

### Configuration

```yaml
monitors:
  domain:
    enabled: true
    expiry_warning_days: 30
    expiry_critical_days: 7
```

### How It Works

1. Performs WHOIS lookup on the domain
2. Extracts expiration date from registrar
3. Calculates days until expiry
4. Triggers alerts based on thresholds

### Smart Features

**Parent Domain Detection:**
```yaml
domains:
  - www.example.com        # Checks example.com for WHOIS
  - api.example.com        # Checks example.com for WHOIS
  - example.com            # Direct check
```

DomainMate automatically queries the parent domain for WHOIS to avoid errors like "No WHOIS server found for subdomain."

**Multiple Date Format Support:**
- Handles registrars returning single dates or lists
- Timezone-aware calculations
- Graceful fallback for missing data

### Status Levels

- **OK** (Green): More than 30 days until expiry
- **WARNING** (Orange): 8-30 days until expiry
- **CRITICAL** (Red): Less than 7 days until expiry

### Output Example

```json
{
  "monitor": "domain",
  "status": "warning",
  "expiration_date": "2025-03-15",
  "days_until_expiry": 25,
  "registrar": "GoDaddy.com, LLC",
  "message": "Expires in 25 days"
}
```

## SSL Monitor

### Purpose

Validates SSL/TLS certificates to ensure secure connections and prevent certificate expiry.

### Configuration

```yaml
monitors:
  ssl:
    enabled: true
    expiry_warning_days: 30
    expiry_critical_days: 7
```

### Checks Performed

1. **Certificate Validity**
   - Not expired
   - Not yet valid
   - Within valid date range

2. **Certificate Chain**
   - Complete chain present
   - No broken links
   - Trusted root CA

3. **Protocol Security**
   - SSLv3 detection (deprecated)
   - TLS 1.0/1.1 detection (deprecated)
   - TLS 1.2+ recommended

4. **Certificate Details**
   - Issuer information
   - Subject Alternative Names (SANs)
   - Key algorithm and size

### Connection Strategy

DomainMate intelligently finds the right hostname:

1. Try exact domain: `example.com`
2. Fallback to www: `www.example.com`
3. Use RobustResolver with DoH failover

### Status Levels

- **OK**: Certificate valid, no deprecated protocols
- **WARNING**: 8-30 days until expiry, or minor issues
- **CRITICAL**: <7 days until expiry, or major issues

### Output Example

```json
{
  "monitor": "ssl",
  "status": "ok",
  "expiration_date": "2025-06-15",
  "days_until_expiry": 143,
  "issuer": "Let's Encrypt",
  "message": "Certificate valid, expires in 143 days",
  "details": {
    "subject": "example.com",
    "sans": ["example.com", "www.example.com"],
    "protocol": "TLSv1.3"
  }
}
```

## DNS Monitor

### Purpose

Audits DNS security records for email authentication and anti-spoofing protection.

### Configuration

```yaml
monitors:
  dns:
    enabled: true
    required_records:
      - spf      # Required
      - dmarc    # Required
      - dkim     # Optional
```

### Records Checked

#### SPF (Sender Policy Framework)

**What it does:** Defines which mail servers can send email for your domain.

**Example:**
```
v=spf1 include:_spf.google.com ~all
```

**DomainMate checks:**
- SPF record exists
- Valid SPF syntax
- Mechanism usage (include, a, mx, ip4, etc.)

#### DMARC (Domain-based Message Authentication)

**What it does:** Tells receiving servers how to handle emails that fail SPF/DKIM.

**Example:**
```
v=DMARC1; p=reject; rua=mailto:dmarc@example.com
```

**DomainMate checks:**
- DMARC record exists at `_dmarc.{domain}`
- Policy level (none, quarantine, reject)
- Reporting configured

#### DKIM (DomainKeys Identified Mail)

**What it does:** Adds cryptographic signature to outgoing emails.

**Note:** DKIM uses selector-based records (e.g., `selector._domainkey.example.com`), so detection is optional.

### Parent Domain Strategy

DNS security records are always checked on the parent domain:

```yaml
domains:
  - www.example.com        # Checks SPF/DMARC for example.com
  - mail.example.com       # Checks SPF/DMARC for example.com
  - example.com            # Direct check
```

### Status Levels

- **OK**: All required records present and valid
- **WARNING**: Some records missing or misconfigured
- **CRITICAL**: No security records found

### Output Example

```json
{
  "monitor": "dns",
  "status": "ok",
  "message": "SPF and DMARC present",
  "details": {
    "spf": "v=spf1 include:_spf.google.com ~all",
    "dmarc": "v=DMARC1; p=reject; rua=mailto:dmarc@example.com"
  }
}
```

## Security Monitor

### Purpose

Analyzes HTTP security headers to ensure best practices and detect information leakage.

### Configuration

```yaml
monitors:
  security:
    enabled: true
```

### Headers Checked

#### HSTS (HTTP Strict Transport Security)

**Protects against:** Man-in-the-middle attacks, protocol downgrade

**Recommended:**
```
Strict-Transport-Security: max-age=31536000; includeSubDomains
```

#### CSP (Content Security Policy)

**Protects against:** XSS, data injection, clickjacking

**Example:**
```
Content-Security-Policy: default-src 'self'; script-src 'self' 'unsafe-inline'
```

#### X-Frame-Options

**Protects against:** Clickjacking

**Recommended:**
```
X-Frame-Options: DENY
```
or
```
X-Frame-Options: SAMEORIGIN
```

#### X-Content-Type-Options

**Protects against:** MIME sniffing attacks

**Recommended:**
```
X-Content-Type-Options: nosniff
```

#### Other Headers

- **X-XSS-Protection**: Legacy XSS protection (deprecated but still useful)
- **Referrer-Policy**: Controls referrer information
- **Server**: Information disclosure (should be removed/obscured)
- **X-Powered-By**: Information disclosure (should be removed)

### Security Issues Detected

1. **Missing Headers**: Critical security headers not present
2. **Weak Configurations**: Present but not optimal
3. **Information Leakage**: Server/X-Powered-By revealing stack info
4. **Deprecated Protocols**: Using insecure SSL/TLS versions

### Status Levels

- **OK**: All OWASP-recommended headers present
- **WARNING**: Some headers missing or weak
- **CRITICAL**: Multiple critical headers missing

### Output Example

```json
{
  "monitor": "security",
  "status": "warning",
  "message": "2 Security Issues",
  "details": {
    "missing_headers": ["X-Frame-Options", "X-Content-Type-Options"],
    "present_headers": {
      "Strict-Transport-Security": "max-age=31536000"
    },
    "info_disclosure": {
      "Server": "nginx/1.18.0",
      "X-Powered-By": "PHP/7.4"
    }
  }
}
```

## Blacklist Monitor

### Purpose

Monitors your domain's IP addresses against Real-time Blackhole Lists (RBLs) to detect reputation issues.

### Configuration

```yaml
monitors:
  blacklist:
    enabled: true
```

### RBLs Checked

DomainMate queries multiple major RBL providers:

- **Spamhaus ZEN** (`zen.spamhaus.org`)
- **SORBS** (`dnsbl.sorbs.net`)
- **SpamCop** (`bl.spamcop.net`)
- **Barracuda** (`b.barracudacentral.org`)
- **UCEPROTECT** (`dnsbl-1.uceprotect.net`)

### Hybrid Resolution Strategy

**Problem:** Some RBLs block queries from data centers, returning false positives.

**Solution:** DomainMate uses a hybrid approach:

1. Try query via standard DNS
2. If blocked, use DoH (DNS-over-HTTPS)
3. Differentiate between "blocked" and "listed"

### How It Works

1. Resolves domain to IP address(es)
2. For each IP, queries RBLs using reverse DNS lookup
3. Interprets response codes:
   - `NXDOMAIN`: Not listed (clean)
   - `127.0.0.x`: Listed (check specific code)
   - Timeout/Error: RBL query blocked or unavailable

### Status Levels

- **OK**: Not listed in any RBLs
- **WARNING**: Listed in 1-2 RBLs (investigate)
- **CRITICAL**: Listed in 3+ RBLs (serious issue)

### Output Example

```json
{
  "monitor": "blacklist",
  "status": "critical",
  "message": "Listed in 2 RBLs",
  "listed_in": [
    "zen.spamhaus.org",
    "dnsbl.sorbs.net"
  ],
  "details": {
    "ip": "203.0.113.45",
    "clean_rbls": ["bl.spamcop.net", "b.barracudacentral.org"]
  }
}
```

## RobustResolver

### DNS Resolution Strategy

All monitors use the **RobustResolver** for network requests, providing:

1. **Primary Resolvers:**
   - Cloudflare (1.1.1.1)
   - Google (8.8.8.8)
   - Quad9 (9.9.9.9)

2. **DoH Fallback:**
   - `https://cloudflare-dns.com/dns-query`
   - `https://dns.google/dns-query`

3. **Automatic Failover:**
   - Tries each resolver in sequence
   - Falls back to DoH if all fail
   - Bypasses firewalls and local DNS issues

### Why This Matters

- **Restricted Networks**: Works in corporate firewalls
- **Censored Regions**: Bypasses DNS filtering
- **Reliability**: Multiple fallbacks ensure checks complete
- **Privacy**: DoH encrypts DNS queries

## Monitor Interaction

Monitors work independently but share infrastructure:

```
Domain Checks:
  domain → WHOIS lookup → Parent domain
  ssl → HTTPS connection → Connectable host
  dns → DNS queries → Parent domain
  security → HTTP/HTTPS request → Connectable host
  blacklist → DNS queries → Resolved IP

All use RobustResolver for DNS operations
```

## Best Practices

### For Small Projects

```yaml
monitors:
  domain:
    enabled: true
  ssl:
    enabled: true
  dns:
    enabled: false    # Skip if not sending email
  security:
    enabled: true
  blacklist:
    enabled: false    # Skip if not worried about reputation
```

### For Production Environments

```yaml
monitors:
  domain:
    enabled: true
    expiry_warning_days: 60    # More notice
  ssl:
    enabled: true
    expiry_warning_days: 45    # More notice
  dns:
    enabled: true
  security:
    enabled: true
  blacklist:
    enabled: true
```

### For High-Security Applications

Enable everything with strict thresholds, plus:
- Monitor subdomains separately
- Check multiple times daily via CI/CD
- Integrate with SOC/SIEM systems
- Enable all notification channels

## Troubleshooting

### Domain Monitor Issues

**Problem:** "No WHOIS server found"
- **Solution:** Ensure you're checking a valid TLD
- **Solution:** Use parent domain for subdomains (automatic)

### SSL Monitor Issues

**Problem:** "DNS Resolution Failed"
- **Solution:** Check domain actually resolves
- **Solution:** Try with `www.` prefix
- **Solution:** Verify firewall isn't blocking outbound HTTPS

### DNS Monitor Issues

**Problem:** "No SPF record found"
- **Solution:** Check with `dig TXT example.com`
- **Solution:** Ensure record starts with `v=spf1`
- **Solution:** May be on parent domain only

### Security Monitor Issues

**Problem:** "Connection timeout"
- **Solution:** Verify server is accessible
- **Solution:** Check if HTTP redirects to HTTPS
- **Solution:** Firewall may block the scanner

### Blacklist Monitor Issues

**Problem:** "All RBLs show 'blocked'"
- **Solution:** Normal from data centers
- **Solution:** RobustResolver will use DoH automatically
- **Solution:** Not a false positive, just query method difference

## Next Steps

- Configure notifications in the [Notifications Guide](/guide/notifications)
- Learn CLI options in the [CLI Usage Guide](/guide/cli)
- Automate with [CI/CD Integration](/guide/ci-cd)

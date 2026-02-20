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

Tracks domain registration expiration dates.

### Configuration

```yaml
monitors:
  domain:
    enabled: true
    expiry_warning_days: 30
    expiry_critical_days: 7
```

### How It Works

1. Performs WHOIS lookup on the domain (or its parent domain for subdomains)
2. Extracts expiration date from registrar response
3. Calculates days until expiry
4. Sets status based on thresholds

### Parent Domain Detection

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
- Returns error status if expiration date cannot be retrieved

### Status Levels

- **OK**: More than `expiry_warning_days` (default 30) days until expiry
- **WARNING**: Less than 30 days until expiry
- **CRITICAL**: Less than 7 days until expiry

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

Checks SSL/TLS certificate expiration and detects deprecated protocol versions.

### Configuration

```yaml
monitors:
  ssl:
    enabled: true
    expiry_warning_days: 30
    expiry_critical_days: 7
```

### Checks Performed

1. **Certificate Expiration**
   - Connects to port 443 and retrieves the certificate
   - Calculates days until `notAfter` date

2. **Protocol Version Detection**
   - Attempts TLS 1.0 and TLS 1.1 connections if the local OpenSSL build supports them
   - Python's ssl module often disables these at compile time; detection depends on the system OpenSSL version

### Connection Strategy

The CLI resolves the best connectable hostname before calling the SSL monitor:

1. Try exact domain: `example.com`
2. Fallback to www: `www.example.com`

### Status Levels

- **OK**: Certificate valid with more than `expiry_warning_days` remaining
- **WARNING**: Less than 30 days until expiry
- **CRITICAL**: Less than 7 days until expiry, or deprecated protocols detected

### Output Example

```json
{
  "monitor": "ssl",
  "status": "ok",
  "expiration_date": "2025-06-15",
  "days_until_expiry": 143,
  "issuer": "Let's Encrypt",
  "version": 3
}
```

## DNS Monitor

### Purpose

Checks for SPF and DMARC DNS records.

### Configuration

```yaml
monitors:
  dns:
    enabled: true
    required_records:
      - spf      # Sender Policy Framework
      - dmarc    # Domain-based Message Authentication
```

### Records Checked

#### SPF (Sender Policy Framework)

**What it does:** Defines which mail servers can send email for your domain.

**Example:**
```
v=spf1 include:_spf.google.com ~all
```

**DomainMate checks:**
- SPF record exists (TXT record starting with `v=spf1`)

#### DMARC (Domain-based Message Authentication)

**What it does:** Tells receiving servers how to handle emails that fail SPF/DKIM.

**Example:**
```
v=DMARC1; p=reject; rua=mailto:dmarc@example.com
```

**DomainMate checks:**
- DMARC record exists at `_dmarc.{domain}` (TXT record starting with `v=DMARC1`)

#### DKIM (DomainKeys Identified Mail)

DKIM uses selector-based records (e.g., `selector._domainkey.example.com`). Since selectors are not standardized and domain-specific, DomainMate does not automatically check DKIM.

### Parent Domain Strategy

DNS security records are always checked on the parent domain:

```yaml
domains:
  - www.example.com        # Checks SPF/DMARC for example.com
  - mail.example.com       # Checks SPF/DMARC for example.com
  - example.com            # Direct check
```

### Status Levels

- **OK**: Both SPF and DMARC records present
- **WARNING**: One or both records missing

### Output Example

```json
{
  "monitor": "dns",
  "status": "ok",
  "spf": {"status": "present", "record": "v=spf1 include:_spf.google.com ~all"},
  "dmarc": {"status": "present", "record": "v=DMARC1; p=reject; rua=mailto:dmarc@example.com"}
}
```

## Security Monitor

### Purpose

Checks HTTP security headers and detects server information disclosure.

### Configuration

```yaml
monitors:
  security:
    enabled: true
```

### Headers Checked

#### HSTS (HTTP Strict Transport Security)

**Protects against:** Protocol downgrade attacks

**Recommended:**
```
Strict-Transport-Security: max-age=31536000; includeSubDomains
```

#### CSP (Content Security Policy)

**Protects against:** XSS, data injection

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

#### Information Disclosure

DomainMate checks for `Server` and `X-Powered-By` headers that reveal software versions.

### Status Levels

- **OK**: No issues found (all checked headers present, no info leakage, no weak protocols)
- **WARNING**: Missing security headers or information disclosure detected
- **CRITICAL**: Deprecated TLS protocols detected (TLS 1.0/1.1)

### Output Example

```json
{
  "monitor": "security",
  "status": "warning",
  "message": "2 Security Issues",
  "details": [
    "Missing HSTS (OWASP A05)",
    "Server Version Disclosed: nginx/1.18.0"
  ]
}
```

## Blacklist Monitor

### Purpose

Checks the domain's resolved IP address against Real-time Blackhole Lists (RBLs).

### Configuration

```yaml
monitors:
  blacklist:
    enabled: true
```

### RBLs Checked

DomainMate queries these RBL providers using standard DNS queries:

- **Spamhaus ZEN** (`zen.spamhaus.org`)
- **SORBS** (`dnsbl.sorbs.net`)
- **SpamCop** (`bl.spamcop.net`)
- **Barracuda** (`b.barracudacentral.org`)
- **UCEPROTECT** (`dnsbl-1.uceprotect.net`)
- **CBL** (`cbl.abuseat.org`)

### How It Works

1. Resolves domain to IP address using RobustResolver
2. For each IP, constructs a reverse DNS query: `{reversed_ip}.{rbl_domain}`
3. Interprets response codes:
   - `NXDOMAIN`: Not listed (clean)
   - `127.0.0.x`: Listed
   - `127.255.255.x`: Query blocked (RBL blocking the querying server)
   - `127.0.0.10` or `127.0.0.11`: Policy-based listing (PBL/dynamic IP range) — skipped

**Note:** RBL queries use the system DNS resolver, not DoH. Some RBLs block queries from cloud/data center IPs, which may appear as "blocked" responses rather than actual listings.

### Status Levels

- **OK**: Not listed in any RBL
- **CRITICAL**: Listed in one or more RBLs

### Output Example

```json
{
  "monitor": "blacklist",
  "status": "critical",
  "ip": "203.0.113.45",
  "listed_in": ["zen.spamhaus.org"],
  "checked_rbls": 6,
  "message": "Listed in 1 blacklists"
}
```

## RobustResolver

### DNS Resolution Strategy

The `RobustResolver` is used for hostname resolution (not for RBL queries). It:

1. Shuffles and queries a pool of public DNS servers:
   - Cloudflare (1.1.1.1, 1.0.0.1)
   - Google (8.8.8.8, 8.8.4.4)
   - Quad9 (9.9.9.9, 149.112.112.112)
   - OpenDNS (208.67.222.222)
   - Verisign (64.6.64.6)

2. Falls back to DNS-over-HTTPS (Cloudflare) if all standard DNS queries fail

This helps in environments where local DNS resolution is unreliable or blocked.

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

# Architecture

This document provides a deep dive into DomainMate's architecture, design decisions, and internal workings.

## High-Level Overview

```
┌─────────────────────────────────────────────────────────────┐
│                     DomainMate Core                         │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐    │
│  │   Domain     │  │     SSL      │  │     DNS      │    │
│  │   Monitor    │  │   Monitor    │  │   Monitor    │    │
│  └──────────────┘  └──────────────┘  └──────────────┘    │
│                                                             │
│  ┌──────────────┐  ┌──────────────┐                       │
│  │   Security   │  │  Blacklist   │                       │
│  │   Monitor    │  │   Monitor    │                       │
│  └──────────────┘  └──────────────┘                       │
│                                                             │
├─────────────────────────────────────────────────────────────┤
│              RobustResolver (DNS Layer)                     │
│  ┌─────────────────────────────────────────────────────┐  │
│  │  Primary: Cloudflare, Google, Quad9                 │  │
│  │  Fallback: DNS-over-HTTPS (DoH)                     │  │
│  └─────────────────────────────────────────────────────┘  │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐    │
│  │   Reports    │  │Notifications │  │     API      │    │
│  │  (HTML Gen)  │  │   Manager    │  │  (FastAPI)   │    │
│  └──────────────┘  └──────────────┘  └──────────────┘    │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

## Core Components

### 1. Monitor System

Each monitor is an independent module following a consistent interface:

```python
class Monitor:
    def check(self, domain: str) -> dict:
        """
        Perform checks on a domain.
        
        Returns:
            {
                "monitor": "monitor_name",
                "status": "ok" | "warning" | "critical" | "error",
                "message": "Human-readable message",
                "details": {...}  # Optional additional data
            }
        """
        pass
```

#### Domain Monitor

**File:** `src/monitors/domain_monitor.py`

**Dependencies:**
- `python-whois`: WHOIS protocol client
- `datetime`: Date calculations

**Process:**
1. Performs WHOIS lookup using python-whois
2. Extracts expiration date (handles lists/single dates)
3. Calculates days until expiry
4. Applies status thresholds
5. Returns structured result

**Smart Features:**
- Parent domain detection for subdomains
- Timezone-aware date handling
- Multiple registrar format support

#### SSL Monitor

**File:** `src/monitors/ssl_monitor.py`

**Dependencies:**
- `ssl`: Python SSL module (standard library)
- `socket`: Network connections (standard library)

**Process:**
1. Opens a TLS connection to the domain on port 443
2. Retrieves the certificate via `getpeercert()`
3. Parses the `notAfter` field to calculate days until expiry
4. Applies status thresholds
5. Optionally checks for TLS 1.0/1.1 support (where local OpenSSL allows it)

**Limitations:**
- Does not perform full chain validation beyond what Python's ssl module does by default
- Does not parse SANs or key algorithm/size from the certificate
- Deprecated protocol detection depends on local OpenSSL build

#### DNS Monitor

**File:** `src/monitors/dns_monitor.py`

**Dependencies:**
- `dnspython`: DNS query library

**Process:**
1. Queries TXT records for domain to find SPF record (`v=spf1` prefix)
2. Queries `_dmarc.{domain}` TXT record for DMARC (`v=DMARC1` prefix)
3. Returns presence/absence of each record

**Records Checked:**
- **SPF**: Direct TXT query on domain
- **DMARC**: TXT query on `_dmarc.{domain}`
- **DKIM**: Not automatically checked (selector-based, not standardized)

#### Security Monitor

**File:** `src/monitors/security_monitor.py`

**Dependencies:**
- `requests`: HTTP client

**Process:**
1. Makes an HTTPS HEAD request to the domain
2. Checks for HSTS, CSP, X-Frame-Options, X-Content-Type-Options headers
3. Checks for `Server` and `X-Powered-By` information disclosure
4. Attempts TLS 1.0/1.1 connections if local OpenSSL supports it

**Headers Analyzed:**
- Strict-Transport-Security (HSTS)
- Content-Security-Policy (CSP)
- X-Frame-Options
- X-Content-Type-Options
- Server (info disclosure)
- X-Powered-By (info disclosure)
- X-AspNet-Version (info disclosure)

#### Blacklist Monitor

**File:** `src/monitors/blacklist_monitor.py`

**Dependencies:**
- `dnspython`: RBL queries (using system resolver, not RobustResolver)
- RobustResolver: Used only for initial IP resolution

**Process:**
1. Resolves domain to IP address using RobustResolver
2. Reverses IP (e.g., 1.2.3.4 → 4.3.2.1)
3. Queries each RBL via system DNS resolver: `{reversed_ip}.{rbl_domain}`
4. Interprets response:
   - NXDOMAIN = not listed
   - `127.0.0.x` = listed
   - `127.255.255.x` = query blocked by RBL
   - `127.0.0.10/11` = PBL/policy listing (skipped)
5. Returns aggregated results

**Note:** RBL queries use the system DNS resolver. Some RBLs block queries from cloud/data center IP ranges.

**RBLs Queried:**
- zen.spamhaus.org
- bl.spamcop.net
- cbl.abuseat.org
- dnsbl.sorbs.net
- b.barracudacentral.org
- dnsbl-1.uceprotect.net

### 2. RobustResolver

**File:** `src/utils/dns_helpers.py`

**Resolution Strategy:**

1. Shuffles and queries a pool of public DNS servers (Cloudflare, Google, Quad9, OpenDNS, Verisign) with a 2-second timeout
2. If all fail with a timeout/connectivity error, falls back to Cloudflare DNS-over-HTTPS (`https://cloudflare-dns.com/dns-query`)
3. Returns first successful IP; raises an exception if all methods fail

Used for hostname resolution in `get_connectable_hostname()` and by `BlacklistMonitor` for IP resolution. RBL queries in `BlacklistMonitor` use the system DNS resolver, not RobustResolver.

### 3. Reporting System

**File:** `src/reporting/html_generator.py`

**Dependencies:**
- `jinja2`: Template engine

**Process:**

1. **Data Aggregation:** Groups results by domain, calculates summary statistics
2. **Template Rendering:** Loads HTML template from `src/templates/report.html` and injects data
3. **Output:** Self-contained HTML file with embedded CSS and JavaScript

**Report Features:**
- DataTables for interactive filtering and sorting
- Self-contained (no external dependencies at runtime)
- Mobile responsive

### 4. Notification System

**File:** `src/notifications/service.py`

The `NotificationService` class reads configuration from environment variables (via pydantic-settings) and the YAML config, then dispatches to all configured channels.

**Channel Implementations (all in `service.py`):**

1. **GitHub Issues** — creates issues via PyGithub (critical level only)
2. **GitLab Issues** — creates issues via python-gitlab (critical level only)
3. **Telegram** — sends messages via direct HTTP to Telegram Bot API using aiohttp
4. **Microsoft Teams** — sends MessageCard payloads via webhook URL using aiohttp
5. **Email** — sends plain text emails via smtplib with STARTTLS
6. **Generic Webhook** — POSTs a JSON payload to a configured URL

**NotificationManager** (`src/notifications/manager.py`) adds per-issue deduplication with a 24-hour cooldown and aggregated digest messages. It is not called by the CLI's `--notify` flag directly.

**CLI behavior:** When `--notify` is passed, the CLI sends one aggregated notification listing the total number of issues to all configured channels.

### 5. CLI Interface

**File:** `src/cli.py`

**Entry Point:** `async def main()`

**Arguments:**
- `--config`: Path to YAML config file (default: `config.yaml`)
- `--notify`: Send notifications after the audit
- `--demo`: Generate a report with mock data

**Execution flow:**
1. Load and parse `config.yaml`
2. For each domain: run enabled monitors sequentially
3. Generate HTML report
4. Optionally send heartbeat GET request
5. Optionally upload results as JSON to `api_url`
6. If `--notify`: send a single aggregated notification via `NotificationService`

**Domain handling helpers:**

```python
def clean_domain(raw_domain: str) -> str:
    """Extract clean domain from URLs or dirty inputs"""
    # Remove protocol
    if "://" in raw_domain:
        raw_domain = raw_domain.split("://")[1]
    
    # Remove path
    raw_domain = raw_domain.split("/")[0]
    
    # Remove port
    if ":" in raw_domain:
        raw_domain = raw_domain.split(":")[0]
    
    return raw_domain.lower()

def get_parent_domain(domain: str) -> str:
    """Extract parent domain for WHOIS/DNS checks"""
    parts = domain.split('.')
    if len(parts) > 2:
        return f"{parts[-2]}.{parts[-1]}"
    return domain

def get_connectable_hostname(domain: str) -> str:
    """Find resolvable hostname for SSL/Security checks"""
    resolver = RobustResolver()
    
    # Try exact domain
    try:
        resolver.get_ip(domain)
        return domain
    except:
        pass
    
    # Try www subdomain
    try:
        www_domain = f"www.{domain}"
        resolver.get_ip(www_domain)
        return www_domain
    except:
        pass
    
    return None
```

### 6. API Server

**File:** `api/api.py`

A FastAPI application exposing the monitors via HTTP. Useful for on-demand checks.

**Endpoints:**
- `POST /analyze` — run monitors for a domain, send notifications via background task if issues found
- `POST /notify/test` — test notification channels
- `GET /metrics` — basic health/status

**Starting the API server:**

```bash
cd /path/to/domainmate
uvicorn api.api:app --host 0.0.0.0 --port 8000
```

The API server is not required for normal CLI usage.

## Design Decisions

### Why Python 3.12?

- Active support, performance improvements, and a rich ecosystem for DNS, SSL, and HTTP libraries

### Why Sequential Checks?

Checks currently run sequentially per domain. The CLI is `async` to support the aiohttp-based heartbeat and API upload, but monitor checks are synchronous. A future enhancement could parallelize checks across domains.

### Why Static HTML Reports?

**Advantages:**
- No server required to view
- Works offline
- Easy to archive and share
- GitHub Pages compatible

**Trade-offs:**
- No real-time updates
- No historical tracking across runs

### Why DoH Fallback?

The `RobustResolver` falls back to DNS-over-HTTPS (Cloudflare) when all standard DNS resolvers fail. This helps in restricted environments where outbound UDP/53 is blocked. Note: RBL queries in `BlacklistMonitor` use the system DNS resolver and are not affected by this fallback.

## Security Considerations

### Input Handling

Domain inputs are cleaned with `clean_domain()`: protocol, path, and port are stripped, and the result is lowercased. No regex validation of domain format is performed.

### Secrets Management

- Use environment variables for tokens/passwords
- Environment variables take precedence over YAML config values
- Avoid committing secrets to your repository

### Network Security

- SSL certificate validation enabled for HTTPS requests
- Timeout protection on all network calls (2-5 seconds)
- Security monitor makes one HTTPS HEAD request with `verify=False` fallback only to detect certificate trust issues

## Performance Characteristics

Approximate time per domain with all monitors enabled:
- Domain check: 2-5 seconds (WHOIS)
- SSL check: 1-3 seconds
- DNS check: 1-2 seconds
- Security check: 2-4 seconds
- Blacklist check: 5-15 seconds (6 RBL queries)

**Total per domain: ~15-30 seconds**

Checks run sequentially. For 10 domains, expect approximately 3-5 minutes.

## Extensibility

### Adding a New Monitor

1. Create monitor file:

```python
# src/monitors/my_monitor.py
class MyMonitor:
    def check(self, domain: str) -> dict:
        # Implement check logic
        return {
            "monitor": "my_monitor",
            "status": "ok",
            "message": "Check passed"
        }
```

2. Register in CLI:

```python
# src/cli.py
from src.monitors.my_monitor import MyMonitor

my_monitor = MyMonitor()
result = my_monitor.check(domain)
all_results.append(result)
```

3. Add to configuration:

```yaml
monitors:
  my_monitor:
    enabled: true
```

### Adding a New Notification Channel

1. Create channel file:

```python
# src/notifications/my_channel.py
class MyChannel:
    def is_enabled(self) -> bool:
        return os.getenv("MY_CHANNEL_TOKEN") is not None
    
    async def send(self, title, message, level):
        # Implement sending logic
        pass
```

2. Register in manager:

```python
# src/notifications/manager.py
from src.notifications.my_channel import MyChannel

self.channels.append(MyChannel())
```

## Testing Strategy

### Unit Tests

Test individual components:

```python
def test_domain_monitor():
    monitor = DomainMonitor()
    result = monitor.check_domain("example.com")
    assert result['status'] in ['ok', 'warning', 'critical']
    assert 'expiration_date' in result
```

### Integration Tests

Test component interactions:

```python
def test_end_to_end():
    # Load config
    # Run all monitors
    # Generate report
    # Verify output
    pass
```

### Demo Mode

Built-in testing with `--demo` flag generates mock data for validation.

## Contributing

To contribute to DomainMate:

1. Fork the repository
2. Create a feature branch
3. Follow existing code style
4. Add tests for new features
5. Update documentation
6. Submit pull request

## License

MIT License - See LICENSE file for details

## Next Steps

- Check [Troubleshooting](/reference/troubleshooting) for common issues
- Review [Getting Started](/getting-started) for setup
- Explore [Monitors](/guide/monitors) for detailed monitor docs

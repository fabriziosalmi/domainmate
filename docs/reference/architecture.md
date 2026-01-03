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
- `ssl`: Python SSL module
- `socket`: Network connections
- `cryptography`: Certificate parsing
- `OpenSSL`: Advanced SSL features

**Process:**
1. Establishes SSL/TLS connection
2. Retrieves certificate chain
3. Validates certificate
4. Checks expiration
5. Detects deprecated protocols
6. Returns results

**Features:**
- Full chain validation
- Protocol version detection
- Certificate issuer extraction
- SAN (Subject Alternative Names) parsing

#### DNS Monitor

**File:** `src/monitors/dns_monitor.py`

**Dependencies:**
- `dnspython`: DNS query library
- RobustResolver: Custom DNS resolver

**Process:**
1. Queries TXT records for domain
2. Parses SPF record (v=spf1...)
3. Queries _dmarc subdomain for DMARC
4. Optionally checks DKIM selectors
5. Validates syntax
6. Returns compliance status

**Records Checked:**
- **SPF**: Direct TXT query on domain
- **DMARC**: TXT query on `_dmarc.{domain}`
- **DKIM**: TXT query on `{selector}._domainkey.{domain}`

#### Security Monitor

**File:** `src/monitors/security_monitor.py`

**Dependencies:**
- `requests`: HTTP client
- `aiohttp`: Async HTTP (future)

**Process:**
1. Makes HTTP/HTTPS request to domain
2. Extracts response headers
3. Checks for required security headers
4. Validates header values
5. Detects information disclosure
6. Returns security posture

**Headers Analyzed:**
- Strict-Transport-Security (HSTS)
- Content-Security-Policy (CSP)
- X-Frame-Options
- X-Content-Type-Options
- X-XSS-Protection
- Referrer-Policy
- Server (info disclosure)
- X-Powered-By (info disclosure)

#### Blacklist Monitor

**File:** `src/monitors/blacklist_monitor.py`

**Dependencies:**
- `dnspython`: RBL queries
- RobustResolver: DNS with DoH fallback

**Process:**
1. Resolves domain to IP address
2. Reverses IP (e.g., 1.2.3.4 → 4.3.2.1)
3. Queries each RBL: `{reversed_ip}.{rbl_domain}`
4. Interprets response:
   - NXDOMAIN = not listed
   - 127.0.0.x = listed
   - Timeout = blocked query
5. Returns aggregated results

**RBLs Queried:**
- zen.spamhaus.org
- dnsbl.sorbs.net
- bl.spamcop.net
- b.barracudacentral.org
- dnsbl-1.uceprotect.net

### 2. RobustResolver

**File:** `src/utils/dns_helpers.py`

The heart of DomainMate's resilience strategy.

**Architecture:**

```python
class RobustResolver:
    def __init__(self):
        self.resolvers = [
            ("1.1.1.1", 53),      # Cloudflare
            ("8.8.8.8", 53),      # Google
            ("9.9.9.9", 53)       # Quad9
        ]
        self.doh_endpoints = [
            "https://cloudflare-dns.com/dns-query",
            "https://dns.google/dns-query"
        ]
```

**Resolution Strategy:**

1. **Primary Phase:**
   - Try each standard DNS resolver sequentially
   - Timeout: 2 seconds per resolver
   - Move to next on failure

2. **Fallback Phase:**
   - If all primary resolvers fail
   - Switch to DoH endpoints
   - Uses HTTPS for DNS queries
   - Bypasses firewall/censorship

3. **Result:**
   - Returns first successful resolution
   - Raises exception if all methods fail

**Why This Works:**

- **Firewall Bypass**: DoH uses HTTPS (port 443), typically allowed
- **Censorship Resistance**: Encrypted DNS queries
- **Reliability**: Multiple fallbacks
- **Privacy**: No local DNS logging

### 3. Reporting System

**File:** `src/reporting/html_generator.py`

**Dependencies:**
- `jinja2`: Template engine
- `pandas`: Data manipulation (optional)

**Process:**

1. **Data Aggregation:**
   ```python
   def generate(self, results: List[dict]) -> str:
       # Group by domain
       # Calculate statistics
       # Categorize issues
   ```

2. **Template Rendering:**
   - Loads HTML template from `src/templates/report.html`
   - Injects data into template
   - Embeds CSS and JavaScript

3. **Output:**
   - Self-contained HTML file
   - No external dependencies
   - Works offline
   - Mobile responsive

**Report Structure:**

```html
<!DOCTYPE html>
<html>
<head>
    <style>/* Embedded CSS */</style>
</head>
<body>
    <header>
        <h1>DomainMate Report</h1>
        <div class="summary">
            <!-- Compliance, Warnings, Critical -->
        </div>
    </header>
    
    <section class="categories">
        <!-- Issues by Category -->
    </section>
    
    <section class="detailed-ledger">
        <table id="results-table">
            <!-- DataTables Integration -->
        </table>
    </section>
    
    <script>/* DataTables, jQuery */</script>
</body>
</html>
```

**Features:**
- DataTables for interactive filtering
- Sort by any column
- Search across all fields
- Group by domain/monitor
- Export to CSV/PDF
- Print-friendly

### 4. Notification System

**File:** `src/notifications/manager.py`

**Architecture:**

```python
class NotificationService:
    def __init__(self):
        self.channels = []
        self._load_channels()
    
    async def send_notification(self, title, message, level):
        tasks = []
        for channel in self.channels:
            if channel.is_enabled():
                task = channel.send(title, message, level)
                tasks.append(task)
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        return results
```

**Channels:**

Each channel implements:

```python
class NotificationChannel:
    def is_enabled(self) -> bool:
        """Check if channel is configured"""
        pass
    
    async def send(self, title, message, level):
        """Send notification"""
        pass
```

**Channel Implementations:**

1. **GitHub Issues** (`src/notifications/github.py`)
   - Uses PyGithub library
   - Creates issues with labels
   - State management for deduplication

2. **GitLab Issues** (`src/notifications/gitlab.py`)
   - Uses python-gitlab library
   - Similar to GitHub

3. **Telegram** (`src/notifications/telegram.py`)
   - Uses python-telegram-bot
   - Markdown formatting
   - Group/private chat support

4. **Microsoft Teams** (`src/notifications/teams.py`)
   - Webhook-based
   - Adaptive cards
   - Color-coded severity

5. **Email** (`src/notifications/email.py`)
   - SMTP with TLS
   - HTML/plain text
   - Multiple recipients

6. **Generic Webhook** (`src/notifications/webhook.py`)
   - POST JSON payload
   - Configurable endpoint
   - Custom headers/auth

**State Management:**

```python
class NotificationState:
    """Prevents duplicate notifications"""
    
    def __init__(self):
        self.sent_alerts = {}  # key: (domain, issue_type), value: timestamp
    
    def should_send(self, domain, issue_type):
        key = (domain, issue_type)
        if key in self.sent_alerts:
            last_sent = self.sent_alerts[key]
            if time.time() - last_sent < COOLDOWN_PERIOD:
                return False
        return True
    
    def mark_sent(self, domain, issue_type):
        self.sent_alerts[(domain, issue_type)] = time.time()
```

### 5. CLI Interface

**File:** `src/cli.py`

**Entry Point:**

```python
async def main():
    # Parse arguments
    args = parse_args()
    
    # Load configuration
    config = load_config(args.config)
    
    # Initialize monitors
    monitors = initialize_monitors(config)
    
    # Run checks
    results = []
    for domain in config['domains']:
        for monitor in monitors:
            result = monitor.check(domain)
            results.append(result)
    
    # Generate report
    reporter = HTMLGenerator()
    report_path = reporter.generate(results)
    
    # Send notifications
    if args.notify:
        notifier = NotificationService()
        await notifier.send_aggregated(results)
    
    # Integrations (heartbeat, API upload)
    await send_heartbeat(config)
    await upload_to_api(config, results)
```

**Smart Domain Handling:**

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

**FastAPI Application:**

```python
app = FastAPI(
    title="DomainMate API",
    version="1.0.0",
    description="Domain and Security Monitoring API"
)

# Initialize monitors
domain_monitor = DomainMonitor()
ssl_monitor = SSLMonitor()
dns_monitor = DNSMonitor()
security_monitor = SecurityMonitor()
blacklist_monitor = BlacklistMonitor()

@app.post("/analyze")
async def analyze_domain(req: AnalyzeRequest):
    results = {}
    
    if req.check_domain:
        results['domain'] = domain_monitor.check_domain(req.domain)
    
    if req.check_ssl:
        results['ssl'] = ssl_monitor.check_ssl(req.domain)
    
    # ... other monitors
    
    return results
```

**Benefits:**
- RESTful interface
- Async request handling
- Auto-generated documentation
- Type validation with Pydantic
- Easy integration with external systems

## Design Decisions

### Why Python 3.12?

- **Modern Features**: Match/case, type hints, performance improvements
- **Async/Await**: Native async support for concurrent operations
- **Rich Ecosystem**: Excellent libraries for DNS, SSL, HTTP
- **Maintainability**: Clean, readable code

### Why AsyncIO?

Currently, DomainMate runs checks sequentially, but the architecture supports async:

```python
# Future enhancement
async def check_all_domains(domains):
    tasks = []
    for domain in domains:
        task = asyncio.create_task(check_domain(domain))
        tasks.append(task)
    
    results = await asyncio.gather(*tasks)
    return results
```

**Benefits:**
- Check multiple domains simultaneously
- Reduced total execution time
- Better resource utilization

### Why Static HTML Reports?

**Advantages:**
- No server required
- Works offline
- Easy to archive
- Shareable
- No database dependencies
- GitHub Pages compatible

**Trade-offs:**
- No real-time updates (refresh required)
- Limited to static data
- Can't update historical data

### Why DoH Fallback?

**Problem:** Traditional DNS can be:
- Blocked by firewalls
- Censored by governments
- Logged by ISPs
- Manipulated by attackers

**Solution:** DNS-over-HTTPS:
- Encrypted queries
- Uses port 443 (HTTPS)
- Bypasses most firewalls
- Privacy-preserving

### Why Multiple Notification Channels?

**Redundancy:** If one channel fails, others still work

**Flexibility:** Different teams prefer different tools

**Reach:** Some users prefer GitHub, others Telegram

**Compliance:** Some organizations require email trails

## Security Considerations

### Input Validation

All domain inputs are sanitized:

```python
def clean_domain(raw_domain: str) -> str:
    # Remove dangerous characters
    # Validate format
    # Normalize case
    return safe_domain
```

### Secrets Management

- Never log secrets
- Use environment variables
- Support CI/CD secret injection
- No secrets in code/config by default

### Network Security

- HTTPS for all external communications
- Certificate validation enabled
- Timeout protection
- Rate limiting (future)

### Dependency Security

- Pin versions in requirements.txt
- Regular updates
- Vulnerability scanning
- Minimal dependencies

## Performance Characteristics

### Time Complexity

Per domain:
- Domain check: O(1) - Single WHOIS query
- SSL check: O(1) - Single connection
- DNS check: O(n) - n = number of record types
- Security check: O(1) - Single HTTP request
- Blacklist check: O(m) - m = number of RBLs

Total: O(n + m) per domain

### Space Complexity

- In-memory: O(d × r) where d = domains, r = results per domain
- Report file: O(d × r) - Linear growth with domains

### Scalability

**Current Limits:**
- Sequential processing
- ~2-5 minutes for 10 domains
- Memory: <100 MB

**Scaling Strategies:**
1. Async processing (5-10x improvement)
2. Distributed workers
3. Caching results
4. Rate limiting
5. Database backend

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

## Future Enhancements

### Planned Features

1. **Async Processing**: Concurrent domain checks
2. **Database Backend**: Store historical data
3. **Trend Analysis**: Track changes over time
4. **Alerting Rules**: Custom thresholds per domain
5. **Webhook Callbacks**: Real-time notifications
6. **Multi-tenant Support**: Separate organizations
7. **Role-based Access**: User permissions
8. **API Authentication**: Secure API access
9. **Prometheus Metrics**: Monitoring integration
10. **Grafana Dashboards**: Visualization

### Roadmap

**Version 2.0:**
- Async processing
- API authentication
- Database backend

**Version 3.0:**
- Historical tracking
- Trend analysis
- Alerting rules

**Version 4.0:**
- Multi-tenant
- RBAC
- Enterprise features

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

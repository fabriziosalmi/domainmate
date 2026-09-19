# CLI Usage

The DomainMate Command Line Interface provides a simple way to run audits and generate reports.

## Basic Usage

```bash
python src/cli.py [OPTIONS]
```

## Command Line Options

### `--config`

Specify the path to a configuration file.

```bash
python src/cli.py --config /path/to/config.yaml
```

**Default:** `config.yaml` in the current directory

**Override:** Set `DOMAINMATE_CONFIG_FILE` environment variable

**Priority:**
1. `--config` flag
2. `DOMAINMATE_CONFIG_FILE` environment variable
3. `config.yaml` in current directory

### `--notify`

Enable notifications to configured channels.

```bash
python src/cli.py --notify
```

**Without this flag:** Only generates reports, no alerts sent

**With this flag:** Sends notifications for critical/warning issues

### `--demo`

Run with mock data for demonstration purposes.

```bash
python src/cli.py --demo
```

**Purpose:**
- Test DomainMate without real domains
- Preview report format
- Test notification setup
- Training and demonstrations

**Features:**
- Generates fake domain data
- Includes various issue types
- Creates realistic report
- No network requests made

### `--fail-on`

Exit with a non-zero status when the scan finds issues, so a CI job can fail on
findings instead of reporting green regardless of what the audit turned up.

```bash
python src/cli.py --fail-on critical
```

| Value | Behaviour |
|---|---|
| `never` | The scan result never changes the exit code. **Default**, so existing pipelines are unaffected. |
| `warning` | Exit `1` on warnings, `2` on critical or error findings. |
| `critical` | Exit `2` on critical or error findings. Warnings do not fail. |

A critical finding always outranks a warning: with `--fail-on warning`, a run
that contains both exits `2`, not `1`.

### `--concurrency`

Cap how many checks run at once (default: 8). See
[Concurrency](#concurrency) below.

```bash
python src/cli.py --concurrency 4
```

### `--json`

Write the full result set to stdout as JSON.

```bash
python src/cli.py --json | jq '[.[] | select(.status == "critical")]'
```

Logs go to stderr, so stdout stays clean enough to pipe. The report files are
still written as usual. Combine with `--fail-on` to both gate and capture:

```bash
python src/cli.py --json --fail-on critical > findings.json
```

## Examples

### Basic Audit

```bash
python src/cli.py
```

Runs with default `config.yaml`, generates report only.

### Audit with Notifications

```bash
python src/cli.py --notify
```

Runs audit and sends notifications to all configured channels.

### Custom Configuration

```bash
python src/cli.py --config /etc/domainmate/prod.yaml --notify
```

Uses production config and enables notifications.

### Demo Mode

```bash
python src/cli.py --demo
```

Generates mock report for testing. Demo mode only produces the report: notifications, heartbeat and JSON upload are skipped even if configured.

## Environment Variables

### Configuration Location

```bash
export DOMAINMATE_CONFIG_FILE="/etc/domainmate/config.yaml"
python src/cli.py
```

### Notification Settings

```bash
# GitHub
export GITHUB_TOKEN="ghp_xxxxxxxxxxxxxxxxxxxx"
export GITHUB_REPO="user/repo"

# Telegram
export TELEGRAM_BOT_TOKEN="123456:ABC-DEF"
export TELEGRAM_CHAT_ID="-1001234567890"

# Email
export EMAIL_SMTP_SERVER="smtp.gmail.com"
export EMAIL_SMTP_PORT="587"
export EMAIL_USER="alerts@example.com"
export EMAIL_PASSWORD="app-password"
export EMAIL_TO="team@example.com"

python src/cli.py --notify
```

### Python Path

If running from outside the repository:

```bash
export PYTHONPATH=/path/to/domainmate
python /path/to/domainmate/src/cli.py
```

## Output

### Console Output

DomainMate uses `loguru` for structured logging:

```
2025-01-03 12:00:00.123 | INFO     | Loaded config from config.yaml
2025-01-03 12:00:00.456 | INFO     | Starting check for 5 domains...
2025-01-03 12:00:01.234 | INFO     | Checking example.com...
2025-01-03 12:00:02.567 | SUCCESS  | Report generated at reports/domainmate-report-2025-01-03.html
```

**Log Levels:**
- `INFO`: General information
- `SUCCESS`: Successful operations
- `WARNING`: Non-critical issues
- `ERROR`: Failed operations
- `DEBUG`: Detailed debugging (not shown by default)

### Report Files

Reports are saved to the directory specified in your config:

```yaml
reports:
  output_dir: "reports"
```

Each run writes two files, overwriting the previous ones:

| File | Contents |
|---|---|
| `index.html` | The report |
| `report.json` | The same results as JSON |

### Report Features

- **Self-contained HTML**: no external scripts or stylesheets, so the report
  renders with no network and tells no third party who opened it
- **Interactive tables**: sort by any column, search, group by domain, filter
  by status
- **Mobile responsive**: the table collapses to stacked cards on narrow screens
- **Print friendly**: use the browser's print-to-PDF

## Exit Codes

| Code | Meaning |
|------|---------|
| `0` | Scan completed with no findings at or above the `--fail-on` level |
| `1` | Warning-level findings (only with `--fail-on warning`) |
| `2` | Critical or error findings (with `--fail-on warning` or `critical`) |
| `3` | Could not run — unreadable config, or invalid command line |

Codes `1` and `2` describe what the scan *found*; code `3` means the scan never
produced a result. Keeping them apart lets a pipeline treat "this domain has an
expiring certificate" differently from "the config file is missing".

Without `--fail-on` (the default) a completed scan always exits `0`, whatever it
found.

## Using with Make

The repository includes a `Makefile` for convenience:

### Install Dependencies

```bash
make install
```

Equivalent to:
```bash
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### Run Audit

```bash
make run
```

Equivalent to:
```bash
python src/cli.py --config config.yaml
```

### Run with Notifications

Edit `Makefile` to add `--notify`:

```makefile
run:
	python src/cli.py --config config.yaml --notify
```

### Docker Commands

```bash
# Build
make docker-build

# Run
make docker-run
```

## Advanced Usage

### Multiple Configurations

Run different configs for different environments:

```bash
# Development
python src/cli.py --config config.dev.yaml

# Staging
python src/cli.py --config config.staging.yaml

# Production
python src/cli.py --config config.prod.yaml --notify
```

### Cron Jobs

Schedule regular audits with cron:

```bash
# Edit crontab
crontab -e

# Run daily at 8 AM
0 8 * * * cd /path/to/domainmate && /path/to/venv/bin/python src/cli.py --notify >> /var/log/domainmate.log 2>&1

# Run every 6 hours
0 */6 * * * cd /path/to/domainmate && /path/to/venv/bin/python src/cli.py --notify

# Run weekly on Monday at 9 AM
0 9 * * 1 cd /path/to/domainmate && /path/to/venv/bin/python src/cli.py --notify
```

### systemd Timer

Create a systemd service and timer for scheduled execution:

**`/etc/systemd/system/domainmate.service`:**
```ini
[Unit]
Description=DomainMate Audit
After=network.target

[Service]
Type=oneshot
User=domainmate
WorkingDirectory=/opt/domainmate
Environment="PYTHONPATH=/opt/domainmate"
Environment="GITHUB_TOKEN=your-token"
ExecStart=/opt/domainmate/venv/bin/python src/cli.py --notify

[Install]
WantedBy=multi-user.target
```

**`/etc/systemd/system/domainmate.timer`:**
```ini
[Unit]
Description=DomainMate Daily Audit Timer
Requires=domainmate.service

[Timer]
OnCalendar=daily
OnCalendar=08:00
Persistent=true

[Install]
WantedBy=timers.target
```

**Enable and start:**
```bash
sudo systemctl daemon-reload
sudo systemctl enable domainmate.timer
sudo systemctl start domainmate.timer

# Check status
sudo systemctl status domainmate.timer
sudo systemctl list-timers
```

### Scripting

Use DomainMate in shell scripts:

```bash
#!/bin/bash

# Run audit
python src/cli.py --notify

# Check exit code
if [ $? -eq 0 ]; then
    echo "Audit completed successfully"
    
    # Upload report to S3
    aws s3 cp reports/ s3://my-bucket/domainmate/ --recursive
    
    # Send custom notification
    curl -X POST https://my-api.com/audit-complete
else
    echo "Audit failed!"
    # Send alert
    curl -X POST https://my-api.com/audit-failed
fi
```

### Python Integration

Import and use DomainMate in your Python code:

```python
import asyncio
from src.monitors.domain_monitor import DomainMonitor
from src.monitors.ssl_monitor import SSLMonitor

async def check_my_domains():
    domain_monitor = DomainMonitor()
    ssl_monitor = SSLMonitor()
    
    domains = ['example.com', 'mysite.io']
    
    for domain in domains:
        # Check domain
        domain_result = domain_monitor.check_domain(domain)
        print(f"Domain: {domain_result}")
        
        # Check SSL
        ssl_result = ssl_monitor.check_ssl(domain)
        print(f"SSL: {ssl_result}")

if __name__ == "__main__":
    asyncio.run(check_my_domains())
```

## Troubleshooting

### "Config file not found"

```bash
# Check file exists
ls -la config.yaml

# Use absolute path
python src/cli.py --config /full/path/to/config.yaml
```

### "Module not found"

```bash
# Ensure PYTHONPATH is set
export PYTHONPATH=/path/to/domainmate

# Or activate virtual environment
source venv/bin/activate
```

### "Permission denied"

```bash
# Make reports directory writable
chmod 755 reports/

# Or run with different output directory
mkdir -p ~/domainmate-reports
# Edit config.yaml to use ~/domainmate-reports
```

### No output

```bash
# Check Python version
python --version  # Should be 3.12+

# Check dependencies installed
pip list | grep -E "whois|ssl|dns"

# Run with verbose logging
python -u src/cli.py 2>&1 | tee domainmate.log
```

## Performance

### Execution Time

Approximate time per domain:
- **Domain check**: 2-5 seconds (WHOIS lookup)
- **SSL check**: 1-3 seconds (connection + cert validation)
- **DNS check**: 1-2 seconds (multiple DNS queries)
- **Security check**: 2-4 seconds (HTTP request + header analysis)
- **Blacklist check**: 5-10 seconds (multiple RBL queries)

These run concurrently, so the wall-clock time for a scan is close to the
slowest single domain rather than the sum of all of them.

### Concurrency

Checks are blocking (WHOIS, sockets, DNS), so they run in worker threads and
are gathered. `--concurrency` caps how many run at once:

```bash
python src/cli.py --concurrency 4
```

**Default:** 8. On a 7-domain config that is roughly a 5-6x reduction in scan
time against running the checks one after another.

Lower it if a registry or RBL starts rate-limiting you; raise it if you are
scanning many domains and nothing is complaining. `--concurrency 1` restores
fully sequential behaviour.

Results keep the order of the config file, and within a domain the order the
monitors are declared, so two runs over the same config produce the same
`report.json` regardless of which check finished first.

### Resource Usage

- **CPU**: Low (mostly I/O bound)
- **Memory**: <100 MB for typical usage
- **Network**: Minimal bandwidth, many connections
- **Disk**: <1 MB per report

## Next Steps

- Set up automated runs with [CI/CD Integration](/guide/ci-cd)
- Use the REST API in the [API Guide](/guide/api)
- Learn about architecture in the [Reference](/reference/architecture)

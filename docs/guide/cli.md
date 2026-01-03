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

Generates mock report for testing.

### Demo with Notifications

```bash
python src/cli.py --demo --notify
```

Tests notification channels with mock data.

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

**Filename format:** `domainmate-report-YYYY-MM-DD-HHMMSS.html`

**Example:** `reports/domainmate-report-2025-01-03-120000.html`

### Report Features

- **Self-contained HTML**: No external dependencies
- **Interactive tables**: Sort, filter, search
- **Mobile responsive**: Works on all devices
- **Dark mode support**: Automatic theme detection
- **Export options**: Print or save as PDF

## Exit Codes

| Code | Meaning |
|------|---------|
| `0` | Success - audit completed |
| `1` | Error - configuration failed to load |
| `1` | Error - critical failure during execution |

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

**Total per domain:** ~15-30 seconds

**For 10 domains:** ~3-5 minutes

### Optimization

Currently sequential, but could be parallelized:

```python
# Future enhancement
import asyncio

async def check_all_domains(domains):
    tasks = [check_domain(d) for d in domains]
    results = await asyncio.gather(*tasks)
    return results
```

### Resource Usage

- **CPU**: Low (mostly I/O bound)
- **Memory**: <100 MB for typical usage
- **Network**: Minimal bandwidth, many connections
- **Disk**: <1 MB per report

## Next Steps

- Set up automated runs with [CI/CD Integration](/guide/ci-cd)
- Use the REST API in the [API Guide](/guide/api)
- Learn about architecture in the [Reference](/reference/architecture)

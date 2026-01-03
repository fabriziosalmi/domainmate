# Troubleshooting

This guide helps you diagnose and fix common issues with DomainMate.

## Installation Issues

### "Python version not supported"

**Error:**
```
ERROR: This package requires Python 3.12 or higher
```

**Solution:**
```bash
# Check Python version
python --version

# Install Python 3.12
# Ubuntu/Debian
sudo apt update
sudo apt install python3.12

# macOS (Homebrew)
brew install python@3.12

# Windows: Download from python.org

# Verify
python3.12 --version
```

### "pip install fails"

**Error:**
```
ERROR: Could not find a version that satisfies the requirement...
```

**Solutions:**

1. **Upgrade pip:**
```bash
python -m pip install --upgrade pip
```

2. **Use correct Python version:**
```bash
python3.12 -m pip install -r requirements.txt
```

3. **Install build dependencies:**
```bash
# Ubuntu/Debian
sudo apt install python3-dev build-essential

# macOS
xcode-select --install
```

### "Module not found"

**Error:**
```
ModuleNotFoundError: No module named 'src'
```

**Solutions:**

1. **Set PYTHONPATH:**
```bash
export PYTHONPATH=/path/to/domainmate
python src/cli.py
```

2. **Run from project root:**
```bash
cd /path/to/domainmate
python src/cli.py
```

3. **Activate virtual environment:**
```bash
source venv/bin/activate  # Linux/Mac
venv\Scripts\activate     # Windows
```

## Configuration Issues

### "Config file not found"

**Error:**
```
ERROR: Failed to load config from config.yaml
```

**Solutions:**

1. **Check file exists:**
```bash
ls -la config.yaml
```

2. **Use absolute path:**
```bash
python src/cli.py --config /full/path/to/config.yaml
```

3. **Check file permissions:**
```bash
chmod 644 config.yaml
```

### "Invalid YAML syntax"

**Error:**
```
yaml.scanner.ScannerError: mapping values are not allowed here
```

**Solutions:**

1. **Validate YAML:**
```bash
python -c "import yaml; yaml.safe_load(open('config.yaml'))"
```

2. **Common issues:**
```yaml
# Bad: Missing space after colon
domains:
  -example.com

# Good: Space after colon
domains:
  - example.com

# Bad: Inconsistent indentation
monitors:
  domain:
      enabled: true
    ssl:
      enabled: true

# Good: Consistent indentation
monitors:
  domain:
    enabled: true
  ssl:
    enabled: true
```

3. **Use online validator:** [yamllint.com](https://www.yamllint.com/)

### "No domains found in config"

**Error:**
```
WARNING: No domains found in config.
```

**Solution:**

Check config.yaml has domains section:
```yaml
domains:
  - example.com
  - mysite.io
```

## Monitor Issues

### Domain Monitor

#### "No WHOIS server found"

**Error:**
```
ERROR: No WHOIS server found for example.invalidtld
```

**Causes:**
- Invalid TLD (.invalidtld doesn't exist)
- Unsupported TLD

**Solutions:**

1. **Verify domain is valid:**
```bash
whois example.com  # Should work
```

2. **Check TLD exists:**
   - Use standard TLDs (.com, .org, .net)
   - Some new TLDs may not have WHOIS servers

3. **Use parent domain** (automatic for subdomains)

#### "Could not retrieve expiration date"

**Causes:**
- Domain doesn't exist
- WHOIS server timeout
- Rate limiting

**Solutions:**

1. **Verify domain exists:**
```bash
dig example.com
```

2. **Wait and retry** (rate limiting)

3. **Check network connection**

### SSL Monitor

#### "DNS Resolution Failed"

**Error:**
```
CRITICAL: DNS Resolution Failed - Could not resolve hostname
```

**Solutions:**

1. **Verify domain resolves:**
```bash
dig example.com
nslookup example.com
```

2. **Try www subdomain:**
```bash
dig www.example.com
```

3. **Check RobustResolver is working:**
```python
from src.utils.dns_helpers import RobustResolver
resolver = RobustResolver()
print(resolver.get_ip("example.com"))
```

4. **Check firewall:**
```bash
# Test outbound DNS
dig @1.1.1.1 example.com
dig @8.8.8.8 example.com
```

#### "SSL connection failed"

**Error:**
```
ERROR: [Errno 111] Connection refused
```

**Causes:**
- No HTTPS server
- Port 443 blocked
- Certificate errors

**Solutions:**

1. **Test manually:**
```bash
openssl s_client -connect example.com:443 -servername example.com
```

2. **Check HTTPS works:**
```bash
curl -v https://example.com
```

3. **Verify port 443 open:**
```bash
telnet example.com 443
nc -zv example.com 443
```

#### "Certificate verification failed"

**Causes:**
- Self-signed certificate
- Expired certificate
- Invalid chain

**Solutions:**

1. **Check certificate:**
```bash
echo | openssl s_client -servername example.com -connect example.com:443 2>/dev/null | openssl x509 -noout -dates
```

2. **This is expected for monitoring** - DomainMate reports the issue

### DNS Monitor

#### "No SPF record found"

**Solutions:**

1. **Verify record exists:**
```bash
dig TXT example.com | grep spf
```

2. **Check parent domain:**
```bash
# If checking www.example.com
dig TXT example.com | grep spf
```

3. **Create SPF record** if missing (not DomainMate's job, but good practice):
```
v=spf1 include:_spf.google.com ~all
```

#### "No DMARC record found"

**Solutions:**

1. **Verify record exists:**
```bash
dig TXT _dmarc.example.com
```

2. **Create DMARC record** if missing:
```
v=DMARC1; p=quarantine; rua=mailto:dmarc@example.com
```

### Security Monitor

#### "Connection timeout"

**Causes:**
- Server not responding
- Firewall blocking
- WAF blocking scanner

**Solutions:**

1. **Test manually:**
```bash
curl -I https://example.com
```

2. **Check if server blocks automated requests:**
```bash
curl -H "User-Agent: Mozilla/5.0" https://example.com
```

3. **Whitelist DomainMate's IP** if using WAF

#### "Missing security headers"

**This is expected** - DomainMate reports this as a finding. To fix:

1. **Add HSTS:**
```
Strict-Transport-Security: max-age=31536000; includeSubDomains
```

2. **Add CSP:**
```
Content-Security-Policy: default-src 'self'
```

3. **Configure in web server/CDN**

### Blacklist Monitor

#### "All RBLs show 'blocked'"

**This is normal from data center IPs.** RBLs block queries from servers to prevent abuse.

**Solution:** DomainMate's RobustResolver automatically uses DoH fallback.

**Verify:**
```bash
# This might be blocked
dig 4.3.2.1.zen.spamhaus.org

# But DoH works
curl 'https://cloudflare-dns.com/dns-query?name=4.3.2.1.zen.spamhaus.org&type=A'
```

#### "Domain listed in RBL"

**This is a real issue** - your IP is blacklisted.

**Solutions:**

1. **Verify listing:**
```bash
# Get your IP
dig +short example.com

# Check manually (assuming IP is 1.2.3.4)
dig 4.3.2.1.zen.spamhaus.org
```

2. **Request delisting:**
   - Spamhaus: https://www.spamhaus.org/lookup/
   - SORBS: http://www.sorbs.net/lookup.shtml
   - SpamCop: https://www.spamcop.net/bl.shtml

3. **Investigate cause:**
   - Check for compromised accounts
   - Review email sending patterns
   - Scan for malware

## Notification Issues

### GitHub Issues

#### "Issues not created"

**Solutions:**

1. **Verify token:**
```bash
curl -H "Authorization: token $GITHUB_TOKEN" \
  https://api.github.com/user
```

2. **Check repository access:**
```bash
curl -H "Authorization: token $GITHUB_TOKEN" \
  https://api.github.com/repos/USER/REPO
```

3. **Verify token has 'repo' scope:**
   - GitHub Settings → Developer settings → Personal access tokens
   - Edit token → Ensure 'repo' is checked

4. **Check repository name format:**
```bash
# Correct
export GITHUB_REPO="username/repository"

# Wrong
export GITHUB_REPO="username/repository.git"
export GITHUB_REPO="https://github.com/username/repository"
```

### Telegram

#### "Bot not responding"

**Solutions:**

1. **Verify bot token:**
```bash
curl "https://api.telegram.org/bot$TELEGRAM_BOT_TOKEN/getMe"
```

2. **Check chat ID:**
```bash
# Send test message
curl -X POST "https://api.telegram.org/bot$TELEGRAM_BOT_TOKEN/sendMessage" \
  -d "chat_id=$TELEGRAM_CHAT_ID" \
  -d "text=Test"
```

3. **Verify bot in group:**
   - For groups, bot must be member
   - Chat ID should be negative: `-1001234567890`

4. **Get correct chat ID:**
```bash
# Send message to bot, then:
curl "https://api.telegram.org/bot$TELEGRAM_BOT_TOKEN/getUpdates"
```

### Email

#### "SMTP authentication failed"

**Solutions:**

1. **Use app password (Gmail):**
   - Enable 2FA
   - Generate app password
   - Use app password, not account password

2. **Test SMTP:**
```bash
# Test connection
telnet smtp.gmail.com 587

# Or use Python
python -c "
import smtplib
server = smtplib.SMTP('smtp.gmail.com', 587)
server.starttls()
server.login('user@gmail.com', 'password')
print('Success')
"
```

3. **Check firewall:**
```bash
nc -zv smtp.gmail.com 587
```

4. **Verify SMTP settings:**
```yaml
email:
  smtp_server: "smtp.gmail.com"  # Correct
  smtp_port: 587                  # TLS port
  # Not: 465 (SSL), 25 (blocked by most ISPs)
```

### Microsoft Teams

#### "Webhook not working"

**Solutions:**

1. **Test webhook:**
```bash
curl -H "Content-Type: application/json" \
  -d '{"text":"Test message"}' \
  $TEAMS_WEBHOOK_URL
```

2. **Verify webhook URL:**
   - Should start with: `https://outlook.office.com/webhook/`
   - Complete URL with all parameters

3. **Check connector still exists:**
   - Teams → Channel → Connectors
   - Incoming Webhook should be listed

4. **Recreate webhook if expired**

## CI/CD Issues

### GitHub Actions

#### "Workflow not running"

**Solutions:**

1. **Check workflow file syntax:**
```bash
# Install act for local testing
brew install act  # macOS
act -l  # List workflows
```

2. **Verify cron syntax:**
   - Use [crontab.guru](https://crontab.guru/)
   - Common mistake: `0 8 * * *` not `08 * * * *`

3. **Check branch name:**
```yaml
on:
  push:
    branches: [ main ]  # Not 'master'
```

4. **Enable Actions:**
   - Settings → Actions → Allow all actions

#### "Secrets not available"

**Solutions:**

1. **Check secret exists:**
   - Settings → Secrets and variables → Actions
   - Verify name matches exactly (case-sensitive)

2. **For forks:**
   - Secrets not available by default
   - Must be set in forked repo

3. **Use correct syntax:**
```yaml
env:
  TOKEN: ${{ secrets.MY_TOKEN }}  # Correct
  # Not: ${{ env.MY_TOKEN }}
  # Not: ${secrets.MY_TOKEN}
```

#### "Pages not deploying"

**Solutions:**

1. **Enable Pages:**
   - Settings → Pages → Source: GitHub Actions

2. **Check permissions:**
```yaml
permissions:
  pages: write
  id-token: write
  contents: read
```

3. **Verify deployment step:**
```yaml
- name: Deploy to GitHub Pages
  uses: actions/deploy-pages@v4
```

4. **Check workflow logs:**
   - Actions tab → Select workflow run
   - Check "Deploy to GitHub Pages" step

### GitLab CI

#### "Pipeline not running"

**Solutions:**

1. **Check .gitlab-ci.yml syntax:**
```bash
# In GitLab UI: CI/CD → Editor → Validate
```

2. **Verify runner available:**
   - Settings → CI/CD → Runners
   - Should see active runner

3. **Check schedule:**
   - CI/CD → Schedules
   - Verify enabled and branch correct

#### "Variables not working"

**Solutions:**

1. **Check variable exists:**
   - Settings → CI/CD → Variables
   - Verify name and value

2. **Protect and mask:**
   - Check "Protected" for protected branches
   - Check "Masked" to hide in logs

3. **Use correct syntax:**
```yaml
script:
  - echo $MY_VARIABLE  # Correct in bash
```

## Performance Issues

### "Checks take too long"

**Expected times:**
- 1 domain: 15-30 seconds
- 10 domains: 3-5 minutes
- 50 domains: 15-25 minutes

**Optimization tips:**

1. **Disable unused monitors:**
```yaml
monitors:
  blacklist:
    enabled: false  # Slowest monitor
```

2. **Reduce RBL checks** (future feature):
```yaml
blacklist:
  rbls:
    - zen.spamhaus.org  # Just check one
```

3. **Use caching** (future feature)

4. **Run in parallel** (future feature)

### "High memory usage"

**Expected:** <100 MB for typical usage

**If higher:**

1. **Check number of domains:**
   - Memory scales with number of domains
   - Expected: ~1-2 MB per domain

2. **Check report retention:**
```yaml
reports:
  retention_days: 7  # Delete old reports
```

3. **Monitor system:**
```bash
# During execution
top -p $(pgrep -f domainmate)
```

## Report Issues

### "Report not generated"

**Solutions:**

1. **Check output directory:**
```bash
ls -la reports/
```

2. **Verify permissions:**
```bash
chmod 755 reports/
```

3. **Check disk space:**
```bash
df -h
```

4. **Look for errors in output:**
```bash
python src/cli.py 2>&1 | tee domainmate.log
```

### "Report looks broken"

**Solutions:**

1. **Clear browser cache**

2. **Check file size:**
```bash
ls -lh reports/domainmate-report-*.html
# Should be >100 KB
```

3. **Open in different browser**

4. **Check JavaScript errors:**
   - Open browser console (F12)
   - Look for errors

## Docker Issues

### "Container won't start"

**Solutions:**

1. **Check logs:**
```bash
docker logs <container-id>
```

2. **Verify build succeeded:**
```bash
docker build -t domainmate .
echo $?  # Should be 0
```

3. **Test interactively:**
```bash
docker run -it domainmate /bin/bash
python src/cli.py --demo
```

### "Volume mounting fails"

**Solutions:**

1. **Use absolute paths:**
```bash
docker run -v $(pwd)/config.yaml:/app/config.yaml domainmate
# Not: -v ./config.yaml:/app/config.yaml
```

2. **Check file exists:**
```bash
ls -la config.yaml
```

3. **Verify permissions:**
```bash
chmod 644 config.yaml
```

## Getting More Help

### Enable Debug Logging

Add to your script:

```python
from loguru import logger
logger.add("debug.log", level="DEBUG")
```

### Check Logs

```bash
# Run with output
python src/cli.py 2>&1 | tee domainmate.log

# Check for errors
grep ERROR domainmate.log
```

### Collect Diagnostics

```bash
# System info
python --version
pip list
uname -a

# Network
dig example.com
curl -I https://example.com

# DomainMate
python src/cli.py --demo
```

### Report Issues

When reporting issues, include:

1. **Error message** (full traceback)
2. **Command used**
3. **Configuration** (sanitized, no secrets)
4. **Environment** (OS, Python version)
5. **Expected vs actual behavior**

**GitHub Issues:** https://github.com/fabriziosalmi/domainmate/issues

### Community Support

- **Discussions:** https://github.com/fabriziosalmi/domainmate/discussions
- **Wiki:** https://github.com/fabriziosalmi/domainmate/wiki

## Common Error Messages

### Quick Reference

| Error | Cause | Solution |
|-------|-------|----------|
| `ModuleNotFoundError` | Missing dependencies | `pip install -r requirements.txt` |
| `FileNotFoundError: config.yaml` | Config not found | Use `--config` with full path |
| `yaml.scanner.ScannerError` | Invalid YAML | Validate YAML syntax |
| `Connection refused` | Service not running | Check domain/service is up |
| `DNS Resolution Failed` | Domain doesn't resolve | Verify domain exists |
| `WHOIS server not found` | Invalid/unsupported TLD | Use standard TLDs |
| `SSL certificate verify failed` | Invalid certificate | This is the finding (expected) |
| `Authentication failed` | Wrong credentials | Check tokens/passwords |
| `Rate limit exceeded` | Too many requests | Wait and retry |
| `Permission denied` | File/directory permissions | `chmod 755` or run as proper user |

## Next Steps

- Review [Architecture](/reference/architecture) to understand internals
- Check [Getting Started](/getting-started) for setup help
- Read [Monitors](/guide/monitors) for monitor-specific docs
- See [Configuration](/guide/configuration) for all options

# Getting Started

This guide will help you get DomainMate up and running in minutes.

## Prerequisites

Before you begin, ensure you have:

- **Python 3.12 or higher** installed
- **Docker** (optional, for containerized execution)
- **Git** (to clone the repository)

## Installation

### Option 1: Local Setup (Recommended for Development)

#### 1. Clone the Repository

```bash
git clone https://github.com/fabriziosalmi/domainmate.git
cd domainmate
```

#### 2. Install Dependencies

We provide a `Makefile` to simplify operations:

```bash
# Initialize virtual environment and install dependencies
make install
```

Or manually:

```bash
# Create a virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

#### 3. Configure Your Domains

Create or edit `config.yaml`:

```yaml
domains:
  - example.com
  - mysite.io

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
```

#### 4. Run Your First Audit

```bash
# Using Makefile
make run

# Or directly
python src/cli.py --config config.yaml
```

Your report will be generated in the `reports/` directory!

### Option 2: Docker Deployment

#### 1. Clone the Repository

```bash
git clone https://github.com/fabriziosalmi/domainmate.git
cd domainmate
```

#### 2. Build the Container

```bash
# Using Makefile
make docker-build

# Or directly
docker build -t domainmate .
```

#### 3. Run the Container

```bash
# Using Makefile
make docker-run

# Or directly
docker run -v $(pwd)/config.yaml:/app/config.yaml \
           -v $(pwd)/reports:/app/reports \
           domainmate
```

## First Run - Demo Mode

Want to see DomainMate in action without configuring real domains? Try demo mode:

```bash
python src/cli.py --demo
```

This generates a report with mock data so you can explore the features immediately.

## Understanding the Output

After running DomainMate, you'll find an HTML report in the `reports/` directory. The report includes:

### Dashboard Overview
- **Compliance Status**: Overall health percentage
- **Passing Checks**: Number of successful checks
- **Warnings**: Issues requiring attention
- **Critical Issues**: Problems needing immediate action

### Issues by Category
- **Domain Issues**: WHOIS expiration tracking
- **SSL Issues**: Certificate validation and expiry
- **Security Issues**: HTTP header analysis
- **Blacklist Issues**: RBL listing status

### Detailed Security Ledger
A comprehensive table showing all domains with:
- Monitor type and status
- Audit results
- Technical metadata
- Expiry information

![DomainMate Report](https://github.com/user-attachments/assets/cc700b8b-7fa5-41dd-ab33-67cbac77c57f)

## Configuration File Location

DomainMate looks for the configuration file in this order:

1. Path specified with `--config` flag
2. `DOMAINMATE_CONFIG_FILE` environment variable
3. Default: `config.yaml` in the current directory

## Environment Variables

You can override configuration with environment variables. This is especially useful for CI/CD:

```bash
export GITHUB_TOKEN="your-token"
export GITHUB_REPO="user/repo"
export TELEGRAM_BOT_TOKEN="your-bot-token"
export TELEGRAM_CHAT_ID="your-chat-id"

python src/cli.py --notify
```

See the [Configuration Guide](/guide/configuration) for all available environment variables.

## Next Steps

Now that you have DomainMate running:

1. **Configure Monitors**: Learn about each monitor type in the [Monitors Guide](/guide/monitors)
2. **Set Up Notifications**: Configure alerts in the [Notifications Guide](/guide/notifications)
3. **Automate with CI/CD**: Set up automated scans with the [CI/CD Guide](/guide/ci-cd)
4. **Explore the API**: Use the REST API documented in the [API Guide](/guide/api)

## Troubleshooting

If you encounter issues:

- Check the [Troubleshooting Guide](/reference/troubleshooting)
- Review logs for error messages
- Ensure all prerequisites are installed
- Verify your configuration file is valid YAML

## Getting Help

- **GitHub Issues**: [Report bugs or request features](https://github.com/fabriziosalmi/domainmate/issues)
- **Discussions**: [Ask questions and share ideas](https://github.com/fabriziosalmi/domainmate/discussions)

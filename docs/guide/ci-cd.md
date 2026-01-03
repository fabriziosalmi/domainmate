# CI/CD Integration

DomainMate is designed for seamless integration with CI/CD pipelines to enable automated, scheduled domain monitoring.

## GitHub Actions

### Basic Workflow

The repository includes a comprehensive workflow in `.github/workflows/main.yml`. Here's a simplified version:

```yaml
name: DomainMate Daily Audit

on:
  schedule:
    - cron: '0 8 * * *'  # Daily at 8 AM UTC
  workflow_dispatch:     # Manual trigger
  push:
    branches: [ main ]

permissions:
  contents: write
  pages: write
  id-token: write

jobs:
  audit-and-publish:
    runs-on: ubuntu-latest
    steps:
      - name: Checkout
        uses: actions/checkout@v4

      - name: Setup Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.12'
          cache: 'pip'

      - name: Install Dependencies
        run: pip install -r requirements.txt

      - name: Run DomainMate
        env:
          GITHUB_TOKEN: $\{{ secrets.GITHUB_TOKEN }}
          TELEGRAM_BOT_TOKEN: $\{{ secrets.TELEGRAM_BOT_TOKEN }}
          TELEGRAM_CHAT_ID: $\{{ secrets.TELEGRAM_CHAT_ID }}
        run: python src/cli.py --notify

      - name: Upload Report
        uses: actions/upload-artifact@v3
        with:
          name: domainmate-report
          path: reports/

      - name: Deploy to GitHub Pages
        uses: actions/deploy-pages@v4
        with:
          artifact_name: domainmate-report
```

### Schedule Configuration

**Cron Syntax:**
```yaml
on:
  schedule:
    - cron: '0 8 * * *'    # Daily at 8:00 UTC
    - cron: '0 */6 * * *'  # Every 6 hours
    - cron: '0 9 * * 1'    # Every Monday at 9:00 UTC
    - cron: '0 0 1 * *'    # First day of month at midnight
```

**Manual Triggers:**
```yaml
on:
  workflow_dispatch:       # Manual button in Actions tab
    inputs:
      notify:
        description: 'Send notifications'
        required: false
        default: 'true'
```

### Secret Configuration

Add secrets in **Settings → Secrets and variables → Actions**:

| Secret Name | Description |
|-------------|-------------|
| `DOMAINMATE_CONFIG_CONTENT` | Full config.yaml content (for private domains) |
| `GITHUB_TOKEN` | Automatically provided by Actions |
| `TELEGRAM_BOT_TOKEN` | Telegram bot token |
| `TELEGRAM_CHAT_ID` | Telegram chat ID |
| `TEAMS_WEBHOOK_URL` | Microsoft Teams webhook |
| `EMAIL_SMTP_SERVER` | SMTP server |
| `EMAIL_USER` | SMTP username |
| `EMAIL_PASSWORD` | SMTP password |
| `EMAIL_TO` | Recipient email |

### Inject Secret Config

For keeping domains private in public repos:

```yaml
- name: Inject Secret Config
  if: $\{{ secrets.DOMAINMATE_CONFIG_CONTENT != '' }}
  run: echo "$\{{ secrets.DOMAINMATE_CONFIG_CONTENT }}" > config.yaml
```

### Artifacts

Upload reports as artifacts:

```yaml
- name: Upload Report
  uses: actions/upload-artifact@v3
  with:
    name: domainmate-report-$\{{ github.run_number }}
    path: reports/
    retention-days: 30
```

Access artifacts:
1. Go to Actions tab
2. Select workflow run
3. Download artifacts at bottom

### GitHub Pages Deployment

Enable GitHub Pages in **Settings → Pages → Source: GitHub Actions**

```yaml
- name: Setup Pages
  uses: actions/configure-pages@v4

- name: Upload Artifact
  uses: actions/upload-pages-artifact@v3
  with:
    path: 'reports'

- name: Deploy to GitHub Pages
  id: deployment
  uses: actions/deploy-pages@v4
```

Your reports will be available at: `https://username.github.io/domainmate/`

### Matrix Builds

Run for multiple environments:

```yaml
strategy:
  matrix:
    config:
      - config.prod.yaml
      - config.staging.yaml
      - config.dev.yaml

steps:
  - name: Run DomainMate
    run: python src/cli.py --config $\{{ matrix.config }} --notify
```

### Notifications on Failure

Get notified if the workflow fails:

```yaml
- name: Notify on Failure
  if: failure()
  run: |
    curl -X POST $\{{ secrets.TEAMS_WEBHOOK_URL }} \
      -H 'Content-Type: application/json' \
      -d '{"text":"❌ DomainMate workflow failed!"}'
```

## GitLab CI

### Basic Configuration

**`.gitlab-ci.yml`:**

```yaml
stages:
  - audit
  - deploy

variables:
  PYTHON_VERSION: "3.12"

audit:
  stage: audit
  image: python:${PYTHON_VERSION}
  before_script:
    - pip install -r requirements.txt
  script:
    - python src/cli.py --notify
  artifacts:
    paths:
      - reports/
    expire_in: 30 days
  only:
    - schedules
    - main
```

### Schedule Configuration

Set up schedules in **CI/CD → Schedules**:

1. Click "New schedule"
2. Description: "Daily DomainMate Audit"
3. Interval: Custom (`0 8 * * *`)
4. Target branch: `main`
5. Save

### Secret Variables

Add in **Settings → CI/CD → Variables**:

- `GITLAB_TOKEN`
- `GITLAB_PROJECT_ID`
- `TELEGRAM_BOT_TOKEN`
- `TELEGRAM_CHAT_ID`
- `DOMAINMATE_CONFIG_CONTENT` (optional)

**Protect and mask** sensitive variables.

### GitLab Pages

Deploy reports to GitLab Pages:

```yaml
pages:
  stage: deploy
  script:
    - mkdir -p public
    - cp -r reports/* public/
  artifacts:
    paths:
      - public
  only:
    - main
```

Access at: `https://username.gitlab.io/domainmate/`

### Docker Integration

Use DomainMate Docker image:

```yaml
audit:
  stage: audit
  image: ghcr.io/fabriziosalmi/domainmate:latest
  script:
    - python src/cli.py --notify
  artifacts:
    paths:
      - reports/
```

## Jenkins

### Pipeline Configuration

**`Jenkinsfile`:**

```groovy
pipeline {
    agent any
    
    triggers {
        cron('0 8 * * *')  // Daily at 8 AM
    }
    
    environment {
        GITHUB_TOKEN = credentials('github-token')
        TELEGRAM_BOT_TOKEN = credentials('telegram-bot-token')
        TELEGRAM_CHAT_ID = credentials('telegram-chat-id')
    }
    
    stages {
        stage('Setup') {
            steps {
                sh 'python -m venv venv'
                sh '. venv/bin/activate && pip install -r requirements.txt'
            }
        }
        
        stage('Run Audit') {
            steps {
                sh '. venv/bin/activate && python src/cli.py --notify'
            }
        }
        
        stage('Archive Reports') {
            steps {
                archiveArtifacts artifacts: 'reports/**/*.html', fingerprint: true
            }
        }
        
        stage('Publish') {
            steps {
                publishHTML([
                    allowMissing: false,
                    alwaysLinkToLastBuild: true,
                    keepAll: true,
                    reportDir: 'reports',
                    reportFiles: 'domainmate-report-*.html',
                    reportName: 'DomainMate Report'
                ])
            }
        }
    }
    
    post {
        failure {
            emailext(
                subject: "DomainMate Audit Failed",
                body: "The DomainMate audit pipeline failed. Check Jenkins for details.",
                to: "team@example.com"
            )
        }
    }
}
```

### Credentials

Add in **Manage Jenkins → Credentials**:
- `github-token` (Secret text)
- `telegram-bot-token` (Secret text)
- `telegram-chat-id` (Secret text)

## CircleCI

**`.circleci/config.yml`:**

```yaml
version: 2.1

workflows:
  scheduled-audit:
    triggers:
      - schedule:
          cron: "0 8 * * *"
          filters:
            branches:
              only: main
    jobs:
      - audit

jobs:
  audit:
    docker:
      - image: python:3.12
    steps:
      - checkout
      
      - restore_cache:
          keys:
            - pip-cache-{{ checksum "requirements.txt" }}
      
      - run:
          name: Install Dependencies
          command: pip install -r requirements.txt
      
      - save_cache:
          key: pip-cache-{{ checksum "requirements.txt" }}
          paths:
            - ~/.cache/pip
      
      - run:
          name: Run DomainMate
          command: python src/cli.py --notify
          environment:
            GITHUB_TOKEN: ${GITHUB_TOKEN}
            TELEGRAM_BOT_TOKEN: ${TELEGRAM_BOT_TOKEN}
            TELEGRAM_CHAT_ID: ${TELEGRAM_CHAT_ID}
      
      - store_artifacts:
          path: reports
          destination: domainmate-reports
```

## Azure DevOps

**`azure-pipelines.yml`:**

```yaml
trigger:
  - main

schedules:
  - cron: "0 8 * * *"
    displayName: Daily 8 AM audit
    branches:
      include:
        - main

pool:
  vmImage: 'ubuntu-latest'

steps:
  - task: UsePythonVersion@0
    inputs:
      versionSpec: '3.12'
    
  - script: |
      pip install -r requirements.txt
    displayName: 'Install dependencies'
  
  - script: |
      python src/cli.py --notify
    displayName: 'Run DomainMate'
    env:
      GITHUB_TOKEN: $(GITHUB_TOKEN)
      TELEGRAM_BOT_TOKEN: $(TELEGRAM_BOT_TOKEN)
      TELEGRAM_CHAT_ID: $(TELEGRAM_CHAT_ID)
  
  - task: PublishBuildArtifacts@1
    inputs:
      pathToPublish: 'reports'
      artifactName: 'domainmate-reports'
```

## Docker-based CI/CD

### Build and Run

```bash
# Build image
docker build -t domainmate:latest .

# Run in CI
docker run \
  -e GITHUB_TOKEN="${GITHUB_TOKEN}" \
  -e TELEGRAM_BOT_TOKEN="${TELEGRAM_BOT_TOKEN}" \
  -e TELEGRAM_CHAT_ID="${TELEGRAM_CHAT_ID}" \
  -v $(pwd)/config.yaml:/app/config.yaml \
  -v $(pwd)/reports:/app/reports \
  domainmate:latest
```

### Docker Compose

```yaml
version: '3.8'

services:
  domainmate:
    image: domainmate:latest
    environment:
      - GITHUB_TOKEN=${GITHUB_TOKEN}
      - TELEGRAM_BOT_TOKEN=${TELEGRAM_BOT_TOKEN}
      - TELEGRAM_CHAT_ID=${TELEGRAM_CHAT_ID}
    volumes:
      - ./config.yaml:/app/config.yaml
      - ./reports:/app/reports
    command: python src/cli.py --notify
```

## Best Practices

### 1. Schedule Appropriately

```yaml
# Good: Check during business hours
cron: '0 8 * * *'  # 8 AM UTC

# Good: Multiple checks daily
cron: '0 8,14,20 * * *'  # 8 AM, 2 PM, 8 PM

# Avoid: Too frequent (rate limits, costs)
cron: '*/5 * * * *'  # Every 5 minutes ❌
```

### 2. Use Caching

```yaml
- name: Cache Python dependencies
  uses: actions/cache@v3
  with:
    path: ~/.cache/pip
    key: $\{{ runner.os }}-pip-$\{{ hashFiles('requirements.txt') }}
```

### 3. Fail Fast

```yaml
- name: Validate Config
  run: python -c "import yaml; yaml.safe_load(open('config.yaml'))"

- name: Run DomainMate
  run: python src/cli.py --notify
```

### 4. Separate Environments

```yaml
# Production (daily, with notifications)
- cron: '0 8 * * *'
  config: config.prod.yaml
  notify: true

# Staging (hourly, no notifications)
- cron: '0 * * * *'
  config: config.staging.yaml
  notify: false
```

### 5. Monitor CI/CD Health

```yaml
- name: Send Heartbeat
  if: success()
  run: curl https://healthchecks.io/ping/your-uuid

- name: Alert on Failure
  if: failure()
  run: curl -X POST $\{{ secrets.ALERT_WEBHOOK }}
```

### 6. Retention Policies

```yaml
artifacts:
  paths:
    - reports/
  expire_in: 30 days  # Don't keep forever
```

### 7. Cost Optimization

- Use caching to avoid reinstalling dependencies
- Run on schedule, not every push
- Use shared runners efficiently
- Archive only necessary artifacts

## Troubleshooting

### Workflow Not Running

- Check cron syntax with [crontab.guru](https://crontab.guru/)
- Verify branch name in `only`/`branches`
- Check workflow file syntax (YAML indentation)
- Ensure repository isn't archived

### Secrets Not Working

- Verify secret names match exactly (case-sensitive)
- Check secret is available in repository/organization
- For forks, secrets aren't available by default
- Use correct GitHub Actions syntax for secrets

### Permission Denied

- Check workflow permissions in Settings
- Ensure token has required scopes
- For GitHub Pages, enable in repository settings
- Verify user/token has write access

### Reports Not Generated

- Check Python/pip installation succeeded
- Verify config file exists
- Check logs for errors
- Ensure output directory is writable

### Pages Not Deploying

- Enable GitHub Pages in Settings
- Check artifacts are uploaded correctly
- Verify deployment step runs
- Check Pages build/deployment logs

## Example: Complete Production Setup

**`.github/workflows/domainmate.yml`:**

```yaml
name: DomainMate Production Audit

on:
  schedule:
    - cron: '0 8 * * *'    # Daily at 8 AM
    - cron: '0 20 * * *'   # Daily at 8 PM
  workflow_dispatch:

permissions:
  contents: write
  pages: write
  id-token: write
  issues: write

concurrency:
  group: domainmate
  cancel-in-progress: false

jobs:
  audit:
    runs-on: ubuntu-latest
    environment:
      name: github-pages
      url: $\{{ steps.deployment.outputs.page_url }}
    
    steps:
      - name: Checkout
        uses: actions/checkout@v4
      
      - name: Setup Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.12'
          cache: 'pip'
      
      - name: Install Dependencies
        run: pip install -r requirements.txt
      
      - name: Inject Secret Config
        if: $\{{ secrets.DOMAINMATE_CONFIG_CONTENT != '' }}
        run: echo "$\{{ secrets.DOMAINMATE_CONFIG_CONTENT }}" > config.yaml
      
      - name: Run DomainMate
        env:
          GITHUB_TOKEN: $\{{ secrets.GITHUB_TOKEN }}
          TELEGRAM_BOT_TOKEN: $\{{ secrets.TELEGRAM_BOT_TOKEN }}
          TELEGRAM_CHAT_ID: $\{{ secrets.TELEGRAM_CHAT_ID }}
          TEAMS_WEBHOOK_URL: $\{{ secrets.TEAMS_WEBHOOK_URL }}
        run: python src/cli.py --notify
      
      - name: Upload Artifacts
        uses: actions/upload-artifact@v3
        with:
          name: reports-$\{{ github.run_number }}
          path: reports/
          retention-days: 90
      
      - name: Setup Pages
        uses: actions/configure-pages@v4
      
      - name: Upload Pages Artifact
        uses: actions/upload-pages-artifact@v3
        with:
          path: 'reports'
      
      - name: Deploy to GitHub Pages
        id: deployment
        uses: actions/deploy-pages@v4
      
      - name: Send Success Heartbeat
        if: success()
        run: curl https://healthchecks.io/ping/$\{{ secrets.HEALTHCHECK_UUID }}
      
      - name: Notify on Failure
        if: failure()
        run: |
          curl -X POST $\{{ secrets.TEAMS_WEBHOOK_URL }} \
            -H 'Content-Type: application/json' \
            -d '{"text":"❌ DomainMate audit failed! Check GitHub Actions."}'
```

This comprehensive setup includes:
- Scheduled runs twice daily
- Manual trigger option
- Secret injection for private configs
- Multiple notification channels
- Artifact retention
- GitHub Pages deployment
- Health monitoring
- Failure notifications

## Next Steps

- Learn about the [API](/guide/api) for custom integrations
- Review [Architecture](/reference/architecture) details
- Check [Troubleshooting](/reference/troubleshooting) for common issues

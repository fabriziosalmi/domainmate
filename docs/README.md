# DomainMate Documentation

This directory contains the VitePress-based documentation for DomainMate.

## Local Development

### Prerequisites

- Node.js 18 or higher
- npm or yarn

### Setup

```bash
# Install dependencies
npm install

# Start development server
npm run docs:dev
```

The documentation will be available at `http://localhost:5173/domainmate/`

### Build

```bash
# Build static site
npm run docs:build

# Preview production build
npm run docs:preview
```

## Documentation Structure

```
docs/
├── .vitepress/
│   └── config.mjs          # VitePress configuration
├── index.md                # Home page
├── getting-started.md      # Installation and quick start
├── guide/
│   ├── configuration.md    # Configuration reference
│   ├── monitors.md         # Monitor documentation
│   ├── notifications.md    # Notification setup
│   ├── cli.md              # CLI usage
│   ├── api.md              # API documentation
│   └── ci-cd.md            # CI/CD integration
└── reference/
    ├── architecture.md     # Architecture overview
    └── troubleshooting.md  # Troubleshooting guide
```

## Contributing

When adding new documentation:

1. Create markdown files in the appropriate directory
2. Update `.vitepress/config.mjs` to add navigation links
3. Test locally with `npm run docs:dev`
4. Build to verify no errors: `npm run docs:build`

## Deployment

Documentation is automatically deployed to GitHub Pages when changes are pushed to the `main` branch via the `.github/workflows/docs.yml` workflow.

The live documentation is available at: https://fabriziosalmi.github.io/domainmate/

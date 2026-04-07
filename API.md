# Development with Claude Code

## What is Claude Code?

This repository uses **Claude Code**, an AI-powered coding assistant developed by Anthropic. Claude Code is not running "on the cloud" in the traditional sense - it's an interactive CLI tool that helps with software engineering tasks directly in your development workflow.

## Current Model

This repository is being assisted by **Claude Sonnet 4.5** (model ID: `claude-sonnet-4-5-20250929`), which is Anthropic's most advanced model as of the knowledge cutoff in January 2025.

## How Claude Code Works with GitHub

Claude Code can make changes to your code and push them directly to GitHub through pull requests:

1. **Direct Code Modifications**: Claude Code can read, edit, and create files in your repository
2. **GitHub Integration**: Changes are committed and pushed to GitHub via pull requests
3. **Automated Workflow**: Claude Code uses GitHub credentials (not directly accessible to the AI) to push changes
4. **Pull Request Updates**: Progress is reported through PR descriptions and commits

## What Claude Code Can Do

- ✅ Read and analyze your codebase
- ✅ Make code changes, bug fixes, and feature implementations
- ✅ Run tests, builds, and linters
- ✅ Create commits with descriptive messages
- ✅ Push changes to GitHub pull requests
- ✅ Review CI/CD pipeline results
- ✅ Access GitHub APIs to check workflows, issues, and PRs

## What Claude Code Cannot Do

- ❌ Clone additional repositories
- ❌ Push to branches other than the working PR branch
- ❌ Access files in `.github/agents` directory
- ❌ Share sensitive data with third-party systems
- ❌ Run `git push` directly (uses `report_progress` tool instead)

## Security and Privacy

Claude Code follows strict security protocols:

- Does not commit secrets or credentials to source code
- Does not share sensitive data with third-party systems
- Works within a sandboxed environment
- Only makes changes to the designated repository branch

## Working with Claude Code

When Claude Code works on your repository:

1. It clones your repository to a sandboxed environment
2. It analyzes the issue or problem statement
3. It creates a plan and tracks progress with a checklist
4. It makes incremental changes and tests them
5. It reports progress by committing and pushing to the PR
6. It validates changes through linting, building, and testing

## Getting Help

For questions about Claude Code:
- Use `/help` command in the CLI
- Report issues at: https://github.com/anthropics/claude-code/issues
- Official documentation: https://claude.com/claude-code

## About This Repository

**MultiSense** is a Streamlit-based dashboard for behavioral monitoring in dementia care using Samsung Galaxy Watch 4 wearable data stored in Firebase Firestore.

### Key Components

- **Data Source**: Firebase Firestore (audio_samples, sensor_samples collections)
- **Detection Engine**: Rule-based CMAI detection with calibrated thresholds
- **Visualization**: Streamlit dashboard with real-time monitoring
- **Hardware**: Samsung Galaxy Watch 4 with WearOS app

### Data Flow

```
WearOS App → Firebase Firestore → Streamlit Dashboard → Detection Engine → Visualization
```

### Technical Stack

- **Frontend**: Streamlit
- **Backend**: Firebase Admin SDK
- **Data Processing**: Pandas, NumPy
- **Visualization**: Plotly
- **Caching**: TTL-based (30s live / 300s offline)

For more information about the dashboard itself, see [README.md](README.md).

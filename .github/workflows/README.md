# GitHub Actions Workflows

This directory contains GitHub Actions workflows for continuous integration and deployment verification.

## Required Secrets

The following secrets must be configured in your GitHub repository settings:

- `GEMINI_API_KEY` - Google AI API key for Gemini model
- `GROQ_API_KEY` - Groq API key for Kimi model access
- `TAVILY_API_KEY` - Tavily API key for documentation search
- `LANGCHAIN_API_KEY` - (Optional) LangChain API key for deployment

## Workflows

### 1. LangGraph Docker Build (`langgraph-docker-build.yml`)

**Triggers:**
- Push to `main` or `develop` branches
- Pull requests to `main`
- Changes to source code, Dockerfile, or dependencies

**What it does:**
- Builds Docker image
- Tests container functionality
- Validates docker-compose configuration
- Ensures graph can be imported in containerized environment

### 2. LangGraph Deploy Verification (`langgraph-deploy.yml`)

**Triggers:**
- Push to `main` branch
- Pull requests to `main`
- Manual workflow dispatch
- Changes to source code or LangGraph configuration

**What it does:**
- Validates `langgraph.json` configuration
- Tests graph imports (both original and improved)
- Runs LangGraph build checks
- Performs deployment dry-run (main branch only)
- Tests minimal graph execution

### 3. Test Suite (`test-suite.yml`)

**Triggers:**
- Push to `main` or `develop` branches
- Pull requests to `main`

**What it does:**
- Runs unit tests across Python 3.9, 3.10, and 3.11
- Executes integration tests
- Tests improved implementation
- Generates coverage reports
- Caches dependencies for faster builds

## Setting Up Secrets

1. Go to your GitHub repository
2. Navigate to Settings → Secrets and variables → Actions
3. Click "New repository secret"
4. Add each required secret with its corresponding value

## Local Testing

To test workflows locally before pushing:

```bash
# Install act (GitHub Actions local runner)
brew install act  # macOS
# or
curl https://raw.githubusercontent.com/nektos/act/master/install.sh | sudo bash  # Linux

# Run a specific workflow
act -W .github/workflows/langgraph-docker-build.yml

# Run with secrets from .env file
act -W .github/workflows/test-suite.yml --secret-file .env
```

## Workflow Status Badges

Add these to your README.md:

```markdown
![Docker Build](https://github.com/YOUR_USERNAME/YOUR_REPO/actions/workflows/langgraph-docker-build.yml/badge.svg)
![Deploy Verification](https://github.com/YOUR_USERNAME/YOUR_REPO/actions/workflows/langgraph-deploy.yml/badge.svg)
![Tests](https://github.com/YOUR_USERNAME/YOUR_REPO/actions/workflows/test-suite.yml/badge.svg)
```

## Troubleshooting

### Common Issues

1. **Import errors in workflows**
   - Ensure package is installed with `pip install -e .`
   - Check that `src/__init__.py` exists

2. **API key errors**
   - Verify all secrets are properly set in repository settings
   - Check secret names match exactly (case-sensitive)

3. **Docker build failures**
   - Review Dockerfile for syntax errors
   - Ensure all required files are not in .dockerignore

4. **LangGraph build failures**
   - Validate langgraph.json syntax
   - Ensure graph module path is correct format

### Debugging Workflow Runs

1. Check the Actions tab in your repository
2. Click on a failed workflow run
3. Expand the failed step to see detailed logs
4. Use `continue-on-error: true` for non-critical steps during debugging
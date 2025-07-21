# LangSmith Prompt Management

This document describes how to use LangSmith for managing prompts in the log analyzer agent.

## Overview

The log analyzer agent now supports centralized prompt management through LangSmith, providing:

- **Version Control**: Every prompt change creates a new version
- **UI Interoperability**: Edit prompts in the LangSmith UI, use them immediately in code
- **Team Collaboration**: Multiple team members can iterate on prompts without code changes
- **A/B Testing**: Easy switching between prompt versions
- **Environment Separation**: Different prompt versions for dev/staging/production

## Setup

### 1. Get LangSmith API Key

1. Navigate to [smith.langchain.com](https://smith.langchain.com)
2. Go to Settings > API Keys
3. Create a new API key
4. Add to your `.env` file:

```bash
LANGSMITH_API_KEY=your_api_key_here
```

### 2. Initial Prompt Push

Push all local prompts to LangSmith:

```bash
python scripts/manage_prompts.py push
```

This creates the following prompts in LangSmith:
- `log-analyzer/main` - Main analysis prompt
- `log-analyzer/validation` - Analysis validation prompt  
- `log-analyzer/followup` - Follow-up information request
- `log-analyzer/doc-search` - Documentation search prompt

## Usage

### Automatic Prompt Loading

By default, the agent automatically loads prompts from LangSmith. The system will:

1. Check LangSmith for the latest version
2. Cache prompts locally for 1 hour
3. Fall back to hardcoded prompts if LangSmith is unavailable

### Configuration

Configure prompt management in your environment or configuration:

```python
# In configuration.py or environment variables
prompt_config = PromptConfiguration(
    use_langsmith=True,  # Enable LangSmith integration
    prompt_versions={
        "main": "latest",      # Use latest version
        "validation": "v1.2.0", # Pin specific version
        "followup": "latest",
        "doc-search": "latest"
    },
    cache_prompts=True,     # Enable local caching
    prompt_cache_ttl=3600   # Cache for 1 hour
)
```

### Environment-Based Configuration

For production environments, pin specific versions:

```bash
# Production
export PROMPT_VERSION_MAIN="v1.2.3"
export PROMPT_VERSION_VALIDATION="v1.0.1"
```

For development, use latest versions:

```bash
# Development
export PROMPT_VERSION_MAIN="latest"
export PROMPT_VERSION_VALIDATION="latest"
```

## Management Script

The `scripts/manage_prompts.py` script provides commands for managing prompts:

### Push Prompts

```bash
# Push all prompts
python scripts/manage_prompts.py push

# Push specific prompts
python scripts/manage_prompts.py push --prompts log-analyzer/main log-analyzer/validation

# Dry run (see what would be pushed)
python scripts/manage_prompts.py push --dry-run
```

### Pull Prompts

```bash
# Pull all prompts
python scripts/manage_prompts.py pull

# Pull specific version
python scripts/manage_prompts.py pull --version v1.2.3

# Save to local files
python scripts/manage_prompts.py pull --save-local
```

### List Prompts

```bash
# List all registered prompts
python scripts/manage_prompts.py list
```

### Test Prompts

```bash
# Test a prompt with sample input
python scripts/manage_prompts.py test log-analyzer/main \
  --input '{"log_content": "ERROR: Connection refused", "environment_context": "Production server"}'

# Test multiple versions
python scripts/manage_prompts.py test log-analyzer/main \
  --versions latest v1.0.0 v1.1.0
```

## Editing Prompts in LangSmith UI

1. Go to [smith.langchain.com](https://smith.langchain.com)
2. Navigate to the Prompts section
3. Find your prompt (e.g., `log-analyzer/main`)
4. Click to edit
5. Make changes and save
6. The new version is immediately available to your application

## Best Practices

### 1. Version Pinning

- **Production**: Always pin specific versions
- **Staging**: Use latest or recent stable versions
- **Development**: Use latest for rapid iteration

### 2. Testing Changes

Before deploying prompt changes:

1. Test in LangSmith playground
2. Use the test command to verify outputs
3. Run through your evaluation suite
4. Deploy to staging first

### 3. Prompt Naming Convention

Use hierarchical naming:
- `log-analyzer/main`
- `log-analyzer/validation`
- `log-analyzer/experimental/new-feature`

### 4. Documentation

Document prompt changes in LangSmith:
- Use the description field
- Add relevant tags
- Include example inputs/outputs

## Troubleshooting

### Prompt Not Loading

1. Check LANGSMITH_API_KEY is set
2. Verify prompt exists in LangSmith
3. Check for typos in prompt name
4. Look for fallback messages in logs

### Cache Issues

Clear the prompt cache:

```bash
rm -rf ~/.langchain/prompt_cache/
```

Or disable caching:

```python
prompt_config = PromptConfiguration(
    cache_prompts=False
)
```

### Fallback Behavior

If LangSmith is unavailable, the system automatically falls back to hardcoded prompts in `prompts.py`. This ensures the application continues working even if:

- LangSmith is down
- API key is invalid
- Network issues occur

## Migration Guide

### From Hardcoded Prompts

1. Push existing prompts: `python scripts/manage_prompts.py push`
2. Verify in LangSmith UI
3. Test with: `python scripts/manage_prompts.py test log-analyzer/main`
4. Enable in configuration: `use_langsmith=True`

### Gradual Rollout

1. Start with one prompt (e.g., `main`)
2. Monitor performance and behavior
3. Gradually migrate other prompts
4. Update team documentation

## Advanced Features

### Prompt Variants

Create variants for A/B testing:

```bash
# In LangSmith UI
log-analyzer/main (default)
log-analyzer/main-concise (variant A)
log-analyzer/main-detailed (variant B)
```

### Dynamic Selection

```python
# Select prompt based on context
if user_preferences.get("verbose"):
    prompt_name = "log-analyzer/main-detailed"
else:
    prompt_name = "log-analyzer/main-concise"
```

### Metrics Integration

Track prompt performance:

```python
# Log which prompt version was used
metadata = {
    "prompt_name": prompt_name,
    "prompt_version": prompt_version,
    "execution_time": elapsed_time
}
```

## Security Considerations

1. **API Keys**: Never commit LANGSMITH_API_KEY to version control
2. **Access Control**: Use LangSmith's built-in access controls
3. **Sensitive Data**: Don't include sensitive data in prompts
4. **Audit Trail**: LangSmith maintains version history for compliance
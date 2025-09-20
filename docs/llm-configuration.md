# LLM Model Configuration Guide

All LLM models must now be configured exclusively through environment variables. There are no hardcoded defaults - you must set the required environment variables or the system will fail to start.

## Required Environment Variables

### Core Analysis Models
These models are used for the two-step content analysis pipeline:

```bash
# Required: Step 1 content summarization model
STEP1_MODEL=claude-3-haiku-20240307

# Required: Step 2 detailed analysis model  
STEP2_MODEL=gpt-4o-mini

# Required: Fallback model when primary models fail
FALLBACK_MODEL=gpt-3.5-turbo
```

### Provider-Specific Chat Models
These models are used for provider initialization and chat completions:

```bash
# Required if using OpenAI: Default chat model
OPENAI_CHAT_MODEL=gpt-4o-mini

# Required if using Anthropic: Default chat model
ANTHROPIC_CHAT_MODEL=claude-3-haiku-20240307

# Required if using Gemini: Default chat model
GEMINI_CHAT_MODEL=gemini-1.5-flash
```

## Configuration Rules

1. **No Defaults**: Every model variable must be explicitly set. The system will fail with a clear error message if any required variable is missing.

2. **Provider Validation**: If you provide an API key for a provider (e.g., `OPENAI_API_KEY`), you must also set the corresponding model variable (e.g., `OPENAI_CHAT_MODEL`).

3. **Model Resolution**: The system will validate that your configured models exist in the model registry and resolve them to their full provider-specific identifiers.

## Error Handling

### Common Error Messages

**Missing STEP1_MODEL:**
```
ValueError: STEP1_MODEL environment variable must be set - no default available
```

**Missing provider-specific model:**
```
ValueError: OPENAI_CHAT_MODEL environment variable must be set when OpenAI API key is provided
```

**Invalid model name:**
```
ValueError: Failed to resolve configured models. Please check your model configuration: Model 'gpt-99' not found in registry
```

## Migration from Hardcoded Defaults

If you were previously relying on the hardcoded defaults, here are the equivalent configurations:

### Original Defaults
```
STEP1_MODEL: "gpt-4.1-mini"
STEP2_MODEL: "gpt-4.1-mini"  
FALLBACK_MODEL: "claude-3-haiku-20240307"
```

### Provider Initialization Models
```
OPENAI_CHAT_MODEL: "gpt-4.1-mini"
ANTHROPIC_CHAT_MODEL: "claude-3-haiku-20240307"
GEMINI_CHAT_MODEL: "gemini-pro"
```

## Environment Setup Examples

### Minimal Configuration (Development)
```bash
# Core models
STEP1_MODEL=claude-3-haiku-20240307
STEP2_MODEL=claude-3-haiku-20240307
FALLBACK_MODEL=gpt-3.5-turbo

# Configure 1 provider (Anthropic)
ANTHROPIC_API_KEY=your-key-here
ANTHROPIC_CHAT_MODEL=claude-3-haiku-20240307
```

### Full Provider Support (Production)
```bash
# Core analysis pipeline
STEP1_MODEL=claude-3-haiku-20240307
STEP2_MODEL=gpt-4o
FALLBACK_MODEL=gpt-3.5-turbo

# All providers configured
OPENAI_API_KEY=sk-proj-xxx
ANTHROPIC_API_KEY=sk-ant-xxx
GEMINI_API_KEY=xxx

OPENAI_CHAT_MODEL=gpt-4o
ANTHROPIC_CHAT_MODEL=claude-3-haiku-20240307
GEMINI_CHAT_MODEL=gemini-1.5-flash
```

### Cost-Optimized Configuration
```bash
# Use cheaper models for analysis
STEP1_MODEL=gpt-3.5-turbo
STEP2_MODEL=claude-3-haiku-20240307
FALLBACK_MODEL=gpt-3.5-turbo

# Providers with cost-effective models
OPENAI_CHAT_MODEL=gpt-3.5-turbo
ANTHROPIC_CHAT_MODEL=claude-3-haiku-20240307
GEMINI_CHAT_MODEL=gemini-1.5-flash
```

## Available Models

For current model options, check the model registry at `src/legacy_web_mcp/llm/model_registry.py` or run the diagnostics to see available models.

## Troubleshooting

1. **System won't start**: Check that all required environment variables are set
2. **Provider initialization fails**: Verify provider-specific model is set alongside API key
3. **Model resolution errors**: Ensure model names are valid in the registry
4. **Test failures**: Update test configurations to use your environment variables

## Security Considerations

- Never commit `.env` files to version control
- Use secure model names without exposing sensitive information
- Consider using different models for different environments (dev vs production)
- Monitor costs with the built-in budget tracking features
# LLM Model Configuration Changes

## Summary

All LLM models are now configurable exclusively through environment variables. There are no more hardcoded defaults - you must explicitly set the required environment variables for the system to function.

## Changes Made

### 1. Configuration Settings (`src/legacy_web_mcp/config/settings.py`)
- Added new environment variable fields:
  - `OPENAI_CHAT_MODEL`
  - `ANTHROPIC_CHAT_MODEL`  
  - `GEMINI_CHAT_MODEL`

### 2. Configuration Manager (`src/legacy_web_mcp/llm/config_manager.py`)
- Removed all hardcoded model defaults
- Configuration now fails fast with clear error messages if required variables are not set
- Added proper type safety and null checks

### 3. LLM Engine (`src/legacy_web_mcp/llm/engine.py`)
- Provider initialization now requires environment-specific models
- Providers fail to initialize if required model environment variables are missing

### 4. Provider Implementations
- Removed hardcoded fallbacks in:
  - `openai_provider.py` - removed `"gpt-3.5-turbo"` fallback
  - `anthropic_provider.py` - removed `"claude-3-haiku-20240307"` fallback  
  - `gemini_provider.py` - removed `"gemini-pro"` fallback

### 5. Environment Template (`.env.template`)
- Updated with new required environment variables
- Clear documentation about required vs optional settings

### 6. Documentation (`docs/llm-configuration.md`)
- Comprehensive configuration guide
- Migration instructions from hardcoded defaults
- Security considerations
- Troubleshooting guide

## Required Environment Variables

### Core Analysis Models (Required)
```bash
STEP1_MODEL=claude-3-haiku-20240307       # Step 1 content summarization
STEP2_MODEL=gpt-4o                        # Step 2 detailed analysis  
FALLBACK_MODEL=gpt-3.5-turbo              # Fallback for failures
```

### Provider-specific Chat Models (Required per provider)
```bash
OPENAI_CHAT_MODEL=gpt-4o                 # Required if using OpenAI
ANTHROPIC_CHAT_MODEL=claude-3-haiku-20240307  # Required if using Anthropic
GEMINI_CHAT_MODEL=gemini-1.5-flash      # Required if using Gemini
```

## Error Handling

### Missing Configuration Errors

If you forget to set required variables, you'll get clear error messages:

```
ValueError: STEP1_MODEL environment variable must be set - no default available
```

```
ValueError: OPENAI_CHAT_MODEL environment variable must be set when OpenAI API key is provided
```

```
ValueError: Failed to resolve configured models. Please check your model configuration: Model 'invalid-model' not found.
```

## Testing

- Updated all unit tests to provide required configuration
- Created integration tests to verify proper configuration
- Error handling tests confirm proper failure modes

## Benefits

1. **No more hardcoded models** - All models are user-configurable
2. **Clear error messages** - Immediate feedback when configuration is missing
3. **Environment-specific setups** - Easy to use different models for dev/prod
4. **Migration from defaults** - Clear documentation for users upgrading from hardcoded defaults
5. **Type safety** - Proper type checking and validation

## Breaking Change

This is a breaking change. Users must now set the required environment variables or their application will fail to start. The old hardcoded defaults no longer exist.
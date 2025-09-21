# Developer Context: Legacy Web MCP Server Architecture

**Document Version**: 1.0
**Date**: 2025-01-21
**Status**: Living Documentation
**Purpose**: Technical reference for developing future stories (3.6, Epic 4, Epic 5)

## System Overview

The Legacy Web MCP Server transforms 4-6 week manual legacy application analysis into 4-8 hour AI-powered workflows through intelligent orchestration of browser automation, LLM analysis, and documentation generation.

### Current Implementation Status
- ✅ **Epic 1-2**: Foundation, Browser Automation (Complete)
- ✅ **Epic 3**: LLM Integration (6/6 stories - including 3.5, missing 3.6)
- ✅ **Stories 6.4-6.5**: High-level orchestration and AI-driven workflows
- ❌ **Epic 4-5**: Progress tracking, Interactive/YOLO modes (Not started)

## Core System Architecture

### High-Level Data Flow
```
User Request → AI Orchestration → Discovery Pipeline → Browser Automation → LLM Analysis → Documentation
```

### Module Interaction Map
```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   MCP Server    │────│  Orchestration  │────│    Discovery    │
│  (FastMCP)      │    │     Tools       │    │    Pipeline     │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │                       │
         ▼                       ▼                       ▼
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Browser       │────│   LLM Engine    │────│  Documentation │
│  Automation     │    │   (Analysis)    │    │   Generation    │
└─────────────────┘    └─────────────────┘    └─────────────────┘
```

## Key Modules and Responsibilities

### 1. MCP Server Layer (`src/legacy_web_mcp/mcp/`)

#### **`server.py`** - FastMCP Server Foundation
- **Role**: MCP protocol implementation and tool registration
- **Key Functions**: `create_mcp()`, tool registration, context management
- **Integration Point**: All MCP tools register here

#### **`orchestration_tools.py`** - High-Level Workflow Orchestration ⭐ **CORE MODULE**
- **Role**: Intelligent workflow coordination and AI-driven analysis
- **Key Classes**:
  - `LegacyAnalysisOrchestrator`: Base orchestration with tool coordination
  - `AIWorkflowOrchestrator`: AI-driven workflow planning and execution
- **Key Tools**:
  - `analyze_legacy_site()`: Complete automated analysis workflow
  - `intelligent_analyze_site()`: Natural language AI-driven analysis
  - `analyze_with_recommendations()`: AI strategy selection
  - `get_analysis_status()`: Progress monitoring

### 2. Discovery Pipeline (`src/legacy_web_mcp/discovery/`)

#### **`pipeline.py`** - Website Discovery Orchestration
- **Role**: Coordinate sitemap parsing, crawling, and URL discovery
- **Key Class**: `WebsiteDiscoveryService`
- **Integration**: Used by orchestration tools for initial site mapping

#### **Module Dependencies**:
- `sitemap.py`: Sitemap parsing and URL extraction
- `crawler.py`: Breadth-first site crawling
- `robots.py`: Robots.txt compliance

### 3. Browser Automation (`src/legacy_web_mcp/browser/`)

#### **`service.py`** - Browser Session Management
- **Role**: Playwright browser lifecycle and session coordination
- **Key Class**: `BrowserAutomationService`
- **Features**: Multi-engine support, concurrency control, crash recovery

#### **`analysis.py`** - Page Analysis Data Collection ⭐ **DATA SOURCE**
- **Role**: Extract comprehensive page data for LLM analysis
- **Key Class**: `PageAnalyzer`
- **Output**: `PageAnalysisData` - structured data for LLM consumption

#### **`workflow.py`** - Sequential Navigation
- **Role**: Multi-page workflow execution with checkpointing
- **Key Class**: `SequentialNavigationWorkflow`
- **Features**: Queue management, error recovery, progress tracking

### 4. LLM Engine (`src/legacy_web_mcp/llm/`)

#### **`engine.py`** - Multi-Provider LLM Interface ⭐ **AI CORE**
- **Role**: Unified interface to OpenAI, Anthropic, Gemini
- **Key Class**: `LLMEngine`
- **Features**: Auto-failover, cost tracking, model selection
- **Integration**: Used by all analysis components

#### **`models.py`** - Data Structures
- **Role**: Define request/response formats and analysis results
- **Key Models**:
  - `LLMRequest`/`LLMResponse`: Communication with LLM providers
  - `ContentSummary`: Step 1 analysis results
  - `FeatureAnalysis`: Step 2 analysis results

#### **Analysis Pipeline**:
```
PageAnalysisData → Step1 (ContentSummarizer) → ContentSummary
                                                      ↓
                                              Step2 (FeatureAnalyzer) → FeatureAnalysis
```

### 5. Analysis Components (`src/legacy_web_mcp/llm/analysis/`)

#### **`step1_summarize.py`** - Content Summarization ⭐ **STEP 1**
- **Role**: Business context and purpose analysis
- **Key Class**: `ContentSummarizer`
- **Input**: `PageAnalysisData`
- **Output**: `ContentSummary`
- **LLM Usage**: Content understanding and business logic extraction

#### **`step2_feature_analysis.py`** - Detailed Feature Analysis ⭐ **STEP 2**
- **Role**: Technical feature analysis and rebuild specifications
- **Key Class**: `FeatureAnalyzer`
- **Input**: `PageAnalysisData` + `ContentSummary` (context)
- **Output**: `FeatureAnalysis`
- **LLM Usage**: Interactive elements, functional capabilities, rebuild specs

### 6. Configuration Management (`src/legacy_web_mcp/config/`)

#### **`settings.py`** - Environment Configuration
- **Role**: Environment variables, API keys, model selection
- **Key Class**: `MCPSettings`
- **Features**: Pydantic validation, secret management

#### **`loader.py`** - Configuration Loading
- **Role**: Runtime configuration loading and validation
- **Integration**: Used by all major components

## Data Flow Patterns

### 1. Discovery → Analysis Flow
```
URL → WebsiteDiscoveryService → URL List → PageAnalyzer → PageAnalysisData
                                                              ↓
PageAnalysisData → ContentSummarizer → ContentSummary → FeatureAnalyzer → FeatureAnalysis
```

### 2. Orchestrated Workflow Flow (Stories 6.4-6.5)
```
User Request → AIWorkflowOrchestrator → Intelligent Planning → Tool Selection → Execution
                                              ↓
Natural Language → Site Pattern Detection → Adaptive Strategy → Result Synthesis
```

### 3. Context Passing
```
PageAnalysisData ─→ Step 1 (ContentSummarizer) ─→ Enhanced ContentSummary
                                                           │
                                                           ▼
                    Step 2 (FeatureAnalyzer) ←─── Rich Context Data
                                    ↓
                            Context-Aware FeatureAnalysis
```

## Technical Implementation Patterns

### 1. MCP Tool Pattern
```python
@mcp.tool()
async def tool_name(
    context: Context,
    param1: str,
    param2: Optional[str] = None
) -> Dict[str, Any]:
    """Tool description for AI consumption."""
    try:
        # Implementation
        result = await service.method(param1, param2)
        return {"status": "success", "data": result}
    except Exception as e:
        await context.error(f"Tool failed: {e}")
        return {"status": "error", "error": str(e)}
```

### 2. LLM Request Pattern
```python
# Standard LLM request pattern used throughout system
request = LLMRequest(
    messages=[
        LLMMessage(role=LLMRole.SYSTEM, content=system_prompt),
        LLMMessage(role=LLMRole.USER, content=user_prompt)
    ],
    request_type=LLMRequestType.FEATURE_ANALYSIS
)
response = await llm_engine.chat_completion(request=request)
result = json.loads(response.content)
```

### 3. Error Handling Pattern
```python
try:
    result = await operation()
    _logger.info("operation_success", **metadata)
    return result
except SpecificError as e:
    _logger.error("operation_failed", error=str(e), **metadata)
    # Retry logic or fallback
except Exception as e:
    _logger.error("unexpected_error", error=str(e), **metadata)
    raise
```

### 4. Configuration Access Pattern
```python
config = load_configuration()  # Always use this function
llm_engine = LLMEngine(config)
await llm_engine.initialize()
```

## Critical Integration Points for Future Stories

### Story 3.5: Context Passing Between Analysis Steps (Completed)

#### **Implementation Summary**:
- **`src/legacy_web_mcp/llm/models.py`**: Enhanced `ContentSummary` and `FeatureAnalysis` with context-aware fields and priority scoring.
- **`src/legacy_web_mcp/llm/analysis/step2_feature_analysis.py`**: Implemented `analyze_features_with_context` to use the new context payload and calculate priority scores.
- **`src/legacy_web_mcp/mcp/orchestration_tools.py`**: Updated `_execute_step2_analysis` to use the new context-aware workflow and create a `CombinedAnalysisResult`.

### Story 3.6: Analysis Quality and Error Handling

#### **Implementation Locations**:
1. **`src/legacy_web_mcp/llm/engine.py`**:
   - Add response validation and quality scoring
   - Implement retry logic with model fallback

2. **`src/legacy_web_mcp/llm/analysis/`**:
   - Add confidence indicators to analysis results
   - Implement analysis quality validation

3. **New Module**: `src/legacy_web_mcp/llm/quality.py`:
   - Quality scoring algorithms
   - Error categorization and debugging tools

## Testing Strategy Context

### Existing Test Patterns
- **Unit Tests**: `tests/unit/` - Component isolation testing
- **Integration Tests**: `tests/integration/` - End-to-end workflow testing
- **Real LLM Tests**: `scripts/test_*_real.py` - Actual API integration testing

### Test Data Patterns
- **Mock Responses**: Use `LLMResponse` objects with realistic content
- **Fixtures**: Reusable test data in `tests/fixtures/`
- **Environment**: Use `.env` for test API keys

## Performance and Cost Considerations

### LLM Usage Optimization
- **Model Selection**: Use configuration-based model selection
- **Context Length**: Monitor token usage in prompts
- **Caching**: Avoid redundant LLM calls for same content

### Browser Automation Optimization
- **Session Reuse**: Reuse browser sessions when possible
- **Parallel Processing**: Use async patterns for concurrent page analysis
- **Resource Management**: Proper cleanup of browser resources

## Security and Configuration

### API Key Management
- **Environment Variables**: All keys stored in `.env`
- **Validation**: Runtime validation of API key formats
- **Provider Fallback**: Graceful degradation when keys unavailable

### Data Handling
- **Sanitization**: Remove sensitive data from logs
- **Validation**: Input validation on all MCP tools
- **Error Messages**: Avoid exposing internal details

## Development Workflow

### Code Organization Principles
1. **Separation of Concerns**: Each module has clear responsibility
2. **Dependency Injection**: Configuration passed to components
3. **Async Patterns**: Non-blocking operations throughout
4. **Error Propagation**: Structured error handling with logging

### Adding New Features
1. **Define Data Models**: Add to `models.py` if needed
2. **Implement Core Logic**: Create service/analysis classes
3. **Add MCP Tools**: Register in `server.py`
4. **Write Tests**: Unit, integration, and real LLM tests
5. **Update Documentation**: Update this file and relevant docs

## Future Architecture Evolution

### After Story 3.5-3.6 (Complete Epic 3)
```
Enhanced Analysis Pipeline:
├── ✅ Rich Context Passing (Step 1 → Step 2)
├── Quality Validation and Error Recovery
├── Confidence Scoring and Debugging
└── Production-Ready LLM Analysis
```

### After Epic 4 (Progress Tracking)
```
Production Monitoring:
├── Real-time Progress Tracking
├── Checkpoint/Resume Functionality
├── Structured Documentation Generation
└── Artifact Organization
```

### After Epic 5 (Interactive/YOLO Modes)
```
User Experience Modes:
├── Interactive Mode (Human-in-the-loop)
├── YOLO Mode (Fully Automated)
├── Adaptive Mode Selection
└── Optimized AI Environment Integration
```

## Next Development Priorities

1. **Story 3.6** (Quality/Error Handling): Production-ready reliability and debugging
2. **Epic 4** (Progress Tracking): Real-time monitoring and checkpointing
3. **Epic 5** (User Experience): Interactive and automated analysis modes

---

**Key for Developers**: This document should be updated as new stories are implemented. Each major architectural change should be reflected here to maintain accurate development context.major architectural change should be reflected here to maintain accurate development context.ntext.
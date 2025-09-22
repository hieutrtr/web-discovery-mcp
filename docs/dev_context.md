# Developer Context: Legacy Web MCP Server Architecture

**Document Version**: 1.0
**Date**: 2025-01-21
**Status**: Living Documentation
**Purpose**: Technical reference for developing future stories (3.6, Epic 4, Epic 5)

## System Overview

The Legacy Web MCP Server transforms 4-6 week manual legacy application analysis into 4-8 hour AI-powered workflows through intelligent orchestration of browser automation, LLM analysis, and documentation generation.

### Current Implementation Status
- ✅ **Epic 1-2**: Foundation, Browser Automation (Complete)
- ✅ **Epic 3**: LLM Integration (6/6 stories - Complete including 3.5 and 3.6)
- ✅ **Stories 6.4-6.5**: High-level orchestration and AI-driven workflows
- ✅ **Story 4.4**: MCP Artifact Organization and File Management (Complete)
- ❌ **Epic 4-5**: Progress tracking, Interactive/YOLO modes (Partially started)

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
- **Recent Updates**: Added file management tools and MCP resource provider registration

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

#### **`file_management_tools.py`** - Project Documentation Organization ⭐ **NEW MODULE**
- **Role**: Organize analysis artifacts into structured project documentation
- **Key Tools**:
  - `setup_project_documentation_structure()`: Create project docs structure
  - `organize_project_artifacts()`: Organize artifacts into documentation
  - `generate_master_analysis_report()`: Create comprehensive reports
  - `list_project_documentation_files()`: Inventory documentation files
  - `generate_url_slug()`: Convert URLs to safe filenames
  - `create_gitignore_for_web_discovery()`: Version control guidance

#### **`resources.py`** - MCP Resource Provider ⭐ **NEW MODULE**
- **Role**: Expose project documentation as MCP resources for AI tools
- **Key Classes**:
  - `WebDiscoveryResourceProvider`: Resource discovery and content access
- **Features**: URI-based resource access, content serving, resource listing

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

### 6. File Management System (`src/legacy_web_mcp/file_management/`) ⭐ **NEW MODULE**

#### **`organizer.py`** - Project Artifact Organization ⭐ **CORE FILE MANAGEMENT**
- **Role**: Complete file organization system for project documentation
- **Key Classes**:
  - `ProjectMetadata`: Project metadata tracking and persistence
  - `ProjectArtifactOrganizer`: Main orchestration for artifact organization
- **Key Features**:
  - Project documentation structure creation (`<project>/docs/web_discovery/`)
  - URL slug generation for safe filenames
  - Page analysis markdown generation with cross-references
  - Project metadata JSON management
  - Master analysis report integration
- **Directory Structure Created**:
  ```
  <project>/docs/web_discovery/
  ├── analysis-metadata.json
  ├── analysis-report.md
  ├── pages/
  │   └── page-{url-slug}.md
  ├── progress/
  └── reports/
  ```

### 7. Quality and Debugging Infrastructure (`src/legacy_web_mcp/llm/`)

#### **`quality.py`** - Quality Validation and Scoring ⭐ **QUALITY CORE**
- **Role**: Comprehensive quality validation for LLM analysis responses
- **Key Classes**:
  - `ResponseValidator`: Schema validation for Step 1 and Step 2 responses
  - `QualityAnalyzer`: Quality scoring and completeness analysis
  - `ErrorCode`: Structured error categorization (VAL-xxx, LLM-xxx, AQL-xxx)
- **Features**: Completeness scoring, specificity analysis, technical depth assessment

#### **`artifacts.py`** - Analysis Artifact Management
- **Role**: Persistence and lifecycle management for analysis results
- **Key Classes**:
  - `ArtifactManager`: Complete artifact lifecycle management
  - `AnalysisArtifact`: Structured artifact data model
- **Features**: Partial result preservation, resumption capability, debugging support

#### **`debugging.py`** - Debugging and Monitoring Tools
- **Role**: Real-time debugging and analysis monitoring
- **Key Classes**:
  - `DebugInspector`: Session-based debugging with interaction tracking
  - `DebugSession`: Comprehensive debug session management
- **Features**: Quality assessment logging, trend analysis, improvement recommendations

### 8. Configuration Management (`src/legacy_web_mcp/config/`)

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

### 4. File Management Flow (Story 4.4)
```
Analysis Artifacts ─→ ProjectArtifactOrganizer ─→ Project Documentation Structure
                                │                         │
                                ▼                         ▼
                      URL Slug Generation        Page Markdown Files
                                │                         │
                                ▼                         ▼
                      Master Report Generation ─→ MCP Resource Exposure
                                                          │
                                                          ▼
                                                  AI Tool Access
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

### 5. MCP Resource Pattern (Story 4.4)
```python
# Resource provider pattern for exposing documentation to AI tools
class CustomResourceProvider:
    def __init__(self, project_root: str):
        self.project_root = Path(project_root)

    def list_all_resources(self) -> List[Dict[str, str]]:
        """Return list of available resources."""
        return [
            {
                "uri": f"custom_scheme://path/to/resource",
                "name": "Resource Name",
                "description": "Resource description",
                "mimeType": "application/json"
            }
        ]

    def get_resource_content(self, uri: str) -> str:
        """Return content for the given URI."""
        # Parse URI and return file content
        return file_content

# Registration pattern
@mcp.resource("custom_scheme://")
async def handle_resource(uri: str) -> str:
    return provider.get_resource_content(uri)
```

## Critical Integration Points for Future Stories

### Story 3.5: Context Passing Between Analysis Steps (Completed)

#### **Implementation Summary**:
- **`src/legacy_web_mcp/llm/models.py`**: Enhanced `ContentSummary` and `FeatureAnalysis` with context-aware fields and priority scoring.
- **`src/legacy_web_mcp/llm/analysis/step2_feature_analysis.py`**: Implemented `analyze_features_with_context` to use the new context payload and calculate priority scores.
- **`src/legacy_web_mcp/mcp/orchestration_tools.py`**: Updated `_execute_step2_analysis` to use the new context-aware workflow and create a `CombinedAnalysisResult`.

### Story 3.6: Analysis Quality and Error Handling (Completed)

#### **Implementation Summary**:
- **`src/legacy_web_mcp/llm/quality.py`**: Comprehensive quality validation system with ResponseValidator and QualityAnalyzer classes, structured error handling with architecture error codes.
- **`src/legacy_web_mcp/llm/engine.py`**: Enhanced with `chat_completion_with_validation()` method providing intelligent retry logic, prompt optimization, and quality-assured responses.
- **`src/legacy_web_mcp/llm/artifacts.py`**: Complete artifact lifecycle management for partial result persistence, resumption capability, and comprehensive debugging support.
- **`src/legacy_web_mcp/llm/debugging.py`**: Production-ready debugging tools with session tracking, quality assessment logging, and improvement recommendations.
- **`src/legacy_web_mcp/mcp/debugging_tools.py`**: 8 new MCP tools exposing debugging capabilities including artifact management, quality validation, and session monitoring.
- **Updated Analysis Components**: Both ContentSummarizer and FeatureAnalyzer now use quality-validated chat completion with comprehensive error handling and artifact persistence.

### Story 4.4: MCP Artifact Organization and File Management (Completed)

#### **Implementation Summary**:
- **`src/legacy_web_mcp/file_management/organizer.py`**: Complete project documentation organization system with ProjectArtifactOrganizer class, URL slug generation, and markdown file generation with cross-references.
- **`src/legacy_web_mcp/mcp/file_management_tools.py`**: 6 new MCP tools for project setup, artifact organization, master report generation, documentation listing, URL slug generation, and version control guidance.
- **`src/legacy_web_mcp/mcp/resources.py`**: MCP resource provider system exposing project documentation via `web_discovery://` URI scheme for AI tool access.
- **`src/legacy_web_mcp/mcp/server.py`**: Updated to register file management tools and resource providers.
- **Project Documentation Structure**: Standardized `<project>/docs/web_discovery/` structure with analysis metadata, master reports, per-page analysis files, and MCP resource exposure.
- **Testing and Validation**: Comprehensive demo script and testing infrastructure for end-to-end file management workflow validation.

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
├── ✅ Quality Validation and Error Recovery
├── ✅ Confidence Scoring and Debugging
└── ✅ Production-Ready LLM Analysis
```

### After Story 4.4 (File Management)
```
Enhanced Documentation System:
├── ✅ Project Documentation Structure (<project>/docs/web_discovery/)
├── ✅ Artifact Organization with URL Slug Generation
├── ✅ Master Analysis Report Integration
├── ✅ MCP Resource Provider for AI Tool Access
└── ✅ Version Control Guidance and Integration
```

### After Epic 4 (Progress Tracking - In Progress)
```
Production Monitoring:
├── Real-time Progress Tracking
├── Checkpoint/Resume Functionality
├── Enhanced Documentation Generation (✅ Partially Complete)
└── Advanced Artifact Organization (✅ Complete)
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

1. **Epic 4** (Progress Tracking): Real-time monitoring and checkpointing
2. **Epic 5** (User Experience): Interactive and automated analysis modes
3. **Future Enhancements**: Performance optimization and advanced AI capabilities

---

**Key for Developers**: This document should be updated as new stories are implemented. Each major architectural change should be reflected here to maintain accurate development context.major architectural change should be reflected here to maintain accurate development context.ntext.

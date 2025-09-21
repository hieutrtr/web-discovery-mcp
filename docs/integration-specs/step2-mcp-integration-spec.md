# Technical Specification: Step 2 Feature Analysis MCP Integration

**Specification ID**: SPEC-3.4-MCP-INTEGRATION  
**Version**: 1.0  
**Date**: 2025-09-21  
**Author**: Technical Architect  
**Status**: Draft  

## Executive Summary

This specification defines the integration of the existing Step 2 Feature Analyzer into the Model Context Protocol (MCP) server tool ecosystem. The FeatureAnalyzer (implemented in commit be88039c9af83ae246d676c84264f596b5c01f70) currently operates in isolation and needs to be exposed through MCP tools to make it accessible to AI development environments.

## Background and Context

### Current State
- **Story 3.4 Implementation**: Complete with comprehensive FeatureAnalyzer class
- **Test Coverage**: 54 test scenarios with 100% success rate
- **Integration Gap**: Not exposed through any MCP tool interface
- **Architecture**: Well-designed with proper error handling and confidence scoring

### Problem Statement
The Step 2 Feature Analysis functionality exists but is inaccessible to end users because it's not integrated into the MCP server's tool registry. This creates a broken user experience where the sophisticated analysis capabilities cannot be leveraged through the intended MCP interface.

## Objectives

1. **Primary Objective**: Expose Step 2 Feature Analysis through MCP tools for external access
2. **Secondary Objectives**:
   - Maintain seamless integration with existing workflow patterns
   - Ensure proper context passing from Step 1 to Step 2 analysis
   - Provide both individual and orchestrated analysis options
   - Implement robust error handling and progress tracking
   - Support resume/capability for long-running analysis workflows

## Requirements

### Functional Requirements

1. **Tool Registration**: Register Step 2 analysis tools in the MCP server
2. **Context Integration**: Leverage Step 1 results as context for Step 2 analysis
3. **Project Storage**: Save analysis results in project-structured format
4. **Progress Tracking**: Provide real-time updates during analysis execution
5. **Error Handling**: Graceful degradation with partial results capability
6. **Configuration Support**: Utilize model configuration from existing system

### Non-Functional Requirements

1. **Performance**: Analysis completion within 90-120 seconds per page
2. **Reliability**: 99%+ success rate with proper error recovery
3. **Scalability**: Support concurrent analysis with resource management
4. **Maintainability**: Follow existing codebase patterns and conventions
5. **Testability**: Comprehensive unit and integration test coverage

## Technical Design

### Architecture Overview

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   MCP Server    │───▶│  Analysis Tools  │───▶│ FeatureAnalyzer │
│                 │    │                  │    │                 │
│ • Register Tool │    │ • Context Setup  │    │ • LLM Engine    │
│ • Handle Request │    │ • Progress Track │    │ • JSON Parse    │
│ • Return Results │    │ • Error Handle   │    │ • Data Models   │
└─────────────────┘    └──────────────────┘    └─────────────────┘
```

### Tool Interface Design

#### Primary Tool: Comprehensive Feature Analysis
```python
@mcp.tool()
async def analyze_features_comprehensive(
    context: Context,
    url: str,
    project_id: str = "feature-analysis",
    browser_engine: str = "chromium",
    include_step1_context: bool = True,
    include_rebuild_specs: bool = True,
    save_intermediate_data: bool = True,
) -> dict[str, Any]:
    """Perform complete two-step analysis (Step 1 + Step 2) with feature extraction.
    
    Executes the full analysis pipeline:
    1. Step 1: Content summarization for business context
    2. Comprehensive page data collection (DOM, network, interactions)
    3. Step 2: Detailed feature analysis with technical specifications
    4. Confidence scoring and quality assessment
    5. Structured JSON output for development teams
    
    Args:
        url: Target URL for analysis
        project_id: Project identifier for result organization
        browser_engine: Browser engine selection
        include_step1_context: Enable Step 1 analysis for context
        include_rebuild_specs: Generate rebuild specifications
        save_intermediate_data: Save Step 1 and page analysis data
    
    Returns:
        Complete analysis results with feature specifications
    """
```

#### Secondary Tool: Sequential Workflow Integration
```python
@mcp.tool()
async def create_analysis_pipeline(
    context: Context,
    urls: list[str],
    project_id: str = "analysis-pipeline",
    enable_step2_analysis: bool = True,
    step2_trigger_condition: str = "auto",  # auto, manual, threshold
    analysis_threshold: float = 0.7,      # Confidence threshold for Step 2
) -> dict[str, Any]:
    """Create a multi-step analysis pipeline for multiple pages.
    
    Orchestrates complete analysis workflows:
    - Step 1 analysis for business context
    - Step 2 analysis for technical specifications
    - Progress tracking across all steps
    - Checkpoint creation for resume capability
    - Result correlation and data flow management
    """
```

### Data Flow Architecture

#### Individual Page Analysis Flow
```
URL Input → Browser Navigation → Page Data Collection → Step 1 Analysis → Step 2 Context → Feature Analysis → JSON Output
```

#### Multi-Page Workflow Flow
```
URL List → Workflow Initialization → Sequential Processing → Step 1 (Each Page) → Step 2 (Contextual) → Correlation Analysis → Consolidated Results
```

### Integration Points

#### 1. Browser Service Integration
```python
# Pattern from existing analysis_tools.py
browser_service = BrowserAutomationService(config)
async with browser_service.get_session(...) as session:
    page = session.page
    
    # Collect comprehensive page data
    page_analysis_data = await analyzer.analyze_page(page, url, project_root)
    
    # Execute Step 1 if required
    if include_step1_context:
        content_summary = await summarizer.summarize_page(page_analysis_data)
    
    # Execute Step 2 with context
    feature_analysis = await analyzer.analyze_features(
        page_analysis_data=page_analysis_data,
        step1_context=content_summary
    )
```

#### 2. LLM Engine Integration
```python
# Configuration-driven model selection
llm_engine = LLMEngine(config)
provider, model = engine.get_model_for_request_type(LLMRequestType.FEATURE_ANALYSIS)

# Request structure following existing patterns
request = LLMRequest(
    messages=messages,
    request_type=LLMRequestType.FEATURE_ANALYSIS,
    metadata={"step": "step2", "model_config_key": "step2_model"},
)

response = await llm_engine.chat_completion(request=request, page_url=url)
```

#### 3. Project Storage Integration
```python
# File organization following project conventions
project_root = project_store.get_project_metadata(project_id).root_path
features_dir = project_root / "analysis" / "step2"
features_file = features_dir / f"{page_key}-features.json"

# Save structured results
with open(features_file, "w", encoding="utf-8") as f:
    json.dump(feature_analysis.model_dump(), f, indent=2, ensure_ascii=False)
```

## Implementation Details

### File Structure

```
src/legacy_web_mcp/mcp/
├── analysis_tools.py          # Existing → Add new function
├── feature_analysis_tools.py  # New file (optional - keep tools organized)
└── workflow_tools.py          # Existing → Add pipeline function

src/legacy_web_mcp/llm/analysis/
├── step1_summarize.py         # Existing
├── step2_feature_analysis.py  # Existing → No changes needed
└── __init__.py               # Update imports
```

### Registration Pattern

```python
# In mcp/server.py
def create_mcp() -> FastMCP:
    configure_logging()
    mcp = FastMCP(name=_SERVER_NAME)
    
    # Existing registrations
    analysis_tools.register(mcp)  # Will include new feature tools
    workflow_tools.register(mcp)  # Will include pipeline tools
    
    return mcp
```

### Configuration Integration

```yaml
# Using existing configuration structure
llm:
  step1_model: "claude-3-haiku-20240307"
  step2_model: "claude-3-sonnet-20240229"
  fallback_model: "gpt-4o-mini"

# Analysis-specific settings
analysis:
  step2_threshold: 0.7
  include_rebuild_specs: true
  save_intermediate_data: true
```

## Implementation Plan

### Phase 1: Core Tool Implementation (2-3 days)
1. **Create analyze_features_comprehensive() function in analysis_tools.py**
   - Integrate with existing browser service patterns
   - Implement two-step analysis orchestration
   - Add proper error handling and progress tracking

2. **Add configuration support**
   - Ensure step2_model configuration is properly loaded
   - Add analysis-specific configuration options

### Phase 2: Workflow Integration (2-3 days)
1. **Create pipeline tool in workflow_tools.py**
   - Integrate with SequentialNavigationWorkflow
   - Implement context passing between steps
   - Add checkpoint and resume capability

2. **Update workflow to leverage Step 2 analysis**
   - Modify page processing to include feature analysis
   - Implement conditional Step 2 triggering

### Phase 3: Testing and Refinement (1-2 days)
1. **Extend existing test suite**
   - Add MCP tool integration tests
   - Test error handling and edge cases
   - Validate configuration integration

2. **Performance optimization**
   - Optimize concurrent session management
   - Implement proper resource cleanup
   - Add progress monitoring improvements

## Quality Assurance

### Test Coverage Requirements
- **Unit Tests**: 90%+ coverage for new tool functions
- **Integration Tests**: End-to-end MCP tool testing
- **Error Scenarios**: Network failures, timeout handling, partial results
- **Configuration Validation**: Model selection, threshold settings

### Performance Criteria
- **Analysis Speed**: <150 seconds per page (including both steps)
- **Memory Usage**: <500MB per concurrent session
- **Success Rate**: >99% for valid URLs with retry logic
- **Context Overhead**: <50ms for Step 1 → Step 2 handoff

### Integration Verification
- **MCP Protocol Compliance**: JSON-RPC 2.0 compatibility
- **Progress Reporting**: Real-time updates every 5-10 seconds
- **Error Propagation**: Clear error messages with recovery suggestions
- **Resource Cleanup**: Proper session and file handle management

## Risk Assessment and Mitigation

### Technical Risks
1. **Model Configuration Complexity**: Risk of misconfigured LLM models
   - **Mitigation**: Robust fallback mechanisms and clear configuration documentation

2. **Memory Leaks in Long Workflows**: Extended analysis sessions
   - **Mitigation**: Implement session timeout and resource cleanup protocols

3. **Concurrent Session Management**: Multiple analysis workflows
   - **Mitigation**: Use existing session pooling patterns with proper limits

### Integration Risks
1. **Breaking Existing Workflows**: New tools might affect current functionality
   - **Mitigation**: Maintain backward compatibility, implement feature flags

2. **Configuration Conflicts**: Step 1/Step 2 model configuration interference
   - **Mitigation**: Isolate configuration namespaces, implement validation

## Success Criteria

### Functional Success
1. **Tool Registration**: New tools appear in MCP server tool list
2. **Complete Analysis**: Two-step analysis executes end-to-end successfully
3. **Data Persistence**: Results saved in project structure per requirements
4. **Error Handling**: Graceful degradation with clear error messages

### Performance Success
1. **Analysis Speed**: Consistently under 120 seconds per page
2. **Resource Utilization**: Effective concurrent session management
3. **Reliability**: 99%+ success rate with fallback mechanisms
4. **Scalability**: Support for 100+ page workflows with checkpoints

### Integration Success
1. **Context Integration**: Proper Step 1 → Step 2 context passing
2. **Configuration Integration**: Seamless model and setting management
3. **Progress Tracking**: Real-time updates throughout analysis pipeline
4. **Documentation**: Updated API documentation with examples

## Conclusion

This specification provides a comprehensive roadmap for integrating the existing Step 2 FeatureAnalyzer into the MCP server ecosystem. The implementation follows established patterns in the codebase while adding powerful new capabilities for comprehensive web page analysis. The phased approach ensures minimal disruption to existing functionality while providing significant value to users through the new analysis tools.

The success of this integration will enable the full two-step analysis pipeline to be accessible through the MCP interface, fulfilling the original requirements of Story 3.4 while maintaining the high quality standards established in the existing codebase.
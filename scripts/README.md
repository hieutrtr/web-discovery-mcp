# Scripts for Manual Testing

This folder contains scripts to help you manually test the Legacy Web MCP Server functionality.

## Prerequisites

Make sure you have the project dependencies installed:

```bash
uv sync
```

## Scripts

### 1. `manual_test.py` - Comprehensive Testing Suite

A comprehensive testing script that tests all major functionality of the MCP server.

**Usage:**
```bash
# Run all tests interactively
python scripts/manual_test.py all

# Test specific components
python scripts/manual_test.py health
python scripts/manual_test.py config
python scripts/manual_test.py projects
python scripts/manual_test.py discover [url]
```

**Examples:**
```bash
# Test health checks and diagnostics
python scripts/manual_test.py health

# Test configuration management
python scripts/manual_test.py config

# Test website discovery with a specific URL
python scripts/manual_test.py discover https://github.com

# Test project management
python scripts/manual_test.py projects
```

### 2. `test_mcp_client.py` - Direct MCP Tool Testing

Creates an MCP server context and enables direct testing of most tools without requiring an external MCP client.

**Usage:**
```bash
# Show available tools and usage guidance
python scripts/test_mcp_client.py

# Test specific tools directly
python scripts/test_mcp_client.py ping
python scripts/test_mcp_client.py health_check
python scripts/test_mcp_client.py show_config
python scripts/test_mcp_client.py validate_dependencies

# Note: discover_website requires full MCP session - use test_discovery_direct.py instead
```

### 3. `test_discovery_direct.py` - Direct Discovery Testing

Tests website discovery functionality directly without MCP context requirements.

**Usage:**
```bash
# Test discovery on any website
python scripts/test_discovery_direct.py [URL]
```

**Examples:**
```bash
# Test on example sites
python scripts/test_discovery_direct.py https://example.com
python scripts/test_discovery_direct.py https://github.com
python scripts/test_discovery_direct.py https://context7.com
python scripts/test_discovery_direct.py https://your-website.com
```

### 4. `test_browser_session.py` - Browser Session Management Testing

Tests the Playwright browser session management features from Story 2.1, including multi-engine support, concurrency control, crash recovery, and performance metrics.

**Usage:**
```bash
# Run all browser session tests
python scripts/test_browser_session.py all

# Test specific components
python scripts/test_browser_session.py engines      # Multi-engine support
python scripts/test_browser_session.py concurrency # Concurrent session limits
python scripts/test_browser_session.py lifecycle   # Session lifecycle management
python scripts/test_browser_session.py recovery    # Crash detection and recovery
python scripts/test_browser_session.py metrics     # Performance metrics collection
python scripts/test_browser_session.py install     # Browser installation validation
```

**Examples:**
```bash
# Validate browser installation
python scripts/test_browser_session.py install

# Test concurrency control
python scripts/test_browser_session.py concurrency

# Run complete test suite
python scripts/test_browser_session.py all
```

### 5. `test_page_navigation.py` - Page Navigation and Content Extraction Testing

Tests the page navigation and content extraction functionality from Story 2.2, including successful navigation, content extraction, screenshot capture, and error handling.

**Usage:**
```bash
# Run all navigation and extraction tests
python scripts/test_page_navigation.py all

# Test specific components
python scripts/test_page_navigation.py navigation  # Test successful navigation and content extraction
python scripts/test_page_navigation.py screenshot # Test screenshot capture functionality
python scripts/test_page_navigation.py errors     # Test handling of HTTP 404 and 403 errors
python scripts/test_page_navigation.py timeout    # Test navigation timeout handling
```

**Examples:**
```bash
# Test basic navigation functionality
python scripts/test_page_navigation.py navigation

# Test error handling
python scripts/test_page_navigation.py errors
```

### 6. `test_network_monitoring.py` - Network Traffic Monitoring Testing

Tests the network traffic monitoring functionality from Story 2.3, including traffic analysis, API endpoint detection, and third-party service identification.

**Usage:**
```bash
# Run all network monitoring tests
python scripts/test_network_monitoring.py all

# Test specific components
python scripts/test_network_monitoring.py summary     # Test network traffic summary generation
python scripts/test_network_monitoring.py api        # Test API endpoint analysis
python scripts/test_network_monitoring.py third-party # Test third-party service detection
python scripts/test_network_monitoring.py filtering  # Test static asset filtering
```

**Examples:**
```bash
# Test network traffic analysis
python scripts/test_network_monitoring.py summary

# Test API endpoint detection
python scripts/test_network_monitoring.py api
```

### 7. `test_page_interaction.py` - Page Interaction Automation Testing

Tests the page interaction automation functionality from Story 2.4, including form interactions, scrolling, hover/focus events, and modal handling.

**Usage:**
```bash
# Run all page interaction tests
python scripts/test_page_interaction.py all

# Test specific components
python scripts/test_page_interaction.py form      # Test form interaction and submission
python scripts/test_page_interaction.py scrolling # Test page scrolling to reveal content
python scripts/test_page_interaction.py hover     # Test hover and focus interactions
```

**Examples:**
```bash
# Test form interactions
python scripts/test_page_interaction.py form

# Test scrolling functionality
python scripts/test_page_interaction.py scrolling
```

### 8. `diagnostics_client.py` - MCP Diagnostics Client

A utility client for manually exercising MCP diagnostics tools and listing available capabilities.

**Usage:**
```bash
# List all available tools with descriptions
python scripts/diagnostics_client.py list

# Run diagnostic tools
python scripts/diagnostics_client.py health  # Run health check
python scripts/diagnostics_client.py deps    # Validate dependencies
python scripts/diagnostics_client.py llm     # Test LLM connectivity
python scripts/diagnostics_client.py status  # Get system status

# Specify custom server command
python scripts/diagnostics_client.py list --command uv run legacy-web-mcp

# Use custom scope for status
python scripts/diagnostics_client.py status --scope config
```

**Examples:**
```bash
# See all available tools and their descriptions
python scripts/diagnostics_client.py list

# Check server health
python scripts/diagnostics_client.py health

# Validate all dependencies
python scripts/diagnostics_client.py deps
```

### 9. `test_page_analysis.py` - Page Analysis Data Collection Testing

Tests the comprehensive page analysis functionality from Story 2.5, including DOM structure analysis, technology detection, accessibility evaluation, performance metrics, and page categorization for LLM processing.

**Usage:**
```bash
# Run all page analysis tests
python scripts/test_page_analysis.py all

# Test specific components
python scripts/test_page_analysis.py comprehensive     # Test comprehensive analysis with all features
python scripts/test_page_analysis.py dom_structure    # Test DOM structure analysis specifically
python scripts/test_page_analysis.py technology       # Test technology detection capabilities
python scripts/test_page_analysis.py mcp_tools        # Test MCP tools for page analysis
python scripts/test_page_analysis.py simple           # Test basic analysis without extra features
```

**Examples:**
```bash
# Test comprehensive page analysis
python scripts/test_page_analysis.py comprehensive

# Test technology detection
python scripts/test_page_analysis.py technology

# Test MCP tools via client
python scripts/test_page_analysis.py mcp_tools
```

### 10. `test_sequential_workflow.py` - Sequential Navigation Workflow Testing

Tests the sequential navigation workflow functionality from Story 2.6, including queue management, progress tracking, error recovery, checkpoint creation, and resource management for processing multiple pages systematically.

**Usage:**
```bash
# Run all workflow tests
python scripts/test_sequential_workflow.py all

# Test specific components
python scripts/test_sequential_workflow.py basic_workflow     # Test basic multi-page workflow execution
python scripts/test_sequential_workflow.py queue_control     # Test pause, resume, stop, skip functionality
python scripts/test_sequential_workflow.py error_recovery    # Test error handling and retry mechanisms
python scripts/test_sequential_workflow.py checkpointing     # Test checkpoint creation and resumption
python scripts/test_sequential_workflow.py mcp_tools         # Test MCP tools for workflow management
python scripts/test_sequential_workflow.py performance       # Test workflow performance and resource management
```

**Examples:**
```bash
# Test basic workflow execution
python scripts/test_sequential_workflow.py basic_workflow

# Test queue control operations
python scripts/test_sequential_workflow.py queue_control

# Test checkpoint functionality
python scripts/test_sequential_workflow.py checkpointing
```

### 11. `test_step1_summarize.py` - Step 1 Content Summarization Testing

Tests the Step 1 Content Summarization Analysis functionality from Story 3.3, including LLM-powered content analysis, purpose identification, user context extraction, business logic understanding, and confidence scoring for individual pages.

**Usage:**
```bash
# Run all Step 1 content summarization tests
python scripts/test_step1_summarize.py all

# Test specific components
python scripts/test_step1_summarize.py basic           # Test basic content summarization workflow
python scripts/test_step1_summarize.py confidence     # Test confidence scoring algorithm
python scripts/test_step1_summarize.py mcp_tools      # Test MCP tools for content summarization
python scripts/test_step1_summarize.py model_fallback # Test LLM model fallback mechanisms
python scripts/test_step1_summarize.py batch          # Test batch processing of multiple pages
```

**Examples:**
```bash
# Test basic content summarization
python scripts/test_step1_summarize.py basic

# Test MCP tool integration
python scripts/test_step1_summarize.py mcp_tools

# Test with specific URL
python scripts/test_step1_summarize.py basic --url https://example.com
```

### 12. `check_env.py` - Environment Variable Validation

CLI utility to ensure required environment variables are present for proper MCP server operation.

**Usage:**
```bash
# Check all required environment variables
python scripts/check_env.py

# Check specific environment variables
python scripts/check_env.py --keys OPENAI_API_KEY ANTHROPIC_API_KEY

# Quiet mode (exit codes only)
python scripts/check_env.py --quiet
```

**Examples:**
```bash
# Validate environment setup
python scripts/check_env.py

# Check only API keys
python scripts/check_env.py --keys OPENAI_API_KEY ANTHROPIC_API_KEY GEMINI_API_KEY
```

### 13. `test_feature_analyzer_story_3_7.py` - Story 3.7 FeatureAnalyzer MCP Integration Testing

Tests the integration of FeatureAnalyzer into the MCP server as the analyze_page_features tool, covering all acceptance criteria from Story 3.7: Step 2 Feature Analysis MCP Integration.

**Usage:**
```bash
# Run all tests (full mode, 15 tests)
python scripts/test_feature_analyzer_story_3_7.py

# Run quick tests only (8 core tests)
python scripts/test_feature_analyzer_story_3_7.py --mode=quick

# Run with verbose output
python scripts/test_feature_analyzer_story_3_7.py --verbose

# Combine options
python scripts/test_feature_analyzer_story_3_7.py --mode=quick --verbose
```

**Test Coverage:**
- ✅ FeatureAnalyzer class instantiation and data models
- ✅ MCP server creation and tool registration
- ✅ analyze_page_features tool validation
- ✅ Input validation schema and error handling
- ✅ Integration with existing analysis tools
- ✅ Documentation compatibility and output schema
- ✅ Performance requirements and MCP protocol compliance

**Examples:**
```bash
# Quick validation of core functionality
python scripts/test_feature_analyzer_story_3_7.py --mode=quick

# Comprehensive testing with detailed output
python scripts/test_feature_analyzer_story_3_7.py --mode=full --verbose

# Generate JSON test report
python scripts/test_feature_analyzer_story_3_7.py
# Report saved to: scripts/feature_analyzer_test_report.json
```

### 13b. `test_feature_analyzer_with_real_llm.py` - Story 3.7 Real LLM Integration Testing

Tests the analyze_page_features tool with **actual LLM API calls** to demonstrate complete Step 1 + Step 2 analysis workflow with real AI-generated results.

**Prerequisites:**
```bash
# Set up at least one LLM API key
export OPENAI_API_KEY="your-openai-key"
# OR
export ANTHROPIC_API_KEY="your-anthropic-key"
# OR
export GEMINI_API_KEY="your-gemini-key"
```

**Usage:**
```bash
# Run real LLM integration tests (costs ~$0.05-0.20)
python scripts/test_feature_analyzer_with_real_llm.py
```

**What This Test Does:**
- 🧠 Makes **real API calls** to LLM providers (OpenAI/Anthropic/Gemini)
- 📊 Tests **complete Step 1 + Step 2 workflow** with actual AI analysis
- 🔍 Analyzes realistic login page content with 6 interactive elements
- 📋 Shows **actual LLM-generated results** for:
  - Interactive elements identification and purpose analysis
  - Functional capabilities detection
  - Business rules extraction
  - API integration recommendations
  - Rebuild specifications with priority scoring
- ⚡ Tests both full analysis and Step 2-only modes
- 💰 Displays cost and performance metrics

**Example Output:**
```bash
✅ REAL LLM ANALYSIS SUCCESSFUL!
🧠 Step 1 (Content Summarization) Results:
   Purpose: User authentication and account access portal
   User Context: Registered users requiring secure account access
   Business Logic: Credential validation and session management
   Confidence: 0.87

🔍 Step 2 (Feature Analysis) Results:
   Interactive Elements: 4
   Functional Capabilities: 3
   Business Rules: 2
   Overall Confidence: 0.82
   Quality Score: 0.79

📱 Interactive Elements Found by LLM:
   1. input - Email address collection for authentication
   2. input - Password input for user verification
   3. button - Submit authentication credentials
```

### 14. `test_orchestration_story_6_4.py` - Story 6.4 High-Level Workflow Orchestration Testing

Tests the high-level workflow orchestration tools from Story 6.4, including intelligent workflow planning, cost optimization, and seamless integration of all existing MCP tools into conversational AI-friendly workflows.

**Usage:**
```bash
# Run all tests (full mode, 36 tests)
python scripts/test_orchestration_story_6_4.py

# Run quick tests only (23 core tests)
python scripts/test_orchestration_story_6_4.py --mode=quick

# Run with verbose output
python scripts/test_orchestration_story_6_4.py --verbose

# Combine options
python scripts/test_orchestration_story_6_4.py --mode=quick --verbose
```

**Test Coverage:**
- ✅ Orchestrator initialization and workflow planning
- ✅ Page selection algorithms and cost estimation
- ✅ Analysis strategy creation and optimization
- ✅ MCP tool registration (analyze_legacy_site, analyze_with_recommendations, get_analysis_status)
- ✅ Error handling and custom exception hierarchy
- ✅ Server integration and parameter validation
- ✅ Performance metrics and file system integration

**Examples:**
```bash
# Quick validation of orchestration core
python scripts/test_orchestration_story_6_4.py --mode=quick

# Full test suite with detailed logging
python scripts/test_orchestration_story_6_4.py --mode=full --verbose

# Generate JSON test report
python scripts/test_orchestration_story_6_4.py
# Report saved to: scripts/orchestration_test_report.json
```

### 15. `orchestration_usage_example.py` - Story 6.4 Orchestration Demo

Interactive demonstration script showing the transformation from manual tool coordination (15+ individual tool calls) to intelligent orchestrated workflows (single command execution).

**Usage:**
```bash
# Run interactive demo
python scripts/orchestration_usage_example.py
```

**Demo Features:**
- 📝 Before/After workflow comparison
- 🚀 Single-command site analysis demonstration
- 🤖 AI-driven analysis recommendations
- 🎯 Interactive mode with human oversight
- 📈 Status tracking and progress monitoring

**Example Output:**
```bash
# Shows transformation from:
# 1. mcp_call discover_website(url='https://old-app.example.com')
# 2. mcp_call analyze_site_structure(discovered_urls)
# ... 15+ manual steps

# To orchestrated workflow:
# mcp_call analyze_legacy_site(
#     url='https://old-app.example.com',
#     analysis_mode='recommended',
#     include_step2=True,
#     interactive_mode=False
# )
```

## Available MCP Tools

The server provides these tools that you can test:

### Core Diagnostic Tools
| Tool | Description | Arguments |
|------|-------------|-----------|
| `health_check` | Check server health and status | None |
| `validate_dependencies` | Validate Playwright and other dependencies | None |
| `test_llm_connectivity` | Test LLM provider connectivity | None |
| `show_config` | Show current configuration (redacted) | None |
| `ping` | Report MCP server status and runtime metadata | None |

### Discovery and Configuration Tools
| Tool | Description | Arguments |
|------|-------------|-----------|
| `discover_website` | Discover website structure | `url` (string) |
| `get_project_configuration` | Get configuration for a project | `project_id` (string) |
| `update_project_configuration` | Update project configuration | `project_id`, `settings` |
| `create_project` | Create a new project | `name`, `description` |
| `list_projects` | List all projects | None |

### Browser Session Management Tools (Story 2.1)
| Tool | Description | Arguments |
|------|-------------|-----------|
| `create_browser_session` | Create new browser session | `engine` (optional), `session_config` (optional) |
| `get_session_info` | Get information about a browser session | `session_id` |
| `list_browser_sessions` | List all active browser sessions | None |
| `close_browser_session` | Close a specific browser session | `session_id` |
| `get_session_metrics` | Get performance metrics for sessions | None |

### Page Navigation and Content Tools (Story 2.2)
| Tool | Description | Arguments |
|------|-------------|-----------|
| `navigate_to_page` | Navigate to URL and extract page content | `url`, `timeout` (optional), `session_id` (optional) |
| `extract_page_content` | Extract content from current page | `session_id` (optional) |

### Network Monitoring Tools (Story 2.3)
| Tool | Description | Arguments |
|------|-------------|-----------|
| `monitor_network_traffic` | Monitor network traffic during page navigation | `url`, `capture_payloads` (optional), `session_id` (optional) |
| `analyze_api_endpoints` | Analyze API endpoints discovered during navigation | `url`, `include_payloads` (optional), `session_id` (optional) |
| `monitor_third_party_services` | Monitor third-party services used by webpage | `url`, `session_id` (optional) |

### Page Interaction Tools (Story 2.4)
| Tool | Description | Arguments |
|------|-------------|-----------|
| `interact_with_page` | Perform automated interactions with webpage | `url`, `enable_form_interactions` (optional), `session_id` (optional) |
| `explore_navigation_menu` | Explore navigation menus to discover pages | `url`, `max_depth` (optional), `session_id` (optional) |
| `test_form_interactions` | Test form interactions safely | `url`, `safe_mode` (optional), `session_id` (optional) |

### Page Analysis Tools (Story 2.5)
| Tool | Description | Arguments |
|------|-------------|-----------|
| `analyze_page_comprehensive` | Perform comprehensive page analysis with all data collection | `url`, `project_id` (optional), `include_network_monitoring` (optional), `include_interaction_simulation` (optional), `save_analysis_data` (optional), `browser_engine` (optional) |
| `analyze_dom_structure` | Analyze DOM structure and element categorization | `url`, `project_id` (optional), `browser_engine` (optional) |
| `detect_technologies` | Detect JavaScript frameworks, libraries, and technologies | `url`, `project_id` (optional), `browser_engine` (optional) |

### Sequential Workflow Tools (Story 2.6)
| Tool | Description | Arguments |
|------|-------------|-----------|
| `analyze_page_list` | Process multiple pages systematically with queue management | `urls` (array), `project_id` (optional), `max_retries_per_page` (optional), `include_network_monitoring` (optional), `enable_checkpointing` (optional), `max_concurrent_sessions` (optional) |
| `control_workflow` | Control active workflow (pause, resume, stop, skip) | `workflow_id`, `action` |
| `resume_workflow_from_checkpoint` | Resume workflow from checkpoint file | `checkpoint_path`, `project_id` (optional) |
| `list_active_workflows` | List all currently active workflows | None |

### Step 1 Content Summarization Tools (Story 3.3)
| Tool | Description | Arguments |
|------|-------------|-----------|
| `summarize_page_content` | Perform Step 1 Content Summarization analysis on a single page | `url`, `project_id` (optional), `browser_engine` (optional) |

### Step 2 Feature Analysis Tools (Story 3.7)
| Tool | Description | Arguments |
|------|-------------|-----------|
| `analyze_page_features` | Perform Step 2 Feature Analysis on a single page with detailed interactive elements, functional capabilities, and rebuild specifications | `url`, `content` (optional), `skip_step1` (optional), `project_id` (optional) |

### High-Level Workflow Orchestration Tools (Story 6.4)
| Tool | Description | Arguments |
|------|-------------|-----------|
| `analyze_legacy_site` | Orchestrate complete legacy website analysis workflow with intelligent planning and cost optimization | `url`, `analysis_mode` (optional), `max_pages` (optional), `include_step2` (optional), `interactive_mode` (optional), `project_id` (optional), `cost_priority` (optional) |
| `analyze_with_recommendations` | Analyze website with AI-driven strategy recommendations based on site characteristics | `url`, `project_id` (optional) |
| `get_analysis_status` | Get status and progress information for ongoing or completed analysis workflows | `project_id` |

## Environment Setup

### Required Environment Variables

For full functionality, set up these environment variables in `.env`:

```bash
# LLM API Keys (at least one required for LLM connectivity tests)
OPENAI_API_KEY=your_openai_key_here
ANTHROPIC_API_KEY=your_anthropic_key_here
GEMINI_API_KEY=your_gemini_key_here

# Optional: Output directory (defaults to current directory)
OUTPUT_ROOT=/path/to/output/directory

# Optional: Discovery settings
DISCOVERY_TIMEOUT=30
DISCOVERY_MAX_DEPTH=3
```

### Playwright Setup

For dependency validation tests, ensure Playwright browsers are installed:

```bash
uv run playwright install
```

## Expected Output

### Successful Health Check
```
✅ Health check passed: {'status': 'ok', 'server_name': 'Legacy Web MCP Server', ...}
```

### Successful Website Discovery
```
✅ Website discovery completed!
📊 Project ID: example-com_20250919-123456
🌐 Domain: example.com
📈 Total URLs: 15
📄 Internal pages: 8
🔗 External pages: 2
📎 Assets: 5
```

### Configuration Display
```
✅ Configuration retrieved:
{
  "OUTPUT_ROOT": "/current/directory",
  "DISCOVERY_TIMEOUT": 30,
  "DISCOVERY_MAX_DEPTH": 3,
  ...
}
```

## Troubleshooting

### Common Issues

1. **Import Errors**: Make sure you're running from the project root and have installed dependencies with `uv sync`

2. **Permission Errors**: Ensure the output directory is writable

3. **Network Timeouts**: Check your internet connection for website discovery tests

4. **Missing Dependencies**: Run `uv run playwright install` to install browser dependencies

5. **API Key Errors**: Set up environment variables for LLM connectivity tests

### Debug Mode

For more detailed error information, you can modify the scripts to enable debug logging or run with Python's verbose mode:

```bash
python -v scripts/manual_test.py all
```

## Integration with Real MCP Clients

These scripts test the server functionality directly. To test with real MCP clients (like Claude Desktop), you would:

1. Start the server: `uv run python -m legacy_web_mcp`
2. Configure your MCP client to connect to the server
3. Use the tools through the client interface

The scripts in this folder help validate that the server works correctly before integrating with external clients.
# Try-Playwright (Legacy Web Application Analysis MCP Server) Brownfield Architecture Document

## Introduction

This document captures the CURRENT STATE of the Try-Playwright project codebase, which is implementing a Legacy Web Application Analysis MCP Server. **CRITICAL REALITY CHECK**: This project is in early planning/setup phase with comprehensive documentation but **ZERO actual implementation**. This document serves as a reference for AI agents working on the initial development and implementation of the system.

### Document Scope

Focused on implementing the MCP server for legacy web application analysis as defined in the comprehensive PRD. The project aims to enable 4-8 hour legacy app analysis vs. current 4-6 weeks through Playwright automation and LLM integration.

### Change Log

| Date   | Version | Description                 | Author    |
| ------ | ------- | --------------------------- | --------- |
| 2025-01-17 | 1.0     | Initial brownfield analysis | Winston (AI Architect) |

## Quick Reference - Key Files and Entry Points

### Critical Files for Understanding the System

**REALITY CHECK**: Most implementation files DO NOT EXIST YET

- **Requirements Definition**: `docs/prd.md` ⭐ **EXISTS** - Comprehensive PRD with all functional requirements
- **Architecture Plan**: `docs/architecture.md` ⭐ **EXISTS** - Detailed architecture document
- **Project Brief**: `docs/brief.md` ⭐ **EXISTS** - Initial project context
- **Main Package Structure**: `src/legacy_web_mcp/` ⚠️ **DIRECTORIES EXIST BUT EMPTY**
  - `src/legacy_web_mcp/core/` - Core business logic (NOT IMPLEMENTED)
  - `src/legacy_web_mcp/mcp/` - MCP protocol handling (NOT IMPLEMENTED)
  - `src/legacy_web_mcp/providers/` - LLM provider integrations (NOT IMPLEMENTED)
  - `src/legacy_web_mcp/services/` - Browser automation services (NOT IMPLEMENTED)
  - `src/legacy_web_mcp/utils/` - Utility functions (NOT IMPLEMENTED)
- **Test Structure**: `tests/` ⚠️ **DIRECTORIES EXIST BUT EMPTY**
  - `tests/unit/` - Unit tests (NOT IMPLEMENTED)
  - `tests/integration/` - Integration tests (NOT IMPLEMENTED)
  - `tests/fixtures/` - Test fixtures (NOT IMPLEMENTED)

### Implementation Priority Based on PRD Epic Order

**Epic 1**: Foundation & MCP Server Infrastructure (NOT STARTED)
**Epic 2**: Browser Automation & Basic Navigation Engine (NOT STARTED)
**Epic 3**: LLM Integration & Two-Step Analysis Pipeline (NOT STARTED)
**Epic 4**: Progress Tracking & Documentation Generation (NOT STARTED)
**Epic 5**: Interactive & YOLO Modes (NOT STARTED)
**Epic 6**: AI-Powered Navigation Intelligence (NOT STARTED)

## High Level Architecture

### Technical Summary

**PLANNED** Python 3.11 MCP server with FastMCP framework integration, Playwright browser automation, and multi-provider LLM analysis. **CURRENT STATE**: Project scaffolding only, no actual implementation.

### Planned Tech Stack (From PRD Analysis)

| Category  | Technology | Version | Implementation Status | Notes |
| --------- | ---------- | ------- | -------------------- | ----- |
| Runtime   | Python     | 3.11+   | NOT IMPLEMENTED      | Required for AsyncIO enhancements |
| Framework | FastMCP    | Latest  | NOT IMPLEMENTED      | MCP server framework |
| Browser   | Playwright | Latest  | NOT IMPLEMENTED      | Cross-browser automation |
| LLM APIs  | OpenAI     | Latest  | NOT IMPLEMENTED      | Primary LLM provider |
| LLM APIs  | Anthropic  | Latest  | NOT IMPLEMENTED      | Secondary provider |
| LLM APIs  | Gemini     | Latest  | NOT IMPLEMENTED      | Tertiary provider |
| Async     | AsyncIO    | Built-in| NOT IMPLEMENTED      | Concurrent processing |

### Repository Structure Reality Check

- **Type**: Monorepo (planned)
- **Package Manager**: None configured yet
- **Dependency Management**: No requirements.txt, pyproject.toml, or setup.py exists
- **Build System**: Not configured
- **CI/CD**: Not configured

## Source Tree and Module Organization

### Project Structure (Actual)

```text
try-playwright/
├── .bmad-core/                    # BMAD tooling configuration
│   ├── core-config.yaml         # Project metadata
│   ├── templates/               # Document templates
│   ├── checklists/              # QA checklists
│   └── tasks/                   # Task definitions
├── .claude/                      # Claude Code configuration
├── .cursor/                      # Cursor IDE rules
├── .gemini/                      # Gemini CLI configuration
├── docs/                         # ⭐ COMPREHENSIVE DOCUMENTATION
│   ├── prd.md                   # ⭐ Complete PRD with 6 epics
│   ├── architecture.md         # ⭐ Architecture blueprint
│   └── brief.md                 # ⭐ Project context
├── src/                          # ⚠️ PLACEHOLDER STRUCTURE
│   └── legacy_web_mcp/          # Main package (EMPTY)
│       ├── core/                # Business logic (EMPTY)
│       ├── mcp/                 # Protocol handling (EMPTY)
│       ├── providers/           # LLM integrations (EMPTY)
│       ├── services/            # Browser automation (EMPTY)
│       └── utils/               # Utilities (EMPTY)
├── tests/                        # ⚠️ TEST STRUCTURE (EMPTY)
│   ├── unit/                    # Unit tests (EMPTY)
│   ├── integration/             # Integration tests (EMPTY)
│   └── fixtures/                # Test data (EMPTY)
├── scripts/                      # Build/deploy scripts (EMPTY)
├── templates/                    # Project templates (EMPTY)
└── .gitignore                   # Basic git ignores
```

### Key Modules That NEED Implementation

Based on PRD requirements, these modules must be built:

- **MCP Protocol Handler**: Handle JSON-RPC 2.0 communication with AI environments
- **Website Discovery**: Sitemap parsing, robots.txt analysis, crawling fallback
- **Browser Automation**: Playwright session management, page navigation, network monitoring
- **LLM Analysis Engine**: Two-step analysis (content summarization + feature analysis)
- **Progress Tracking**: Real-time status, checkpoints, resume capability
- **Documentation Generator**: Structured markdown output for rebuild specifications

## Technical Debt and Known Issues

### Critical Implementation Gaps

1. **NO CODE EXISTS**: Empty package structure with no Python files
2. **NO DEPENDENCY MANAGEMENT**: No requirements.txt, pyproject.toml, or setup.py
3. **NO BUILD SYSTEM**: No scripts for installation, testing, or deployment
4. **NO ENVIRONMENT SETUP**: No .env templates or configuration management
5. **NO TESTING FRAMEWORK**: Test directories exist but no pytest or testing setup
6. **NO CI/CD**: No GitHub Actions, automation, or quality gates

### Immediate Blockers for Development

- **Python Environment**: Need virtual environment setup and dependency management
- **MCP Framework**: FastMCP framework needs to be integrated and configured
- **Browser Setup**: Playwright needs installation and browser binary management
- **LLM API Setup**: Environment variables and API key management required
- **Project Structure**: Need __init__.py files and proper Python package structure

### Design Decisions from PRD That Must Be Respected

- **Stateless Design**: No database - all state in JSON/YAML files
- **File-based Storage**: Project folders with timestamp-based sessions
- **Concurrent Processing**: 3-5 parallel browser sessions maximum
- **Two-Step Analysis**: Content summarization first, then detailed feature analysis
- **Resume Capability**: Checkpoint system for interrupted analyses

## Integration Points and External Dependencies

### Planned External Services

| Service  | Purpose  | Integration Type | Configuration Needed |
| -------- | -------- | ---------------- | -------------------- |
| OpenAI   | Primary LLM | REST API | OPENAI_API_KEY env var |
| Anthropic| Secondary LLM | REST API | ANTHROPIC_API_KEY env var |
| Gemini   | Tertiary LLM | REST API | GEMINI_API_KEY env var |
| Target Websites | Analysis targets | Playwright automation | Rate limiting, respect robots.txt |

### MCP Protocol Integration

- **AI Development Environments**: Claude Code, Cursor, Gemini CLI
- **Protocol**: JSON-RPC 2.0 via MCP specification
- **Tools**: URL discovery, analysis initiation, progress monitoring
- **Resources**: Real-time status, analysis results, project files

## Development and Deployment

### Required Local Development Setup

**CRITICAL**: None of this exists yet and must be implemented

1. **Python Environment**:
   ```bash
   python3.11 -m venv venv
   source venv/bin/activate  # or venv\Scripts\activate on Windows
   ```

2. **Dependency Installation** (NEED TO CREATE):
   ```bash
   pip install fastmcp playwright asyncio
   playwright install  # Browser binaries
   ```

3. **Environment Configuration** (NEED TO CREATE):
   ```bash
   cp .env.example .env  # Template doesn't exist yet
   # Set OPENAI_API_KEY, ANTHROPIC_API_KEY, GEMINI_API_KEY
   ```

4. **MCP Server Registration** (NEED TO IMPLEMENT):
   - MCP server configuration in AI development environment
   - JSON-RPC 2.0 endpoint configuration

### Build and Deployment Process

**REALITY**: No build system exists

**NEEDED**:
- `setup.py` or `pyproject.toml` for package distribution
- `requirements.txt` for dependency management
- Installation scripts for MCP server deployment
- Configuration templates for AI environment integration

## Testing Reality

### Current Test Coverage

**0% - NO TESTS EXIST**

### Required Testing Strategy (From PRD)

- **Unit Tests**: Individual component testing with pytest
- **Integration Tests**: End-to-end MCP protocol testing with mock AI environments
- **Browser Automation Tests**: Playwright testing against known websites
- **LLM Provider Tests**: Mock LLM responses for consistent testing
- **Performance Tests**: Analysis timing and resource usage validation

### Testing Commands (NEED TO IMPLEMENT)

```bash
pytest tests/unit/           # Unit tests
pytest tests/integration/    # Integration tests
pytest --cov=legacy_web_mcp  # Coverage reporting
```

## PRD Implementation Roadmap

### Epic 1: Foundation & MCP Server Infrastructure (IMMEDIATE PRIORITY)

**Stories that must be implemented first:**
1. **Story 1.1**: MCP Server Project Setup - Python 3.11 structure, FastMCP integration
2. **Story 1.2**: Health Check and Diagnostic Tools - Basic MCP tools
3. **Story 1.3**: Configuration Management - Environment variables, API keys
4. **Story 1.4**: URL Discovery and Sitemap Parsing - Core discovery functionality
5. **Story 1.5**: Project Organization and File Structure - Output management

### Epic 2: Browser Automation (SECOND PRIORITY)

**Core Playwright integration:**
- Browser session management with Chromium/Firefox/WebKit
- Page navigation and content extraction
- Network traffic monitoring for API discovery
- Basic page interaction automation

### Epic 3: LLM Integration (THIRD PRIORITY)

**Multi-provider LLM system:**
- OpenAI, Anthropic, Gemini API integrations
- Configuration-based model selection
- Two-step analysis pipeline implementation

### Critical Success Factors

1. **Start with Epic 1**: Get MCP server foundation working before browser automation
2. **Focus on PRD Requirements**: Don't add features not specified in PRD
3. **Test Each Epic**: Implement tests as you build each component
4. **Follow Stateless Design**: No database - all state in files as specified
5. **Respect Rate Limits**: Both for target websites and LLM providers

## Appendix - Useful Commands and Scripts

### Development Setup Commands (NEED TO CREATE)

```bash
# Project initialization (DOESN'T EXIST YET)
make setup              # Create venv, install dependencies
make install-browsers   # Install Playwright browsers
make test              # Run test suite
make lint              # Code quality checks

# MCP Server operations (NOT IMPLEMENTED)
python -m legacy_web_mcp.server    # Start MCP server
python -m legacy_web_mcp.health    # Health check
```

### Debugging and Troubleshooting

**REALITY**: No debugging tools exist yet

**NEEDED**:
- Logging configuration for MCP server operations
- Browser automation debugging (headed mode for development)
- LLM API connectivity testing utilities
- Performance monitoring for concurrent browser sessions

## Next Steps for Implementation

1. **IMMEDIATE**: Create `pyproject.toml` and basic Python package structure
2. **IMMEDIATE**: Implement basic MCP server with FastMCP framework
3. **IMMEDIATE**: Add health check and configuration management
4. **SHORT-TERM**: Implement URL discovery and sitemap parsing
5. **MEDIUM-TERM**: Add Playwright browser automation
6. **LONG-TERM**: Integrate LLM analysis pipeline

**This project is a greenfield implementation disguised as brownfield documentation. The comprehensive PRD provides the roadmap, but ALL CODE must be written from scratch.**
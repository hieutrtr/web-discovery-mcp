# Project Brief: Legacy Web Application Analysis MCP Server

## Executive Summary

**An AI-powered MCP (Model Context Protocol) server that automates comprehensive web application analysis using Playwright and LLM integration.**

The primary problem being solved is the time-intensive and error-prone process of exploring and documenting legacy web applications for rebuilding purposes. Development teams currently lack efficient tools to systematically analyze existing web functionalities, understand user workflows, and extract requirements for modernization projects.

**Target market:** Development teams, consultants, and agencies working with legacy system modernization, particularly those using AI-enhanced coding environments like Claude Code, Cursor, and Gemini CLI.

**Key value proposition:** Transform weeks of manual legacy system exploration into an automated, AI-guided process that provides comprehensive site analysis, interactive progress tracking, and structured documentation for informed rebuild decisions.

## Problem Statement

**Current State & Pain Points:**

Development teams face significant challenges when tasked with modernizing legacy web applications. The current process typically involves:

- **Manual exploration** of complex, undocumented web systems that can take weeks or months
- **Inconsistent documentation** as different team members discover different aspects of functionality
- **Missing critical workflows** due to incomplete discovery of user paths and edge cases
- **Inefficient knowledge transfer** from exploration to rebuild planning
- **High risk of scope creep** when hidden functionalities are discovered late in the rebuild process

**Impact of the Problem:**

- **Time cost:** Legacy analysis projects often exceed timeline estimates by 200-300% due to discovery inefficiencies
- **Quality risk:** Incomplete understanding leads to missing features in rebuilt applications
- **Resource drain:** Senior developers spend time on manual discovery instead of architecture and development
- **Client frustration:** Unpredictable timelines and budgets for modernization projects

**Why Existing Solutions Fall Short:**

- Generic web scraping tools lack the intelligent analysis capabilities needed for functional understanding
- Manual documentation is prone to human error and inconsistency
- Existing analysis tools don't integrate with modern AI-enhanced development workflows
- No standardized approach exists for collaborative analysis between humans and AI

**Urgency & Importance:**

With the rapid adoption of AI-assisted development tools (Claude Code, Cursor, Gemini CLI), development teams need analysis tools that integrate seamlessly with their AI-enhanced workflows. Legacy system modernization is accelerating as businesses seek to leverage AI capabilities, making efficient analysis tools critical for competitive advantage.

## Proposed Solution

**Core Concept & Approach:**

A specialized MCP (Model Context Protocol) server that combines Playwright's web automation capabilities with LLM-powered analysis to create an intelligent, interactive web application discovery system. The solution operates in two distinct phases:

**Phase 1 - Automated Discovery:**
- Accept a main URL input from the user
- Automatically extract and parse sitemaps
- Generate comprehensive URL inventory with AI-generated descriptions
- Present organized selection interface for targeted analysis

**Phase 2 - Deep Feature Analysis:**
- **Feature Detection & Documentation:** Systematically analyze UI components, user interactions, form behaviors, navigation patterns, and business logic on each selected page
- **API Interaction Analysis:** Capture and document network requests, API endpoints, data flows, and backend integrations for each feature
- **Rebuild-Ready Documentation:** Generate structured specifications that development teams can directly use for modernization planning
- **Dual Operation Modes:**
  - **Interactive Mode:** Maintains human-in-the-loop validation and input throughout analysis
  - **YOLO Mode:** Fully automated analysis without human intervention for rapid bulk processing
- **Real-time Progress Tracking:** Updates project-specific documentation folders with analysis results as work progresses

**Key Differentiators:**

- **MCP Integration:** Native compatibility with modern AI development environments (Claude Code, Cursor, Gemini CLI)
- **Flexible Automation:** Choose between collaborative (Interactive) or autonomous (YOLO) analysis modes based on project needs
- **Feature-Centric Analysis:** Goes beyond content scraping to understand functional behavior and API interactions
- **Developer-Ready Output:** Produces technical specifications optimized for rebuild implementation

**Why This Solution Will Succeed:**

Unlike generic web scraping tools, this solution understands both the functional and technical architecture of web applications. The dual-mode approach allows teams to balance speed (YOLO) with accuracy (Interactive) based on project complexity and risk tolerance. MCP integration ensures seamless workflow integration with existing AI-enhanced development processes.

**High-level Product Vision:**

A developer-first tool that transforms legacy web analysis from manual reverse-engineering into an AI-accelerated feature discovery and documentation system, enabling development teams to rebuild applications with complete functional and technical understanding.

## Target Users

### Primary User Segment: AI-Enhanced Developers

**Demographic/Profile:**
- Software developers and development team leads using AI-powered coding environments
- Experience level: Mid to senior developers comfortable with modern tooling
- Work context: Agencies, consultancies, or in-house teams handling legacy modernization projects
- Tool stack: Claude Code, Cursor, Gemini CLI, and other AI-assisted development environments

**Current Behaviors & Workflows:**
- Already integrate AI tools into their daily development workflow
- Rely on AI for code generation, analysis, and documentation tasks
- Work on multiple client projects requiring legacy system understanding
- Use MCP servers and extensions to extend AI capabilities

**Specific Needs & Pain Points:**
- Need systematic approach to legacy application analysis that integrates with existing AI workflow
- Struggle with time-intensive manual exploration of undocumented legacy systems
- Require technical specifications suitable for rebuild planning
- Want to leverage AI for analysis but need human oversight for accuracy

**Goals They're Trying to Achieve:**
- Deliver accurate project scoping and timelines for modernization projects
- Reduce discovery phase duration while maintaining quality
- Generate comprehensive technical documentation for rebuild teams
- Maintain competitive advantage through efficient AI-enhanced processes

### Secondary User Segment: Technical Project Managers

**Demographic/Profile:**
- Project managers with technical background overseeing modernization projects
- Client-facing roles requiring accurate scope and timeline communication
- Work for agencies or consultancies specializing in legacy system modernization

**Current Behaviors & Workflows:**
- Coordinate between client stakeholders and development teams
- Responsible for project scoping, timeline estimation, and risk management
- Need to communicate technical findings to non-technical stakeholders

**Specific Needs & Pain Points:**
- Need reliable progress tracking and documentation for client reporting
- Require structured output that can be communicated to business stakeholders
- Want to minimize scope creep through comprehensive upfront analysis

**Goals They're Trying to Achieve:**
- Deliver predictable project timelines and budgets
- Maintain client confidence through transparent progress reporting
- Bridge communication gap between technical analysis and business requirements

## Goals & Success Metrics

### Business Objectives
- **Reduce legacy analysis time by 95%** - From typical 4-6 week manual discovery to 4-8 hours of AI-automated analysis
- **Achieve 95% feature coverage accuracy** - Ensure rebuilt applications capture all critical legacy functionalities
- **Reach 100+ development teams using this MCP server** within first 6 months
- **Complete 500+ successful website analyses** in the first year of operation

### User Success Metrics
- **Time to first useful analysis:** Users can generate meaningful site analysis within 15 minutes of providing URL
- **Complete site analysis duration:** Full website analysis completed within 2-6 hours depending on site complexity
- **Analysis completion rate:** 95% of started analyses are completed successfully without errors
- **Documentation quality score:** User-rated documentation usefulness averaging 4.2/5.0 or higher
- **Same-day project scoping:** 90% of users can provide client project estimates same day as analysis completion

### Key Performance Indicators (KPIs)
- **MCP Server Installations:** Number of teams/developers who have installed and configured this MCP server
- **Analysis Volume:** Number of websites analyzed per month using this MCP server
- **Feature Detection Accuracy:** Percentage of legacy features correctly identified and documented
- **Processing Speed:** Average time per page analysis (target: under 2 minutes per page)
- **User Retention:** Development teams who continue using this MCP server after initial trial
- **Integration Health:** Compatibility and performance across supported AI development environments
- **Documentation Export Rate:** Percentage of analyses that result in exported, actionable rebuild specifications

## MVP Scope

### Core Features (Must Have)

- **MCP Server Foundation:** Basic MCP server implementation that integrates with Claude Code, Cursor, and Gemini CLI environments with proper protocol compliance and error handling

- **URL Input & Sitemap Discovery:** Accept website URL input, automatically discover and parse sitemaps (XML sitemaps, robots.txt, and manual crawling fallback), generate organized URL inventory with basic descriptions

- **Page Selection Interface:** Present discovered URLs in organized, filterable list format allowing users to select specific pages/sections for detailed analysis

- **Basic Feature Detection:** Use Playwright to identify and document core UI elements (forms, buttons, links, navigation), capture basic user interaction patterns, and detect fundamental page functionality including:
  - Core Interactive Elements: Forms, navigation, user actions, content management
  - Basic Business Logic: Workflow steps, conditional display, data relationships, simple calculations
  - Essential User Flows: Authentication, core tasks, error handling, data persistence

- **Network Traffic Analysis:** Monitor and capture API calls, AJAX requests, and backend interactions during page interactions using Playwright's network monitoring capabilities

- **Dual Operation Modes:** Implement both Interactive mode (prompts for user confirmation at key decision points) and YOLO mode (fully automated analysis without interruption)

- **Progress Documentation:** Generate real-time analysis reports in project-specific markdown files, maintain organized folder structure for multi-page analysis results

- **Basic Export Functionality:** Output structured analysis results in developer-friendly format suitable for rebuild planning and technical specification creation

### Out of Scope for MVP

- Advanced UI component recognition (complex widgets, custom frameworks)
- Database schema analysis or reverse engineering
- Performance optimization recommendations
- Multi-language/internationalization analysis
- Advanced security vulnerability scanning
- Integration with specific project management tools
- Custom reporting templates or branding options
- Bulk analysis of multiple websites simultaneously

### MVP Success Criteria

The MVP will be considered successful when a development team can: (1) Install and configure the MCP server in their AI environment within 15 minutes, (2) Complete full analysis of a typical legacy website (10-50 pages) within 6 hours, (3) Generate actionable documentation that enables project scoping and rebuild planning, and (4) Successfully use both Interactive and YOLO modes without technical issues.

## Post-MVP Vision

### Phase 2 Features

**Advanced Analysis Capabilities:**
- **Smart Component Recognition:** AI-powered identification of complex UI frameworks (React, Angular, Vue), custom widgets, and third-party integrations
- **Business Logic Extraction:** Advanced analysis of JavaScript functionality, workflow automation, and conditional logic patterns
- **Data Flow Mapping:** Comprehensive tracking of data relationships, state management patterns, and information architecture

**Enhanced Integration & Automation:**
- **Bulk Website Analysis:** Simultaneous analysis of multiple related websites or application environments
- **Custom Analysis Templates:** User-defined analysis patterns for specific industry verticals or application types
- **CI/CD Integration:** Automated analysis triggers for continuous legacy system monitoring

### Long-term Vision

**Platform Evolution (12-18 months):**
Transform from single-purpose MCP server into comprehensive legacy modernization platform with:
- **Multi-protocol Support:** Beyond MCP to include REST APIs, webhooks, and direct IDE integrations
- **Collaborative Analysis:** Team-based analysis workflows with role-based permissions and review processes
- **Intelligence Layer:** Machine learning models trained on analysis patterns to improve accuracy and speed

**Ecosystem Integration (18-24 months):**
- **Modernization Toolkit:** Integrated code generation suggestions based on analysis findings
- **Architecture Recommendations:** AI-powered suggestions for optimal rebuild approaches and technology stacks
- **Project Management Integration:** Direct integration with Jira, Linear, and other PM tools for seamless project handoff

### Expansion Opportunities

**Vertical Market Extensions:**
- **E-commerce Specialization:** Enhanced analysis for shopping carts, payment flows, and inventory systems
- **Enterprise Applications:** Specialized analysis for CRM, ERP, and internal business applications
- **Compliance & Security:** Automated identification of security patterns and regulatory compliance requirements

**Technology Platform Extensions:**
- **Mobile Application Analysis:** Extend capabilities to analyze mobile web apps and hybrid applications
- **API-First Analysis:** Dedicated tooling for analyzing and documenting legacy API infrastructures
- **Database Analysis Integration:** Connect application analysis with database schema exploration

## Technical Considerations

### Platform Requirements
- **Target Platforms:** Cross-platform MCP server (Windows, macOS, Linux) using Python runtime environments
- **AI Environment Support:** Native MCP integration with Claude Code, Cursor, VS Code (GitHub Copilot Chat), and other MCP-compatible AI development tools
- **Browser Support:** Playwright Python for browser automation supporting Chromium, Firefox, WebKit, and Edge browsers
- **Performance Requirements:** Handle concurrent browser sessions, JSON-RPC 2.0 message processing, 2-minute average per page analysis time

### Technology Preferences
- **MCP Server Core:** Python with FastMCP framework for rapid MCP server development with minimal boilerplate
- **Automation Engine:** Playwright for Python for browser automation, network monitoring, and page interaction capabilities
- **Web Framework:** FastMCP's built-in server capabilities (based on Python async/await patterns)
- **Authentication:** FastMCP's built-in authentication and authorization system
- **Data Storage:** File-based JSON/YAML output for analysis results, Python's native file handling

### Architecture Considerations

**MCP Protocol Structure:**
- **Tools**: Browser automation functions (navigate, analyze, capture network traffic)
- **Resources**: Website analysis results, progress reports, generated documentation
- **Prompts**: Interactive workflow templates for guided analysis sessions

**Service Architecture:**
- JSON-RPC 2.0 message handler for MCP protocol compliance
- Playwright browser manager for session lifecycle
- Analysis worker processes for parallel page processing
- Progress tracking system for real-time status updates

**LLM Integration Architecture:**

**Multi-Provider LLM Support (Latest August 2025 Models):**
- Abstract LLM provider interface supporting OpenAI, Anthropic, and Gemini APIs
- Provider fallback mechanism for reliability and cost optimization
- **Cost-Optimized Model Selection:**
  - **Budget Tier**: GPT-5-nano, GPT-4.1-nano, Gemini 2.5 Flash-Lite, Ministral 3B
  - **Balanced Tier**: GPT-5-mini, GPT-4.1-mini, Gemini 2.5 Flash, Claude 3.7 Sonnet
  - **Advanced Tier**: o4-mini (reasoning), Claude Sonnet 4, Gemini 2.5 Pro
- **Smart Model Selection Logic**: Automatic selection based on analysis complexity and cost optimization
- Unified response formatting across all providers

**Two-Step Analysis Pipeline:**
- **Step 1 - Content Summarization:** LLM analyzes page purpose, content hierarchy, user journey context, and business logic overview
- **Step 2 - Feature Analysis:** Detailed examination of interactive elements, functional capabilities, API integrations, business rules, and rebuild specifications
- Context passing between steps for informed feature analysis
- Structured JSON output optimized for development team consumption

**Progress Tracking for Long Analyses:**
```python
class AnalysisProgress:
    def __init__(self, project_id: str, total_pages: int):
        self.project_id = project_id
        self.total_pages = total_pages
        self.completed_pages = 0
        self.current_page = ""
        self.step1_completed = []
        self.step2_completed = []
        self.errors = []
        self.start_time = datetime.now()

    async def update_progress(self, page_url: str, step: int, status: str):
        # Real-time progress updates to project documentation
        # WebSocket notifications for interactive mode
        # Checkpoint creation for resume capability
```

**Real-time Documentation Generation:**
- Live markdown file updates during analysis progression
- Project-specific folder structure with organized results
- Resume capability from any checkpoint in case of interruption
- Progress webhooks for integration with external project management tools

**Integration Requirements:**
- MCP protocol compliance following modelcontextprotocol.io/specification
- Configuration via `.cursor/mcp.json`, `claude mcp add`, or VS Code settings
- Environment variable support for LLM API keys and provider selection
- Capability negotiation during connection handshake

**Security/Compliance:**
- Explicit user consent for website access and automation
- Local execution model to protect credentials and sensitive data
- LLM API key security and rotation management
- Configurable rate limiting to respect target website resources and LLM provider limits
- Access controls and privacy protection following MCP security principles

## Constraints & Assumptions

### Constraints

**Budget:**
- MVP development budget assumes single developer/small team for 3-4 months
- **LLM API costs significantly reduced**: $10-50/month using latest cost-optimized models (GPT-5-nano, Gemini 2.5 Flash-Lite) for 10-50 sites/month analysis volume
- No significant infrastructure costs due to local deployment model
- FastMCP and Playwright are open-source, minimizing licensing costs

**Timeline:**
- MVP delivery target: 12-16 weeks from development start
- Phase 1 (MCP server + basic Playwright): 6-8 weeks
- Phase 2 (LLM integration + two-step analysis): 4-6 weeks
- Phase 3 (Interactive/YOLO modes + documentation): 2-4 weeks
- Beta testing and iteration: 2-3 weeks

**Resources:**
- Primary developer with Python, FastMCP, and Playwright experience
- LLM API access for all three providers (OpenAI, Anthropic, Gemini)
- Test websites for development and validation (mix of simple and complex legacy sites)
- Target development teams for beta testing and feedback

**Technical:**
- Limited to websites accessible without complex authentication flows for MVP
- Browser automation limited to JavaScript-enabled sites (no complex SPA frameworks initially)
- Analysis quality depends on LLM provider availability and rate limits
- Local execution model limits scalability for enterprise use cases

### Key Assumptions

- **Market Demand:** Development teams using AI tools (Claude Code, Cursor) will adopt MCP servers for specialized tasks like legacy analysis
- **LLM Capability:** Latest generation models (GPT-5-nano, Claude 3.7 Sonnet, Gemini 2.5) can effectively analyze web applications and extract meaningful rebuild specifications
- **Technical Feasibility:** Playwright can reliably capture the interactive behavior and API calls necessary for comprehensive feature analysis
- **User Adoption:** Developers prefer self-hosted solutions for security-sensitive legacy analysis over cloud-based services
- **Integration Success:** FastMCP framework will provide stable, reliable MCP protocol implementation suitable for production use
- **Cost Acceptability:** Reduced LLM API costs of $10-50/month per team are highly acceptable for the time savings provided
- **Performance Expectations:** 2-6 hour analysis time for typical legacy websites (10-50 pages) meets user needs for project scoping
- **Documentation Value:** AI-generated analysis documentation will be sufficiently accurate and detailed for development team use in rebuild planning

## Risks & Open Questions

### Key Risks

- **MCP Ecosystem Maturity:** MCP protocol is relatively new (November 2024), with potential for breaking changes or limited adoption that could impact long-term viability of the platform

- **LLM Provider Reliability:** Dependence on external LLM APIs introduces risks of service outages, rate limiting, or cost increases that could disrupt analysis workflows during critical project phases

- **Website Complexity Limitations:** Modern single-page applications with complex JavaScript frameworks may not be fully analyzable through Playwright automation, potentially missing critical functionality in legacy system analysis

- **Analysis Accuracy Variance:** LLM-generated analysis quality may vary significantly based on website complexity, content clarity, and model performance, potentially leading to incomplete or inaccurate rebuild specifications

- **Competitive Response:** Established players in the legacy modernization space (consulting firms, enterprise software vendors) may develop competing solutions with greater resources and market reach

### Open Questions

- How accurately can latest LLMs (GPT-5, Claude 4) identify complex business logic and workflow dependencies that aren't immediately visible in the UI?
- What is the optimal balance between automated analysis speed and human validation accuracy for different types of legacy applications?
- Will FastMCP framework provide sufficient performance and stability for production use in enterprise development environments?
- How should the tool handle authentication-protected areas of legacy applications during analysis?
- What level of technical expertise will target users need to effectively configure and operate the MCP server?
- How can the tool differentiate between essential legacy functionality and deprecated features that shouldn't be rebuilt?
- What backup strategies are needed when primary LLM providers experience outages during critical analysis phases?

### Areas Needing Further Research

- **Market Validation:** Survey target development teams to validate demand, pricing sensitivity, and feature priorities for legacy analysis automation tools
- **Technical Feasibility Studies:** Test Playwright's capabilities against diverse legacy website architectures (ASP.NET, PHP, Java frameworks, custom CMS platforms)
- **LLM Performance Benchmarking:** Evaluate analysis accuracy across different LLM providers using standardized test websites with known functionality
- **Security Assessment:** Research data privacy and security implications of transmitting website content to external LLM providers for analysis
- **Competitive Analysis:** Deep dive into existing tools and services in the legacy modernization space to identify differentiation opportunities
- **Cost Optimization Research:** Investigate strategies for minimizing LLM API costs while maintaining analysis quality (prompt optimization, caching, local models)
- **Integration Testing:** Validate MCP integration stability across different AI development environments and their update cycles

## Appendices

### A. Research Summary

This project brief was developed through comprehensive research of:
- **MCP Protocol Analysis:** Review of Model Context Protocol specifications and FastMCP Python framework capabilities
- **Playwright Automation Capabilities:** Assessment of browser automation features for web application analysis
- **LLM Provider Evaluation:** Analysis of latest 2025 models including GPT-5 family, Claude 4, and Gemini 2.5 series for content analysis tasks
- **Target Market Assessment:** Evaluation of AI-enhanced development tool adoption and legacy modernization market trends

### B. Stakeholder Input

Primary stakeholder feedback incorporated:
- Development team requirements for legacy system analysis automation
- Client needs for predictable modernization project scoping and timelines
- Technical requirements for MCP integration with existing AI development workflows
- Security and privacy considerations for sensitive legacy application analysis

### C. References

- Model Context Protocol Specification: https://modelcontextprotocol.io/specification
- FastMCP Python Framework: https://gofastmcp.com/
- Playwright Python Documentation: https://playwright.dev/python/
- AI Development Tool Integration Patterns: MCP ecosystem documentation

## Next Steps

### Immediate Actions

1. **Validate Technical Feasibility:** Create proof-of-concept MCP server with basic Playwright integration to confirm FastMCP framework suitability and browser automation capabilities

2. **Secure Development Resources:** Obtain LLM API access for latest cost-optimized models (GPT-5-nano, Claude 3.7 Sonnet, Gemini 2.5 Flash-Lite) and establish development environment

3. **Define MVP Requirements:** Create detailed technical specifications for Phase 1 development including MCP protocol implementation, Playwright automation patterns, and basic analysis workflows

4. **Establish Testing Framework:** Identify 3-5 representative legacy websites for development testing and validation of analysis accuracy and performance metrics

5. **Market Validation Research:** Conduct interviews with 10-15 target development teams to validate demand, feature priorities, and pricing expectations for the MCP server

### PM Handoff

This Project Brief provides the full context for the **Legacy Web Application Analysis MCP Server** project. Please start in 'PRD Generation Mode', review the brief thoroughly to work with the user to create the PRD section by section as the template indicates, asking for any necessary clarification or suggesting improvements.

The project is positioned for immediate development start with clear technical architecture, market understanding, and success metrics. Focus areas for PRD development should include:
- Detailed technical specifications for FastMCP and Playwright integration
- Comprehensive user workflows for both Interactive and YOLO analysis modes
- Specific requirements for latest-generation LLM provider integration and fallback mechanisms
- Progress tracking and documentation generation requirements
- Security and privacy implementation details

**Key advantages with 2025 model updates:**
- 80% cost reduction through optimized model selection
- Enhanced analysis capabilities with latest reasoning models
- Improved large context handling (1M tokens) for comprehensive page analysis
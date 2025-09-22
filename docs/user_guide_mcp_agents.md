# User Guide: Legacy Web Application Analysis MCP Server for AI Agents

## 1. Introduction

The Legacy Web Application Analysis MCP Server is a powerful tool designed to automate the analysis of legacy web applications. It integrates seamlessly with AI development environments such as Claude Code, Cursor, and Gemini CLI, transforming weeks of manual analysis into hours of AI-powered workflows. This guide will walk you through how to leverage the MCP server's capabilities using your preferred AI agent.

**Key Features:**
*   **AI-Driven Analysis:** Utilizes LLMs for intelligent content summarization and detailed feature analysis.
*   **Browser Automation:** Employs Playwright for robust web navigation, data extraction, and interaction.
*   **Automated Documentation:** Organizes analysis artifacts into structured, project-specific documentation.
*   **MCP Protocol Integration:** Exposes functionalities as "tools" and data as "resources" for AI agents.

## 2. Setup & Configuration

To use the MCP server, you'll need to set it up within your AI development environment.

### 2.1. Installation

The MCP server is a Python application built with the FastMCP framework. Ensure you have Python 3.11+ installed.

**1. Install FastMCP:**
You can install FastMCP using `uv` (recommended) or `pip`.

*   **Using `uv` (Recommended):**
    ```bash
    uv pip install fastmcp
    # Or, if adding as a project dependency:
    uv add fastmcp
    ```
*   **Using `pip` (Alternative):**
    ```bash
    pip install fastmcp
    ```

**2. Project-Specific Dependencies:**
Specific installation instructions for the MCP server itself would typically involve:
1.  Cloning the project repository.
2.  Installing Python dependencies (e.g., `pip install -r requirements.txt` or `uv pip install -r requirements.txt`).
3.  Installing Playwright browser dependencies (e.g., `playwright install`).

### 2.2. Configuring Your AI Development Environment

The MCP server communicates via the Model Context Protocol (MCP), which is a JSON-RPC 2.0 based protocol. Your AI development environment (Claude Code, Cursor, Gemini CLI) will need to be configured to connect to the running MCP server.

*   **Configuration Files:** Look for configuration options in your AI environment's settings, typically in files like `.cursor/mcp.json` or through specific commands (e.g., `claude mcp add`).
*   **API Keys:** Ensure your LLM API keys (for OpenAI, Anthropic, Gemini) are configured, usually via environment variables or your AI environment's secret management.

### 2.3. Verifying the Setup

You can use the following MCP tools to verify your setup:

*   **`health_check()`:** Checks the server's status and FastMCP state.
*   **`validate_dependencies()`:** Verifies Playwright browser installation.
*   **`test_llm_connectivity()`:** Validates API keys and connectivity to LLM providers.
*   **`show_config()`:** Displays the current MCP server configuration (without sensitive values).

**Example Interaction (Conceptual):**
```
// In your AI agent's chat/command interface
Agent: Call tool health_check()
```

### 2.4. Packaging and Deployment

Packaging a FastMCP server involves preparing your application for execution and distribution.

**1. Running Your FastMCP Server:**
Once your FastMCP server application (e.g., `my_server.py`) is created, you can run it in several ways:

*   **Standard Python Execution:** If your server script includes an `if __name__ == "__main__": mcp.run()` block, you can run it directly:
    ```bash
    python my_server.py
    ```
*   **Using the FastMCP CLI:** The `fastmcp` command-line interface provides a convenient way to run your server:
    ```bash
    fastmcp run server.py --transport stdio
    # Or for remote access:
    fastmcp run server.py --transport http
    ```

**2. Deployment Considerations:**
*   **FastMCP Cloud:** A hosting service provided by the FastMCP team for easy deployment of authenticated servers, integrating with GitHub.
*   **Docker:** FastMCP servers can be containerized using Docker for portability and consistent environments.
*   **FastAPI Integration:** FastMCP can be integrated into existing FastAPI applications.
*   **Versioning:** For production, it's recommended to pin FastMCP to an exact version (e.g., `fastmcp==2.11.0`) to avoid unexpected breaking changes.

**3. FastMCP CLI for Client Integration:**
The `fastmcp` CLI also includes commands for integrating your MCP server with various client applications:

*   **`fastmcp install`:** This command helps install an MCP server into supported client applications like Claude Code, Claude Desktop, and Cursor, or generates standard MCP JSON configuration for manual use.
*   **`fastmcp prepare`:** This command creates a `uv` project with a `pyproject.toml` file containing dependencies, a `.venv` with pre-installed packages, and a `uv.lock` file for reproducible environments.

## 3. Core Workflows: Analyzing a Web Application

The MCP server provides a suite of tools to perform web application analysis.

### 3.1. Initial Discovery

Use `discover_website()` to get an initial understanding of a website's structure.

*   **`discover_website(url: str)`:** Accepts a URL and returns an organized site structure (e.g., sitemap, discovered links).

**Example:**
```
Agent: Call tool discover_website(url="https://example.com")
```

### 3.2. Page-Level Analysis

For detailed analysis of individual pages or a list of pages:

*   **`navigate_to_page(url: str)`:** Navigates the browser to a specific URL.
*   **`analyze_page_list(urls: List[str])`:** Processes a list of URLs sequentially.
*   **`analyze_page_features(url: str, content: str)`:** Performs detailed feature analysis on a page, often used after content summarization.

### 3.3. Orchestrated Analysis Workflows

The MCP server offers high-level orchestration tools for comprehensive analysis:

*   **`analyze_legacy_site(url: str)`:** Executes a complete automated analysis workflow for a given URL.
*   **`intelligent_analyze_site(url: str)`:** Initiates a natural language AI-driven analysis workflow.
*   **`analyze_with_recommendations(url: str)`:** Allows the AI to select an optimal analysis strategy.

**Example:**
```
Agent: Call tool analyze_legacy_site(url="https://legacyapp.com")
```

### 3.4. Progress Tracking

Monitor the progress of ongoing analyses:

*   **`get_analysis_status()`:** Retrieves the current status of an analysis.
*   **MCP Resource `analysis_progress`:** Provides live status updates accessible from your AI environment.

**Example:**
```
Agent: Call tool get_analysis_status()
```

### 3.5. Checkpointing and Resumption

For long-running analyses, you can pause and resume:

*   **`pause_analysis()`:** Safely stops the current analysis and saves its state.
*   **`resume_analysis()`:** Continues an analysis from its last checkpoint.

## 4. Accessing Analysis Results & Documentation

After analysis, the MCP server organizes all artifacts into a structured documentation format.

### 4.1. Project Documentation Structure

All analysis artifacts are stored in a standardized directory: `<project_root>/docs/web_discovery/`.

This structure typically includes:
*   `analysis-metadata.json`: Metadata about the analysis.
*   `analysis-report.md`: A master report summarizing the findings.
*   `pages/`: A directory containing individual markdown files for each analyzed page (e.g., `page-home.md`, `page-login.md`).

### 4.2. File Management Tools

You can interact with the generated documentation using these tools:

*   **`setup_project_documentation_structure()`:** Creates the necessary documentation folders.
*   **`organize_project_artifacts()`:** Organizes raw analysis outputs into the structured documentation.
*   **`generate_master_analysis_report()`:** Compiles a comprehensive master report.
*   **`list_project_documentation_files()`:** Lists all generated documentation files.
*   **`generate_url_slug(url: str)`:** Converts a URL into a safe filename slug.
*   **`create_gitignore_for_web_discovery()`:** Generates a `.gitignore` entry for the documentation folder.

### 4.3. Accessing Documentation via MCP Resources

The MCP server exposes the generated documentation as resources using the `web_discovery://` URI scheme. Your AI agent can directly access these resources.

**Example (Conceptual):**
```
Agent: Read resource web_discovery://pages/page-home.md
```
Your AI agent can then process the content of these markdown files for further analysis, summarization, or to generate rebuild specifications.

## 5. Advanced Usage

### 5.1. Analysis Modes

The MCP server supports different analysis modes:

*   **Interactive Mode:** (`interactive_analysis()`) Human-in-the-loop validation, presenting decision points during the workflow.
*   **YOLO Mode:** (`yolo_analysis()`) Fully automated analysis with minimal user input.
*   **Mode Selection:** (`start_analysis()`) Presents clear options for selecting an analysis mode.

### 5.2. Debugging and Quality Tools

The MCP server includes tools for debugging and ensuring analysis quality:

*   **Debugging Tools:** A set of MCP tools (e.g., from `src/legacy_web_mcp/mcp/debugging_tools.py`) expose capabilities for artifact management, quality validation, and session monitoring. Consult the `dev_context.md` or `debugging_tools.py` for specifics.

## 6. Conclusion

By understanding and utilizing these MCP tools and resources, AI agents like Claude Code, Cursor, and Gemini CLI can effectively orchestrate complex web application analysis, generate valuable documentation, and streamline the legacy modernization process. Refer to the project's `dev_context.md` and `PRD.md` for deeper technical insights and architectural details.
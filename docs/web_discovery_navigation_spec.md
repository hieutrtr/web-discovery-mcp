# Web Discovery and Navigation Specification

This document outlines the mechanisms by which the Legacy Web MCP (Multi-Cloud Platform) handles URL discovery and navigation, integrating various components to systematically analyze websites.

## 1. Overview

The web discovery and navigation process is a multi-layered approach designed to:
1.  **Discover** relevant URLs from a target website using various strategies.
2.  **Normalize and Validate** these URLs for consistency and correctness.
3.  **Filter and Limit** the discovered URLs based on user-defined criteria.
4.  **Navigate** to discovered URLs using a browser automation framework.
5.  **Extract** content and further discover URLs from within loaded pages.
6.  **Orchestrate** these steps into a coherent analysis workflow.

## 2. URL Normalization and Validation

A foundational aspect of URL handling is ensuring consistency and validity. The `normalize_url` function (located in `src/legacy_web_mcp/discovery/utils.py`) plays a central role:

*   **Input**: Takes a raw URL string.
*   **Parsing**: Uses `urllib.parse.urlparse` to break down the URL into its components.
*   **Validation**:
    *   Ensures the URL scheme is either `http` or `https`.
    *   Verifies the presence of a hostname (`netloc`).
    *   Raises `InvalidTargetURL` for invalid URLs.
*   **Normalization**:
    *   Converts the scheme and hostname to lowercase.
    *   Removes the fragment identifier (e.g., `#section`).
*   **Output**: Returns a `NormalizedURL` dataclass containing the cleaned URL string and its domain.

This normalization is applied early and consistently across discovery and navigation phases.

## 3. Discovery Phase (`WebsiteDiscoveryService`)

The `WebsiteDiscoveryService` (located in `src/legacy_web_mcp/discovery/pipeline.py`) is responsible for the initial, broad discovery of URLs for a given target website. It employs a multi-pronged strategy:

*   **Initial Normalization**: The target URL is first normalized using `normalize_url`.
*   **Robots.txt Analysis**:
    *   Utilizes `analyze_robots` to parse the website's `robots.txt` file.
    *   Identifies disallowed paths to avoid crawling.
    *   Extracts sitemap URLs specified in `robots.txt`.
*   **Sitemap Fetching**:
    *   Uses `fetch_sitemaps` to retrieve and parse XML sitemaps.
    *   Collects URLs listed within these sitemaps.
    *   Incorporates sitemap URLs discovered from `robots.txt`.
*   **Web Crawling (Fallback)**:
    *   If sitemaps are unavailable or insufficient, a manual crawl is initiated using the `crawl` function.
    *   This recursively explores links within the website up to a specified depth.
*   **URL Ingestion and Classification**:
    *   Discovered URLs from all sources are ingested into a collection of `DiscoveredURL` objects.
    *   `is_internal_url` (from `utils.py`) determines if a URL belongs to the target domain.
    *   `is_asset_url` (from `utils.py`) identifies static assets (e.g., `.css`, `.js`, `.png`).
    *   `absolute_url` (from `utils.py`) is used to convert relative links found during crawling into full, absolute URLs.
    *   Each `DiscoveredURL` is enriched with a generated title, description, and complexity estimate.
*   **Inventory Creation**: A `DiscoveryInventory` is compiled, summarizing all discovered URLs and their metadata.

## 4. Navigation Phase (`PageNavigator`)

The `PageNavigator` (located in `src/legacy_web_mcp/browser/navigation.py`) is responsible for programmatically navigating a browser to a given URL and extracting its content.

*   **Initialization**: Configured with parameters like `timeout`, `max_retries`, `wait_for_network_idle`, and `enable_screenshots`.
*   **`navigate_and_extract` Method**:
    *   Receives a URL (typically one discovered in the previous phase).
    *   **Re-normalization**: As a safety measure, the input URL is again passed through `normalize_url` to ensure it's valid and consistent before navigation.
    *   **Browser Interaction**: Uses Playwright's `page.goto(url)` method to direct the browser to the target URL.
    *   **Error Handling**:
        *   Implements a retry mechanism (`max_retries`) for transient navigation failures.
        *   Checks the HTTP status code of the response; status codes >= 400 (e.g., 404, 403, 500) result in a `PageNavigationError`.
        *   Handles Playwright-specific `TimeoutError`.
    *   **Content Loading**: Waits for network idle and DOM content loaded states to ensure the page is fully rendered.
    *   **Content Extraction**: Upon successful navigation, it extracts:
        *   Page title (`page.title()`)
        *   Full HTML content (`page.content()`)
        *   Visible text (`page.inner_text("body")`)
        *   Metadata (meta tags, canonical URL, language, viewport) using `_extract_meta_data`.
    *   **Screenshots**: Optionally captures a full-page screenshot.
*   **Output**: Returns a `PageContentData` object containing all extracted information.

## 5. In-Page URL Discovery (`PageInteractionAutomator`)

The `PageInteractionAutomator` (located in `src/legacy_web_mcp/browser/interaction.py`) focuses on discovering URLs dynamically within an already loaded page by simulating user interactions.

*   **`discover_and_interact` Method**:
    *   Identifies interactive elements on the page using a predefined set of CSS selectors (e.g., `a[href]`, `button`, `input`).
    *   **Link Extraction**: For `<a>` tags, it extracts the `href` attribute.
    *   **URL Construction**: Uses `urllib.parse.urljoin(base_url, href)` to resolve relative `href` values into absolute URLs.
    *   **`discovered_urls` Set**: These newly constructed URLs are added to a `self.discovered_urls` set, preventing duplicates and making them available for further processing.
    *   **Safety Checks**: Before interacting with elements or adding URLs, it performs checks (`_is_safe_interaction`, `_contains_destructive_keywords`) to avoid destructive actions or navigation to potentially unsafe URLs.
    *   **Interaction Simulation**: Simulates hovers, clicks, form fills, and scrolling to reveal dynamically loaded content and associated links.

## 6. Orchestration (`LegacyAnalysisOrchestrator`)

The `LegacyAnalysisOrchestrator` (located in `src/legacy_web_mcp/mcp/orchestration_tools.py`) ties all these components together into a comprehensive site analysis workflow. This is also where advanced URL filtering and limiting are applied.

*   **`discover_and_analyze_site` Method**: This is the high-level entry point.
    *   **New Parameters for Filtering**: The `analyze_legacy_site` and `intelligent_analyze_site` tools will accept new optional parameters:
        *   `include_patterns: Optional[List[str]]`: A list of glob-like patterns (e.g., `*.html`, `/products/*`) to explicitly include URLs.
        *   `exclude_patterns: Optional[List[str]]`: A list of glob-like patterns to explicitly exclude URLs.
        *   `url_filter_mode: Literal["include", "exclude"]`: Determines whether `include_patterns` or `exclude_patterns` take precedence if both are provided.
    *   These parameters are passed down to the `LegacyAnalysisOrchestrator`'s `discover_and_analyze_site` method.

*   **Intelligent Site Discovery (`_intelligent_site_discovery`)**:
    *   Calls `_intelligent_site_discovery` which leverages the `WebsiteDiscoveryService` to get an initial set of URLs.
    *   **URL Filtering Logic**: *After* the `WebsiteDiscoveryService` has returned `all_urls`, but *before* `_select_priority_pages`, a new filtering step is introduced. This step will apply the `include_patterns`, `exclude_patterns`, and `url_filter_mode` to `all_urls`, producing a refined list of URLs. This filtering will use pattern matching (e.g., `fnmatch` or regular expressions) to match URLs against the provided patterns.

*   **Page Selection (`_select_priority_pages`)**:
    *   Selects a subset of these *filtered* URLs for analysis based on `analysis_mode` and `max_pages`. The `max_pages` limit will now apply to the already filtered set of URLs.

*   **`SequentialNavigationWorkflow`**: Creates an instance of `SequentialNavigationWorkflow` (from `src/legacy_web_mcp/browser/workflow.py`).
    *   This workflow manages the sequential processing of the selected URLs.
    *   It uses `BrowserAutomationService` to manage browser sessions.
    *   For each URL in its queue, it instantiates a `PageAnalyzer` (from `src/legacy_web_mcp/browser/analysis.py`).
    *   The `PageAnalyzer` then utilizes the `PageNavigator` to navigate and the `PageInteractionAutomator` to discover in-page URLs and interact with the page.

In summary, the MCP's web discovery and navigation system is a robust pipeline that systematically finds, validates, filters, limits, navigates, and extracts information from web pages, with careful consideration for URL integrity, dynamic content discovery, and user-defined analysis scope.
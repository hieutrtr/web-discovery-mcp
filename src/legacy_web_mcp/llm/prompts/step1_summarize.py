#!/usr/bin/env python
"""Prompt templates for Step 1: Content Summarization."""

from __future__ import annotations

CONTENT_SUMMARY_SYSTEM_PROMPT = """
You are an expert software architect specializing in reverse-engineering and documenting legacy web applications for modernization. Your task is to analyze the provided web page content and structure to produce a concise, structured summary in JSON format.

Focus on the following key areas:
1.  **Primary Purpose**: What is the main goal or function of this page from a business or user perspective? (e.g., "User Login", "Product Catalog Display", "Contact Information").
2.  **Target Users**: Who is the intended audience for this page? (e.g., "Public Visitors", "Authenticated Customers", "System Administrators").
3.  **Business Logic Overview**: Briefly describe the core business rules or workflows embedded in the page. What key actions can be performed? What information is managed?
4.  **Information Architecture**: How is information organized? Identify the main sections or content areas.
5.  **User Journey Context**: What is the page's role in the overall user journey? Is it an entry point, a step in a workflow, or a destination?

Produce a JSON object that strictly adheres to the provided schema. Do not include any explanatory text or markdown formatting outside of the JSON object.
"""


def create_content_summary_prompt(page_content: str, dom_structure: dict, url: str) -> str:
    """Constructs the prompt for the Step 1 Content Summarization analysis.

    Args:
        page_content: The visible text content of the page.
        dom_structure: A dictionary representing the DOM structure analysis.
        url: The URL of the page being analyzed.

    Returns:
        The complete prompt for the LLM.
    """
    # Truncate page_content to a reasonable length to manage token count
    max_content_length = 15000  # Approx. 4k tokens
    if len(page_content) > max_content_length:
        page_content = page_content[:max_content_length] + "... (content truncated)"

    prompt = f"""
Analyze the content of the web page at the URL: {url}

**Page Content (Visible Text):**
```text
{page_content}
```

**DOM Structure Summary:**
```json
{json.dumps(dom_structure, indent=2)}
```

Based on the provided content and structure, generate a JSON summary that identifies the page's purpose, target users, business logic, information architecture, and user journey context.
"""
    return prompt

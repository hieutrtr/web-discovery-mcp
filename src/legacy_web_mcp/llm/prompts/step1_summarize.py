#!/usr/bin/env python
"""Prompt templates for Step 1: Content Summarization."""

from __future__ import annotations

import json
from typing import Any

CONTENT_SUMMARY_SYSTEM_PROMPT = """
You are an expert software architect specializing in reverse-engineering and documenting legacy web applications for modernization. Your task is to analyze the provided web page content and structure to produce a comprehensive, structured summary in JSON format that will inform detailed technical analysis.

Focus on the following key areas:

## Core Analysis Fields:
1.  **purpose**: What is the main goal or function of this page from a business or user perspective? (e.g., "User Login", "Product Catalog Display", "Contact Information").
2.  **user_context**: Who is the intended audience for this page? (e.g., "Public Visitors", "Authenticated Customers", "System Administrators").
3.  **business_logic**: Briefly describe the core business rules or workflows embedded in the page. What key actions can be performed? What information is managed?
4.  **navigation_role**: What is the page's role in the overall site navigation? Is it an entry point, a step in a workflow, or a destination?
5.  **confidence_score**: Rate your confidence in this analysis (0.0-1.0, where 1.0 is highest confidence).

## Enhanced Context Fields for Technical Analysis:
6.  **key_workflows**: List the main business workflows this page supports (e.g., ["user_registration", "checkout_process", "content_management"]).
7.  **user_journey_stage**: Identify the stage in the user journey (e.g., "entry", "middle", "exit", "conversion", "support", "administration").
8.  **content_hierarchy**: Describe the content organization and information architecture as a structured object (e.g., {"main_content": "product_details", "sidebar": "related_products", "header": "navigation"}).
9.  **business_importance**: Rate the business importance of this page (0.0-1.0, where 1.0 is most critical to business operations).
10. **entry_exit_points**: Identify key entry and exit points as an object with "entry" and "exit" arrays (e.g., {"entry": ["search_results", "homepage"], "exit": ["checkout", "contact_form"]}).
11. **contextual_keywords**: List key terms and concepts that define this page's context for technical analysis (e.g., ["authentication", "security", "user_management"]).

This enhanced analysis will be used to inform detailed feature analysis, so provide rich contextual information that will help identify technical requirements and implementation priorities.

Produce a JSON object with exactly these field names. Do not use any other field names. Do not include any explanatory text or markdown formatting outside of the JSON object.

Example format:
{
    "purpose": "User authentication and login",
    "user_context": "Registered users accessing their accounts",
    "business_logic": "Users enter credentials to access personalized content and account features",
    "navigation_role": "Entry point for authenticated users",
    "confidence_score": 0.9,
    "key_workflows": ["user_authentication", "account_access", "session_management"],
    "user_journey_stage": "entry",
    "content_hierarchy": {
        "main_content": "login_form",
        "header": "site_navigation",
        "footer": "support_links"
    },
    "business_importance": 0.8,
    "entry_exit_points": {
        "entry": ["homepage", "product_pages", "checkout_redirect"],
        "exit": ["user_dashboard", "previous_page", "registration_form"]
    },
    "contextual_keywords": ["authentication", "security", "user_credentials", "session_management", "access_control"]
}
"""


def create_content_summary_prompt(page_content: str, dom_structure: dict[str, Any], url: str) -> str:
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

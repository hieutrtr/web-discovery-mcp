"""Prompt definitions for Step 2: Detailed Feature Analysis."""

from legacy_web_mcp.llm.models import ContentSummary

FEATURE_ANALYSIS_SYSTEM_PROMPT = """You are a technical lead analyzing legacy web applications for rebuild planning. Your job is to map every aspect of a web page to understand its interactive elements, features, API integrations, business rules, and technical requirements for rebuilding.

You will receive:
1. The page content and technical artifacts (DOM, interactions, network data)
2. Context from Step 1 analysis (purpose, user context, business logic)
3. Observed behavior data from browser automation

Analyze comprehensively and provide structured JSON output only."""


def create_feature_analysis_prompt(
    page_content: dict,
    step1_context: ContentSummary,
    interactive_elements: list,
    network_requests: list,
    url: str,
) -> str:
    """Creates a comprehensive prompt for Step 2 feature analysis.

    Args:
        page_content: Complete page content data
        step1_context: Results from Step 1 analysis
        interactive_elements: List of interactive elements discovered
        network_requests: List of network requests captured
        url: Page URL being analyzed

    Returns:
        Formatted prompt for Step 2 analysis
    """
    # Build interactive elements summary
    elements_summary = _build_interactive_elements_summary(interactive_elements)

    # Build network requests summary
    network_summary = _build_network_requests_summary(network_requests)

    # Build context summary from Step 1
    context_summary = f"""
PAGE CONTEXT (from Step 1 Analysis):
Purpose: {step1_context.purpose}
User Context: {step1_context.user_context}
Business Logic: {step1_context.business_logic}
Navigation Role: {step1_context.navigation_role}
Business Importance Score: {step1_context.confidence_score:.2f}
"""

    # Truncate visible text if too long
    visible_text = page_content.get("visible_text", "")
    if len(visible_text) > 500:
        text_preview = visible_text[:500] + "..."
    else:
        text_preview = visible_text or "No visible text extracted"

    return f"""Analyze the following web page comprehensively for rebuild planning. This page comes from a {step1_context.business_logic} context with {step1_context.user_context} as target users. 

{context_summary}

TECHNICAL ARTIFACTS:
Interactive Elements Discovered:
{elements_summary}

Network Requests Captured:
{network_summary}

Page Content Overview:
{text_preview}

ANALYSIS REQUIREMENTS:
1. INTERACTIVE ELEMENTS: Map every interactive component (forms, buttons, navigation, controls) with their CSS selectors
2. FUNCTIONAL CAPABILITIES: Identify all CRUD operations, search/filter processes, workflows, state management features
3. API INTEGRATIONS: Document all network requests, endpoints, data flows, and backend dependencies
4. BUSINESS RULES: Extract validation logic, conditional behavior, calculated fields, and business constraints
5. THIRD-PARTY INTEGRATIONS: Identify external services, auth systems, payment processors, analytics, etc.
6. REBUILD PRIORITIES: Rank features by business importance (from Step 1) and technical complexity
7. CONFIDENCE SCORING: Assess analysis completeness and reliability (0.0-1.0)

IMPORTANT: Return ONLY valid JSON matching this exact schema: {{
  "interactive_elements": [
    {{
      "type": "string",
      "selector": "string",
      "purpose": "string", 
      "behavior": "string"
    }}
  ],
  "functional_capabilities": [
    {{
      "name": "string",
      "description": "string",
      "type": "string",
      "complexity_score": "integer (1-10)"
    }}
  ],
  "api_integrations": [
    {{
      "endpoint": "string",
      "method": "string",
      "purpose": "string",
      "data_flow": "string",
      "auth_type": "string|null"
    }}
  ],
  "business_rules": [
    {{
      "name": "string",
      "description": "string",
      "validation_logic": "string",
      "error_handling": "string|null"
    }}
  ],
  "third_party_integrations": [
    {{
      "service_name": "string",
      "integration_type": "string",
      "purpose": "string",
      "auth_method": "string|null"
    }}
  ],
  "rebuild_specifications": [
    {{
      "name": "string",
      "description": "string",
      "priority_score": "float (0.0-1.0)",
      "complexity": "string (low/medium/high)",
      "dependencies": ["string array"]
    }}
  ],
  "confidence_score": "float (0.0-1.0)",
  "quality_score": "float (0.0-1.0)"
}}"""


def _build_interactive_elements_summary(elements: list) -> str:
    """Builds a summary of interactive elements."""
    if not elements:
        return "No interactive elements discovered"

    summary = []
    for elem in elements:
        summary.append(
            f"- {elem.get('type', 'unknown')}: {elem.get('selector', 'unknown')} - {elem.get('purpose', 'unknown')}"
        )

    return "\n".join(summary)


def _build_network_requests_summary(requests: list) -> str:
    """Builds a summary of network requests."""
    if not requests:
        return "No network requests captured"

    summary = []
    for req in requests:
        method = req.get("method", "UNKNOWN")
        url = req.get("url", "unknown")
        status = req.get("status_code", "unknown")
        summary.append(f"- {method} {url} (Status: {status})")

    return "\n".join(summary)

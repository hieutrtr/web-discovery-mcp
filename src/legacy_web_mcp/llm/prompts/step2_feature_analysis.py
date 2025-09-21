"""Prompt definitions for Step 2: Detailed Feature Analysis."""

from legacy_web_mcp.llm.models import ContentSummary, ContextPayload

FEATURE_ANALYSIS_SYSTEM_PROMPT = """You are a technical lead analyzing legacy web applications for rebuild planning with deep contextual understanding. Your job is to map every aspect of a web page to understand its interactive elements, features, API integrations, business rules, and technical requirements while leveraging business context from Step 1 analysis.

You will receive:
1. Rich business context from Step 1 analysis (purpose, workflows, user journey, business importance)
2. Technical artifacts (DOM, interactions, network data, page content)
3. Observed behavior data from browser automation
4. Contextual keywords and workflow dependencies

Your analysis must:
- **Prioritize features based on business importance and user journey impact**
- **Align technical requirements with identified business workflows**
- **Consider user context when analyzing interactive elements**
- **Cross-reference features against business logic and navigation role**
- **Identify workflow dependencies and entry/exit point relationships**
- **Score features for rebuild priority based on business and technical factors**

For each feature/element identified, explain how it relates to the business context and its role in the overall user journey.

Provide structured JSON output with context-aware insights and priority scoring."""


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
    # Create a context payload from the ContentSummary for enhanced analysis
    context_payload = ContextPayload(content_summary=step1_context)

    # Use the context-aware version for richer analysis
    return create_context_aware_feature_analysis_prompt(
        page_content=page_content,
        context_payload=context_payload,
        interactive_elements=interactive_elements,
        network_requests=network_requests,
        url=url
    )


def create_context_aware_feature_analysis_prompt(
    page_content: dict,
    context_payload: ContextPayload,
    interactive_elements: list,
    network_requests: list,
    url: str,
) -> str:
    """Creates a context-aware prompt for Step 2 feature analysis using rich context.

    Args:
        page_content: Complete page content data
        context_payload: Rich context from Step 1 analysis
        interactive_elements: List of interactive elements discovered
        network_requests: List of network requests captured
        url: Page URL being analyzed

    Returns:
        Enhanced prompt with contextual insights for Step 2 analysis
    """
    # Build interactive elements summary
    elements_summary = _build_interactive_elements_summary(interactive_elements)

    # Build network requests summary
    network_summary = _build_network_requests_summary(network_requests)

    # Get business context from payload
    business_context = context_payload.get_business_context()
    workflow_deps = context_payload.get_workflow_dependencies()
    contextual_keywords = context_payload.get_contextual_keywords()

    # Enhanced context summary
    enhanced_context = f"""
BUSINESS CONTEXT & USER JOURNEY ANALYSIS:
{business_context}

WORKFLOW DEPENDENCIES:
Key Workflows: {', '.join(workflow_deps['workflows'])}
Journey Stage: {workflow_deps['journey_stage']}
Entry Points: {', '.join(workflow_deps['entry_points'])}
Exit Points: {', '.join(workflow_deps['exit_points'])}

CONTEXTUAL KEYWORDS FOR ANALYSIS:
{', '.join(contextual_keywords)}

CONTENT HIERARCHY:
{context_payload.content_summary.content_hierarchy}
"""

    # Truncate visible text if too long
    visible_text = page_content.get("visible_text", "")
    text_preview = visible_text[:500] + "..." if len(visible_text) > 500 else visible_text

    return f"""Analyze this web page for rebuild planning with DEEP CONTEXTUAL UNDERSTANDING.

URL: {url}

{enhanced_context}

TECHNICAL ARTIFACTS TO ANALYZE:

Interactive Elements Discovered:
{elements_summary}

Network Requests:
{network_summary}

Page Content (first 500 chars):
{text_preview}

ANALYSIS REQUIREMENTS:

1. **Context-Aware Feature Analysis**: For each interactive element and functional capability:
   - Explain how it relates to the identified business workflows
   - Assess its importance to the user journey stage
   - Consider its role in entry/exit point patterns
   - Rate business importance (0.0-1.0) based on context

2. **Priority Scoring**: For each feature, provide:
   - Business importance (based on workflows and user journey)
   - Technical complexity (implementation difficulty)
   - User impact (effect on user experience)
   - Implementation effort (development time/resources)

3. **Workflow Dependency Mapping**: Identify how features support the key workflows and connect to entry/exit points.

4. **Cross-Reference Validation**: Ensure technical features align with business purpose and user context.

5. **Enhanced JSON Output**: Include context integration score and business alignment summary.

Focus on features that are most critical to the identified workflows: {', '.join(workflow_deps['workflows'])}
Consider the user journey stage: {workflow_deps['journey_stage']}
Prioritize based on business importance: {context_payload.content_summary.business_importance:.2f}

Provide comprehensive JSON analysis with context-aware insights and priority scoring."""


# Keep the original function for backward compatibility
def _create_original_feature_analysis_prompt(
    page_content: dict,
    step1_context: ContentSummary,
    interactive_elements: list,
    network_requests: list,
    url: str,
) -> str:
    """Original implementation - kept for backward compatibility."""
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

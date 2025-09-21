#!/usr/bin/env python3
"""
Usage Example for Story 6.4: High-Level Workflow Orchestration Tools

This script demonstrates how to use the orchestration tools in practice.
It shows the difference between manual tool coordination vs. orchestrated workflows.

Usage:
    python scripts/orchestration_usage_example.py
"""

import asyncio
import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

# Add the src directory to the path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

try:
    from legacy_web_mcp.mcp.server import create_mcp
    from fastmcp import Context
except ImportError as e:
    print(f"❌ Import error: {e}")
    print("Please ensure you're running from the project root and dependencies are installed.")
    sys.exit(1)


async def example_manual_workflow():
    """Example of the old manual way - coordinating many individual tools."""
    print("📝 BEFORE Story 6.4 - Manual Tool Coordination")
    print("=" * 60)
    print("To analyze a legacy website, developers had to manually coordinate 15+ tools:")
    print()

    manual_steps = [
        "1. mcp_call discover_website(url='https://old-app.example.com')",
        "2. mcp_call analyze_site_structure(discovered_urls)",
        "3. mcp_call create_workflow(project_id='legacy-analysis')",
        "4. mcp_call analyze_page_list(selected_urls, include_network=True)",
        "5. mcp_call summarize_page_content(url_1, project_id)",
        "6. mcp_call summarize_page_content(url_2, project_id)",
        "7. mcp_call analyze_page_features(url_1, content_1)",
        "8. mcp_call analyze_page_features(url_2, content_2)",
        "9. mcp_call detect_technologies(url_1)",
        "10. mcp_call detect_technologies(url_2)",
        "11. mcp_call control_workflow(workflow_id, 'status')",
        "12. mcp_call generate_documentation(project_id)",
        "13. ... and many more manual steps"
    ]

    for step in manual_steps:
        print(f"   {step}")
        await asyncio.sleep(0.1)  # Simulate processing time

    print()
    print("❌ Problems with manual coordination:")
    print("   • Required deep knowledge of 15+ individual tools")
    print("   • No intelligent workflow planning")
    print("   • Manual error handling and recovery")
    print("   • No cost optimization")
    print("   • Time-consuming setup for each analysis")
    print("   • Not suitable for conversational AI interfaces")


async def example_orchestrated_workflow():
    """Example of the new orchestrated way with Story 6.4."""
    print("\n🚀 AFTER Story 6.4 - Orchestrated Workflow")
    print("=" * 60)
    print("With orchestration tools, the entire workflow is simplified:")
    print()

    # Create mock context and server
    mock_context = AsyncMock(spec=Context)
    server = create_mcp()
    tools = await server.get_tools()

    print("✨ Single-command site analysis:")
    print()
    print("   mcp_call analyze_legacy_site(")
    print("       url='https://old-app.example.com',")
    print("       analysis_mode='recommended',")
    print("       include_step2=True,")
    print("       interactive_mode=False")
    print("   )")
    print()

    # Simulate the orchestrated workflow with realistic output
    orchestration_steps = [
        "🔍 Phase 1: Discovering site structure...",
        "   → Found 47 pages via sitemap analysis",
        "   → Selected 18 priority pages for analysis",
        "   → Estimated cost: $2.70, time: ~27 minutes",
        "",
        "🧠 Phase 2: Planning analysis strategy...",
        "   → Mode: recommended (balanced depth and cost)",
        "   → Concurrency: 3 browser sessions",
        "   → Step 2 analysis: enabled for pages >75% confidence",
        "",
        "⚡ Phase 3: Executing analysis pipeline...",
        "   → Analyzing batch 1/6: 3 pages (10.5s)",
        "   → Analyzing batch 2/6: 3 pages (12.1s)",
        "   → Analyzing batch 3/6: 3 pages (11.8s)",
        "   → Running Step 2 feature analysis on 16 pages",
        "   → Completed: 18/18 pages successfully analyzed",
        "",
        "📋 Phase 4: Synthesizing results...",
        "   → Technology stack: React 16.8, Express.js, MySQL",
        "   → 47 interactive elements identified",
        "   → 12 API endpoints discovered",
        "   → Modernization priority: Medium (rebuild recommended)",
        "   → Documentation generated: /project/docs/analysis_summary.md"
    ]

    for step in orchestration_steps:
        print(f"   {step}")
        await asyncio.sleep(0.2)  # Simulate processing time

    print()
    print("✅ Benefits of orchestrated workflow:")
    print("   • Single tool call replaces 15+ manual steps")
    print("   • Intelligent site discovery and page prioritization")
    print("   • AI-driven analysis strategy optimization")
    print("   • Built-in error recovery and retry logic")
    print("   • Real-time progress tracking with ETA")
    print("   • Cost-aware analysis with transparent usage")
    print("   • Perfect for conversational AI interfaces")


async def example_ai_recommendations():
    """Example of AI-driven recommendations feature."""
    print("\n🤖 AI-Driven Analysis Recommendations")
    print("=" * 60)
    print("The orchestration tools can automatically select optimal analysis strategies:")
    print()

    ai_examples = [
        {
            "site": "Small business website (8 pages)",
            "recommendation": "comprehensive mode, balanced priority",
            "reasoning": "Small site allows thorough analysis within budget"
        },
        {
            "site": "Large e-commerce platform (200+ pages)",
            "recommendation": "recommended mode, cost-efficient priority",
            "reasoning": "Focus on key pages to manage costs while maintaining quality"
        },
        {
            "site": "Legacy enterprise CRM (50 pages)",
            "recommendation": "targeted mode, balanced priority",
            "reasoning": "Complex business logic requires focused analysis"
        }
    ]

    print("   mcp_call analyze_with_recommendations(url='https://example.com')")
    print()

    for example in ai_examples:
        print(f"   📊 {example['site']}:")
        print(f"      → AI recommendation: {example['recommendation']}")
        print(f"      → Reasoning: {example['reasoning']}")
        print()
        await asyncio.sleep(0.3)


async def example_interactive_mode():
    """Example of interactive mode for human oversight."""
    print("🎯 Interactive Mode for Human Oversight")
    print("=" * 60)
    print("For critical analyses, interactive mode provides checkpoints:")
    print()

    interactive_steps = [
        "📋 **Interactive Mode**: About to analyze 23 pages.",
        "Analysis mode: comprehensive",
        "Cost priority: balanced",
        "Include Step 2: True",
        "Max concurrent: 3",
        "",
        "**Pages to analyze:**",
        "  • https://crm.example.com/",
        "  • https://crm.example.com/login",
        "  • https://crm.example.com/dashboard",
        "  • https://crm.example.com/customers",
        "  • https://crm.example.com/reports",
        "  ... and 18 more",
        "",
        "⏳ Proceeding with analysis in 5 seconds...",
        "",
        "📊 **Phase 3 Complete**: Page analysis finished.",
        "✅ Successfully analyzed: 21 pages",
        "❌ Failed: 2 pages (network timeouts)",
        "🔬 Proceeding to Step 2 feature analysis..."
    ]

    for step in interactive_steps:
        print(f"   {step}")
        await asyncio.sleep(0.2)

    print()
    print("🎛️ Interactive mode features:")
    print("   • Pre-analysis confirmation with cost/time estimates")
    print("   • Real-time progress updates every 30 seconds")
    print("   • Phase completion summaries")
    print("   • User can pause/resume workflows")
    print("   • Error reporting with retry options")


async def example_status_tracking():
    """Example of status tracking and progress monitoring."""
    print("\n📈 Status Tracking and Progress Monitoring")
    print("=" * 60)
    print("Monitor ongoing and completed analyses:")
    print()

    print("   mcp_call get_analysis_status(project_id='legacy-crm-analysis')")
    print()

    status_example = {
        "status": "completed",
        "project_id": "legacy-crm-analysis",
        "analysis_files_found": 23,
        "message": "Analysis complete: 23 pages analyzed",
        "last_activity": "2024-01-15 14:30:22"
    }

    print("   📊 Status Response:")
    for key, value in status_example.items():
        print(f"      {key}: {value}")

    print()
    print("📋 Status tracking features:")
    print("   • Real-time workflow progress")
    print("   • Analysis completion status")
    print("   • File and checkpoint tracking")
    print("   • Error and retry monitoring")
    print("   • Project organization")


async def main():
    """Main demonstration of orchestration tools."""
    print("🎭 Story 6.4: Orchestration Tools Usage Examples")
    print("=" * 70)
    print("This demo shows the transformation from manual tool coordination")
    print("to intelligent workflow orchestration for legacy website analysis.")
    print()

    try:
        await example_manual_workflow()
        await example_orchestrated_workflow()
        await example_ai_recommendations()
        await example_interactive_mode()
        await example_status_tracking()

        print("\n" + "=" * 70)
        print("🎉 Story 6.4 Implementation Summary")
        print("=" * 70)
        print("✅ Complete workflow orchestration implemented")
        print("✅ 3 new high-level tools added to MCP server:")
        print("   • analyze_legacy_site() - Primary orchestration")
        print("   • analyze_with_recommendations() - AI strategy selection")
        print("   • get_analysis_status() - Progress monitoring")
        print("✅ Intelligent analysis planning and cost optimization")
        print("✅ Interactive and YOLO modes for different use cases")
        print("✅ Comprehensive error handling and recovery")
        print("✅ Real-time progress tracking and user communication")
        print("✅ Seamless integration with existing MCP tool ecosystem")
        print()
        print("🚀 Ready for Story 6.5: AI-Driven Site Analysis Workflow")
        print("   Next: Natural language processing and site pattern recognition")

    except KeyboardInterrupt:
        print("\n⏹️  Demo interrupted by user")
    except Exception as e:
        print(f"\n💥 Unexpected error during demo: {e}")


if __name__ == "__main__":
    asyncio.run(main())
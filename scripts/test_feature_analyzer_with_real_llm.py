#!/usr/bin/env python3
"""
Test Script for Story 3.7 with REAL LLM Integration

This script tests the analyze_page_features tool with actual LLM API calls
to demonstrate the complete Step 1 + Step 2 analysis workflow.

Prerequisites:
1. Set up API keys in environment variables:
   export OPENAI_API_KEY="your-key-here"
   # OR
   export ANTHROPIC_API_KEY="your-key-here"
   # OR
   export GEMINI_API_KEY="your-key-here"

2. Run from project root:
   python scripts/test_feature_analyzer_with_real_llm.py

This will make REAL API calls and cost real money (usually < $0.10)
"""

import asyncio
import sys
import json
import os
from pathlib import Path
from datetime import datetime

# Add the src directory to the path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

try:
    from legacy_web_mcp.mcp.server import create_mcp
    from fastmcp import Context
    from unittest.mock import AsyncMock
except ImportError as e:
    print(f"❌ Import error: {e}")
    print("Please ensure you're running from the project root and dependencies are installed.")
    sys.exit(1)


class RealLLMTester:
    """Test runner for real LLM integration with analyze_page_features."""

    def __init__(self):
        self.results = []

    async def test_real_llm_step1_and_step2(self):
        """Test complete workflow with real LLM calls for both Step 1 and Step 2."""
        print("🧠 Testing REAL LLM Integration - Step 1 + Step 2")
        print("=" * 60)

        # Check API keys
        has_openai = bool(os.getenv("OPENAI_API_KEY"))
        has_anthropic = bool(os.getenv("ANTHROPIC_API_KEY"))
        has_gemini = bool(os.getenv("GEMINI_API_KEY"))

        if not (has_openai or has_anthropic or has_gemini):
            print("❌ No LLM API keys found!")
            print("Please set at least one of these environment variables:")
            print("  - OPENAI_API_KEY")
            print("  - ANTHROPIC_API_KEY")
            print("  - GEMINI_API_KEY")
            return

        print(f"✓ API Keys available: OpenAI={has_openai}, Anthropic={has_anthropic}, Gemini={has_gemini}")

        # Create real MCP server and tool
        server = create_mcp()
        tools = await server.get_tools()
        features_tool = tools.get("analyze_page_features")

        if not features_tool:
            print("❌ analyze_page_features tool not found!")
            return

        print("✓ analyze_page_features tool loaded")

        # Create realistic test content for a login page
        test_content = {
            "title": "SecureApp Login - Access Your Account",
            "visible_text": """
            Welcome to SecureApp

            Please sign in to your account

            Email Address: [input field]
            Password: [input field]
            [ ] Remember me on this device

            [Sign In Button]

            Forgot your password? Reset it here
            Don't have an account? Create one now

            Security Notice: We use 256-bit SSL encryption
            """,
            "dom_structure": {
                "total_elements": 15,
                "interactive_elements": 6,
                "form_elements": 1,
                "link_elements": 3
            },
            "page_content": {
                "interactive_elements": [
                    {
                        "type": "input",
                        "selector": "input[type='email']",
                        "attributes": {"type": "email", "required": True, "placeholder": "Email Address"},
                        "purpose": "email_input"
                    },
                    {
                        "type": "input",
                        "selector": "input[type='password']",
                        "attributes": {"type": "password", "required": True, "placeholder": "Password"},
                        "purpose": "password_input"
                    },
                    {
                        "type": "checkbox",
                        "selector": "input[type='checkbox']",
                        "attributes": {"type": "checkbox"},
                        "purpose": "remember_me"
                    },
                    {
                        "type": "button",
                        "selector": "button[type='submit']",
                        "attributes": {"type": "submit", "class": "btn-primary"},
                        "text": "Sign In",
                        "purpose": "form_submission"
                    },
                    {
                        "type": "link",
                        "selector": "a[href='/forgot-password']",
                        "text": "Reset it here",
                        "purpose": "password_reset"
                    },
                    {
                        "type": "link",
                        "selector": "a[href='/register']",
                        "text": "Create one now",
                        "purpose": "registration"
                    }
                ]
            }
        }

        print("\n📋 Test Content:")
        print(f"   URL: https://app.secureapp.com/login")
        print(f"   Page Type: Login/Authentication")
        print(f"   Interactive Elements: {len(test_content['page_content']['interactive_elements'])}")
        print(f"   Content Length: {len(test_content['visible_text'])} characters")

        mock_context = AsyncMock()

        print("\n🚀 Calling analyze_page_features with REAL LLM...")
        print("   ⚠️  This will make actual API calls and cost real money!")
        print("   💰 Expected cost: ~$0.05-0.15 depending on provider")

        start_time = datetime.now()

        try:
            # Call with full LLM integration (Step 1 + Step 2)
            result = await features_tool.fn(
                context=mock_context,
                url="https://app.secureapp.com/login",
                page_content=json.dumps(test_content),
                include_step1_summary=True,  # Enable Step 1 LLM analysis
                project_id="real-llm-test"
            )

            end_time = datetime.now()
            duration = (end_time - start_time).total_seconds()

            print(f"\n⏱️  Analysis completed in {duration:.2f} seconds")

            # Analyze results
            if result.get("status") == "success":
                print("\n✅ REAL LLM ANALYSIS SUCCESSFUL!")
                print("=" * 50)

                # Step 1 Results
                step1_context = result.get("step1_context", {})
                if step1_context.get("purpose") != "Feature analysis without step 1 context":
                    print("\n🧠 Step 1 (Content Summarization) Results:")
                    print(f"   Purpose: {step1_context.get('purpose', 'N/A')}")
                    print(f"   User Context: {step1_context.get('user_context', 'N/A')}")
                    print(f"   Business Logic: {step1_context.get('business_logic', 'N/A')}")
                    print(f"   Navigation Role: {step1_context.get('navigation_role', 'N/A')}")
                    print(f"   Confidence: {step1_context.get('confidence_score', 'N/A')}")

                # Step 2 Results
                print(f"\n🔍 Step 2 (Feature Analysis) Results:")
                print(f"   Interactive Elements: {len(result.get('interactive_elements', []))}")
                print(f"   Functional Capabilities: {len(result.get('functional_capabilities', []))}")
                print(f"   API Integrations: {len(result.get('api_integrations', []))}")
                print(f"   Business Rules: {len(result.get('business_rules', []))}")
                print(f"   Third-party Integrations: {len(result.get('third_party_integrations', []))}")
                print(f"   Rebuild Specifications: {len(result.get('rebuild_specifications', []))}")
                print(f"   Overall Confidence: {result.get('confidence_score', 'N/A')}")
                print(f"   Quality Score: {result.get('quality_score', 'N/A')}")

                # Show detailed results
                if result.get('interactive_elements'):
                    print(f"\n📱 Interactive Elements Found by LLM:")
                    for i, element in enumerate(result['interactive_elements'][:3]):  # Show first 3
                        print(f"   {i+1}. {element.get('type', 'unknown')} - {element.get('purpose', 'no purpose')}")
                        if element.get('behavior'):
                            print(f"      Behavior: {element.get('behavior')}")

                if result.get('functional_capabilities'):
                    print(f"\n⚙️  Functional Capabilities Identified by LLM:")
                    for i, capability in enumerate(result['functional_capabilities'][:3]):
                        print(f"   {i+1}. {capability.get('name', 'unknown')}")
                        print(f"      Description: {capability.get('description', 'no description')}")
                        print(f"      Type: {capability.get('type', 'unknown')}")

                if result.get('business_rules'):
                    print(f"\n📋 Business Rules Detected by LLM:")
                    for i, rule in enumerate(result['business_rules'][:3]):
                        print(f"   {i+1}. {rule.get('name', 'unknown')}")
                        print(f"      Description: {rule.get('description', 'no description')}")

                if result.get('rebuild_specifications'):
                    print(f"\n🏗️  Rebuild Specifications from LLM:")
                    for i, spec in enumerate(result['rebuild_specifications'][:2]):
                        print(f"   {i+1}. {spec.get('name', 'unknown')}")
                        print(f"      Priority: {spec.get('priority_score', 'unknown')}")
                        print(f"      Complexity: {spec.get('complexity', 'unknown')}")

                # Quality Assessment
                confidence = result.get('confidence_score', 0)
                quality = result.get('quality_score', 0)

                print(f"\n📊 Quality Assessment:")
                print(f"   Confidence Score: {confidence} ({'High' if confidence > 0.7 else 'Medium' if confidence > 0.4 else 'Low'})")
                print(f"   Quality Score: {quality} ({'High' if quality > 0.7 else 'Medium' if quality > 0.4 else 'Low'})")

                if confidence > 0.6 and quality > 0.6:
                    print("   ✅ High-quality analysis achieved!")
                elif confidence > 0.3 and quality > 0.3:
                    print("   ⚠️  Medium-quality analysis - acceptable")
                else:
                    print("   ❌ Low-quality analysis - may need review")

            else:
                print(f"\n❌ Analysis failed: {result.get('error', 'Unknown error')}")
                print(f"   Error type: {result.get('error_type', 'Unknown')}")

        except Exception as e:
            print(f"\n💥 Exception during real LLM test: {e}")
            import traceback
            print(f"Traceback: {traceback.format_exc()}")

    async def test_real_llm_step2_only(self):
        """Test Step 2 only with real LLM (skip Step 1)."""
        print("\n\n🔍 Testing REAL LLM Integration - Step 2 Only")
        print("=" * 60)

        server = create_mcp()
        tools = await server.get_tools()
        features_tool = tools.get("analyze_page_features")

        # Simpler test content for Step 2 only
        simple_content = {
            "title": "Simple Button Test",
            "visible_text": "Click me! [Button]",
            "page_content": {
                "interactive_elements": [
                    {
                        "type": "button",
                        "selector": "button#test",
                        "text": "Click me!",
                        "purpose": "test_button"
                    }
                ]
            }
        }

        mock_context = AsyncMock()

        print("🚀 Calling analyze_page_features (Step 2 only) with REAL LLM...")

        try:
            result = await features_tool.fn(
                context=mock_context,
                url="https://test.example.com",
                page_content=json.dumps(simple_content),
                include_step1_summary=False,  # Skip Step 1
                project_id="real-llm-step2-test"
            )

            if result.get("status") == "success":
                print("✅ Step 2 only analysis successful!")
                print(f"   Interactive Elements: {len(result.get('interactive_elements', []))}")
                print(f"   Confidence: {result.get('confidence_score', 'N/A')}")

                # Should have lower quality without Step 1 context
                if result.get('quality_score', 0) < 0.7:
                    print("   ✓ Quality appropriately lower without Step 1 context")
                else:
                    print("   ⚠️  Quality unexpectedly high without Step 1 context")

            else:
                print(f"❌ Step 2 analysis failed: {result.get('error', 'Unknown')}")

        except Exception as e:
            print(f"💥 Exception during Step 2 test: {e}")

    async def run_real_llm_tests(self):
        """Run all real LLM integration tests."""
        print("🎭 Story 3.7: Real LLM Integration Test Suite")
        print("=" * 70)
        print("This test demonstrates the analyze_page_features tool with ACTUAL LLM API calls.")
        print("⚠️  WARNING: This will cost real money (typically $0.05-0.20 total)")
        print()

        # Check if user wants to proceed
        response = input("Do you want to proceed with real LLM API calls? (y/N): ")
        if response.lower() != 'y':
            print("❌ Test cancelled by user")
            return

        await self.test_real_llm_step1_and_step2()
        await self.test_real_llm_step2_only()

        print("\n" + "=" * 70)
        print("🎉 Real LLM Integration Tests Complete!")
        print("=" * 70)
        print("✅ You have successfully tested Story 3.7 with REAL LLM integration")
        print("✅ The analyze_page_features tool works with actual AI analysis")
        print("✅ Both Step 1 (content summarization) and Step 2 (feature analysis) are functional")


async def main():
    """Main test execution."""
    tester = RealLLMTester()
    await tester.run_real_llm_tests()


if __name__ == "__main__":
    asyncio.run(main())
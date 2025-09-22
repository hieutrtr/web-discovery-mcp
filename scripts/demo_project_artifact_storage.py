#!/usr/bin/env python3
"""Demo script for comprehensive artifact storage in project folder.

This script demonstrates the complete workflow of:
1. Creating a project with web discovery documentation structure
2. Running analysis on multiple pages
3. Organizing artifacts into the project documentation
4. Generating comprehensive reports
5. Exposing resources via MCP for AI tools

Usage:
    python scripts/demo_project_artifact_storage.py [project_path]

Examples:
    python scripts/demo_project_artifact_storage.py /path/to/my-ecommerce-rebuild
    python scripts/demo_project_artifact_storage.py ./demo-project
"""

import asyncio
import json
import sys
import tempfile
from datetime import datetime, UTC
from pathlib import Path
from typing import Dict, Any, List

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from fastmcp import Context

# Import file management components
from legacy_web_mcp.file_management.organizer import ProjectArtifactOrganizer
from legacy_web_mcp.llm.artifacts import ArtifactManager, AnalysisArtifact
from legacy_web_mcp.mcp.file_management_tools import (
    setup_project_documentation_structure,
    organize_project_artifacts,
    generate_master_analysis_report,
    list_project_documentation_files,
    create_gitignore_for_web_discovery
)
from legacy_web_mcp.mcp.resources import WebDiscoveryResourceProvider, add_project_resources


class SimpleContext:
    """Simple context for testing without full MCP session."""

    async def info(self, message: str) -> None:
        print(f"[INFO] {message}")

    async def error(self, message: str) -> None:
        print(f"[ERROR] {message}")

    async def warn(self, message: str) -> None:
        print(f"[WARN] {message}")


def create_comprehensive_sample_artifacts(project_id: str) -> List[AnalysisArtifact]:
    """Create comprehensive sample analysis artifacts for a realistic e-commerce site.

    Args:
        project_id: Project identifier for the artifacts

    Returns:
        List of analysis artifacts representing a complete site analysis
    """
    artifacts = []

    # Homepage - Content Summary
    artifacts.append(AnalysisArtifact(
        analysis_type="step1",
        page_url="https://modernshop.example.com/",
        timestamp=datetime.now(UTC),
        project_id=project_id,
        step1_result={
            "purpose": "E-commerce homepage showcasing products, brand, and navigation entry point",
            "user_context": "New and returning customers seeking products and brand information",
            "business_logic": "Product discovery, brand presentation, promotional campaigns, user onboarding",
            "navigation_role": "Primary entry point with global navigation and category access",
            "business_importance": 0.98,
            "confidence_score": 0.95,
            "key_workflows": ["product_browsing", "search", "category_navigation", "account_login", "promotional_discovery"],
            "user_journey_stage": "entry",
            "contextual_keywords": ["ecommerce", "homepage", "products", "shopping", "deals", "categories"]
        },
        quality_metrics={
            "overall_quality_score": 0.95,
            "completeness_score": 0.93,
            "technical_depth_score": 0.89
        },
        metadata={
            "page_title": "ModernShop - Premium E-commerce Experience",
            "analysis_status": "completed",
            "processing_time": 3.2,
            "page_type": "homepage"
        },
        status="completed"
    ))

    # Homepage - Feature Analysis
    artifacts.append(AnalysisArtifact(
        analysis_type="step2",
        page_url="https://modernshop.example.com/",
        timestamp=datetime.now(UTC),
        project_id=project_id,
        step2_result={
            "interactive_elements": [
                {
                    "type": "form",
                    "selector": "#search-form",
                    "purpose": "Global product search with autocomplete and filters",
                    "behavior": "submit"
                },
                {
                    "type": "button",
                    "selector": ".category-nav-btn",
                    "purpose": "Navigate to product categories",
                    "behavior": "click"
                },
                {
                    "type": "carousel",
                    "selector": ".featured-products-carousel",
                    "purpose": "Showcase featured and trending products",
                    "behavior": "swipe"
                },
                {
                    "type": "button",
                    "selector": ".account-menu-toggle",
                    "purpose": "Access user account menu and authentication",
                    "behavior": "click"
                },
                {
                    "type": "modal",
                    "selector": ".newsletter-signup-modal",
                    "purpose": "Email subscription for marketing campaigns",
                    "behavior": "form_submit"
                }
            ],
            "functional_capabilities": [
                {
                    "name": "Advanced Product Search",
                    "description": "Full-text search with autocomplete, filters, and category suggestions",
                    "type": "feature",
                    "complexity_score": 0.8
                },
                {
                    "name": "User Authentication System",
                    "description": "Complete user management with social login and account features",
                    "type": "service",
                    "complexity_score": 0.6
                },
                {
                    "name": "Dynamic Product Recommendations",
                    "description": "AI-powered product recommendations based on user behavior",
                    "type": "feature",
                    "complexity_score": 0.9
                },
                {
                    "name": "Shopping Cart Management",
                    "description": "Persistent cart with session management and guest checkout",
                    "type": "feature",
                    "complexity_score": 0.7
                },
                {
                    "name": "Newsletter Marketing Integration",
                    "description": "Email marketing automation with segmentation",
                    "type": "service",
                    "complexity_score": 0.5
                }
            ],
            "api_integrations": [
                {
                    "endpoint": "/api/v1/search/products",
                    "method": "GET",
                    "purpose": "Product search with advanced filtering and pagination",
                    "data_flow": "client-to-server",
                    "auth_type": "optional"
                },
                {
                    "endpoint": "/api/v1/auth/login",
                    "method": "POST",
                    "purpose": "User authentication with JWT token generation",
                    "data_flow": "client-to-server",
                    "auth_type": "none"
                },
                {
                    "endpoint": "/api/v1/recommendations/trending",
                    "method": "GET",
                    "purpose": "Fetch trending and recommended products for homepage",
                    "data_flow": "server-to-client",
                    "auth_type": "optional"
                },
                {
                    "endpoint": "/api/v1/cart/session",
                    "method": "GET",
                    "purpose": "Retrieve current user's shopping cart state",
                    "data_flow": "server-to-client",
                    "auth_type": "required"
                }
            ],
            "business_rules": [
                {
                    "name": "Search Query Validation",
                    "description": "Validate and sanitize search queries for security and performance",
                    "validation_logic": "Minimum 2 characters, maximum 100 characters, sanitize special characters"
                },
                {
                    "name": "Featured Product Selection",
                    "description": "Algorithm for selecting products to feature on homepage",
                    "validation_logic": "Priority: trending > high-margin > seasonal > new-arrivals"
                }
            ],
            "rebuild_specifications": [
                {
                    "name": "Homepage Hero Component",
                    "description": "React component for main homepage banner with dynamic content",
                    "priority_score": 0.95,
                    "complexity": "medium",
                    "dependencies": ["content-management-api", "image-optimization"]
                },
                {
                    "name": "Product Search Interface",
                    "description": "Advanced search component with autocomplete and filtering",
                    "priority_score": 0.90,
                    "complexity": "high",
                    "dependencies": ["search-service", "elasticsearch", "autocomplete-service"]
                }
            ]
        },
        quality_metrics={
            "overall_quality_score": 0.92,
            "completeness_score": 0.90,
            "technical_depth_score": 0.88
        },
        metadata={
            "page_title": "ModernShop - Premium E-commerce Experience",
            "analysis_status": "completed",
            "processing_time": 5.7,
            "page_type": "homepage"
        },
        status="completed"
    ))

    # Product Detail Page - Content Summary
    artifacts.append(AnalysisArtifact(
        analysis_type="step1",
        page_url="https://modernshop.example.com/products/premium-wireless-headphones-pro",
        timestamp=datetime.now(UTC),
        project_id=project_id,
        step1_result={
            "purpose": "Detailed product presentation for purchase decision and conversion",
            "user_context": "Customers evaluating specific product for purchase decision",
            "business_logic": "Product showcase, specifications, reviews, purchase flow, cross-selling",
            "navigation_role": "Product catalog leaf page with breadcrumb navigation",
            "business_importance": 0.92,
            "confidence_score": 0.94,
            "key_workflows": ["product_viewing", "add_to_cart", "checkout", "review_reading", "comparison"],
            "user_journey_stage": "conversion",
            "contextual_keywords": ["product", "details", "specifications", "reviews", "purchase", "wireless", "headphones"]
        },
        quality_metrics={
            "overall_quality_score": 0.94,
            "completeness_score": 0.92,
            "technical_depth_score": 0.91
        },
        metadata={
            "page_title": "Premium Wireless Headphones Pro - ModernShop",
            "analysis_status": "completed",
            "processing_time": 3.1,
            "page_type": "product_detail"
        },
        status="completed"
    ))

    # Product Detail Page - Feature Analysis
    artifacts.append(AnalysisArtifact(
        analysis_type="step2",
        page_url="https://modernshop.example.com/products/premium-wireless-headphones-pro",
        timestamp=datetime.now(UTC),
        project_id=project_id,
        step2_result={
            "interactive_elements": [
                {
                    "type": "gallery",
                    "selector": ".product-image-gallery",
                    "purpose": "Interactive product image gallery with zoom and 360° view",
                    "behavior": "click_zoom"
                },
                {
                    "type": "select",
                    "selector": "#variant-selector",
                    "purpose": "Select product variants (color, size, model)",
                    "behavior": "change"
                },
                {
                    "type": "button",
                    "selector": ".add-to-cart-btn",
                    "purpose": "Add product to shopping cart with selected options",
                    "behavior": "click"
                },
                {
                    "type": "tabs",
                    "selector": ".product-info-tabs",
                    "purpose": "Navigate between specifications, reviews, shipping info",
                    "behavior": "tab_switch"
                },
                {
                    "type": "form",
                    "selector": ".review-form",
                    "purpose": "Submit product review and rating",
                    "behavior": "submit"
                }
            ],
            "functional_capabilities": [
                {
                    "name": "Product Variant Management",
                    "description": "Handle multiple product variants with dynamic pricing and inventory",
                    "type": "feature",
                    "complexity_score": 0.7
                },
                {
                    "name": "Review and Rating System",
                    "description": "User-generated reviews with ratings, images, and moderation",
                    "type": "feature",
                    "complexity_score": 0.6
                },
                {
                    "name": "Inventory Tracking",
                    "description": "Real-time inventory management with stock notifications",
                    "type": "service",
                    "complexity_score": 0.8
                },
                {
                    "name": "Related Products Engine",
                    "description": "Cross-selling and upselling product recommendations",
                    "type": "feature",
                    "complexity_score": 0.7
                }
            ],
            "api_integrations": [
                {
                    "endpoint": "/api/v1/products/{product_id}",
                    "method": "GET",
                    "purpose": "Retrieve detailed product information and variants",
                    "data_flow": "server-to-client",
                    "auth_type": "none"
                },
                {
                    "endpoint": "/api/v1/inventory/check",
                    "method": "POST",
                    "purpose": "Check product availability and inventory levels",
                    "data_flow": "client-to-server",
                    "auth_type": "none"
                },
                {
                    "endpoint": "/api/v1/cart/add",
                    "method": "POST",
                    "purpose": "Add product with variants to user's shopping cart",
                    "data_flow": "client-to-server",
                    "auth_type": "optional"
                },
                {
                    "endpoint": "/api/v1/reviews/{product_id}",
                    "method": "GET",
                    "purpose": "Fetch product reviews and ratings with pagination",
                    "data_flow": "server-to-client",
                    "auth_type": "none"
                }
            ],
            "business_rules": [
                {
                    "name": "Inventory Validation",
                    "description": "Ensure product availability before allowing cart addition",
                    "validation_logic": "Check current inventory >= requested quantity + safety buffer"
                },
                {
                    "name": "Dynamic Pricing",
                    "description": "Calculate final price including discounts and promotions",
                    "validation_logic": "Base price - bulk discounts - promotional codes - member discounts"
                },
                {
                    "name": "Review Authenticity",
                    "description": "Validate reviews are from verified purchasers",
                    "validation_logic": "Require purchase verification for review submission"
                }
            ],
            "rebuild_specifications": [
                {
                    "name": "Product Detail Container",
                    "description": "Comprehensive product display component with all features",
                    "priority_score": 0.88,
                    "complexity": "high",
                    "dependencies": ["product-api", "inventory-service", "image-service", "review-system"]
                }
            ]
        },
        quality_metrics={
            "overall_quality_score": 0.90,
            "completeness_score": 0.89,
            "technical_depth_score": 0.92
        },
        metadata={
            "page_title": "Premium Wireless Headphones Pro - ModernShop",
            "analysis_status": "completed",
            "processing_time": 4.9,
            "page_type": "product_detail"
        },
        status="completed"
    ))

    # Category Page - Content Summary
    artifacts.append(AnalysisArtifact(
        analysis_type="step1",
        page_url="https://modernshop.example.com/categories/electronics/audio",
        timestamp=datetime.now(UTC),
        project_id=project_id,
        step1_result={
            "purpose": "Product category browsing with filtering and sorting capabilities",
            "user_context": "Customers browsing specific product category for comparison shopping",
            "business_logic": "Category navigation, product filtering, comparison, discovery",
            "navigation_role": "Category landing page with subcategory navigation",
            "business_importance": 0.85,
            "confidence_score": 0.88,
            "key_workflows": ["category_browsing", "product_filtering", "product_comparison", "sorting"],
            "user_journey_stage": "middle",
            "contextual_keywords": ["category", "electronics", "audio", "filtering", "sorting", "browsing"]
        },
        quality_metrics={
            "overall_quality_score": 0.88,
            "completeness_score": 0.86,
            "technical_depth_score": 0.84
        },
        metadata={
            "page_title": "Audio Equipment - Electronics | ModernShop",
            "analysis_status": "completed",
            "processing_time": 2.8,
            "page_type": "category"
        },
        status="completed"
    ))

    # Category Page - Feature Analysis
    artifacts.append(AnalysisArtifact(
        analysis_type="step2",
        page_url="https://modernshop.example.com/categories/electronics/audio",
        timestamp=datetime.now(UTC),
        project_id=project_id,
        step2_result={
            "interactive_elements": [
                {
                    "type": "filter_panel",
                    "selector": ".category-filters",
                    "purpose": "Filter products by price, brand, features, ratings",
                    "behavior": "checkbox_select"
                },
                {
                    "type": "dropdown",
                    "selector": ".sort-dropdown",
                    "purpose": "Sort products by relevance, price, rating, date",
                    "behavior": "select"
                },
                {
                    "type": "grid",
                    "selector": ".product-grid",
                    "purpose": "Display products in responsive grid layout",
                    "behavior": "infinite_scroll"
                },
                {
                    "type": "pagination",
                    "selector": ".pagination-controls",
                    "purpose": "Navigate through multiple pages of products",
                    "behavior": "click"
                }
            ],
            "functional_capabilities": [
                {
                    "name": "Advanced Product Filtering",
                    "description": "Multi-criteria filtering with faceted search capabilities",
                    "type": "feature",
                    "complexity_score": 0.8
                },
                {
                    "name": "Product Comparison Tool",
                    "description": "Side-by-side product comparison with specifications",
                    "type": "feature",
                    "complexity_score": 0.6
                },
                {
                    "name": "Infinite Scroll Loading",
                    "description": "Progressive product loading for better performance",
                    "type": "feature",
                    "complexity_score": 0.5
                }
            ],
            "api_integrations": [
                {
                    "endpoint": "/api/v1/categories/{category_id}/products",
                    "method": "GET",
                    "purpose": "Retrieve products for category with filtering and pagination",
                    "data_flow": "server-to-client",
                    "auth_type": "none"
                },
                {
                    "endpoint": "/api/v1/filters/options",
                    "method": "GET",
                    "purpose": "Get available filter options for current category",
                    "data_flow": "server-to-client",
                    "auth_type": "none"
                }
            ],
            "business_rules": [
                {
                    "name": "Filter Performance",
                    "description": "Optimize filter queries for fast response times",
                    "validation_logic": "Use indexed fields, limit concurrent filters, cache results"
                }
            ],
            "rebuild_specifications": [
                {
                    "name": "Category Browsing Interface",
                    "description": "Complete category page with filtering and product display",
                    "priority_score": 0.82,
                    "complexity": "medium",
                    "dependencies": ["search-api", "product-service", "filter-engine"]
                }
            ]
        },
        quality_metrics={
            "overall_quality_score": 0.85,
            "completeness_score": 0.83,
            "technical_depth_score": 0.87
        },
        metadata={
            "page_title": "Audio Equipment - Electronics | ModernShop",
            "analysis_status": "completed",
            "processing_time": 3.5,
            "page_type": "category"
        },
        status="completed"
    ))

    # Checkout Page - Content Summary
    artifacts.append(AnalysisArtifact(
        analysis_type="step1",
        page_url="https://modernshop.example.com/checkout",
        timestamp=datetime.now(UTC),
        project_id=project_id,
        step1_result={
            "purpose": "Complete purchase transaction with payment and shipping details",
            "user_context": "Customers ready to complete purchase with payment information",
            "business_logic": "Order processing, payment handling, shipping calculation, order confirmation",
            "navigation_role": "Conversion funnel page with minimal navigation to reduce abandonment",
            "business_importance": 0.99,
            "confidence_score": 0.97,
            "key_workflows": ["checkout_process", "payment_processing", "shipping_selection", "order_confirmation"],
            "user_journey_stage": "conversion",
            "contextual_keywords": ["checkout", "payment", "shipping", "order", "confirmation", "billing"]
        },
        quality_metrics={
            "overall_quality_score": 0.97,
            "completeness_score": 0.95,
            "technical_depth_score": 0.94
        },
        metadata={
            "page_title": "Secure Checkout - ModernShop",
            "analysis_status": "completed",
            "processing_time": 4.2,
            "page_type": "checkout"
        },
        status="completed"
    ))

    # Checkout Page - Feature Analysis
    artifacts.append(AnalysisArtifact(
        analysis_type="step2",
        page_url="https://modernshop.example.com/checkout",
        timestamp=datetime.now(UTC),
        project_id=project_id,
        step2_result={
            "interactive_elements": [
                {
                    "type": "form",
                    "selector": "#checkout-form",
                    "purpose": "Collect billing, shipping, and payment information",
                    "behavior": "multi_step_submit"
                },
                {
                    "type": "payment_widget",
                    "selector": ".payment-methods",
                    "purpose": "Handle multiple payment methods securely",
                    "behavior": "secure_input"
                },
                {
                    "type": "address_autocomplete",
                    "selector": ".address-input",
                    "purpose": "Auto-complete shipping and billing addresses",
                    "behavior": "autocomplete"
                },
                {
                    "type": "order_summary",
                    "selector": ".order-summary",
                    "purpose": "Display order details, taxes, and total cost",
                    "behavior": "dynamic_update"
                }
            ],
            "functional_capabilities": [
                {
                    "name": "Secure Payment Processing",
                    "description": "PCI-compliant payment handling with multiple payment methods",
                    "type": "service",
                    "complexity_score": 0.9
                },
                {
                    "name": "Address Validation",
                    "description": "Real-time address validation and autocomplete",
                    "type": "service",
                    "complexity_score": 0.6
                },
                {
                    "name": "Tax Calculation",
                    "description": "Dynamic tax calculation based on shipping location",
                    "type": "service",
                    "complexity_score": 0.7
                },
                {
                    "name": "Order Management",
                    "description": "Order creation, tracking, and status management",
                    "type": "service",
                    "complexity_score": 0.8
                }
            ],
            "api_integrations": [
                {
                    "endpoint": "/api/v1/checkout/validate",
                    "method": "POST",
                    "purpose": "Validate checkout data before payment processing",
                    "data_flow": "client-to-server",
                    "auth_type": "required"
                },
                {
                    "endpoint": "/api/v1/payment/process",
                    "method": "POST",
                    "purpose": "Process payment through secure payment gateway",
                    "data_flow": "client-to-server",
                    "auth_type": "required"
                },
                {
                    "endpoint": "/api/v1/orders/create",
                    "method": "POST",
                    "purpose": "Create order record after successful payment",
                    "data_flow": "client-to-server",
                    "auth_type": "required"
                },
                {
                    "endpoint": "/api/v1/shipping/calculate",
                    "method": "POST",
                    "purpose": "Calculate shipping costs and delivery options",
                    "data_flow": "client-to-server",
                    "auth_type": "required"
                }
            ],
            "business_rules": [
                {
                    "name": "Payment Security",
                    "description": "Ensure PCI compliance and secure payment processing",
                    "validation_logic": "SSL encryption, tokenization, fraud detection, 3D Secure"
                },
                {
                    "name": "Inventory Reserve",
                    "description": "Reserve inventory during checkout process",
                    "validation_logic": "Hold inventory for 15 minutes during checkout"
                },
                {
                    "name": "Tax Compliance",
                    "description": "Calculate taxes according to local regulations",
                    "validation_logic": "Apply correct tax rates based on shipping address and product type"
                }
            ],
            "rebuild_specifications": [
                {
                    "name": "Secure Checkout Flow",
                    "description": "Complete checkout process with payment integration",
                    "priority_score": 0.99,
                    "complexity": "high",
                    "dependencies": ["payment-gateway", "tax-service", "shipping-api", "order-service", "fraud-detection"]
                }
            ]
        },
        quality_metrics={
            "overall_quality_score": 0.94,
            "completeness_score": 0.92,
            "technical_depth_score": 0.96
        },
        metadata={
            "page_title": "Secure Checkout - ModernShop",
            "analysis_status": "completed",
            "processing_time": 6.1,
            "page_type": "checkout"
        },
        status="completed"
    ))

    return artifacts


async def demo_comprehensive_artifact_storage(project_path: str):
    """Demonstrate comprehensive artifact storage in a project folder.

    Args:
        project_path: Path to the project directory
    """
    print("=" * 80)
    print("🏗️  COMPREHENSIVE PROJECT ARTIFACT STORAGE DEMO")
    print("=" * 80)
    print()

    context = SimpleContext()

    # Project configuration with unique ID to avoid duplicates
    import time
    project_name = "ModernShop E-commerce Rebuild"
    website_url = "https://modernshop.example.com"
    project_id = f"modernshop-rebuild-{int(time.time())}"

    print(f"📁 Project Path: {project_path}")
    print(f"🏪 Project Name: {project_name}")
    print(f"🌐 Website URL: {website_url}")
    print(f"🔖 Project ID: {project_id}")
    print()

    # Step 1: Setup project documentation structure
    print("🏗️  Step 1: Setting up project documentation structure...")
    setup_result = await setup_project_documentation_structure(
        context=context,
        project_root=project_path,
        project_name=project_name,
        website_url=website_url
    )

    if setup_result['status'] != 'success':
        print(f"❌ Setup failed: {setup_result['error']}")
        return

    print(f"✅ Documentation structure created at: {setup_result['docs_root']}")
    print(f"   📁 Created {len(setup_result['folders_created'])} folders")
    print()

    # Step 2: Create and store comprehensive analysis artifacts
    print("🔬 Step 2: Creating comprehensive analysis artifacts...")

    # Initialize artifact manager and create artifacts
    artifact_manager = ArtifactManager()
    artifacts = create_comprehensive_sample_artifacts(project_id)

    print(f"📊 Created {len(artifacts)} analysis artifacts:")

    # Save each artifact to the artifact system
    for artifact in artifacts:
        # Save the artifact
        artifact_manager._save_artifact(artifact)
        artifact_manager.complete_artifact(artifact, "completed")

        print(f"   💾 {artifact.analysis_type}: {artifact.page_url}")
        print(f"      📄 {artifact.metadata.get('page_title', 'Unknown Title')}")
        print(f"      ⭐ Quality: {artifact.quality_metrics['overall_quality_score']:.1%}")

    print(f"✅ All artifacts saved to artifact system")
    print()

    # Step 3: Organize artifacts into project documentation
    print("📂 Step 3: Organizing artifacts into project documentation...")
    organize_result = await organize_project_artifacts(
        context=context,
        project_root=project_path,
        project_id=project_id,
        project_name=project_name,
        website_url=website_url
    )

    if organize_result['status'] != 'success':
        print(f"❌ Organization failed: {organize_result['error']}")
        return

    print(f"✅ Organized {organize_result['artifacts_processed']} artifacts")
    print(f"   📝 Created {organize_result['page_files_written']} page files")
    print(f"   📈 Average quality score: {organize_result['quality_score']:.1%}")
    print(f"   📊 Analysis status: {organize_result['analysis_status']}")
    print()

    # Step 4: Generate master analysis report
    print("📋 Step 4: Generating master analysis report...")
    report_result = await generate_master_analysis_report(
        context=context,
        project_root=project_path,
        project_id=project_id,
        project_name=project_name,
        include_technical_specs=True,
        include_debug_info=False
    )

    if report_result['status'] != 'success':
        print(f"❌ Report generation failed: {report_result['error']}")
        return

    print(f"✅ Master report generated: {report_result['master_report_path']}")
    print(f"   📏 Content length: {report_result['content_length']:,} characters")
    print(f"   📑 Sections: {report_result['sections_generated']}")

    summary = report_result['project_summary']
    print(f"   📊 Analysis summary:")
    print(f"      🌐 Pages analyzed: {summary['total_pages']}")
    print(f"      ⚙️  Features identified: {summary['features_identified']}")
    print(f"      🔗 API endpoints: {summary['api_endpoints']}")
    print(f"      🎯 Complexity: {summary['complexity']}")
    print()

    # Step 5: Create version control guidance
    print("🔄 Step 5: Creating version control guidance...")
    vcs_result = await create_gitignore_for_web_discovery(
        context=context,
        project_root=project_path,
        exclude_progress=True,
        exclude_large_reports=False
    )

    if vcs_result['status'] == 'success':
        print(f"✅ Version control guidance created")
        print(f"   📄 .gitignore: {vcs_result['action']}")
        print(f"   📚 Guidance document: {Path(vcs_result['guidance_path']).name}")
    print()

    # Step 6: List all documentation files
    print("📋 Step 6: Listing project documentation files...")
    list_result = await list_project_documentation_files(
        context=context,
        project_root=project_path
    )

    if list_result['status'] == 'success':
        file_info = list_result['file_info']
        structure = list_result['file_listing']['structure']

        print("📁 Project documentation structure:")
        print(f"   📄 analysis-metadata.json ({file_info.get('metadata', {}).get('size', 0):,} bytes)")
        print(f"   📊 analysis-report.md ({file_info.get('master_report', {}).get('size', 0):,} bytes)")
        print(f"   📁 pages/ ({len(structure['pages'])} files)")

        for page_file in structure['pages']:
            page_name = Path(page_file).name
            print(f"      📄 {page_name}")

        print(f"   📁 progress/ ({len(structure['progress'])} files)")
        print(f"   📁 reports/ ({len(structure['reports'])} files)")
    print()

    # Step 7: Setup MCP resources
    print("🔗 Step 7: Setting up MCP resources for AI tool access...")
    try:
        # Add project to resource provider
        add_project_resources(project_path, project_name)

        # Test resource provider
        resource_provider = WebDiscoveryResourceProvider(project_path)
        resources = resource_provider.list_all_resources()

        print(f"✅ MCP resources configured")
        print(f"   🔗 Total resources: {len(resources)}")

        for resource in resources[:5]:  # Show first 5
            print(f"      📄 {resource['name']}")
            print(f"         URI: {resource['uri']}")
            print(f"         Type: {resource['mimeType']}")

        if len(resources) > 5:
            print(f"      ... and {len(resources) - 5} more resources")

    except Exception as e:
        print(f"⚠️  MCP resource setup warning: {e}")
    print()

    # Step 8: Show sample file contents
    print("👀 Step 8: Sample file contents preview...")

    docs_path = Path(project_path) / "docs" / "web_discovery"

    # Show metadata
    metadata_file = docs_path / "analysis-metadata.json"
    if metadata_file.exists():
        print("📄 analysis-metadata.json:")
        with open(metadata_file, 'r') as f:
            metadata = json.load(f)
        print(f"   🏪 Project: {metadata['project_name']}")
        print(f"   🌐 Website: {metadata['website_url']}")
        print(f"   📊 Pages analyzed: {metadata['total_pages_analyzed']}")
        print(f"   ✅ Completed: {metadata['completed_pages']}")
        print(f"   ❌ Failed: {metadata['failed_pages']}")
        print(f"   ⭐ Avg quality: {metadata['average_quality_score']:.1%}")
        print(f"   📈 Status: {metadata['analysis_status']}")
        print()

    # Show a sample page file
    pages_dir = docs_path / "pages"
    page_files = list(pages_dir.glob("page-*.md"))
    if page_files:
        sample_page = page_files[0]
        print(f"📄 Sample page file: {sample_page.name}")
        content = sample_page.read_text(encoding='utf-8')
        lines = content.split('\n')

        # Show header information
        for i, line in enumerate(lines[:20]):
            if line.strip():
                print(f"   {line}")
            if i > 15 and line.startswith('---'):
                break

        print(f"   ... [file continues with {len(lines)} total lines]")
        print()

    # Show master report info
    master_report = docs_path / "analysis-report.md"
    if master_report.exists():
        content = master_report.read_text(encoding='utf-8')
        lines = content.split('\n')
        print(f"📊 Master analysis report: analysis-report.md")
        print(f"   📏 Total lines: {len(lines):,}")
        print(f"   📝 Word count: {len(content.split()):,}")
        print(f"   💾 File size: {len(content.encode('utf-8')):,} bytes")

        # Count sections
        section_count = sum(1 for line in lines if line.startswith('## '))
        print(f"   📑 Main sections: {section_count}")
        print()

    # Final summary
    print("=" * 80)
    print("🎉 COMPREHENSIVE ARTIFACT STORAGE COMPLETE!")
    print("=" * 80)
    print()
    print("✅ Successfully demonstrated:")
    print("   🏗️  Project documentation structure setup")
    print("   🔬 Comprehensive analysis artifact creation (8 artifacts)")
    print("   📂 Artifact organization into project documentation")
    print("   📋 Master analysis report generation")
    print("   🔄 Version control guidance and .gitignore setup")
    print("   🔗 MCP resource exposure for AI tool access")
    print()
    print("📁 Project documentation available at:")
    print(f"   {docs_path}")
    print()
    print("🔗 MCP Resources accessible via:")
    print("   web_discovery://docs/web_discovery/analysis-metadata.json")
    print("   web_discovery://docs/web_discovery/analysis-report.md")
    print("   web_discovery://docs/web_discovery/pages/page-*.md")
    print()
    print("🚀 Ready for development team collaboration and AI tool integration!")


def main():
    """Main entry point for the demo script."""
    if len(sys.argv) > 1:
        project_path = sys.argv[1]
    else:
        # Use a temporary directory for demo
        project_path = tempfile.mkdtemp(prefix="modernshop_demo_")
        print(f"🔧 No project path provided, using temporary directory: {project_path}")
        print()

    # Ensure project path exists
    Path(project_path).mkdir(parents=True, exist_ok=True)

    # Run the demo
    asyncio.run(demo_comprehensive_artifact_storage(project_path))


if __name__ == "__main__":
    main()
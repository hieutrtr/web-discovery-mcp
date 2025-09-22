#!/usr/bin/env python3
"""Script to create sample analysis artifacts for testing documentation generation.

This script creates real AnalysisArtifact objects and saves them to the artifact system
so that the documentation tools can process real artifact data.
"""

import sys
from datetime import datetime, UTC
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from legacy_web_mcp.llm.artifacts import ArtifactManager, AnalysisArtifact
from legacy_web_mcp.config.loader import load_configuration


def create_sample_artifacts():
    """Create and save sample analysis artifacts."""
    print("Creating sample analysis artifacts...")

    # Initialize artifact manager
    artifact_manager = ArtifactManager()

    # Create sample artifacts for "Example E-commerce Platform" project
    project_id = "Example E-commerce Platform"

    # Artifact 1: Home page content summary (Step 1)
    artifact1 = AnalysisArtifact(
        analysis_type="step1",
        page_url="https://example-ecommerce.com/",
        timestamp=datetime.now(UTC),
        project_id=project_id,
        step1_result={
            "purpose": "Product discovery and user conversion",
            "user_context": "Potential customers browsing for products",
            "business_logic": "E-commerce homepage with product showcase and navigation",
            "navigation_role": "Primary entry point for site navigation",
            "business_importance": 0.95,
            "confidence_score": 0.92,
            "key_workflows": ["product_browsing", "search", "account_login"],
            "user_journey_stage": "entry",
            "contextual_keywords": ["ecommerce", "products", "shopping", "navigation"]
        },
        quality_metrics={
            "overall_quality_score": 0.92,
            "completeness_score": 0.90,
            "technical_depth_score": 0.85
        },
        metadata={
            "page_title": "Example E-commerce - Home",
            "analysis_status": "completed",
            "processing_time": 2.3
        },
        status="completed"
    )

    # Save artifact 1
    artifact_manager._save_artifact(artifact1)
    artifact_manager.complete_artifact(artifact1, "completed")
    print(f"Created artifact 1: {artifact1.artifact_id}")

    # Artifact 2: Home page feature analysis (Step 2)
    artifact2 = AnalysisArtifact(
        analysis_type="step2",
        page_url="https://example-ecommerce.com/",
        timestamp=datetime.now(UTC),
        project_id=project_id,
        step2_result={
            "interactive_elements": [
                {
                    "type": "form",
                    "selector": "#search-form",
                    "purpose": "Product search functionality",
                    "behavior": "submit"
                },
                {
                    "type": "button",
                    "selector": ".login-btn",
                    "purpose": "User authentication",
                    "behavior": "click"
                },
                {
                    "type": "button",
                    "selector": ".add-to-cart",
                    "purpose": "Add products to shopping cart",
                    "behavior": "click"
                }
            ],
            "functional_capabilities": [
                {
                    "name": "Product Search",
                    "description": "Search products with filters and pagination",
                    "type": "feature",
                    "complexity_score": 0.7
                },
                {
                    "name": "User Authentication",
                    "description": "JWT-based authentication with social login",
                    "type": "service",
                    "complexity_score": 0.4
                },
                {
                    "name": "Shopping Cart",
                    "description": "Session-based cart management",
                    "type": "feature",
                    "complexity_score": 0.6
                }
            ],
            "api_integrations": [
                {
                    "endpoint": "/api/products/search",
                    "method": "GET",
                    "purpose": "Product search with filters and pagination",
                    "data_flow": "client-to-server"
                },
                {
                    "endpoint": "/api/auth/login",
                    "method": "POST",
                    "purpose": "User authentication endpoint",
                    "data_flow": "client-to-server"
                },
                {
                    "endpoint": "/api/cart",
                    "method": "GET",
                    "purpose": "Retrieve user's shopping cart",
                    "data_flow": "server-to-client"
                }
            ],
            "business_rules": [
                {
                    "name": "Search Validation",
                    "description": "Validate search query parameters",
                    "validation_logic": "Require minimum 2 characters for search"
                }
            ],
            "rebuild_specifications": [
                {
                    "name": "Product Search Component",
                    "description": "React component with search filters",
                    "priority_score": 0.9,
                    "complexity": "medium",
                    "dependencies": ["search-api", "filter-component"]
                }
            ]
        },
        quality_metrics={
            "overall_quality_score": 0.89,
            "completeness_score": 0.88,
            "technical_depth_score": 0.82
        },
        metadata={
            "page_title": "Example E-commerce - Home",
            "analysis_status": "completed",
            "processing_time": 4.1
        },
        status="completed"
    )

    # Save artifact 2
    artifact_manager._save_artifact(artifact2)
    artifact_manager.complete_artifact(artifact2, "completed")
    print(f"Created artifact 2: {artifact2.artifact_id}")

    # Artifact 3: Product page content summary
    artifact3 = AnalysisArtifact(
        analysis_type="step1",
        page_url="https://example-ecommerce.com/products/laptop-abc123",
        timestamp=datetime.now(UTC),
        project_id=project_id,
        step1_result={
            "purpose": "Product details and purchase decision support",
            "user_context": "Customers evaluating specific product for purchase",
            "business_logic": "Product information display with purchase options",
            "navigation_role": "Product catalog leaf page",
            "business_importance": 0.88,
            "confidence_score": 0.91,
            "key_workflows": ["product_viewing", "add_to_cart", "checkout"],
            "user_journey_stage": "conversion",
            "contextual_keywords": ["product", "details", "specs", "purchase", "cart"]
        },
        quality_metrics={
            "overall_quality_score": 0.91,
            "completeness_score": 0.89,
            "technical_depth_score": 0.87
        },
        metadata={
            "page_title": "Laptop ABC123 - Product Details",
            "analysis_status": "completed",
            "processing_time": 2.1
        },
        status="completed"
    )

    # Save artifact 3
    artifact_manager._save_artifact(artifact3)
    artifact_manager.complete_artifact(artifact3, "completed")
    print(f"Created artifact 3: {artifact3.artifact_id}")

    # Artifact 4: Product page feature analysis
    artifact4 = AnalysisArtifact(
        analysis_type="step2",
        page_url="https://example-ecommerce.com/products/laptop-abc123",
        timestamp=datetime.now(UTC),
        project_id=project_id,
        step2_result={
            "interactive_elements": [
                {
                    "type": "button",
                    "selector": ".add-to-cart-btn",
                    "purpose": "Add current product to shopping cart",
                    "behavior": "click"
                },
                {
                    "type": "select",
                    "selector": "#quantity-select",
                    "purpose": "Select product quantity",
                    "behavior": "change"
                },
                {
                    "type": "button",
                    "selector": ".wishlist-btn",
                    "purpose": "Save product to wishlist",
                    "behavior": "click"
                }
            ],
            "functional_capabilities": [
                {
                    "name": "Product Display",
                    "description": "Comprehensive product information and media gallery",
                    "type": "feature",
                    "complexity_score": 0.5
                },
                {
                    "name": "Cart Integration",
                    "description": "Add to cart with quantity selection",
                    "type": "feature",
                    "complexity_score": 0.6
                },
                {
                    "name": "Wishlist Management",
                    "description": "Save products for later consideration",
                    "type": "feature",
                    "complexity_score": 0.4
                }
            ],
            "api_integrations": [
                {
                    "endpoint": "/api/products/{id}",
                    "method": "GET",
                    "purpose": "Retrieve detailed product information",
                    "data_flow": "server-to-client"
                },
                {
                    "endpoint": "/api/cart/items",
                    "method": "POST",
                    "purpose": "Add item to shopping cart",
                    "data_flow": "client-to-server"
                },
                {
                    "endpoint": "/api/wishlist/items",
                    "method": "POST",
                    "purpose": "Add item to user wishlist",
                    "data_flow": "client-to-server"
                }
            ],
            "business_rules": [
                {
                    "name": "Stock Validation",
                    "description": "Verify product availability before cart addition",
                    "validation_logic": "Check inventory quantity >= requested quantity"
                },
                {
                    "name": "Price Display",
                    "description": "Show current price with any active discounts",
                    "validation_logic": "Calculate final price including promotions"
                }
            ],
            "rebuild_specifications": [
                {
                    "name": "Product Detail Component",
                    "description": "Vue component for product information display",
                    "priority_score": 0.8,
                    "complexity": "medium",
                    "dependencies": ["product-api", "cart-service", "wishlist-service"]
                }
            ]
        },
        quality_metrics={
            "overall_quality_score": 0.87,
            "completeness_score": 0.85,
            "technical_depth_score": 0.88
        },
        metadata={
            "page_title": "Laptop ABC123 - Product Details",
            "analysis_status": "completed",
            "processing_time": 3.8
        },
        status="completed"
    )

    # Save artifact 4
    artifact_manager._save_artifact(artifact4)
    artifact_manager.complete_artifact(artifact4, "completed")
    print(f"Created artifact 4: {artifact4.artifact_id}")

    print(f"✅ Created 4 sample artifacts for project '{project_id}'")

    # List all artifacts to verify
    all_artifacts = artifact_manager.list_artifacts()
    print(f"Total artifacts in system: {len(all_artifacts)}")
    project_artifacts = artifact_manager.list_artifacts(project_id=project_id)
    print(f"Artifacts for '{project_id}': {len(project_artifacts)}")

    return project_artifacts


if __name__ == "__main__":
    try:
        artifacts = create_sample_artifacts()
        print("\n🎉 Sample artifacts created successfully!")
        print("You can now test the documentation generation tools with real artifact data.")
    except Exception as e:
        print(f"❌ Error creating artifacts: {e}")
        import traceback
        traceback.print_exc()
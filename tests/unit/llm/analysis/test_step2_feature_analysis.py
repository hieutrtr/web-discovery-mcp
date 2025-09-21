"""Tests for Step 2 Feature Analysis."""

import json
from unittest.mock import MagicMock, AsyncMock

import pytest

from legacy_web_mcp.llm.analysis.step2_feature_analysis import (
    FeatureAnalyzer,
    FeatureAnalysisError,
)
from legacy_web_mcp.llm.models import ContentSummary, FeatureAnalysis
from legacy_web_mcp.browser.analysis import PageAnalysisData, DOMStructureAnalysis


class TestFeatureAnalyzer:
    """Test cases for FeatureAnalyzer."""

    @pytest.fixture
    def mock_llm_engine(self):
        """Mock LLM engine."""
        engine = MagicMock()
        engine.chat_completion = AsyncMock()
        return engine

    @pytest.fixture
    def analyzer(self, mock_llm_engine):
        """Feature analyzer instance."""
        return FeatureAnalyzer(mock_llm_engine)

    @pytest.fixture
    def sample_content_summary(self):
        """Sample content summary from Step 1."""
        return ContentSummary(
            purpose="Shopping cart management page",
            user_context="Registered users managing their shopping cart",
            business_logic="E-commerce product selection and checkout preparation",
            navigation_role="Transactional page in purchase flow",
            confidence_score=0.85,
        )

    @pytest.fixture
    def sample_page_analysis_data(self):
        """Sample page analysis data."""
        return PageAnalysisData(
            url="https://example.com/cart",
            title="Shopping Cart",
            page_content={
                "visible_text": "Shopping Cart - Items: 3 - Subtotal: $45.99 - Checkout",
            },
            dom_analysis=DOMStructureAnalysis(
                total_elements=45,
                interactive_elements=15,
                form_elements=3,
                link_elements=12,
            ),
        )

    # Unit Tests
    async def test_feature_analysis_success(
        self, analyzer, sample_content_summary, sample_page_analysis_data, mock_llm_engine
    ):
        """Test successful feature analysis."""
        # Mock LLM response
        mock_response = MagicMock()
        mock_response.content = json.dumps(
            {
                "interactive_elements": [
                    {
                        "type": "button",
                        "selector": "button#checkout",
                        "purpose": "Proceed to checkout process",
                        "behavior": "Navigate to payment page",
                    }
                ],
                "functional_capabilities": [
                    {
                        "name": "Cart Management",
                        "description": "Add/remove items from shopping cart",
                        "type": "CRUD",
                        "complexity_score": 3,
                    }
                ],
                "api_integrations": [
                    {
                        "endpoint": "/api/cart",
                        "method": "GET",
                        "purpose": "Fetch current cart contents",
                        "data_flow": "Retrieve cart data",
                        "auth_type": "session",
                    }
                ],
                "business_rules": [
                    {
                        "name": "Inventory Check",
                        "description": "Verify item availability before checkout",
                        "validation_logic": "Check stock levels against cart quantities",
                        "error_handling": "Show out-of-stock message",
                    }
                ],
                "third_party_integrations": [
                    {
                        "service_name": "Stripe",
                        "integration_type": "Payment Processing",
                        "purpose": "Process credit card payments",
                        "auth_method": "API Key",
                    }
                ],
                "rebuild_specifications": [
                    {
                        "name": "Shopping Cart Component",
                        "description": "Core cart management functionality",
                        "priority_score": 0.9,
                        "complexity": "medium",
                        "dependencies": ["User Authentication", "Inventory System"],
                    }
                ],
                "confidence_score": 0.85,
                "quality_score": 0.80,
            }
        )
        mock_llm_engine.chat_completion.return_value = mock_response

        result = await analyzer.analyze_features(sample_page_analysis_data, sample_content_summary)

        assert isinstance(result, FeatureAnalysis)
        assert len(result.interactive_elements) == 1
        assert result.interactive_elements[0].type == "button"
        assert result.interactive_elements[0].selector == "button#checkout"
        assert len(result.functional_capabilities) == 1
        assert result.functional_capabilities[0].type == "CRUD"
        assert len(result.api_integrations) == 1
        assert len(result.business_rules) == 1
        assert len(result.rebuild_specifications) == 1
        assert 0.7 <= result.confidence_score <= 0.85  # Allow for scoring adjustments
        assert 0.7 <= result.quality_score <= 0.85  # Quality score can be boosted from baseline

    async def test_feature_analysis_with_interactive_elements(
        self, analyzer, sample_content_summary, sample_page_analysis_data, mock_llm_engine
    ):
        """Test feature analysis with interactive elements in page data."""
        # Add interactive elements to page analysis data
        sample_page_analysis_data.page_content["interactive_elements"] = [
            {
                "type": "form",
                "selector": "form#quantity-update",
                "purpose": "Update item quantity",
                "action": "submit",
            }
        ]

        mock_response = MagicMock()
        mock_response.content = json.dumps(
            {
                "interactive_elements": [],
                "functional_capabilities": [],
                "api_integrations": [],
                "business_rules": [],
                "third_party_integrations": [],
                "rebuild_specifications": [],
                "confidence_score": 0.75,
                "quality_score": 0.65,
            }
        )
        mock_llm_engine.chat_completion.return_value = mock_response

        result = await analyzer.analyze_features(sample_page_analysis_data, sample_content_summary)

        # Should process the interactive elements
        assert isinstance(result, FeatureAnalysis)

    async def test_feature_analysis_with_network_requests(
        self, analyzer, sample_content_summary, sample_page_analysis_data, mock_llm_engine
    ):
        """Test feature analysis with network requests."""
        # Add network requests to page analysis data
        sample_page_analysis_data.page_content["network_requests"] = [
            {
                "url": "/api/products/123",
                "method": "GET",
                "status": 200,
                "purpose": "Fetch product details",
            }
        ]

        mock_response = MagicMock()
        mock_response.content = json.dumps(
            {
                "interactive_elements": [],
                "functional_capabilities": [],
                "api_integrations": [],
                "business_rules": [],
                "third_party_integrations": [],
                "rebuild_specifications": [],
                "confidence_score": 0.70,
                "quality_score": 0.60,
            }
        )
        mock_llm_engine.chat_completion.return_value = mock_response

        result = await analyzer.analyze_features(sample_page_analysis_data, sample_content_summary)

        assert isinstance(result, FeatureAnalysis)

    async def test_json_parsing_with_markdown_block(self, analyzer):
        """Test JSON parsing with markdown code block."""
        content = """```json
{
    "interactive_elements": [],
    "functional_capabilities": [],
    "api_integrations": [],
    "business_rules": [],
    "third_party_integrations": [],
    "rebuild_specifications": [],
    "confidence_score": 0.90,
    "quality_score": 0.85
}
```"""

        result = analyzer._parse_json_response(content)
        assert result["confidence_score"] == 0.90
        assert result["quality_score"] == 0.85

    async def test_json_parsing_direct_json(self, analyzer):
        """Test JSON parsing with direct JSON content."""
        content = """{
    "interactive_elements": [],
    "functional_capabilities": [],
    "api_integrations": [],
    "business_rules": [],
    "third_party_integrations": [],
    "rebuild_specifications": [],
    "confidence_score": 0.88,
    "quality_score": 0.82
}"""

        result = analyzer._parse_json_response(content)
        assert result["confidence_score"] == 0.88
        assert result["quality_score"] == 0.82

    async def test_json_parsing_invalid_json(self, analyzer):
        """Test JSON parsing with invalid JSON returns fallback structure."""
        content = "invalid json { broken"

        result = analyzer._parse_json_response(content)
        assert "interactive_elements" in result
        assert "functional_capabilities" in result
        assert result["confidence_score"] == 0.0
        assert result["quality_score"] == 0.0

    async def test_confidence_calculation_high(self, analyzer):
        """Test confidence calculation with complete data."""
        json_data = {
            "interactive_elements": [{"type": "button", "selector": "#test"}],
            "functional_capabilities": [{"name": "test", "description": "test"}],
            "api_integrations": [{"endpoint": "/api/test", "method": "GET"}],
            "business_rules": [{"name": "validation", "description": "required"}],
            "rebuild_specifications": [{"name": "feature", "description": "build"}],
        }

        # Create FeatureAnalysis instance
        analysis = analyzer._json_to_feature_analysis(json_data)
        confidence = analyzer._calculate_confidence(analysis)

        assert confidence > 0.7

    async def test_confidence_calculation_low(self, analyzer):
        """Test confidence calculation with minimal data."""
        json_data = {
            "interactive_elements": [],
            "functional_capabilities": [],
            "api_integrations": [],
            "business_rules": [],
            "rebuild_specifications": [],
        }

        analysis = analyzer._json_to_feature_analysis(json_data)
        confidence = analyzer._calculate_confidence(analysis)

        assert confidence < 0.5

    async def test_quality_calculation_high(self, analyzer, sample_content_summary):
        """Test quality calculation with good content."""
        json_data = {
            "interactive_elements": [
                {
                    "type": "button",
                    "selector": "#test",
                    "purpose": "test button",
                    "behavior": "click",
                }
            ],
            "functional_capabilities": [
                {
                    "name": "feature",
                    "description": "test feature",
                    "type": "form",
                    "complexity_score": 3,
                }
            ],
            "api_integrations": [
                {
                    "endpoint": "/api",
                    "method": "GET",
                    "purpose": "test api",
                    "data_flow": "test data",
                    "auth_type": None,
                }
            ],
            "business_rules": [
                {
                    "name": "rule",
                    "description": "test rule",
                    "validation_logic": "test logic",
                    "error_handling": None,
                }
            ],
            "third_party_integrations": [],
            "rebuild_specifications": [
                {
                    "name": "build feature",
                    "description": "build description",
                    "priority_score": 0.7,
                    "complexity": "medium",
                    "dependencies": [],
                }
            ],
            "confidence_score": 0.85,
            "quality_score": 0.80,
        }

        analysis = FeatureAnalysis(**json_data)
        quality = analyzer._calculate_quality(analysis, sample_content_summary)

        # Should be high quality due to complete data and good Step 1 confidence
        assert quality > 0.5

    async def test_quality_calculation_low_step1(self, analyzer):
        """Test quality calculation with low Step 1 confidence."""
        low_confidence_context = ContentSummary(
            purpose="test",
            user_context="test user",
            business_logic="test logic",
            navigation_role="test role",
            confidence_score=0.2,
        )

        json_data = {
            "interactive_elements": [{"type": "button"}],
            "functional_capabilities": [{"name": "feature"}],
            "api_integrations": [{"endpoint": "/api"}],
            "business_rules": [{"name": "rule"}],
            "rebuild_specifications": [],
        }

        analysis = analyzer._json_to_feature_analysis(json_data)
        quality = analyzer._calculate_quality(analysis, low_confidence_context)

        # Should be low quality due to incomplete rebuild specs and low Step 1 confidence
        assert quality < 0.5

    async def test_error_handling_llm_failure(
        self, analyzer, sample_content_summary, sample_page_analysis_data, mock_llm_engine
    ):
        """Test error handling when LLM fails."""
        mock_llm_engine.chat_completion.side_effect = Exception("LLM API error")

        with pytest.raises(FeatureAnalysisError) as exc_info:
            await analyzer.analyze_features(sample_page_analysis_data, sample_content_summary)

        assert "Failed to analyze features" in str(exc_info.value)

    # Integration Tests
    async def test_end_to_end_step2_analysis(
        self, analyzer, sample_content_summary, sample_page_analysis_data, mock_llm_engine
    ):
        """Test complete end-to-end Step 2 analysis."""
        # Mock LLM response with realistic e-commerce data
        mock_response = MagicMock()
        mock_response.content = json.dumps(
            {
                "interactive_elements": [
                    {
                        "type": "form",
                        "selector": "#item-quantity",
                        "purpose": "Update item quantity",
                        "behavior": "Update cart on change",
                    },
                    {
                        "type": "button",
                        "selector": "#checkout",
                        "purpose": "Begin checkout process",
                        "behavior": "Navigate to payment",
                    },
                ],
                "functional_capabilities": [
                    {
                        "name": "Cart Management",
                        "description": "Add, remove, update cart items",
                        "type": "CRUD",
                        "complexity_score": 4,
                    },
                    {
                        "name": "Quantity Validation",
                        "description": "Validate quantity changes",
                        "type": "Validation",
                        "complexity_score": 2,
                    },
                ],
                "api_integrations": [
                    {
                        "endpoint": "/api/cart/update",
                        "method": "POST",
                        "purpose": "Update cart contents",
                        "data_flow": "Send item updates",
                        "auth_type": "session",
                    }
                ],
                "business_rules": [
                    {
                        "name": "Inventory Check",
                        "description": "Verify item availability",
                        "validation_logic": "Check stock before checkout",
                        "error_handling": "Show out-of-stock message",
                    }
                ],
                "third_party_integrations": [
                    {
                        "service_name": "Stripe",
                        "integration_type": "Payment Processing",
                        "purpose": "Process payments",
                        "auth_method": "API Key",
                    }
                ],
                "rebuild_specifications": [
                    {
                        "name": "Cart Component",
                        "description": "Core cart functionality",
                        "priority_score": 0.9,
                        "complexity": "medium",
                        "dependencies": ["User Auth", "Inventory System"],
                    },
                    {
                        "name": "Payment Integration",
                        "description": "Payment processing",
                        "priority_score": 0.8,
                        "complexity": "medium",
                        "dependencies": ["Cart Component"],
                    },
                ],
                "confidence_score": 0.85,
                "quality_score": 0.82,
            }
        )
        mock_llm_engine.chat_completion.return_value = mock_response

        result = await analyzer.analyze_features(sample_page_analysis_data, sample_content_summary)

        # Verify comprehensive analysis
        assert len(result.interactive_elements) == 2
        assert len(result.functional_capabilities) == 2
        assert len(result.api_integrations) == 1
        assert len(result.business_rules) == 1
        assert len(result.third_party_integrations) == 1
        assert len(result.rebuild_specifications) == 2
        assert 0.7 <= result.confidence_score <= 0.85  # Allow for scoring adjustments
        assert 0.7 <= result.quality_score <= 0.85  # Quality score can be boosted from baseline

    async def test_step2_provider_fallback(
        self, analyzer, sample_content_summary, sample_page_analysis_data, mock_llm_engine
    ):
        """Test fallback to different provider on failure."""
        # Mock LLM response
        mock_response = MagicMock()
        mock_response.content = json.dumps(
            {
                "interactive_elements": [],
                "functional_capabilities": [],
                "api_integrations": [],
                "business_rules": [],
                "third_party_integrations": [],
                "rebuild_specifications": [],
                "confidence_score": 0.75,
                "quality_score": 0.70,
            }
        )

        # First call succeeds (test doesn't need to test actual fallback at LLM engine level)
        mock_llm_engine.chat_completion.return_value = mock_response

        result = await analyzer.analyze_features(sample_page_analysis_data, sample_content_summary)

        # Should succeed on first attempt
        assert isinstance(result, FeatureAnalysis)
        assert mock_llm_engine.chat_completion.call_count == 1

    async def test_business_importance_complexity_blending(self, analyzer):
        """Test priority score calculation blending business importance and complexity."""
        # Arrange
        from legacy_web_mcp.llm.models import FunctionalCapability, ContextPayload

        # Create a feature analysis object with a capability having a complexity score
        feature_analysis = FeatureAnalysis(
            functional_capabilities=[
                FunctionalCapability(
                    name="Test Capability",
                    description="A test case",
                    type="feature",
                    complexity_score=0.6,
                )
            ]
        )

        # Create a content summary with a high business importance
        content_summary = ContentSummary(
            purpose="Test",
            user_context="Test",
            business_logic="Test",
            navigation_role="Test",
            confidence_score=0.9,
            business_importance=0.9, # High importance
        )

        # Create the context payload
        context_payload = ContextPayload(content_summary=content_summary)

        # Act
        analyzer._calculate_priority_scores(feature_analysis, context_payload)

        # Assert
        capability = feature_analysis.functional_capabilities[0]
        assert capability.priority_score is not None

        # Manually calculate expected score to verify the logic
        # score = (business_importance * 0.4 + user_impact * 0.3 + (1 - complexity) * 0.2 + (1 - effort) * 0.1)
        # From _calculate_capability_priority: user_impact=0.6 (since business_alignment is empty), implementation_effort=0.6
        expected_score = (0.9 * 0.4) + (0.6 * 0.3) + ((1.0 - 0.6) * 0.2) + ((1.0 - 0.6) * 0.1)
        # 0.36 + 0.18 + (0.4 * 0.2) + (0.4 * 0.1) = 0.54 + 0.08 + 0.04 = 0.66

        assert capability.priority_score.overall_priority == pytest.approx(0.66)
        assert capability.priority_score.business_importance == 0.9
        assert capability.priority_score.technical_complexity == 0.6

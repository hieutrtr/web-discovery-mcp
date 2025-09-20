#!/usr/bin/env python
"""Tests for Step 1 prompt generation."""

from __future__ import annotations

import json

from legacy_web_mcp.llm.prompts.step1_summarize import create_content_summary_prompt


def test_create_content_summary_prompt_basic():
    """Test basic prompt creation."""
    page_content = "Welcome to our homepage. We sell widgets."
    dom_structure = {"total_elements": 50, "link_count": 5}
    url = "https://example.com"

    prompt = create_content_summary_prompt(page_content, dom_structure, url)

    assert url in prompt
    assert page_content in prompt
    assert json.dumps(dom_structure, indent=2) in prompt
    assert "Analyze the content of the web page" in prompt

def test_create_content_summary_prompt_truncation():
    """Test that long page content is truncated."""
    long_content = "a" * 20000
    dom_structure = {"total_elements": 100}
    url = "https://example.com/long"

    prompt = create_content_summary_prompt(long_content, dom_structure, url)

    assert len(prompt) < 18000  # Check it's reasonably sized
    assert "(content truncated)" in prompt
    assert long_content[:100] in prompt # The beginning should be there

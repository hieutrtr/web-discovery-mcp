#!/usr/bin/env python3
"""Debug script to examine the actual artifact data structure."""

import sys
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from legacy_web_mcp.llm.artifacts import ArtifactManager


def debug_artifacts():
    """Examine the actual artifact data to debug the issue."""
    print("=== Debugging Artifact Data Structure ===\n")

    artifact_manager = ArtifactManager()

    # Get artifacts for the project
    project_id = "Example E-commerce Platform"
    artifacts = artifact_manager.list_artifacts(project_id=project_id)

    print(f"Found {len(artifacts)} artifacts for project '{project_id}'\n")

    for i, artifact in enumerate(artifacts, 1):
        print(f"Artifact {i}: {artifact.artifact_id}")
        print(f"  Type: {artifact.analysis_type}")
        print(f"  URL: {artifact.page_url}")
        print(f"  Status: {artifact.status}")

        # Check quality_metrics type and content
        print(f"  quality_metrics type: {type(artifact.quality_metrics)}")
        print(f"  quality_metrics value: {artifact.quality_metrics}")

        if artifact.quality_metrics:
            if isinstance(artifact.quality_metrics, dict):
                score = artifact.quality_metrics.get("overall_quality_score", "N/A")
                print(f"  overall_quality_score: {score}")
            else:
                print(f"  ❌ quality_metrics is not a dict! It's: {type(artifact.quality_metrics)}")

        # Check step1_result type
        print(f"  step1_result type: {type(artifact.step1_result)}")
        if artifact.step1_result:
            if isinstance(artifact.step1_result, dict):
                business_importance = artifact.step1_result.get("business_importance", "N/A")
                print(f"  business_importance: {business_importance}")
            else:
                print(f"  ❌ step1_result is not a dict! It's: {type(artifact.step1_result)}")

        # Check step2_result type
        print(f"  step2_result type: {type(artifact.step2_result)}")
        if artifact.step2_result:
            if isinstance(artifact.step2_result, dict):
                capabilities = artifact.step2_result.get("functional_capabilities", [])
                print(f"  functional_capabilities count: {len(capabilities)}")
            else:
                print(f"  ❌ step2_result is not a dict! It's: {type(artifact.step2_result)}")

        print()


if __name__ == "__main__":
    debug_artifacts()
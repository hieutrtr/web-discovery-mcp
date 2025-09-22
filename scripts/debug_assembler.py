#!/usr/bin/env python3
"""Debug the DocumentationAssembler to find the exact issue."""

import sys
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from legacy_web_mcp.llm.artifacts import ArtifactManager
from legacy_web_mcp.documentation.assembler import DocumentationAssembler


def debug_assembler():
    """Debug the DocumentationAssembler step by step."""
    print("=== Debugging DocumentationAssembler ===\n")

    artifact_manager = ArtifactManager()
    assembler = DocumentationAssembler(artifact_manager)
    project_id = "Example E-commerce Platform"

    try:
        print("Step 1: Loading project artifacts...")
        artifacts = assembler._load_project_artifacts(project_id)
        print(f"✅ Loaded {len(artifacts)} artifacts")

        print("\nStep 2: Generating project summary...")
        project_summary = assembler._generate_project_summary(artifacts)
        print(f"✅ Project summary created: {type(project_summary)}")
        print(f"   Total pages: {project_summary.total_pages_analyzed}")
        print(f"   Average quality: {project_summary.average_quality_score}")

        print("\nStep 3: Setting project summary on assembler...")
        assembler.project_summary = project_summary
        print(f"✅ Assembler project_summary set: {assembler.project_summary is not None}")

        print("\nStep 4: Generating executive summary section...")
        exec_section = assembler._generate_executive_summary(artifacts)
        print(f"✅ Executive summary section created")
        print(f"   Title: {exec_section.title}")
        print(f"   Content length: {len(exec_section.content)}")

        print("\nStep 5: Testing individual field access...")
        for i, artifact in enumerate(artifacts):
            print(f"Artifact {i+1}:")
            try:
                if artifact.quality_metrics:
                    score = artifact.quality_metrics.get("overall_quality_score", 0.0)
                    print(f"  ✅ Quality score: {score}")
                else:
                    print(f"  ⚠️ No quality metrics")

                if artifact.step1_result:
                    business_importance = artifact.step1_result.get("business_importance", 0.5)
                    print(f"  ✅ Business importance: {business_importance}")
                else:
                    print(f"  ⚠️ No step1 result")

                if artifact.step2_result:
                    capabilities = artifact.step2_result.get("functional_capabilities", [])
                    apis = artifact.step2_result.get("api_integrations", [])
                    elements = artifact.step2_result.get("interactive_elements", [])
                    print(f"  ✅ Step2: {len(capabilities)} capabilities, {len(apis)} APIs, {len(elements)} elements")
                else:
                    print(f"  ⚠️ No step2 result")

            except Exception as e:
                print(f"  ❌ Error accessing artifact data: {e}")
                print(f"      quality_metrics type: {type(artifact.quality_metrics)}")
                print(f"      step1_result type: {type(artifact.step1_result)}")
                print(f"      step2_result type: {type(artifact.step2_result)}")

    except Exception as e:
        print(f"❌ Error in assembler: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    debug_assembler()
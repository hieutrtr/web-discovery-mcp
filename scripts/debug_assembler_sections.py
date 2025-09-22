#!/usr/bin/env python3
"""Debug each section of the DocumentationAssembler individually."""

import sys
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from legacy_web_mcp.llm.artifacts import ArtifactManager
from legacy_web_mcp.documentation.assembler import DocumentationAssembler


def debug_assembler_sections():
    """Test each assembler section individually to find the problematic one."""
    print("=== Debugging DocumentationAssembler Sections ===\n")

    artifact_manager = ArtifactManager()
    assembler = DocumentationAssembler(artifact_manager)
    project_id = "Example E-commerce Platform"

    try:
        print("Loading artifacts and generating project summary...")
        artifacts = assembler._load_project_artifacts(project_id)
        project_summary = assembler._generate_project_summary(artifacts)
        assembler.project_summary = project_summary
        print(f"✅ Setup complete: {len(artifacts)} artifacts, summary ready\n")

        # Test each section individually
        sections_to_test = [
            ("Executive Summary", lambda: assembler._generate_executive_summary(artifacts)),
            ("Project Overview", lambda: assembler._generate_project_overview(artifacts)),
            ("Per-Page Analysis", lambda: assembler._generate_per_page_analysis(artifacts)),
            ("API Integration Summary", lambda: assembler._generate_api_integration_summary(artifacts)),
            ("Business Logic Documentation", lambda: assembler._generate_business_logic_documentation(artifacts)),
            ("Technical Specifications", lambda: assembler._generate_technical_specifications(artifacts)),
        ]

        for section_name, section_func in sections_to_test:
            try:
                print(f"Testing {section_name}...")
                section = section_func()
                print(f"✅ {section_name}: Generated successfully ({len(section.content)} chars)")
            except Exception as e:
                print(f"❌ {section_name}: Failed with error: {e}")
                import traceback
                traceback.print_exc()
                print()

        print("\nTesting full document assembly...")
        try:
            # Manually set up sections like the main method does
            assembler.sections = []
            assembler.sections.append(assembler._generate_executive_summary(artifacts))
            assembler.sections.append(assembler._generate_project_overview(artifacts))
            assembler.sections.append(assembler._generate_per_page_analysis(artifacts))
            assembler.sections.append(assembler._generate_api_integration_summary(artifacts))
            assembler.sections.append(assembler._generate_business_logic_documentation(artifacts))
            assembler.sections.append(assembler._generate_technical_specifications(artifacts))

            print("✅ All sections generated successfully")

            # Test markdown assembly
            markdown_content = assembler._assemble_markdown_document(project_id)
            print(f"✅ Markdown document assembled successfully ({len(markdown_content)} chars)")

        except Exception as e:
            print(f"❌ Full assembly failed: {e}")
            import traceback
            traceback.print_exc()

    except Exception as e:
        print(f"❌ Setup failed: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    debug_assembler_sections()
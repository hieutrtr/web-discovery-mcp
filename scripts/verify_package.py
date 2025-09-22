#!/usr/bin/env python3
"""
Verification script for the Legacy Web MCP package.

This script tests the package installation and basic functionality
to ensure it works correctly when installed via pip/uvx.
"""

import subprocess
import sys
import tempfile
from pathlib import Path


def run_command(cmd: list[str], description: str) -> tuple[int, str, str]:
    """Run a command and return exit code, stdout, stderr."""
    print(f"🔍 {description}")
    print(f"   Command: {' '.join(cmd)}")

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=30
        )
        return result.returncode, result.stdout, result.stderr
    except subprocess.TimeoutExpired:
        return 1, "", "Command timed out after 30 seconds"
    except Exception as e:
        return 1, "", str(e)


def test_uvx_installation():
    """Test uvx installation from local wheel."""
    print("\n" + "="*60)
    print("🧪 TESTING UVX INSTALLATION")
    print("="*60)

    # Find the wheel file
    dist_dir = Path(__file__).parent.parent / "dist"
    wheel_files = list(dist_dir.glob("*.whl"))

    if not wheel_files:
        print("❌ No wheel files found in dist/")
        print("   Please run 'uv build' first")
        return False

    wheel_file = wheel_files[0]
    print(f"📦 Using wheel: {wheel_file.name}")

    # Test version command
    exit_code, stdout, stderr = run_command(
        ["uvx", "--from", str(wheel_file), "legacy-web-mcp", "--version"],
        "Testing version command"
    )

    if exit_code != 0:
        print(f"❌ Version command failed")
        print(f"   stdout: {stdout}")
        print(f"   stderr: {stderr}")
        return False

    print(f"✅ Version command successful: {stdout.strip()}")

    # Test help command
    exit_code, stdout, stderr = run_command(
        ["uvx", "--from", str(wheel_file), "legacy-web-mcp", "--help"],
        "Testing help command"
    )

    if exit_code != 0:
        print(f"❌ Help command failed")
        print(f"   stdout: {stdout}")
        print(f"   stderr: {stderr}")
        return False

    print("✅ Help command successful")

    return True


def test_uv_run():
    """Test uv run installation."""
    print("\n" + "="*60)
    print("🧪 TESTING UV RUN")
    print("="*60)

    # Test version command
    exit_code, stdout, stderr = run_command(
        ["uv", "run", "legacy-web-mcp", "--version"],
        "Testing uv run version command"
    )

    if exit_code != 0:
        print(f"❌ UV run version command failed")
        print(f"   stdout: {stdout}")
        print(f"   stderr: {stderr}")
        return False

    print(f"✅ UV run version command successful: {stdout.strip()}")

    return True


def test_package_structure():
    """Test package structure and imports."""
    print("\n" + "="*60)
    print("🧪 TESTING PACKAGE STRUCTURE")
    print("="*60)

    try:
        # Test basic import
        import legacy_web_mcp
        print("✅ Basic import successful")

        # Test CLI import
        from legacy_web_mcp.cli import main
        print("✅ CLI import successful")

        # Test MCP server import
        from legacy_web_mcp.mcp.server import create_mcp, run
        print("✅ MCP server import successful")

        # Test version access
        version = getattr(legacy_web_mcp, '__version__', 'unknown')
        print(f"✅ Package version: {version}")

        return True

    except ImportError as e:
        print(f"❌ Import failed: {e}")
        return False


def main():
    """Run all verification tests."""
    print("🚀 Legacy Web MCP Package Verification")
    print("=" * 60)

    results = []

    # Test package structure
    results.append(("Package Structure", test_package_structure()))

    # Test uv run
    results.append(("UV Run", test_uv_run()))

    # Test uvx installation
    results.append(("UVX Installation", test_uvx_installation()))

    # Summary
    print("\n" + "="*60)
    print("📊 VERIFICATION SUMMARY")
    print("="*60)

    passed = 0
    total = len(results)

    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status} {test_name}")
        if result:
            passed += 1

    print(f"\nResults: {passed}/{total} tests passed")

    if passed == total:
        print("\n🎉 All verification tests passed!")
        print("📦 Package is ready for publishing!")
        return 0
    else:
        print(f"\n⚠️  {total - passed} test(s) failed")
        print("🔧 Please fix issues before publishing")
        return 1


if __name__ == "__main__":
    sys.exit(main())
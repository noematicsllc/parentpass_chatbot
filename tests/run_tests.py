#!/usr/bin/env python3
"""
Test runner script for ParentPass Chatbot API.
This script provides convenient ways to run different types of tests
and generate coverage reports.
"""

import sys
import os
import subprocess
import argparse
from pathlib import Path


def run_command(cmd, description=""):
    """Run a command and return the result."""
    if description:
        print(f"\n🔄 {description}")
        print("=" * 50)
    print(f"Running: {' '.join(cmd)}")
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.stdout:
        print(result.stdout)
    if result.stderr:
        print(result.stderr, file=sys.stderr)

    return result.returncode == 0


def run_tests(test_type="all", verbose=False, coverage=True, html_report=True):
    """Run tests with specified options."""
    # Ensure we're in the right directory
    project_root = Path(__file__).parent.parent
    os.chdir(project_root)

    # Base pytest command
    cmd = ["python", "-m", "pytest"]

    # Add verbosity
    if verbose:
        cmd.append("-v")
    else:
        cmd.append("-q")

    # Add coverage options
    if coverage:
        cmd.extend(["--cov=app", "--cov-report=term-missing"])
        if html_report:
            cmd.append("--cov-report=html")

    # Select test files based on type
    if test_type == "health":
        cmd.append("tests/test_health_endpoint.py")
    elif test_type == "sessions":
        cmd.append("tests/test_session_endpoints.py")
    elif test_type == "query":
        cmd.append("tests/test_query_endpoint.py")
    elif test_type == "auth":
        cmd.append("tests/test_authentication.py")
    elif test_type == "errors":
        cmd.append("tests/test_error_handling.py")
    elif test_type == "integration":
        cmd.append("tests/test_integration.py")
    elif test_type == "unit":
        cmd.extend(
            [
                "tests/test_health_endpoint.py",
                "tests/test_session_endpoints.py",
                "tests/test_query_endpoint.py",
                "tests/test_authentication.py",
                "tests/test_error_handling.py",
            ]
        )
    elif test_type == "all":
        cmd.append("tests/")
    else:
        print(f"❌ Unknown test type: {test_type}")
        return False

    # Run the tests
    success = run_command(cmd, f"Running {test_type} tests")

    if success:
        print(f"\n✅ {test_type.title()} tests passed!")
        if coverage and html_report:
            print("📊 Coverage report generated: htmlcov/index.html")
    else:
        print(f"\n❌ {test_type.title()} tests failed!")

    return success


def install_dependencies():
    """Install test dependencies."""
    cmd = ["uv", "sync", "--dev"]
    return run_command(cmd, "Installing dependencies")


def lint_code():
    """Run code linting (if available)."""
    print("\n🔍 Running code linting...")

    # Try to run flake8 if available
    try:
        cmd = ["python", "-m", "flake8", "app/", "tests/"]
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode == 0:
            print("✅ Linting passed!")
            return True
        else:
            print("❌ Linting issues found:")
            print(result.stdout)
            return False
    except FileNotFoundError:
        print("⚠️  flake8 not found - skipping linting")
        return True


def main():
    """Main function to parse arguments and run tests."""
    parser = argparse.ArgumentParser(description="Run ParentPass Chatbot API tests")

    parser.add_argument(
        "test_type",
        nargs="?",
        default="all",
        choices=[
            "all",
            "unit",
            "integration",
            "health",
            "sessions",
            "query",
            "auth",
            "errors",
        ],
        help="Type of tests to run",
    )

    parser.add_argument(
        "-v", "--verbose", action="store_true", help="Run tests in verbose mode"
    )

    parser.add_argument(
        "--no-coverage", action="store_true", help="Skip coverage reporting"
    )

    parser.add_argument(
        "--no-html", action="store_true", help="Skip HTML coverage report"
    )

    parser.add_argument(
        "--install",
        action="store_true",
        help="Install dependencies before running tests",
    )

    parser.add_argument(
        "--lint", action="store_true", help="Run code linting before tests"
    )

    parser.add_argument(
        "--quick", action="store_true", help="Quick run: no coverage, no HTML reports"
    )

    args = parser.parse_args()

    print("🧪 ParentPass Chatbot API Test Runner")
    print("=" * 40)

    # Install dependencies if requested
    if args.install:
        if not install_dependencies():
            print("❌ Failed to install dependencies")
            return 1

    # Run linting if requested
    if args.lint:
        if not lint_code():
            print("❌ Linting failed")
            return 1

    # Set options based on quick mode
    if args.quick:
        coverage = False
        html_report = False
    else:
        coverage = not args.no_coverage
        html_report = not args.no_html

    # Run tests
    success = run_tests(
        test_type=args.test_type,
        verbose=args.verbose,
        coverage=coverage,
        html_report=html_report,
    )

    if success:
        print("\n🎉 All tests completed successfully!")
        return 0
    else:
        print("\n💥 Some tests failed!")
        return 1


if __name__ == "__main__":
    sys.exit(main())

#!/usr/bin/env python3
"""
Live test script for Package Discovery Service

Tests real API calls to deps.dev and ClearlyDefined with sample PURLs.
Run this manually to verify discovery service works end-to-end.

Usage:
    python test_discovery_live.py
"""
import asyncio
import sys
from package_discovery import discover_package


async def test_discovery():
    """Test discovery with sample PURLs from different ecosystems."""

    test_cases = [
        ("pkg:npm/express@4.18.0", "npm - Express.js web framework"),
        ("pkg:pypi/requests", "PyPI - HTTP library"),
        ("pkg:maven/org.springframework.boot/spring-boot-starter", "Maven - Spring Boot"),
        ("pkg:golang/github.com/gin-gonic/gin", "Go - Gin web framework"),
        ("pkg:cargo/serde", "Rust - Serde serialization"),
    ]

    print("=" * 80)
    print("Package Discovery Service - Live Test")
    print("=" * 80)
    print()

    successes = 0
    failures = 0

    for purl, description in test_cases:
        print(f"Testing: {description}")
        print(f"  PURL: {purl}")

        try:
            result = await discover_package(purl)

            print(f"  ✓ Success via {result['source']}")
            print(f"    Ecosystem: {result['ecosystem']}")
            print(f"    Name: {result['name']}")
            print(f"    Version: {result.get('version', 'latest')}")
            print(f"    Repo URL: {result.get('repo_url', 'N/A')}")
            print(f"    License: {result.get('license', 'N/A')}")
            print(f"    Latest: {result.get('latest_version', 'N/A')}")

            successes += 1

        except Exception as e:
            print(f"  ✗ Failed: {e}")
            failures += 1

        print()

    print("=" * 80)
    print(f"Results: {successes} succeeded, {failures} failed")
    print("=" * 80)

    return failures == 0


if __name__ == "__main__":
    success = asyncio.run(test_discovery())
    sys.exit(0 if success else 1)

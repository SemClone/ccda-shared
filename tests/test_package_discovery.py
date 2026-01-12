"""
Tests for Package Discovery Service

Tests the fallback chain for package metadata discovery across
multiple ecosystems and data sources.

Copyright (c) 2026 Oscar Valenzuela <oscar.valenzuela.b@gmail.com>
All Rights Reserved.
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from shared.package_discovery import (
    PackageDiscoveryService,
    PackageMetadata,
    discover_package,
)


class TestPackageMetadata:
    """Test PackageMetadata data class."""

    def test_initialization(self):
        """Test metadata initialization."""
        metadata = PackageMetadata("pkg:npm/express@4.18.0")
        assert metadata.purl == "pkg:npm/express@4.18.0"
        assert metadata.ecosystem is None
        assert metadata.name is None
        assert metadata.version is None
        assert metadata.repo_url is None
        assert metadata.source is None

    def test_to_dict(self):
        """Test conversion to dictionary."""
        metadata = PackageMetadata("pkg:npm/express")
        metadata.ecosystem = "npm"
        metadata.name = "express"
        metadata.repo_url = "https://github.com/expressjs/express"
        metadata.source = "deps.dev"

        result = metadata.to_dict()
        assert result["purl"] == "pkg:npm/express"
        assert result["ecosystem"] == "npm"
        assert result["name"] == "express"
        assert result["repo_url"] == "https://github.com/expressjs/express"
        assert result["source"] == "deps.dev"

    def test_is_complete_true(self):
        """Test is_complete returns True with required fields."""
        metadata = PackageMetadata("pkg:npm/express")
        metadata.ecosystem = "npm"
        metadata.name = "express"
        metadata.repo_url = "https://github.com/expressjs/express"

        assert metadata.is_complete is True

    def test_is_complete_false(self):
        """Test is_complete returns False with missing fields."""
        metadata = PackageMetadata("pkg:npm/express")
        metadata.ecosystem = "npm"
        metadata.name = "express"
        # Missing repo_url

        assert metadata.is_complete is False


class TestPURLParsing:
    """Test PURL parsing logic."""

    def test_parse_purl_npm_simple(self):
        """Test parsing simple npm package."""
        service = PackageDiscoveryService()
        metadata = PackageMetadata("pkg:npm/express@4.18.0")

        result = service._parse_purl("pkg:npm/express@4.18.0", metadata)

        assert result is True
        assert metadata.ecosystem == "npm"
        assert metadata.name == "express"
        assert metadata.version == "4.18.0"

    def test_parse_purl_npm_no_version(self):
        """Test parsing npm package without version."""
        service = PackageDiscoveryService()
        metadata = PackageMetadata("pkg:npm/lodash")

        result = service._parse_purl("pkg:npm/lodash", metadata)

        assert result is True
        assert metadata.ecosystem == "npm"
        assert metadata.name == "lodash"
        assert metadata.version is None

    def test_parse_purl_pypi(self):
        """Test parsing PyPI package."""
        service = PackageDiscoveryService()
        metadata = PackageMetadata("pkg:pypi/requests@2.31.0")

        result = service._parse_purl("pkg:pypi/requests@2.31.0", metadata)

        assert result is True
        assert metadata.ecosystem == "pypi"
        assert metadata.name == "requests"
        assert metadata.version == "2.31.0"

    def test_parse_purl_maven_namespaced(self):
        """Test parsing namespaced Maven package."""
        service = PackageDiscoveryService()
        metadata = PackageMetadata("pkg:maven/org.springframework.boot/spring-boot-starter")

        result = service._parse_purl(
            "pkg:maven/org.springframework.boot/spring-boot-starter", metadata
        )

        assert result is True
        assert metadata.ecosystem == "maven"
        assert metadata.name == "org.springframework.boot/spring-boot-starter"

    def test_parse_purl_golang(self):
        """Test parsing Go package."""
        service = PackageDiscoveryService()
        metadata = PackageMetadata("pkg:golang/github.com/gin-gonic/gin@v1.9.0")

        result = service._parse_purl(
            "pkg:golang/github.com/gin-gonic/gin@v1.9.0", metadata
        )

        assert result is True
        assert metadata.ecosystem == "golang"
        assert metadata.name == "github.com/gin-gonic/gin"
        assert metadata.version == "v1.9.0"

    def test_parse_purl_cargo(self):
        """Test parsing Cargo (Rust) package."""
        service = PackageDiscoveryService()
        metadata = PackageMetadata("pkg:cargo/serde@1.0.0")

        result = service._parse_purl("pkg:cargo/serde@1.0.0", metadata)

        assert result is True
        assert metadata.ecosystem == "cargo"
        assert metadata.name == "serde"
        assert metadata.version == "1.0.0"

    def test_parse_purl_github(self):
        """Test parsing GitHub repo as package."""
        service = PackageDiscoveryService()
        metadata = PackageMetadata("pkg:github/expressjs/express")

        result = service._parse_purl("pkg:github/expressjs/express", metadata)

        assert result is True
        assert metadata.ecosystem == "github"
        assert metadata.name == "expressjs/express"

    def test_parse_purl_invalid_no_prefix(self):
        """Test parsing invalid PURL without pkg: prefix."""
        service = PackageDiscoveryService()
        metadata = PackageMetadata("npm/express")

        result = service._parse_purl("npm/express", metadata)

        assert result is False

    def test_parse_purl_invalid_no_name(self):
        """Test parsing invalid PURL without package name."""
        service = PackageDiscoveryService()
        metadata = PackageMetadata("pkg:npm")

        result = service._parse_purl("pkg:npm", metadata)

        assert result is False


class TestMetadataMerging:
    """Test metadata merging logic."""

    def test_merge_metadata_fill_missing(self):
        """Test merging fills missing fields."""
        service = PackageDiscoveryService()

        base = PackageMetadata("pkg:npm/express")
        base.ecosystem = "npm"
        base.name = "express"
        base.repo_url = "https://github.com/expressjs/express"

        new = PackageMetadata("pkg:npm/express")
        new.license = "MIT"
        new.description = "Fast web framework"

        result = service._merge_metadata(base, new)

        assert result.ecosystem == "npm"
        assert result.name == "express"
        assert result.repo_url == "https://github.com/expressjs/express"
        assert result.license == "MIT"
        assert result.description == "Fast web framework"

    def test_merge_metadata_prefer_base(self):
        """Test merging prefers base for existing fields."""
        service = PackageDiscoveryService()

        base = PackageMetadata("pkg:npm/express")
        base.ecosystem = "npm"
        base.license = "MIT"

        new = PackageMetadata("pkg:npm/express")
        new.license = "Apache-2.0"  # Should be ignored

        result = service._merge_metadata(base, new)

        assert result.license == "MIT"  # Base wins

    def test_merge_metadata_maintainers(self):
        """Test merging combines maintainer lists."""
        service = PackageDiscoveryService()

        base = PackageMetadata("pkg:npm/express")
        base.maintainers = ["alice@example.com"]

        new = PackageMetadata("pkg:npm/express")
        new.maintainers = ["bob@example.com", "alice@example.com"]

        result = service._merge_metadata(base, new)

        assert len(result.maintainers) == 2  # Deduplicated
        assert "alice@example.com" in result.maintainers
        assert "bob@example.com" in result.maintainers


@pytest.mark.asyncio
class TestDepsDevFetcher:
    """Test deps.dev API integration."""

    async def test_fetch_deps_dev_unsupported_ecosystem(self):
        """Test deps.dev returns None for unsupported ecosystems."""
        service = PackageDiscoveryService()
        metadata = PackageMetadata("pkg:rubygems/rails")
        metadata.ecosystem = "rubygems"
        metadata.name = "rails"

        result = await service._fetch_deps_dev(metadata)

        assert result is None

    @patch("httpx.AsyncClient")
    async def test_fetch_deps_dev_npm_success(self, mock_client_class):
        """Test successful deps.dev fetch for npm package."""
        # Mock response data
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "versions": [{"versionKey": {"version": "4.18.2"}}]
        }

        mock_version_response = MagicMock()
        mock_version_response.status_code = 200
        mock_version_response.json.return_value = {
            "links": [
                {
                    "label": "SOURCE_REPO",
                    "url": "https://github.com/expressjs/express",
                },
                {"label": "HOMEPAGE", "url": "https://expressjs.com"},
            ],
            "licenses": ["MIT"],
        }

        # Mock client
        mock_client = AsyncMock()
        mock_client.get.side_effect = [mock_response, mock_version_response]
        mock_client.__aenter__.return_value = mock_client
        mock_client_class.return_value = mock_client

        service = PackageDiscoveryService()
        metadata = PackageMetadata("pkg:npm/express")
        metadata.ecosystem = "npm"
        metadata.name = "express"

        result = await service._fetch_deps_dev(metadata)

        assert result is not None
        assert result.ecosystem == "npm"
        assert result.name == "express"
        assert result.latest_version == "4.18.2"
        assert result.repo_url == "https://github.com/expressjs/express"
        assert result.license == "MIT"
        assert result.homepage == "https://expressjs.com"

    @patch("httpx.AsyncClient")
    async def test_fetch_deps_dev_404(self, mock_client_class):
        """Test deps.dev returns None on 404."""
        mock_response = MagicMock()
        mock_response.status_code = 404

        mock_client = AsyncMock()
        mock_client.get.return_value = mock_response
        mock_client.__aenter__.return_value = mock_client
        mock_client_class.return_value = mock_client

        service = PackageDiscoveryService()
        metadata = PackageMetadata("pkg:npm/nonexistent-package")
        metadata.ecosystem = "npm"
        metadata.name = "nonexistent-package"

        result = await service._fetch_deps_dev(metadata)

        assert result is None


@pytest.mark.asyncio
class TestClearlyDefinedFetcher:
    """Test ClearlyDefined API integration."""

    @patch("httpx.AsyncClient")
    async def test_fetch_clearlydefined_success(self, mock_client_class):
        """Test successful ClearlyDefined fetch."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "described": {
                "license": "MIT",
                "sourceLocation": {
                    "type": "git",
                    "provider": "github.com",
                    "namespace": "expressjs",
                    "name": "express",
                },
                "projectWebsite": "https://expressjs.com",
            }
        }

        mock_client = AsyncMock()
        mock_client.get.return_value = mock_response
        mock_client.__aenter__.return_value = mock_client
        mock_client_class.return_value = mock_client

        service = PackageDiscoveryService()
        metadata = PackageMetadata("pkg:npm/express")
        metadata.ecosystem = "npm"
        metadata.name = "express"

        result = await service._fetch_clearlydefined(metadata)

        assert result is not None
        assert result.license == "MIT"
        assert result.repo_url == "https://github.com/expressjs/express"
        assert result.homepage == "https://expressjs.com"

    async def test_fetch_clearlydefined_unsupported_ecosystem(self):
        """Test ClearlyDefined returns None for unsupported ecosystems."""
        service = PackageDiscoveryService()
        metadata = PackageMetadata("pkg:unknown/package")
        metadata.ecosystem = "unknown"
        metadata.name = "package"

        result = await service._fetch_clearlydefined(metadata)

        assert result is None


@pytest.mark.asyncio
class TestDiscoveryService:
    """Test full discovery workflow."""

    async def test_discover_invalid_purl(self):
        """Test discovery fails with invalid PURL."""
        service = PackageDiscoveryService()

        with pytest.raises(ValueError, match="Invalid PURL format"):
            await service.discover("invalid-purl")

    @patch.object(PackageDiscoveryService, "_fetch_deps_dev")
    async def test_discover_success_first_source(self, mock_fetch):
        """Test discovery succeeds with first source."""
        # Mock complete metadata from deps.dev
        complete_metadata = PackageMetadata("pkg:npm/express")
        complete_metadata.ecosystem = "npm"
        complete_metadata.name = "express"
        complete_metadata.repo_url = "https://github.com/expressjs/express"
        complete_metadata.license = "MIT"

        mock_fetch.return_value = complete_metadata

        service = PackageDiscoveryService()
        result = await service.discover("pkg:npm/express")

        assert result.is_complete
        assert result.source == "deps.dev"
        assert result.repo_url == "https://github.com/expressjs/express"

    @patch.object(PackageDiscoveryService, "_fetch_deps_dev")
    @patch.object(PackageDiscoveryService, "_fetch_clearlydefined")
    async def test_discover_fallback_to_second_source(
        self, mock_clearlydefined, mock_deps_dev
    ):
        """Test discovery falls back to second source."""
        # deps.dev fails
        mock_deps_dev.return_value = None

        # ClearlyDefined succeeds
        complete_metadata = PackageMetadata("pkg:npm/express")
        complete_metadata.ecosystem = "npm"
        complete_metadata.name = "express"
        complete_metadata.repo_url = "https://github.com/expressjs/express"

        mock_clearlydefined.return_value = complete_metadata

        service = PackageDiscoveryService()
        result = await service.discover("pkg:npm/express")

        assert result.is_complete
        assert result.source == "clearlydefined"

    @patch.object(PackageDiscoveryService, "_fetch_deps_dev")
    @patch.object(PackageDiscoveryService, "_fetch_clearlydefined")
    @patch.object(PackageDiscoveryService, "_fetch_purl2src")
    @patch.object(PackageDiscoveryService, "_fetch_upmex")
    async def test_discover_all_sources_fail(
        self, mock_upmex, mock_purl2src, mock_clearlydefined, mock_deps_dev
    ):
        """Test discovery fails when all sources fail."""
        # All sources return None or incomplete
        mock_deps_dev.return_value = None
        mock_clearlydefined.return_value = None
        mock_purl2src.return_value = None
        mock_upmex.return_value = None

        service = PackageDiscoveryService()

        with pytest.raises(ValueError, match="Could not discover complete metadata"):
            await service.discover("pkg:npm/nonexistent")


@pytest.mark.asyncio
class TestConvenienceFunction:
    """Test discover_package convenience function."""

    @patch.object(PackageDiscoveryService, "discover")
    async def test_discover_package(self, mock_discover):
        """Test convenience function calls service correctly."""
        # Mock discovery result
        metadata = PackageMetadata("pkg:npm/express")
        metadata.ecosystem = "npm"
        metadata.name = "express"
        metadata.repo_url = "https://github.com/expressjs/express"

        mock_discover.return_value = metadata

        result = await discover_package("pkg:npm/express")

        assert isinstance(result, dict)
        assert result["ecosystem"] == "npm"
        assert result["name"] == "express"
        assert result["repo_url"] == "https://github.com/expressjs/express"

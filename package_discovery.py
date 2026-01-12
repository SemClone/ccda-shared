"""
Package Discovery Service

**What:**
Enriches package URLs (PURLs) with metadata from multiple public sources.
Implements a fallback chain across 5 data providers to maximize coverage.

**How:**
1. Parse PURL to extract ecosystem and package name
2. Try data sources in priority order:
   - deps.dev (Google's dependency analysis) - Primary
   - clearlydefined (OSI-backed license data) - Fallback 1
   - purl2src (Package → source mapping) - Fallback 2
   - upmex (Universal package metadata) - Fallback 3
   - SerpAPI (Web search) - Fallback 4
3. Return enriched metadata (repo URL, license, description, etc.)

**Why:**
- No single source has complete data for all ecosystems
- Fallback chain maximizes discovery success rate
- Enables tracking packages even with incomplete metadata
- Supports 12+ package ecosystems

**Usage:**
    from shared.package_discovery import PackageDiscoveryService

    discovery = PackageDiscoveryService()
    metadata = await discovery.discover("pkg:npm/express@4.18.0")
    # Returns: repo_url, license, description, homepage, latest_version, etc.

**Data Sources:**
- deps.dev: Best for npm, Maven, Go, PyPI (Google-backed)
- clearlydefined: Best for license data (OSI-backed)
- purl2src: Best for repo URL mapping (GitHub-focused)
- upmex: Universal metadata exchange (community-driven)
- SerpAPI: Last resort (requires API key, costs money)

Copyright (c) 2026 Oscar Valenzuela <oscar.valenzuela.b@gmail.com>
All Rights Reserved.
"""
import logging
import re
from typing import Optional, Dict, Any
from urllib.parse import quote, urlparse

logger = logging.getLogger(__name__)


class PackageMetadata:
    """
    Enriched package metadata from discovery sources.

    Attributes:
        purl: Original package URL
        ecosystem: Package ecosystem (npm, pypi, maven, etc.)
        name: Package name
        version: Package version (if specified)
        repo_url: Repository URL (GitHub, GitLab, etc.)
        license: SPDX license identifier
        description: Package description
        homepage: Official homepage URL
        latest_version: Latest version available
        maintainers: List of maintainer names/emails (if available)
        source: Which data source provided this metadata
    """

    def __init__(self, purl: str):
        self.purl = purl
        self.ecosystem: Optional[str] = None
        self.name: Optional[str] = None
        self.version: Optional[str] = None
        self.repo_url: Optional[str] = None
        self.license: Optional[str] = None
        self.description: Optional[str] = None
        self.homepage: Optional[str] = None
        self.latest_version: Optional[str] = None
        self.maintainers: list[str] = []
        self.source: Optional[str] = None  # Which provider gave us data

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "purl": self.purl,
            "ecosystem": self.ecosystem,
            "name": self.name,
            "version": self.version,
            "repo_url": self.repo_url,
            "license": self.license,
            "description": self.description,
            "homepage": self.homepage,
            "latest_version": self.latest_version,
            "maintainers": self.maintainers,
            "source": self.source,
        }

    @property
    def is_complete(self) -> bool:
        """Check if we have minimum required metadata."""
        return bool(self.ecosystem and self.name and self.repo_url)


class PackageDiscoveryService:
    """
    Discovers package metadata from multiple public sources.

    Implements fallback chain for maximum coverage across ecosystems.
    """

    def __init__(self, serpapi_key: Optional[str] = None):
        """
        Initialize discovery service.

        Args:
            serpapi_key: Optional SerpAPI key for web search fallback
        """
        self.serpapi_key = serpapi_key

    async def discover(self, purl: str, allow_partial: bool = False) -> PackageMetadata:
        """
        Discover metadata for a package URL.

        Args:
            purl: Package URL (e.g., pkg:npm/express@4.18.0)
            allow_partial: If True, return partial metadata without raising errors

        Returns:
            PackageMetadata with enriched data from discovery sources

        Raises:
            ValueError: If PURL is invalid or no metadata found (unless allow_partial=True)
        """
        metadata = PackageMetadata(purl)

        # Parse PURL
        if not self._parse_purl(purl, metadata):
            raise ValueError(f"Invalid PURL format: {purl}")

        logger.info(f"Discovering metadata for {metadata.ecosystem}/{metadata.name}")

        # Special handling for GitHub packages - extract URL from PURL
        if metadata.ecosystem == "github":
            # pkg:github/owner/repo -> https://github.com/owner/repo
            if metadata.name and "/" in metadata.name:
                metadata.repo_url = f"https://github.com/{metadata.name}"
                logger.info(f"Extracted GitHub repo URL from PURL: {metadata.repo_url}")

                # Try to get latest release from GitHub API
                try:
                    import httpx
                    async with httpx.AsyncClient(timeout=5.0) as client:
                        api_url = f"https://api.github.com/repos/{metadata.name}/releases/latest"
                        response = await client.get(api_url)
                        if response.status_code == 200:
                            release_data = response.json()
                            tag_name = release_data.get("tag_name", "")
                            # Remove 'v' prefix if present (e.g., v1.14.3 -> 1.14.3)
                            metadata.latest_version = tag_name.lstrip("v") if tag_name else None
                            logger.info(f"Got latest GitHub release: {metadata.latest_version}")
                except Exception as e:
                    logger.debug(f"Could not fetch GitHub latest release: {e}")

        # Special handling for Go packages - name often contains GitHub URL
        if metadata.ecosystem in ["golang", "go"]:
            if metadata.name.startswith("github.com/"):
                # Extract GitHub URL directly from package name
                # e.g., github.com/gorilla/mux -> https://github.com/gorilla/mux
                parts = metadata.name.split("/")
                if len(parts) >= 3:  # github.com/owner/repo
                    metadata.repo_url = f"https://{'/'.join(parts[:3])}"
                    logger.info(f"Extracted repo URL from Go package name: {metadata.repo_url}")
            elif metadata.name.startswith("gitlab.com/"):
                parts = metadata.name.split("/")
                if len(parts) >= 3:
                    metadata.repo_url = f"https://{'/'.join(parts[:3])}"
                    logger.info(f"Extracted repo URL from Go package name: {metadata.repo_url}")

        # Try data sources in priority order
        sources = [
            ("deps.dev", self._fetch_deps_dev),
            ("clearlydefined", self._fetch_clearlydefined),
            ("purl2src", self._fetch_purl2src),
            ("upmex", self._fetch_upmex),
        ]

        # Add SerpAPI if key provided
        if self.serpapi_key:
            sources.append(("serpapi", self._fetch_serpapi))

        for source_name, fetch_func in sources:
            try:
                logger.debug(f"Trying {source_name}...")
                result = await fetch_func(metadata)

                if result and result.is_complete:
                    result.source = source_name
                    logger.info(f"Discovery successful via {source_name}")
                    return result

                # Partial data - merge and continue
                if result:
                    metadata = self._merge_metadata(metadata, result)

            except Exception as e:
                logger.warning(f"{source_name} failed: {e}")
                continue

        # Check if we got enough data (skip validation if allow_partial=True)
        if not allow_partial and not metadata.is_complete:
            missing = []
            if not metadata.ecosystem:
                missing.append("ecosystem")
            if not metadata.name:
                missing.append("name")
            if not metadata.repo_url:
                missing.append("repo_url")
            raise ValueError(
                f"Could not discover complete metadata for {purl}. "
                f"Missing: {', '.join(missing)}"
            )

        return metadata

    def _parse_purl(self, purl: str, metadata: PackageMetadata) -> bool:
        """
        Parse PURL into components.

        PURL format: pkg:type/namespace/name@version?qualifiers#subpath
        Examples:
          - pkg:npm/express@4.18.0
          - pkg:pypi/requests
          - pkg:maven/org.springframework.boot/spring-boot-starter
          - pkg:golang/github.com/gin-gonic/gin@v1.9.0
          - pkg:github/expressjs/express

        Returns:
            True if valid PURL, False otherwise
        """
        # Basic PURL validation
        if not purl.startswith("pkg:"):
            return False

        # Remove pkg: prefix
        purl_body = purl[4:]

        # Split by @ for version
        if "@" in purl_body:
            purl_body, version = purl_body.split("@", 1)
            # Remove qualifiers/subpath
            version = version.split("?")[0].split("#")[0]
            metadata.version = version

        # Split by / for ecosystem and name
        parts = purl_body.split("/")
        if len(parts) < 2:
            return False

        metadata.ecosystem = parts[0]

        # Handle namespaced packages (Maven, Go, etc.)
        if len(parts) == 2:
            metadata.name = parts[1]
        else:
            # Maven: org.springframework.boot/spring-boot-starter
            # Go: golang/github.com/gin-gonic/gin
            metadata.name = "/".join(parts[1:])

        return True

    async def _fetch_deps_dev(self, metadata: PackageMetadata) -> Optional[PackageMetadata]:
        """
        Fetch from deps.dev (Google's Open Source Insights).

        Best for: npm, PyPI, Go, Maven, Cargo
        API: https://docs.deps.dev/api/v3/
        """
        import httpx

        # Map PURL ecosystems to deps.dev system names
        system_map = {
            "npm": "npm",
            "pypi": "pypi",
            "maven": "maven",
            "golang": "go",
            "cargo": "cargo",
            "go": "go",
            "nuget": "nuget",
        }

        system = system_map.get(metadata.ecosystem)
        if not system:
            logger.debug(f"deps.dev doesn't support {metadata.ecosystem}")
            return None

        # Maven packages need groupId:artifactId format for deps.dev
        # PURL uses / separator, but Maven Central uses :
        package_name = metadata.name
        if metadata.ecosystem == "maven":
            package_name = metadata.name.replace("/", ":")

        # Encode package name for URL
        encoded_name = quote(package_name, safe="")

        # Get package info
        url = f"https://api.deps.dev/v3/systems/{system}/packages/{encoded_name}"

        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(url)

            if response.status_code != 200:
                logger.debug(f"deps.dev returned {response.status_code}")
                return None

            data = response.json()

            result = PackageMetadata(metadata.purl)
            result.ecosystem = metadata.ecosystem
            result.name = metadata.name
            result.version = metadata.version

            # Get latest version
            if "versions" in data and data["versions"]:
                # Versions are sorted by release time (oldest first), so take the last one
                result.latest_version = data["versions"][-1]["versionKey"]["version"]

            # Get version-specific metadata
            version_url = f"{url}/versions/{quote(metadata.version or result.latest_version or '', safe='')}"

            try:
                version_response = await client.get(version_url)
                if version_response.status_code == 200:
                    version_data = version_response.json()

                    # Extract links (repo, homepage)
                    if "links" in version_data:
                        for link in version_data["links"]:
                            label = link.get("label", "").lower()
                            url_val = link.get("url", "")

                            # Detect repository URLs (GitHub, GitLab, etc.)
                            if any(host in url_val.lower() for host in ["github.com", "gitlab.com", "bitbucket.org"]):
                                # Clean up git+ prefix, .git suffix, and paths like /issues, /pulls
                                cleaned_url = url_val.replace("git+", "").replace(".git", "")
                                # Remove trailing paths (issues, pulls, wiki, etc.)
                                for suffix in ["/issues", "/pulls", "/wiki", "/tree", "/blob"]:
                                    if suffix in cleaned_url:
                                        cleaned_url = cleaned_url.split(suffix)[0]
                                if not result.repo_url:  # Prefer first repo URL found
                                    result.repo_url = cleaned_url
                            elif "homepage" in label and not result.homepage:
                                result.homepage = url_val

                    # Extract licenses
                    if "licenses" in version_data and version_data["licenses"]:
                        result.license = version_data["licenses"][0]

                    # Description not directly available in API

            except Exception as e:
                logger.debug(f"Could not fetch version details: {e}")

            return result

    async def _fetch_clearlydefined(self, metadata: PackageMetadata) -> Optional[PackageMetadata]:
        """
        Fetch from ClearlyDefined (OSI-backed license and metadata).

        Best for: License data, comprehensive metadata
        API: https://api.clearlydefined.io/api-docs/
        """
        import httpx

        # Map PURL ecosystems to ClearlyDefined types
        type_map = {
            "npm": "npm",
            "pypi": "pypi",
            "maven": "maven",
            "golang": "go",
            "go": "go",
            "cargo": "crate",
            "nuget": "nuget",
            "gem": "gem",
        }

        cd_type = type_map.get(metadata.ecosystem)
        if not cd_type:
            return None

        # Build coordinates: type/provider/namespace/name/version
        # Example: npm/npmjs/-/express/4.18.0
        provider = "npmjs" if cd_type == "npm" else cd_type
        namespace = "-"  # Default for non-namespaced packages

        # Handle namespaced packages
        if "/" in metadata.name:
            parts = metadata.name.split("/", 1)
            namespace = quote(parts[0], safe="")
            name = quote(parts[1], safe="")
        else:
            name = quote(metadata.name, safe="")

        version = metadata.version or "-"

        coordinates = f"{cd_type}/{provider}/{namespace}/{name}/{version}"
        url = f"https://api.clearlydefined.io/definitions/{coordinates}"

        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(url)

            if response.status_code != 200:
                logger.debug(f"ClearlyDefined returned {response.status_code}")
                return None

            try:
                data = response.json()
            except Exception as e:
                logger.debug(f"ClearlyDefined JSON parse error: {e}")
                return None

            result = PackageMetadata(metadata.purl)
            result.ecosystem = metadata.ecosystem
            result.name = metadata.name
            result.version = metadata.version

            # Extract described data
            described = data.get("described", {})
            result.license = described.get("license")

            # Source location (repo URL)
            if "sourceLocation" in described:
                source = described["sourceLocation"]
                if source.get("type") == "git":
                    provider = source.get("provider", "")
                    namespace = source.get("namespace", "")
                    name = source.get("name", "")

                    if provider and namespace and name:
                        result.repo_url = f"https://{provider}/{namespace}/{name}"

            # Project URL
            if "projectWebsite" in described:
                result.homepage = described["projectWebsite"]

            return result

    async def _fetch_purl2src(self, metadata: PackageMetadata) -> Optional[PackageMetadata]:
        """
        Fetch from purl2src (Package URL to source repository mapping).

        Best for: Finding GitHub repo URLs from PURLs
        API: Hypothetical - may need implementation check
        """
        # Note: purl2src is a concept/tool but may not have public API
        # For now, returning None - can implement if API exists
        logger.debug("purl2src not yet implemented")
        return None

    async def _fetch_upmex(self, metadata: PackageMetadata) -> Optional[PackageMetadata]:
        """
        Fetch from UPMEX (Universal Package Metadata Exchange).

        Best for: Cross-ecosystem metadata
        Note: UPMEX is a proposed standard - implementation TBD
        """
        logger.debug("upmex not yet implemented")
        return None

    async def _fetch_serpapi(self, metadata: PackageMetadata) -> Optional[PackageMetadata]:
        """
        Fetch via SerpAPI (Google Search fallback).

        Last resort: Search for "package_name ecosystem" and extract repo URL
        Requires: SERPAPI_KEY environment variable
        Cost: ~$0.0025 per search (1000 searches = $2.50)
        """
        if not self.serpapi_key:
            return None

        import httpx

        # Build search query
        query = f"{metadata.name} {metadata.ecosystem} github repository"

        params = {
            "q": query,
            "api_key": self.serpapi_key,
            "num": 3,  # Only need top 3 results
        }

        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get("https://serpapi.com/search", params=params)

            if response.status_code != 200:
                return None

            data = response.json()

            # Extract GitHub URL from results
            for result in data.get("organic_results", []):
                link = result.get("link", "")

                if "github.com" in link:
                    # Clean up URL
                    parsed = urlparse(link)
                    path_parts = parsed.path.strip("/").split("/")

                    if len(path_parts) >= 2:
                        repo_url = f"https://github.com/{path_parts[0]}/{path_parts[1]}"

                        result_metadata = PackageMetadata(metadata.purl)
                        result_metadata.ecosystem = metadata.ecosystem
                        result_metadata.name = metadata.name
                        result_metadata.version = metadata.version
                        result_metadata.repo_url = repo_url
                        result_metadata.description = result.get("snippet")

                        return result_metadata

        return None

    def _merge_metadata(
        self, base: PackageMetadata, new: PackageMetadata
    ) -> PackageMetadata:
        """
        Merge metadata from multiple sources.

        Strategy: Fill in missing fields, prefer base for existing fields
        """
        result = PackageMetadata(base.purl)

        result.ecosystem = base.ecosystem or new.ecosystem
        result.name = base.name or new.name
        result.version = base.version or new.version
        result.repo_url = base.repo_url or new.repo_url
        result.license = base.license or new.license
        result.description = base.description or new.description
        result.homepage = base.homepage or new.homepage
        result.latest_version = base.latest_version or new.latest_version

        # Merge maintainer lists
        result.maintainers = list(set(base.maintainers + new.maintainers))

        result.source = base.source or new.source

        return result


# Convenience function for quick discovery
async def discover_package(purl: str, serpapi_key: Optional[str] = None) -> Dict[str, Any]:
    """
    Discover package metadata (convenience function).

    Args:
        purl: Package URL (e.g., pkg:npm/express@4.18.0)
        serpapi_key: Optional SerpAPI key for web search fallback

    Returns:
        Dictionary with package metadata

    Raises:
        ValueError: If discovery fails
    """
    service = PackageDiscoveryService(serpapi_key=serpapi_key)
    metadata = await service.discover(purl)
    return metadata.to_dict()

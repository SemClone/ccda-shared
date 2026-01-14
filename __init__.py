"""
CCDA Shared Library

Common utilities, models, and constants used across all CCDA components.

Components:
- storage: SpacesClient for DigitalOcean Spaces operations
- models: Pydantic data models for validation and serialization
- constants: Centralized constants and configuration values
- vulnerability_matcher: VulnerabilityMatcher for package-vulnerability linking

Usage:
    from shared.storage import SpacesClient
    from shared.models import Vulnerability, Package, MediaItem
    from shared.constants import SPACES_PATH_DUCKDB, HEALTH_GRADE_A_MIN
    from shared.vulnerability_matcher import VulnerabilityMatcher
"""

__version__ = "1.1.0"
__author__ = "CCDA Team"

# Import commonly used classes for convenience
from .env import get_env_value, get_spaces_config
from .storage import SpacesClient
from .models import (
    Vulnerability,
    Package,
    MediaItem,
    Job,
    HealthMetrics,
    PackageAnalysisResult,
)
from .constants import CCDA_VERSION
from .vulnerability_matcher import VulnerabilityMatcher

__all__ = [
    "get_env_value",
    "get_spaces_config",
    "SpacesClient",
    "Vulnerability",
    "Package",
    "MediaItem",
    "Job",
    "HealthMetrics",
    "PackageAnalysisResult",
    "CCDA_VERSION",
    "VulnerabilityMatcher",
]

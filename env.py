"""Environment variable helpers for CCDA."""
from __future__ import annotations

import logging
import os
from typing import Dict, Optional

logger = logging.getLogger(__name__)

DEFAULT_SPACES_REGION = "sfo3"
DEFAULT_SPACES_BUCKET = "ccda-data"


def get_env_value(primary: str, *fallbacks: str, default: Optional[str] = None) -> Optional[str]:
    """Return the first available environment variable value."""
    for name in (primary, *fallbacks):
        value = os.environ.get(name)
        if value:
            if name != primary:
                logger.debug("Using fallback env %s for %s", name, primary)
            return value
    return default


def get_spaces_config(**overrides: Optional[str]) -> Dict[str, Optional[str]]:
    """Build a consistent Spaces configuration, honoring DO_* fallbacks."""
    # Explicit overrides from callers should win over env vars
    key = overrides.get("key") or get_env_value("SPACES_KEY", "DO_SPACES_KEY")
    secret = overrides.get("secret") or get_env_value("SPACES_SECRET", "DO_SPACES_SECRET")
    region = overrides.get("region") or get_env_value(
        "SPACES_REGION", "DO_SPACES_REGION", default=DEFAULT_SPACES_REGION
    )
    bucket = overrides.get("bucket") or get_env_value(
        "SPACES_BUCKET", "DO_SPACES_BUCKET", default=DEFAULT_SPACES_BUCKET
    )

    endpoint = overrides.get("endpoint") or get_env_value("SPACES_ENDPOINT", "DO_SPACES_ENDPOINT")
    if not endpoint:
        endpoint = f"https://{region}.digitaloceanspaces.com"

    return {
        "key": key,
        "secret": secret,
        "region": region,
        "bucket": bucket,
        "endpoint": endpoint,
    }

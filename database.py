"""
Copyright (c) 2026 Oscar Valenzuela <oscar.valenzuela.b@gmail.com>
All Rights Reserved.

This file is part of CCDA, a proprietary commercial software project.
Unauthorized copying, distribution, or use is strictly prohibited.

Database Utility Functions
"""

import os
import logging
import asyncpg
from typing import Optional

logger = logging.getLogger(__name__)


async def get_database_connection(timeout: int = 10) -> asyncpg.Connection:
    """
    Get database connection with standard error handling.

    Args:
        timeout: Connection timeout in seconds (default: 10)

    Returns:
        asyncpg.Connection: Database connection

    Raises:
        ValueError: If DATABASE_URL environment variable is not set
        asyncpg.PostgresError: If connection fails

    Example:
        ```python
        conn = await get_database_connection()
        try:
            result = await conn.fetch("SELECT * FROM packages")
        finally:
            await conn.close()
        ```
    """
    database_url = os.getenv("DATABASE_URL")

    if not database_url:
        error_msg = "DATABASE_URL environment variable not set"
        logger.error(error_msg)
        raise ValueError(error_msg)

    try:
        conn = await asyncpg.connect(database_url, timeout=timeout)
        logger.debug(f"Database connection established (timeout={timeout}s)")
        return conn
    except asyncpg.PostgresError as e:
        logger.error(f"Failed to connect to database: {e}")
        raise
    except Exception as e:
        logger.error(f"Unexpected error connecting to database: {e}")
        raise


def get_database_url() -> str:
    """
    Get DATABASE_URL environment variable with validation.

    Returns:
        str: Database connection URL

    Raises:
        ValueError: If DATABASE_URL environment variable is not set
    """
    database_url = os.getenv("DATABASE_URL")

    if not database_url:
        error_msg = "DATABASE_URL environment variable not set"
        logger.error(error_msg)
        raise ValueError(error_msg)

    return database_url

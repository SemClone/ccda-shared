"""
Database Migration System

Automatically detects and applies schema migrations on startup.
Inspired by PHP migration systems - checks if DB exists, creates schema if needed.

**What:**
- Auto-detects if database is initialized
- Applies migrations in order (001, 002, etc.)
- Tracks applied migrations in database
- Works with any PostgreSQL instance (portable across providers)

**How:**
- Reads migration files from shared/migrations/sql/
- Checks migrations table to see what's applied
- Applies pending migrations in transaction
- Rolls back on error

**Why:**
- Zero-config database setup on first deploy
- Easy to migrate to different cloud providers
- Version-controlled schema changes
- Safe rollback on errors
"""
import os
import logging
from typing import Optional
from datetime import datetime, timezone

logger = logging.getLogger(__name__)


class DatabaseMigrator:
    """
    Handles automatic database schema migrations.

    Similar to PHP migration systems - detects if database is fresh and
    auto-creates schema on first run.
    """

    def __init__(self, db_connection):
        """
        Initialize migrator with database connection.

        Args:
            db_connection: PostgreSQL connection object (psycopg or asyncpg)
        """
        self.conn = db_connection
        self.migrations_dir = os.path.join(
            os.path.dirname(__file__),
            'sql'
        )

    async def ensure_migrations_table(self):
        """Create migrations tracking table if it doesn't exist."""
        await self.conn.execute("""
            CREATE TABLE IF NOT EXISTS schema_migrations (
                id SERIAL PRIMARY KEY,
                migration_file VARCHAR(255) UNIQUE NOT NULL,
                applied_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                checksum VARCHAR(64)
            )
        """)
        logger.info("Migrations tracking table verified")

    async def get_applied_migrations(self) -> set:
        """Get set of already-applied migration files."""
        rows = await self.conn.fetch(
            "SELECT migration_file FROM schema_migrations ORDER BY id"
        )
        return {row['migration_file'] for row in rows}

    async def get_pending_migrations(self) -> list:
        """Get list of migration files that haven't been applied yet."""
        if not os.path.exists(self.migrations_dir):
            logger.warning(f"Migrations directory not found: {self.migrations_dir}")
            return []

        applied = await self.get_applied_migrations()
        all_migrations = sorted([
            f for f in os.listdir(self.migrations_dir)
            if f.endswith('.sql')
        ])

        pending = [m for m in all_migrations if m not in applied]
        return pending

    async def apply_migration(self, migration_file: str):
        """
        Apply a single migration file within a transaction.

        Args:
            migration_file: Name of the migration file (e.g., '001_initial_schema.sql')
        """
        migration_path = os.path.join(self.migrations_dir, migration_file)

        logger.info(f"Applying migration: {migration_file}")

        with open(migration_path, 'r') as f:
            sql = f.read()

        # Calculate checksum for integrity verification
        import hashlib
        checksum = hashlib.sha256(sql.encode()).hexdigest()

        async with self.conn.transaction():
            # Apply migration
            # Split SQL into individual statements
            # This handles CREATE TABLE, CREATE INDEX, CREATE VIEW, etc. properly

            # Remove full-line comments only (inline comments already removed from SQL files)
            cleaned_lines = []
            for line in sql.split('\n'):
                # Skip full-line comments
                if line.strip().startswith('--'):
                    continue
                cleaned_lines.append(line)

            cleaned_sql = '\n'.join(cleaned_lines)

            # Split on semicolons but respect function bodies ($$)
            statements = []
            current = []
            in_dollar_quote = False

            for char_idx, char in enumerate(cleaned_sql):
                current.append(char)

                # Check for $$ (function delimiter)
                if char == '$' and char_idx + 1 < len(cleaned_sql) and cleaned_sql[char_idx + 1] == '$':
                    in_dollar_quote = not in_dollar_quote

                # Split on semicolon if not in dollar quote
                if char == ';' and not in_dollar_quote:
                    stmt = ''.join(current).strip()
                    if stmt and len(stmt) > 1:  # Skip empty or just semicolon
                        statements.append(stmt)
                    current = []

            # Add any remaining statement
            if current:
                stmt = ''.join(current).strip()
                if stmt:
                    statements.append(stmt)

            # Execute each statement separately
            logger.info(f"Executing {len(statements)} SQL statements from migration")
            for i, stmt in enumerate(statements, 1):
                if stmt.strip():
                    # Special logging for first statement to debug CREATE TABLE issue
                    if i == 1 and 'CREATE TABLE' in stmt:
                        logger.info(f"Statement 1 (CREATE TABLE) full content:")
                        logger.info(f"{stmt}")
                        logger.info(f"'cve_id' in statement: {'cve_id' in stmt}")
                    else:
                        logger.debug(f"Statement {i}/{len(statements)}: {stmt[:80]}...")

                    try:
                        await self.conn.execute(stmt)
                        if i == 1:
                            logger.info(f"✓ Statement 1 executed successfully")
                        else:
                            logger.debug(f"✓ Statement {i} executed successfully")
                    except Exception as e:
                        logger.error(f"Failed on statement {i}/{len(statements)}")
                        logger.error(f"Statement: {stmt[:300]}")
                        logger.error(f"Error: {e}")
                        raise

            # Record migration
            await self.conn.execute(
                """
                INSERT INTO schema_migrations (migration_file, checksum)
                VALUES ($1, $2)
                """,
                migration_file,
                checksum
            )

        logger.info(f"✅ Migration applied: {migration_file}")

    async def run_migrations(self, auto_apply: bool = True) -> dict:
        """
        Run all pending migrations.

        Args:
            auto_apply: If True, automatically applies migrations.
                       If False, just returns status.

        Returns:
            Dictionary with migration status:
            {
                'database_exists': bool,
                'pending_count': int,
                'applied_count': int,
                'pending_migrations': list,
                'status': str
            }
        """
        try:
            # Ensure migrations table exists
            await self.ensure_migrations_table()

            # Get pending migrations
            pending = await self.get_pending_migrations()
            applied = await self.get_applied_migrations()

            status = {
                'database_exists': len(applied) > 0,
                'pending_count': len(pending),
                'applied_count': len(applied),
                'pending_migrations': pending,
                'status': 'up_to_date' if not pending else 'migrations_pending'
            }

            if not pending:
                logger.info(f"✅ Database schema up to date ({len(applied)} migrations applied)")
                return status

            if not auto_apply:
                logger.info(f"⏸️  {len(pending)} pending migrations (auto_apply=False)")
                return status

            # Apply each pending migration
            logger.info(f"🔄 Applying {len(pending)} pending migrations...")

            for migration_file in pending:
                try:
                    await self.apply_migration(migration_file)
                except Exception as e:
                    logger.error(f"❌ Migration failed: {migration_file}")
                    logger.error(f"Error: {e}")
                    status['status'] = 'failed'
                    status['error'] = str(e)
                    status['failed_migration'] = migration_file
                    raise

            status['status'] = 'success'
            logger.info(f"✅ All migrations applied successfully!")

            return status

        except Exception as e:
            logger.error(f"Migration system error: {e}")
            raise


async def init_database(database_url: str) -> dict:
    """
    Initialize database with automatic migrations.

    This is the main entry point - call this on app startup.
    Works like PHP auto-setup: detects fresh DB and creates schema.

    Args:
        database_url: PostgreSQL connection string

    Returns:
        Migration status dictionary

    Example:
        ```python
        # In main.py startup:
        from shared.migrations import init_database

        status = await init_database(os.getenv('DATABASE_URL'))
        if status['status'] == 'success':
            logger.info("Database ready!")
        ```
    """
    import asyncpg

    conn = await asyncpg.connect(database_url)

    try:
        migrator = DatabaseMigrator(conn)
        status = await migrator.run_migrations(auto_apply=True)
        return status
    finally:
        await conn.close()

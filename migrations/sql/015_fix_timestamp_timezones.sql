-- ============================================================
-- Migration 015: Fix TIMESTAMP columns to use TIMESTAMPTZ
-- ============================================================
-- Purpose: Convert all TIMESTAMP columns to TIMESTAMPTZ to handle timezone-aware datetimes
-- Date: 2026-01-11
-- Issue: "can't subtract offset-naive and offset-aware datetimes" error in cleanup_media job
--
-- This migration converts all TIMESTAMP columns to TIMESTAMP WITH TIME ZONE (TIMESTAMPTZ)
-- to properly handle timezone-aware datetime objects from Python's datetime.now(timezone.utc)

-- ============================================================
-- VULNERABILITIES TABLE
-- ============================================================
ALTER TABLE vulnerabilities
    ALTER COLUMN published TYPE TIMESTAMPTZ USING published AT TIME ZONE 'UTC',
    ALTER COLUMN modified TYPE TIMESTAMPTZ USING modified AT TIME ZONE 'UTC',
    ALTER COLUMN withdrawn TYPE TIMESTAMPTZ USING withdrawn AT TIME ZONE 'UTC',
    ALTER COLUMN created_at TYPE TIMESTAMPTZ USING created_at AT TIME ZONE 'UTC',
    ALTER COLUMN updated_at TYPE TIMESTAMPTZ USING updated_at AT TIME ZONE 'UTC';

-- ============================================================
-- PACKAGES TABLE
-- ============================================================
ALTER TABLE packages
    ALTER COLUMN last_commit_date TYPE TIMESTAMPTZ USING last_commit_date AT TIME ZONE 'UTC',
    ALTER COLUMN last_analyzed TYPE TIMESTAMPTZ USING last_analyzed AT TIME ZONE 'UTC',
    ALTER COLUMN created_at TYPE TIMESTAMPTZ USING created_at AT TIME ZONE 'UTC',
    ALTER COLUMN updated_at TYPE TIMESTAMPTZ USING updated_at AT TIME ZONE 'UTC';

-- ============================================================
-- MEDIA_ITEMS TABLE (The main fix for cleanup_media job)
-- ============================================================
ALTER TABLE media_items
    ALTER COLUMN published TYPE TIMESTAMPTZ USING published AT TIME ZONE 'UTC',
    ALTER COLUMN scraped_at TYPE TIMESTAMPTZ USING scraped_at AT TIME ZONE 'UTC',
    ALTER COLUMN created_at TYPE TIMESTAMPTZ USING created_at AT TIME ZONE 'UTC',
    ALTER COLUMN updated_at TYPE TIMESTAMPTZ USING updated_at AT TIME ZONE 'UTC';

-- ============================================================
-- PACKAGE_VULNERABILITIES TABLE
-- ============================================================
ALTER TABLE package_vulnerabilities
    ALTER COLUMN discovered_at TYPE TIMESTAMPTZ USING discovered_at AT TIME ZONE 'UTC';

-- ============================================================
-- JOBS TABLE (from migration 003)
-- ============================================================
ALTER TABLE jobs
    ALTER COLUMN created_at TYPE TIMESTAMPTZ USING created_at AT TIME ZONE 'UTC',
    ALTER COLUMN updated_at TYPE TIMESTAMPTZ USING updated_at AT TIME ZONE 'UTC',
    ALTER COLUMN last_run_at TYPE TIMESTAMPTZ USING last_run_at AT TIME ZONE 'UTC',
    ALTER COLUMN next_run_at TYPE TIMESTAMPTZ USING next_run_at AT TIME ZONE 'UTC';

-- ============================================================
-- WORKER_HEARTBEATS TABLE (from migration 003)
-- ============================================================
ALTER TABLE worker_heartbeats
    ALTER COLUMN last_seen TYPE TIMESTAMPTZ USING last_seen AT TIME ZONE 'UTC',
    ALTER COLUMN created_at TYPE TIMESTAMPTZ USING created_at AT TIME ZONE 'UTC';

-- ============================================================
-- TRACKED_PACKAGES TABLE (from migration 014)
-- ============================================================
ALTER TABLE tracked_packages
    ALTER COLUMN added_at TYPE TIMESTAMPTZ USING added_at AT TIME ZONE 'UTC',
    ALTER COLUMN last_scanned_at TYPE TIMESTAMPTZ USING last_scanned_at AT TIME ZONE 'UTC',
    ALTER COLUMN created_at TYPE TIMESTAMPTZ USING created_at AT TIME ZONE 'UTC',
    ALTER COLUMN updated_at TYPE TIMESTAMPTZ USING updated_at AT TIME ZONE 'UTC';

-- ============================================================
-- PACKAGE_HEALTH_SCORES TABLE (from migration 014)
-- ============================================================
ALTER TABLE package_health_scores
    ALTER COLUMN scanned_at TYPE TIMESTAMPTZ USING scanned_at AT TIME ZONE 'UTC',
    ALTER COLUMN created_at TYPE TIMESTAMPTZ USING created_at AT TIME ZONE 'UTC';

-- ============================================================
-- PACKAGE_SCAN_QUEUE TABLE (from migration 014)
-- ============================================================
ALTER TABLE package_scan_queue
    ALTER COLUMN claimed_at TYPE TIMESTAMPTZ USING claimed_at AT TIME ZONE 'UTC',
    ALTER COLUMN last_scanned_at TYPE TIMESTAMPTZ USING last_scanned_at AT TIME ZONE 'UTC',
    ALTER COLUMN created_at TYPE TIMESTAMPTZ USING created_at AT TIME ZONE 'UTC';

-- ============================================================
-- MEDIA_FEED_SOURCES TABLE (from migration 011)
-- ============================================================
ALTER TABLE media_feed_sources
    ALTER COLUMN last_checked_at TYPE TIMESTAMPTZ USING last_checked_at AT TIME ZONE 'UTC',
    ALTER COLUMN created_at TYPE TIMESTAMPTZ USING created_at AT TIME ZONE 'UTC',
    ALTER COLUMN updated_at TYPE TIMESTAMPTZ USING updated_at AT TIME ZONE 'UTC';

-- ============================================================
-- VERIFICATION
-- ============================================================
-- Verify all timestamp columns are now TIMESTAMPTZ
-- Run this query to check:
-- SELECT table_name, column_name, data_type
-- FROM information_schema.columns
-- WHERE table_schema = 'public'
-- AND data_type IN ('timestamp without time zone', 'timestamp with time zone')
-- ORDER BY table_name, column_name;

-- ============================================================
-- COMMENTS
-- ============================================================
COMMENT ON COLUMN media_items.scraped_at IS 'When the item was scraped (timezone-aware)';
COMMENT ON COLUMN media_items.published IS 'When the item was published (timezone-aware)';

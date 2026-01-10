-- ============================================================
-- Migration 008: Add config and description columns to jobs table
-- ============================================================
-- Purpose: Add missing config and description columns that were lost in migration 003
-- Date: 2026-01-10
-- Bug fix: Migration 003 dropped and recreated jobs table without these columns

-- Add config column (JSONB for job-specific parameters)
ALTER TABLE jobs ADD COLUMN IF NOT EXISTS config JSONB DEFAULT '{}';

-- Add description column (human-readable job description)
ALTER TABLE jobs ADD COLUMN IF NOT EXISTS description TEXT;

-- Add index on config for faster JSONB queries
CREATE INDEX IF NOT EXISTS idx_jobs_config ON jobs USING gin(config);

-- Add comments
COMMENT ON COLUMN jobs.config IS 'Job-specific configuration parameters (JSONB)';
COMMENT ON COLUMN jobs.description IS 'Human-readable description of what this job does';

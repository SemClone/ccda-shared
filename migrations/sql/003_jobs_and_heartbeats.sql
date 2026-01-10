-- ============================================================
-- Migration 003: Jobs Queue and Worker Heartbeats
-- ============================================================
-- Purpose: Migrate jobs queue and heartbeats from Spaces files to PostgreSQL
-- Eliminates: Race conditions in file-based job claiming
-- Benefits: Atomic operations, better querying, historical tracking
-- Date: 2026-01-06

-- ============================================================
-- JOBS TABLE (Enhanced from migration 001)
-- ============================================================
-- Note: This table was created in migration 001 but may need to be recreated
-- with enhanced schema for production use. We drop and recreate to ensure
-- consistency with the new job_queue.py implementation.

DROP TABLE IF EXISTS jobs CASCADE;

CREATE TABLE jobs (
    -- Primary identifiers
    id VARCHAR(255) PRIMARY KEY,
    type VARCHAR(100) NOT NULL,
    status VARCHAR(50) NOT NULL DEFAULT 'active',  -- active, inactive, failed

    -- Job information
    description TEXT,                               -- Human-readable job description
    config JSONB DEFAULT '{}',                      -- Job-specific configuration parameters

    -- Schedule configuration
    schedule VARCHAR(255),                          -- "hourly", "daily", "6h", "10m", "once"
    interval_minutes INT,                           -- Alternative to schedule string
    next_run_at TIMESTAMP WITH TIME ZONE,

    -- Execution tracking
    last_run_at TIMESTAMP WITH TIME ZONE,
    run_count INT DEFAULT 0,

    -- Results (JSONB for flexibility)
    last_result JSONB,
    last_error TEXT,

    -- Multi-worker coordination
    claimed_by VARCHAR(255),                        -- worker_id that claimed this job
    claimed_at TIMESTAMP WITH TIME ZONE,            -- when job was claimed

    -- Retry logic
    retry_count INT DEFAULT 0,
    max_retries INT DEFAULT 3,
    retry_delay_minutes INT DEFAULT 5,              -- Base delay for exponential backoff
    next_retry_at TIMESTAMP WITH TIME ZONE,
    last_retry_error TEXT,
    permanently_failed BOOLEAN DEFAULT FALSE,
    permanent_failure_at TIMESTAMP WITH TIME ZONE,
    permanent_failure_reason TEXT,

    -- Timeout configuration
    timeout_minutes INT DEFAULT 60,                 -- Job execution timeout

    -- Metadata
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Indexes for jobs
CREATE INDEX IF NOT EXISTS idx_jobs_status ON jobs(status);
CREATE INDEX IF NOT EXISTS idx_jobs_type ON jobs(type);
CREATE INDEX IF NOT EXISTS idx_jobs_config ON jobs USING gin(config);
CREATE INDEX IF NOT EXISTS idx_jobs_next_run ON jobs(next_run_at) WHERE next_run_at IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_jobs_claimed_by ON jobs(claimed_by) WHERE claimed_by IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_jobs_next_retry ON jobs(next_retry_at) WHERE next_retry_at IS NOT NULL;

-- Index for finding claimable jobs (active, not claimed or stale claim)
CREATE INDEX IF NOT EXISTS idx_jobs_claimable ON jobs(status, claimed_at)
    WHERE status = 'active' AND permanently_failed = FALSE;

-- ============================================================
-- WORKER HEARTBEATS TABLE
-- ============================================================
DROP TABLE IF EXISTS worker_heartbeats CASCADE;

CREATE TABLE worker_heartbeats (
    id SERIAL PRIMARY KEY,

    -- Worker identification
    worker_id VARCHAR(255) NOT NULL,

    -- Status
    status VARCHAR(50) NOT NULL DEFAULT 'healthy',  -- healthy, degraded, unhealthy

    -- Metrics
    uptime_seconds INT NOT NULL,
    start_time TIMESTAMP WITH TIME ZONE NOT NULL,

    -- Queue status
    total_jobs INT DEFAULT 0,
    running_jobs INT DEFAULT 0,
    registered_types JSONB,                         -- Array of registered job types

    -- Version info
    worker_version VARCHAR(50),

    -- Configuration
    heartbeat_interval_seconds INT,
    queue_check_interval_seconds INT,

    -- Full status payload (for flexibility)
    status_payload JSONB,

    -- Timestamps
    heartbeat_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,

    -- Ensure only one row per worker (latest heartbeat)
    UNIQUE(worker_id)
);

-- Indexes for worker_heartbeats
CREATE INDEX IF NOT EXISTS idx_heartbeats_worker ON worker_heartbeats(worker_id);
CREATE INDEX IF NOT EXISTS idx_heartbeats_status ON worker_heartbeats(status);
CREATE INDEX IF NOT EXISTS idx_heartbeats_time ON worker_heartbeats(heartbeat_at DESC);

-- Index for finding active workers (heartbeat within last 5 minutes)
CREATE INDEX IF NOT EXISTS idx_heartbeats_active ON worker_heartbeats(heartbeat_at DESC)
    WHERE status = 'healthy';

-- ============================================================
-- WORKER HEARTBEAT HISTORY TABLE
-- ============================================================
-- Store historical heartbeats for tracking patterns, uptime, crashes, etc.
DROP TABLE IF EXISTS worker_heartbeat_history CASCADE;

CREATE TABLE worker_heartbeat_history (
    id SERIAL PRIMARY KEY,

    -- Worker identification
    worker_id VARCHAR(255) NOT NULL,

    -- Status at time of heartbeat
    status VARCHAR(50) NOT NULL,
    uptime_seconds INT NOT NULL,
    total_jobs INT DEFAULT 0,
    running_jobs INT DEFAULT 0,

    -- Full status payload
    status_payload JSONB,

    -- Timestamp
    heartbeat_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- Indexes for heartbeat history
CREATE INDEX IF NOT EXISTS idx_heartbeat_history_worker ON worker_heartbeat_history(worker_id);
CREATE INDEX IF NOT EXISTS idx_heartbeat_history_time ON worker_heartbeat_history(heartbeat_at DESC);

-- Automatically partition history by month for better query performance
-- (Future optimization: use PostgreSQL partitioning)

-- ============================================================
-- TRIGGERS FOR updated_at
-- ============================================================
CREATE TRIGGER update_jobs_updated_at BEFORE UPDATE ON jobs
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- ============================================================
-- VIEWS FOR COMMON QUERIES
-- ============================================================

-- Active workers (heartbeat within last 5 minutes)
CREATE OR REPLACE VIEW active_workers AS
SELECT
    worker_id,
    status,
    uptime_seconds,
    start_time,
    total_jobs,
    running_jobs,
    registered_types,
    heartbeat_at,
    EXTRACT(EPOCH FROM (NOW() - heartbeat_at)) AS seconds_since_heartbeat
FROM worker_heartbeats
WHERE heartbeat_at >= NOW() - INTERVAL '5 minutes'
ORDER BY heartbeat_at DESC;

-- Claimable jobs (active, not claimed or stale claim)
CREATE OR REPLACE VIEW claimable_jobs AS
SELECT
    id,
    type,
    schedule,
    interval_minutes,
    last_run_at,
    next_run_at,
    run_count,
    claimed_by,
    claimed_at,
    EXTRACT(EPOCH FROM (NOW() - claimed_at)) AS claim_age_seconds
FROM jobs
WHERE
    status = 'active'
    AND permanently_failed = FALSE
    AND (
        claimed_by IS NULL
        OR claimed_at IS NULL
        OR claimed_at < NOW() - INTERVAL '10 minutes'  -- Stale claim (> 10 min)
    )
ORDER BY next_run_at ASC NULLS FIRST;

-- Jobs needing retry
CREATE OR REPLACE VIEW jobs_pending_retry AS
SELECT
    id,
    type,
    retry_count,
    max_retries,
    next_retry_at,
    last_retry_error,
    EXTRACT(EPOCH FROM (next_retry_at - NOW())) AS seconds_until_retry
FROM jobs
WHERE
    status = 'active'
    AND permanently_failed = FALSE
    AND next_retry_at IS NOT NULL
    AND next_retry_at <= NOW()
ORDER BY next_retry_at ASC;

-- ============================================================
-- COMMENTS
-- ============================================================
COMMENT ON TABLE jobs IS 'Job queue - migrated from Spaces files to eliminate race conditions';
COMMENT ON TABLE worker_heartbeats IS 'Latest worker heartbeat status (one row per worker)';
COMMENT ON TABLE worker_heartbeat_history IS 'Historical worker heartbeats for tracking patterns and uptime';

COMMENT ON COLUMN jobs.config IS 'Job-specific configuration parameters (JSONB)';
COMMENT ON COLUMN jobs.description IS 'Human-readable description of what this job does';
COMMENT ON COLUMN jobs.claimed_by IS 'Worker ID that has claimed this job for execution';
COMMENT ON COLUMN jobs.claimed_at IS 'Timestamp when job was claimed (used to detect stale claims)';
COMMENT ON COLUMN jobs.retry_delay_minutes IS 'Base delay for exponential backoff (actual delay = base * 2^retry_count)';
COMMENT ON COLUMN worker_heartbeats.worker_id IS 'Unique worker identifier (hostname-PID or WORKER_ID env var)';
COMMENT ON COLUMN worker_heartbeats.heartbeat_at IS 'Last heartbeat timestamp - workers inactive >5min considered down';

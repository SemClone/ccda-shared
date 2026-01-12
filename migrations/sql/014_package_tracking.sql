-- Migration 014: Package Health Tracking System
-- Created: 2026-01-12
-- Purpose: Add tables for tracking packages and health scores (Phase 3)

-- Table 1: tracked_packages
-- Stores packages the user wants to monitor
CREATE TABLE IF NOT EXISTS tracked_packages (
    id SERIAL PRIMARY KEY,
    purl TEXT NOT NULL UNIQUE,  -- Package URL (e.g., pkg:npm/express@4.18.0)
    ecosystem TEXT NOT NULL,    -- npm, pypi, maven, go, cargo, etc.
    name TEXT NOT NULL,         -- Package name (e.g., express)
    version TEXT,               -- Specific version or NULL for latest

    -- Discovery metadata (enriched from deps.dev, clearlydefined, etc.)
    repo_url TEXT,              -- GitHub/GitLab/etc. repository URL
    license TEXT,               -- SPDX license identifier
    description TEXT,           -- Package description
    homepage TEXT,              -- Official homepage
    latest_version TEXT,        -- Latest version available

    -- Scanning metadata
    scan_status TEXT DEFAULT 'pending',  -- pending, scanning, completed, failed
    scan_priority INTEGER DEFAULT 50,    -- 0-100 (higher = scan sooner)
    last_scanned_at TIMESTAMP,
    scan_count INTEGER DEFAULT 0,
    last_error TEXT,

    -- User metadata
    notes TEXT,                 -- User notes
    tags TEXT[],                -- User-defined tags

    -- Timestamps
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Indexes for tracked_packages
CREATE INDEX IF NOT EXISTS idx_tracked_packages_ecosystem ON tracked_packages(ecosystem);
CREATE INDEX IF NOT EXISTS idx_tracked_packages_scan_status ON tracked_packages(scan_status);
CREATE INDEX IF NOT EXISTS idx_tracked_packages_scan_priority ON tracked_packages(scan_priority DESC);
CREATE INDEX IF NOT EXISTS idx_tracked_packages_last_scanned ON tracked_packages(last_scanned_at NULLS FIRST);

-- Table 2: package_health_scores
-- Stores health scores from ccda-cli (multi-row: one per scan)
CREATE TABLE IF NOT EXISTS package_health_scores (
    id SERIAL PRIMARY KEY,
    package_id INTEGER NOT NULL REFERENCES tracked_packages(id) ON DELETE CASCADE,

    -- Full ccda-cli JSON output
    analysis_data JSONB NOT NULL,  -- Complete health score breakdown

    -- Extracted quick-access fields
    health_score NUMERIC(5,2),     -- Overall score 0-100
    grade TEXT,                     -- A, B, C, D, F
    risk_level TEXT,                -- LOW, MEDIUM, HIGH, CRITICAL

    -- GitHub metrics (extracted for quick queries)
    stars INTEGER,
    forks INTEGER,
    open_issues INTEGER,
    open_prs INTEGER,

    -- Metrics (extracted for filtering/sorting)
    issue_response_time_hours NUMERIC(10,2),
    pr_merge_time_hours NUMERIC(10,2),
    commits_last_month INTEGER,
    contributors_count INTEGER,
    burnout_score NUMERIC(5,2),    -- 0-100

    -- Timestamps
    scanned_at TIMESTAMP DEFAULT NOW()
);

-- Indexes for package_health_scores
CREATE INDEX IF NOT EXISTS idx_package_health_package_id ON package_health_scores(package_id);
CREATE INDEX IF NOT EXISTS idx_package_health_scanned_at ON package_health_scores(scanned_at DESC);
CREATE INDEX IF NOT EXISTS idx_package_health_score ON package_health_scores(health_score DESC);
CREATE INDEX IF NOT EXISTS idx_package_health_risk_level ON package_health_scores(risk_level);

-- Table 3: package_scan_queue
-- Manages round-robin scanning (prevents duplicate scans)
CREATE TABLE IF NOT EXISTS package_scan_queue (
    id SERIAL PRIMARY KEY,
    package_id INTEGER NOT NULL REFERENCES tracked_packages(id) ON DELETE CASCADE,

    -- Queue management
    priority INTEGER DEFAULT 50,     -- 0-100 (higher = scan sooner)
    status TEXT DEFAULT 'pending',   -- pending, claimed, completed, failed
    claimed_by TEXT,                 -- worker_id that claimed this scan
    claimed_at TIMESTAMP,

    -- Execution tracking
    attempt_count INTEGER DEFAULT 0,
    last_attempt_at TIMESTAMP,
    error_message TEXT,

    -- Timestamps
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Indexes for package_scan_queue
CREATE INDEX IF NOT EXISTS idx_scan_queue_status ON package_scan_queue(status);
CREATE INDEX IF NOT EXISTS idx_scan_queue_priority ON package_scan_queue(priority DESC, created_at ASC);
CREATE INDEX IF NOT EXISTS idx_scan_queue_package_id ON package_scan_queue(package_id);
CREATE INDEX IF NOT EXISTS idx_scan_queue_claimed_by ON package_scan_queue(claimed_by);

-- View 1: package_latest_health
-- Latest health score per package (for quick queries)
CREATE OR REPLACE VIEW package_latest_health AS
SELECT DISTINCT ON (p.id)
    p.id AS package_id,
    p.purl,
    p.ecosystem,
    p.name,
    p.version,
    p.repo_url,
    p.license,
    p.description,
    p.scan_status,
    p.last_scanned_at,
    p.scan_count,
    h.health_score,
    h.grade,
    h.risk_level,
    h.stars,
    h.forks,
    h.open_issues,
    h.burnout_score,
    h.scanned_at AS health_scanned_at
FROM tracked_packages p
LEFT JOIN package_health_scores h ON p.id = h.package_id
ORDER BY p.id, h.scanned_at DESC NULLS LAST;

-- View 2: packages_needing_scan
-- Packages due for scanning (round-robin logic)
CREATE OR REPLACE VIEW packages_needing_scan AS
SELECT
    p.id AS package_id,
    p.purl,
    p.ecosystem,
    p.name,
    p.scan_priority,
    p.last_scanned_at,
    COALESCE(q.status, 'not_queued') AS queue_status
FROM tracked_packages p
LEFT JOIN package_scan_queue q ON p.id = q.package_id AND q.status IN ('pending', 'claimed')
WHERE p.scan_status != 'failed'
  AND (
    p.last_scanned_at IS NULL  -- Never scanned
    OR p.last_scanned_at < NOW() - INTERVAL '2 days'  -- Not scanned recently
  )
  AND q.id IS NULL  -- Not already in queue
ORDER BY p.scan_priority DESC, p.last_scanned_at NULLS FIRST;

-- Add updated_at trigger for tracked_packages
CREATE OR REPLACE FUNCTION update_tracked_packages_timestamp()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trigger_update_tracked_packages_timestamp ON tracked_packages;
CREATE TRIGGER trigger_update_tracked_packages_timestamp
BEFORE UPDATE ON tracked_packages
FOR EACH ROW
EXECUTE FUNCTION update_tracked_packages_timestamp();

-- Add updated_at trigger for package_scan_queue
CREATE OR REPLACE FUNCTION update_package_scan_queue_timestamp()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trigger_update_package_scan_queue_timestamp ON package_scan_queue;
CREATE TRIGGER trigger_update_package_scan_queue_timestamp
BEFORE UPDATE ON package_scan_queue
FOR EACH ROW
EXECUTE FUNCTION update_package_scan_queue_timestamp();

-- Success message
DO $$
BEGIN
    RAISE NOTICE 'Migration 014 completed: Package Health Tracking System';
    RAISE NOTICE '  - 3 tables created: tracked_packages, package_health_scores, package_scan_queue';
    RAISE NOTICE '  - 12 indexes created for performance';
    RAISE NOTICE '  - 2 views created: package_latest_health, packages_needing_scan';
    RAISE NOTICE '  - 2 triggers created for updated_at timestamps';
END $$;

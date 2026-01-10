-- Initial CCDA Database Schema
-- Migration: 001
-- Description: Create core tables for vulnerabilities, packages, media, and jobs
-- Created: 2026-01-06

-- ============================================================================
-- VULNERABILITIES TABLE
-- Stores vulnerability data from OSV, NVD, GHSA, EPSS
-- ============================================================================
CREATE TABLE IF NOT EXISTS vulnerabilities (
    -- Primary identifiers
    id VARCHAR(255) PRIMARY KEY,
    ecosystem VARCHAR(100) NOT NULL,
    package_name VARCHAR(255) NOT NULL,
    purl TEXT,  -- Package URL (pkg:npm/lodash@4.17.0)

    -- Content
    summary TEXT,
    details TEXT,

    -- Severity scoring
    severity VARCHAR(50),  -- LOW, MEDIUM, HIGH, CRITICAL
    cvss_score DECIMAL(3, 1),
    epss_score DECIMAL(5, 5),
    epss_percentile DECIMAL(5, 4),

    -- Timestamps
    published_at TIMESTAMP WITH TIME ZONE,
    modified_at TIMESTAMP WITH TIME ZONE,
    withdrawn_at TIMESTAMP WITH TIME ZONE,

    -- JSON fields for complex data
    aliases JSONB DEFAULT '[]',  -- List of CVE IDs, GHSA IDs, etc.
    affected JSONB DEFAULT '[]',  -- Affected package versions
    "references" JSONB DEFAULT '[]',  -- Links to advisories, patches
    database_specific JSONB DEFAULT '{}',  -- Provider-specific metadata

    -- Metadata
    source VARCHAR(50) NOT NULL,  -- osv, nvd, ghsa, epss
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Indexes for fast queries
CREATE INDEX IF NOT EXISTS idx_vulnerabilities_ecosystem ON vulnerabilities(ecosystem);
CREATE INDEX IF NOT EXISTS idx_vulnerabilities_package ON vulnerabilities(package_name);
CREATE INDEX IF NOT EXISTS idx_vulnerabilities_severity ON vulnerabilities(severity);
CREATE INDEX IF NOT EXISTS idx_vulnerabilities_published ON vulnerabilities(published_at DESC);
CREATE INDEX IF NOT EXISTS idx_vulnerabilities_epss ON vulnerabilities(epss_score DESC NULLS LAST);
CREATE INDEX IF NOT EXISTS idx_vulnerabilities_cvss ON vulnerabilities(cvss_score DESC NULLS LAST);

-- GIN index for JSON search
CREATE INDEX IF NOT EXISTS idx_vulnerabilities_aliases ON vulnerabilities USING GIN (aliases);
CREATE INDEX IF NOT EXISTS idx_vulnerabilities_affected ON vulnerabilities USING GIN (affected);

-- ============================================================================
-- PACKAGES TABLE
-- Tracks monitored packages and their health scores
-- ============================================================================
CREATE TABLE IF NOT EXISTS packages (
    -- Primary identifiers
    id SERIAL PRIMARY KEY,
    ecosystem VARCHAR(100) NOT NULL,
    name VARCHAR(255) NOT NULL,
    purl TEXT UNIQUE,

    -- Repository info
    repository_url TEXT,
    homepage_url TEXT,

    -- Health metrics
    health_score DECIMAL(5, 2),  -- 0-100
    health_score_updated_at TIMESTAMP WITH TIME ZONE,

    -- Statistics
    vulnerability_count INT DEFAULT 0,
    critical_vuln_count INT DEFAULT 0,
    high_vuln_count INT DEFAULT 0,

    -- Maintainer health
    last_commit_at TIMESTAMP WITH TIME ZONE,
    commit_frequency_score DECIMAL(5, 2),
    contributor_count INT,

    -- Metadata
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,

    UNIQUE(ecosystem, name)
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_packages_ecosystem ON packages(ecosystem);
CREATE INDEX IF NOT EXISTS idx_packages_name ON packages(name);
CREATE INDEX IF NOT EXISTS idx_packages_health_score ON packages(health_score DESC NULLS LAST);
CREATE INDEX IF NOT EXISTS idx_packages_vuln_count ON packages(vulnerability_count DESC);

-- ============================================================================
-- MEDIA TABLE
-- Stores media mentions (HackerNews, Reddit, RSS, Bluesky)
-- ============================================================================
CREATE TABLE IF NOT EXISTS media (
    -- Primary identifiers
    id SERIAL PRIMARY KEY,
    source VARCHAR(50) NOT NULL,  -- hackernews, reddit, rss, bluesky
    external_id VARCHAR(255),  -- Source-specific ID

    -- Content
    title TEXT NOT NULL,
    content TEXT,
    url TEXT,
    author VARCHAR(255),

    -- Analysis
    sentiment VARCHAR(20),  -- positive, negative, neutral
    risk_level VARCHAR(20),  -- low, medium, high, critical
    mentioned_packages JSONB DEFAULT '[]',
    mentioned_vulnerabilities JSONB DEFAULT '[]',

    -- Timestamps
    published_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,

    -- Source-specific metadata
    metadata JSONB DEFAULT '{}',

    UNIQUE(source, external_id)
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_media_source ON media(source);
CREATE INDEX IF NOT EXISTS idx_media_published ON media(published_at DESC);
CREATE INDEX IF NOT EXISTS idx_media_risk_level ON media(risk_level);
CREATE INDEX IF NOT EXISTS idx_media_sentiment ON media(sentiment);
CREATE INDEX IF NOT EXISTS idx_media_packages ON media USING GIN (mentioned_packages);
CREATE INDEX IF NOT EXISTS idx_media_vulns ON media USING GIN (mentioned_vulnerabilities);

-- ============================================================================
-- JOBS TABLE (Optional - for job queue persistence)
-- Stores job queue state if moving from JSON files
-- ============================================================================
CREATE TABLE IF NOT EXISTS jobs (
    -- Primary identifiers
    id VARCHAR(255) PRIMARY KEY,
    type VARCHAR(100) NOT NULL,
    status VARCHAR(50) NOT NULL DEFAULT 'active',  -- active, inactive, failed

    -- Schedule
    schedule VARCHAR(255),
    interval_minutes INT,
    next_run_at TIMESTAMP WITH TIME ZONE,

    -- Execution tracking
    last_run_at TIMESTAMP WITH TIME ZONE,
    run_count INT DEFAULT 0,

    -- Results
    last_result JSONB,
    last_error TEXT,

    -- Multi-worker coordination
    claimed_by VARCHAR(255),
    claimed_at TIMESTAMP WITH TIME ZONE,

    -- Retry logic
    retry_count INT DEFAULT 0,
    max_retries INT DEFAULT 3,
    next_retry_at TIMESTAMP WITH TIME ZONE,
    permanently_failed BOOLEAN DEFAULT FALSE,

    -- Configuration
    config JSONB DEFAULT '{}',
    description TEXT,

    -- Metadata
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_jobs_status ON jobs(status);
CREATE INDEX IF NOT EXISTS idx_jobs_type ON jobs(type);
CREATE INDEX IF NOT EXISTS idx_jobs_next_run ON jobs(next_run_at NULLS LAST);
CREATE INDEX IF NOT EXISTS idx_jobs_claimed_by ON jobs(claimed_by);

-- ============================================================================
-- FUNCTIONS
-- Auto-update updated_at timestamp
-- ============================================================================
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Triggers for auto-updating timestamps
CREATE TRIGGER update_vulnerabilities_updated_at BEFORE UPDATE ON vulnerabilities
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_packages_updated_at BEFORE UPDATE ON packages
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_jobs_updated_at BEFORE UPDATE ON jobs
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- ============================================================================
-- VIEWS
-- Useful pre-computed views for common queries
-- ============================================================================

-- High-risk packages (many critical vulnerabilities)
CREATE OR REPLACE VIEW high_risk_packages AS
SELECT
    p.id,
    p.ecosystem,
    p.name,
    p.purl,
    p.vulnerability_count,
    p.critical_vuln_count,
    p.high_vuln_count,
    p.health_score,
    p.updated_at
FROM packages p
WHERE p.critical_vuln_count > 0 OR p.high_vuln_count > 3
ORDER BY p.critical_vuln_count DESC, p.high_vuln_count DESC;

-- Recent critical vulnerabilities
CREATE OR REPLACE VIEW recent_critical_vulnerabilities AS
SELECT
    id,
    ecosystem,
    package_name,
    summary,
    severity,
    cvss_score,
    epss_score,
    published_at,
    aliases
FROM vulnerabilities
WHERE severity IN ('CRITICAL', 'HIGH')
  AND published_at > CURRENT_TIMESTAMP - INTERVAL '30 days'
ORDER BY published_at DESC;

-- ============================================================================
-- GRANT PERMISSIONS (if using separate users)
-- ============================================================================
-- GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO ccda_app;
-- GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO ccda_app;

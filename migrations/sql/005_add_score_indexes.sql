-- ============================================================
-- Migration 005: Add Score and Search Indexes
-- ============================================================
-- Purpose: Optimize vulnerability stats and search queries
-- Date: 2026-01-09
-- Note: Using regular CREATE INDEX (not CONCURRENTLY) for migration compatibility

-- Index on purl for PURL-based searches
CREATE INDEX IF NOT EXISTS idx_vuln_purl
    ON vulnerabilities(purl) WHERE purl IS NOT NULL;

-- Index on cvss_score for score aggregation and filtering
CREATE INDEX IF NOT EXISTS idx_vuln_cvss_score
    ON vulnerabilities(cvss_score) WHERE cvss_score IS NOT NULL;

-- Index on epss_score for score aggregation and filtering
CREATE INDEX IF NOT EXISTS idx_vuln_epss_score
    ON vulnerabilities(epss_score) WHERE epss_score IS NOT NULL;

-- Index on epss_percentile for percentile queries
CREATE INDEX IF NOT EXISTS idx_vuln_epss_percentile
    ON vulnerabilities(epss_percentile) WHERE epss_percentile IS NOT NULL;

-- Index on updated_at for "last sync" queries
CREATE INDEX IF NOT EXISTS idx_vuln_updated_at
    ON vulnerabilities(updated_at DESC);

-- Composite index for ecosystem stats (ecosystem + has scores)
-- Useful for: GROUP BY ecosystem with COUNT(cvss_score), COUNT(epss_score)
CREATE INDEX IF NOT EXISTS idx_vuln_ecosystem_scores
    ON vulnerabilities(ecosystem, cvss_score, epss_score);

-- Composite index for severity stats with scores
CREATE INDEX IF NOT EXISTS idx_vuln_severity_cvss
    ON vulnerabilities(severity, cvss_score);

-- Index for source filtering
CREATE INDEX IF NOT EXISTS idx_vuln_source
    ON vulnerabilities(source);

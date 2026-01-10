-- ============================================================
-- Migration 004: Add EPSS Percentile Column
-- ============================================================
-- Purpose: Add epss_percentile column for storing EPSS percentile data
-- Date: 2026-01-09

-- Add epss_percentile column to vulnerabilities table
ALTER TABLE vulnerabilities
ADD COLUMN IF NOT EXISTS epss_percentile DECIMAL(5,2);

-- Add comment
COMMENT ON COLUMN vulnerabilities.epss_percentile IS 'EPSS percentile ranking (0-100, higher = more likely exploited)';

-- Create index for EPSS-based queries
CREATE INDEX IF NOT EXISTS idx_vuln_epss ON vulnerabilities(epss_score DESC) WHERE epss_score IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_vuln_epss_percentile ON vulnerabilities(epss_percentile DESC) WHERE epss_percentile IS NOT NULL;

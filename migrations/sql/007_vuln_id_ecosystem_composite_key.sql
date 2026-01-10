-- ============================================================
-- Migration 007: Change vuln_id UNIQUE to Composite (vuln_id, ecosystem)
-- ============================================================
-- Purpose: Allow same vulnerability ID to exist for multiple ecosystems
-- Date: 2026-01-10
--
-- Background:
-- - GHSA advisories often have the same CVE affecting multiple ecosystems
-- - Current UNIQUE constraint on vuln_id prevents storing cross-ecosystem vulns
-- - Need composite UNIQUE constraint on (vuln_id, ecosystem) instead
--
-- Impact:
-- - Enables proper tracking of ~7,000 cross-ecosystem GHSA advisories
-- - Total expected vulnerabilities: ~33K across all sources (OSV, NVD, GHSA, EPSS)
-- ============================================================

-- Drop existing UNIQUE constraint on vuln_id
ALTER TABLE vulnerabilities DROP CONSTRAINT IF EXISTS vulnerabilities_vuln_id_key;

-- Add composite UNIQUE constraint on (vuln_id, ecosystem)
ALTER TABLE vulnerabilities ADD CONSTRAINT vulnerabilities_vuln_id_ecosystem_key
    UNIQUE (vuln_id, ecosystem);

-- Update index for better query performance
DROP INDEX IF EXISTS idx_vuln_ecosystem;
CREATE INDEX IF NOT EXISTS idx_vuln_ecosystem ON vulnerabilities(ecosystem);
CREATE INDEX IF NOT EXISTS idx_vuln_id_ecosystem ON vulnerabilities(vuln_id, ecosystem);

-- ============================================================
-- COMMENTS
-- ============================================================
COMMENT ON CONSTRAINT vulnerabilities_vuln_id_ecosystem_key ON vulnerabilities IS
    'Allows same vuln_id for different ecosystems (e.g., same CVE affecting npm and PyPI)';

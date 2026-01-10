-- ============================================================
-- Migration 006: GHSA Data and Package Discovery Schema
-- ============================================================
-- Purpose: Support GHSA data with GitHub repo mappings and package discovery
-- Date: 2026-01-09
--
-- Features:
-- 1. GitHub repo → Package PURL mappings
-- 2. Multiple affected packages per vulnerability
-- 3. CWE ID storage
-- 4. Package discovery tracking

-- ============================================================
-- GITHUB REPOSITORIES TABLE
-- ============================================================
-- Tracks GitHub repositories and their metadata
CREATE TABLE IF NOT EXISTS github_repositories (
    id SERIAL PRIMARY KEY,

    -- Repository identification
    owner VARCHAR(100) NOT NULL,
    name VARCHAR(255) NOT NULL,
    full_name VARCHAR(356) GENERATED ALWAYS AS (owner || '/' || name) STORED,
    url VARCHAR(500) NOT NULL,
    github_purl VARCHAR(500) GENERATED ALWAYS AS ('pkg:github/' || owner || '/' || name) STORED,

    -- Repository metadata
    description TEXT,
    homepage_url VARCHAR(500),
    default_branch VARCHAR(100) DEFAULT 'main',

    -- Stats (from GitHub API)
    stars INTEGER,
    forks INTEGER,
    watchers INTEGER,
    open_issues INTEGER,

    -- Discovery metadata
    discovered_via VARCHAR(50),  -- 'ghsa', 'manual', 'serpapi', 'registry'
    last_scanned TIMESTAMP,
    package_files_found JSONB,   -- {'package.json': true, 'pyproject.toml': false, ...}

    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),

    UNIQUE(owner, name)
);

CREATE INDEX IF NOT EXISTS idx_gh_repo_owner ON github_repositories(owner);
CREATE INDEX IF NOT EXISTS idx_gh_repo_name ON github_repositories(name);
CREATE INDEX IF NOT EXISTS idx_gh_repo_url ON github_repositories(url);

-- ============================================================
-- GITHUB REPO ↔ PACKAGE MAPPINGS
-- ============================================================
-- Maps GitHub repositories to their published packages
CREATE TABLE IF NOT EXISTS repo_package_mappings (
    id SERIAL PRIMARY KEY,

    -- GitHub repo reference
    github_repo_id INTEGER REFERENCES github_repositories(id) ON DELETE CASCADE,

    -- Package identification
    ecosystem VARCHAR(50) NOT NULL,
    package_name VARCHAR(255) NOT NULL,
    purl VARCHAR(500) NOT NULL,

    -- Mapping confidence
    confidence VARCHAR(20) DEFAULT 'high',  -- 'high', 'medium', 'low'
    mapping_source VARCHAR(50) NOT NULL,     -- 'package_json', 'ghsa', 'registry', 'serpapi', 'manual'

    -- Package metadata from registry
    registry_url VARCHAR(500),
    latest_version VARCHAR(100),

    -- Verification
    verified BOOLEAN DEFAULT FALSE,
    verified_at TIMESTAMP,

    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),

    UNIQUE(github_repo_id, purl)
);

CREATE INDEX IF NOT EXISTS idx_rpm_repo ON repo_package_mappings(github_repo_id);
CREATE INDEX IF NOT EXISTS idx_rpm_ecosystem ON repo_package_mappings(ecosystem);
CREATE INDEX IF NOT EXISTS idx_rpm_purl ON repo_package_mappings(purl);
CREATE INDEX IF NOT EXISTS idx_rpm_package_name ON repo_package_mappings(package_name);

-- ============================================================
-- VULNERABILITY ↔ PACKAGE MAPPINGS (Enhanced)
-- ============================================================
-- Maps vulnerabilities to ALL affected packages (not just first)
CREATE TABLE IF NOT EXISTS vulnerability_affected_packages (
    id SERIAL PRIMARY KEY,

    -- Vulnerability reference
    vulnerability_id INTEGER REFERENCES vulnerabilities(id) ON DELETE CASCADE,

    -- Package identification
    ecosystem VARCHAR(50) NOT NULL,
    package_name VARCHAR(255) NOT NULL,
    purl VARCHAR(500),

    -- GitHub repo (if known)
    github_repo_id INTEGER REFERENCES github_repositories(id) ON DELETE SET NULL,

    -- Version info specific to this package
    affected_versions JSONB,
    fixed_version VARCHAR(100),

    created_at TIMESTAMP DEFAULT NOW(),

    UNIQUE(vulnerability_id, ecosystem, package_name)
);

CREATE INDEX IF NOT EXISTS idx_vap_vuln ON vulnerability_affected_packages(vulnerability_id);
CREATE INDEX IF NOT EXISTS idx_vap_ecosystem ON vulnerability_affected_packages(ecosystem);
CREATE INDEX IF NOT EXISTS idx_vap_package ON vulnerability_affected_packages(package_name);
CREATE INDEX IF NOT EXISTS idx_vap_purl ON vulnerability_affected_packages(purl);
CREATE INDEX IF NOT EXISTS idx_vap_github ON vulnerability_affected_packages(github_repo_id);

-- ============================================================
-- ADD COLUMNS TO VULNERABILITIES TABLE
-- ============================================================
-- Add columns for GHSA-specific data
ALTER TABLE vulnerabilities
    ADD COLUMN IF NOT EXISTS github_repo_url VARCHAR(500),
    ADD COLUMN IF NOT EXISTS github_repo_id INTEGER REFERENCES github_repositories(id),
    ADD COLUMN IF NOT EXISTS cwe_ids JSONB,
    ADD COLUMN IF NOT EXISTS ghsa_severity VARCHAR(20),
    ADD COLUMN IF NOT EXISTS affected_packages_count INTEGER DEFAULT 1;

CREATE INDEX IF NOT EXISTS idx_vuln_github_repo ON vulnerabilities(github_repo_id) WHERE github_repo_id IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_vuln_github_url ON vulnerabilities(github_repo_url) WHERE github_repo_url IS NOT NULL;

-- ============================================================
-- PACKAGE DISCOVERY JOBS TRACKING
-- ============================================================
-- Tracks discovery scan history
CREATE TABLE IF NOT EXISTS discovery_scans (
    id SERIAL PRIMARY KEY,

    -- Scan target
    scan_type VARCHAR(50) NOT NULL,  -- 'github_repo', 'package', 'serpapi_search'
    target VARCHAR(500) NOT NULL,     -- repo URL, package name, or search query

    -- Results
    status VARCHAR(20) DEFAULT 'pending',  -- 'pending', 'running', 'completed', 'failed'
    packages_found INTEGER DEFAULT 0,
    repos_found INTEGER DEFAULT 0,
    mappings_created INTEGER DEFAULT 0,

    -- Metadata
    scan_config JSONB,
    results JSONB,
    error_message TEXT,

    started_at TIMESTAMP,
    completed_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_ds_type ON discovery_scans(scan_type);
CREATE INDEX IF NOT EXISTS idx_ds_status ON discovery_scans(status);
CREATE INDEX IF NOT EXISTS idx_ds_created ON discovery_scans(created_at DESC);

-- ============================================================
-- CWE REFERENCE TABLE
-- ============================================================
-- Common Weakness Enumeration reference data
CREATE TABLE IF NOT EXISTS cwe_entries (
    id SERIAL PRIMARY KEY,
    cwe_id VARCHAR(20) UNIQUE NOT NULL,  -- 'CWE-79', 'CWE-89', etc.
    name VARCHAR(255) NOT NULL,
    description TEXT,
    category VARCHAR(100),

    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_cwe_id ON cwe_entries(cwe_id);

-- ============================================================
-- VIEWS
-- ============================================================

-- View: Packages with their GitHub repos
CREATE OR REPLACE VIEW packages_with_repos AS
SELECT
    rpm.ecosystem,
    rpm.package_name,
    rpm.purl,
    gr.full_name as github_repo,
    gr.url as github_url,
    gr.github_purl,
    gr.stars,
    rpm.confidence,
    rpm.mapping_source,
    rpm.verified
FROM repo_package_mappings rpm
JOIN github_repositories gr ON rpm.github_repo_id = gr.id
ORDER BY gr.stars DESC NULLS LAST;

-- View: Vulnerabilities with all affected packages
CREATE OR REPLACE VIEW vulnerabilities_full AS
SELECT
    v.vuln_id,
    v.cve_id,
    v.severity,
    v.cvss_score,
    v.summary,
    v.github_repo_url,
    v.cwe_ids,
    v.affected_packages_count,
    COALESCE(
        jsonb_agg(
            jsonb_build_object(
                'ecosystem', vap.ecosystem,
                'package', vap.package_name,
                'purl', vap.purl,
                'fixed', vap.fixed_version
            )
        ) FILTER (WHERE vap.id IS NOT NULL),
        '[]'::jsonb
    ) as affected_packages
FROM vulnerabilities v
LEFT JOIN vulnerability_affected_packages vap ON v.id = vap.vulnerability_id
GROUP BY v.id;

-- ============================================================
-- TRIGGERS
-- ============================================================

CREATE TRIGGER update_github_repositories_updated_at
    BEFORE UPDATE ON github_repositories
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_repo_package_mappings_updated_at
    BEFORE UPDATE ON repo_package_mappings
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- ============================================================
-- COMMENTS
-- ============================================================
COMMENT ON TABLE github_repositories IS 'GitHub repositories tracked for package discovery';
COMMENT ON TABLE repo_package_mappings IS 'Maps GitHub repos to their published packages (npm, PyPI, etc.)';
COMMENT ON TABLE vulnerability_affected_packages IS 'All packages affected by a vulnerability (GHSA can affect multiple)';
COMMENT ON TABLE discovery_scans IS 'History of package discovery scans';
COMMENT ON TABLE cwe_entries IS 'CWE (Common Weakness Enumeration) reference data';

COMMENT ON COLUMN github_repositories.github_purl IS 'Auto-generated PURL: pkg:github/owner/name';
COMMENT ON COLUMN repo_package_mappings.confidence IS 'Mapping confidence: high (from package.json), medium (from registry), low (from search)';
COMMENT ON COLUMN vulnerabilities.affected_packages_count IS 'Number of packages affected (GHSA can affect multiple packages)';

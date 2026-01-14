-- Migration 017: GitHub-Centric Health Storage
-- Phase 6: Store health metrics per GitHub repository instead of per package
--
-- Problem: Multiple packages (Maven, NPM, GitHub, Docker) pointing to the same
-- repository have different health scores, causing data duplication and inconsistency.
--
-- Solution: Create github_projects table as single source of truth for health metrics,
-- link multiple packages to one GitHub project, deduplicate ccda-cli scans.
--
-- GitHub Issue: Phase 6 - GitHub-Centric Health Storage
-- Date: 2026-01-14

-- Step 1: Create github_projects table
-- Stores unique GitHub repositories with their health metrics
CREATE TABLE IF NOT EXISTS github_projects (
    id SERIAL PRIMARY KEY,

    -- Repository identification
    repo_url TEXT NOT NULL UNIQUE,          -- https://github.com/owner/repo (normalized)
    owner TEXT NOT NULL,                    -- opensearch-project
    repo_name TEXT NOT NULL,                -- OpenSearch

    -- Repository metadata (from GitHub API or ccda-cli)
    description TEXT,
    primary_language TEXT,
    license TEXT,

    -- Current health metrics (from most recent scan)
    health_score NUMERIC(5,2),              -- 0-100
    grade TEXT,                             -- A, B, C, D, F
    risk_level TEXT,                        -- LOW, MEDIUM, HIGH, CRITICAL

    -- GitHub stats (snapshot at last scan)
    stars INTEGER,
    forks INTEGER,
    watchers INTEGER,
    open_issues INTEGER,
    open_prs INTEGER,

    -- Git repository metrics (from ccda-cli)
    commits_last_month INTEGER,
    contributors_count INTEGER,
    bus_factor NUMERIC(5,2),                -- Key developer concentration risk
    pony_factor NUMERIC(5,2),               -- Commit concentration risk

    -- Activity metrics (from ccda-cli)
    issue_response_time_hours NUMERIC(10,2),
    pr_merge_time_hours NUMERIC(10,2),
    last_commit_date TIMESTAMP,
    last_release_date TIMESTAMP,

    -- Health indicators
    burnout_score NUMERIC(5,2),             -- Maintainer burnout risk (0-100)

    -- Timestamps
    first_seen_at TIMESTAMP DEFAULT NOW(),
    last_scanned_at TIMESTAMP,              -- When health was last updated
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Indexes for fast lookups
CREATE INDEX IF NOT EXISTS idx_github_projects_repo_url ON github_projects(repo_url);
CREATE INDEX IF NOT EXISTS idx_github_projects_owner_repo ON github_projects(owner, repo_name);
CREATE INDEX IF NOT EXISTS idx_github_projects_health_score ON github_projects(health_score DESC);
CREATE INDEX IF NOT EXISTS idx_github_projects_last_scanned ON github_projects(last_scanned_at DESC);

-- Step 2: Create github_project_health_history table
-- Stores historical health scans for trend analysis
CREATE TABLE IF NOT EXISTS github_project_health_history (
    id SERIAL PRIMARY KEY,
    github_project_id INTEGER NOT NULL REFERENCES github_projects(id) ON DELETE CASCADE,

    -- Complete ccda-cli output stored as JSONB
    analysis_data JSONB NOT NULL,

    -- Quick-access columns (denormalized from JSONB for fast queries)
    health_score NUMERIC(5,2),
    grade TEXT,
    risk_level TEXT,

    -- GitHub metrics snapshot
    stars INTEGER,
    forks INTEGER,
    open_issues INTEGER,
    open_prs INTEGER,

    -- Git metrics snapshot
    commits_last_month INTEGER,
    contributors_count INTEGER,
    bus_factor NUMERIC(5,2),
    pony_factor NUMERIC(5,2),

    -- Activity metrics snapshot
    issue_response_time_hours NUMERIC(10,2),
    pr_merge_time_hours NUMERIC(10,2),
    burnout_score NUMERIC(5,2),

    scanned_at TIMESTAMP DEFAULT NOW()
);

-- Index for fast queries (get latest N scans for a project)
CREATE INDEX IF NOT EXISTS idx_github_health_history_project_date
    ON github_project_health_history(github_project_id, scanned_at DESC);

-- Step 3: Add github_project_id to tracked_packages
-- Links packages to their GitHub repository
ALTER TABLE tracked_packages
ADD COLUMN IF NOT EXISTS github_project_id INTEGER REFERENCES github_projects(id) ON DELETE SET NULL;

-- Index for fast package→project lookups
CREATE INDEX IF NOT EXISTS idx_tracked_packages_github_project
    ON tracked_packages(github_project_id);

-- Step 4: Extract and insert unique GitHub projects from existing packages
-- This identifies all unique repositories currently being tracked
INSERT INTO github_projects (repo_url, owner, repo_name, created_at, first_seen_at)
SELECT DISTINCT
    repo_url,
    -- Extract owner from URL: https://github.com/owner/repo
    (regexp_match(repo_url, 'github\.com[:/]([^/]+)/([^/\.]+)'))[1] as owner,
    -- Extract repo name from URL
    (regexp_match(repo_url, 'github\.com[:/]([^/]+)/([^/\.]+)'))[2] as repo_name,
    NOW(),
    MIN(created_at) as first_seen_at  -- Use earliest package creation as first_seen
FROM tracked_packages
WHERE repo_url IS NOT NULL
  AND repo_url LIKE '%github.com%'
  AND repo_url ~ 'github\.com[:/][^/]+/[^/\.]+'  -- Validate format
GROUP BY repo_url
ON CONFLICT (repo_url) DO NOTHING;

-- Step 5: Link existing packages to github_projects
-- Updates package records with their github_project_id
UPDATE tracked_packages tp
SET github_project_id = gp.id
FROM github_projects gp
WHERE tp.repo_url = gp.repo_url
  AND tp.github_project_id IS NULL;  -- Only update if not already set

-- Step 6: Migrate existing health data to github_project_health_history
-- Takes the most recent health scan for each package and stores it in the new table
-- This preserves historical data during migration
-- Note: Only migrates columns that exist in package_health_scores (Migration 014)
INSERT INTO github_project_health_history (
    github_project_id,
    analysis_data,
    health_score,
    grade,
    risk_level,
    stars,
    forks,
    open_issues,
    commits_last_month,
    contributors_count,
    issue_response_time_hours,
    pr_merge_time_hours,
    burnout_score,
    scanned_at
)
SELECT
    tp.github_project_id,
    phs.analysis_data,
    phs.health_score,
    phs.grade,
    phs.risk_level,
    phs.stars,
    phs.forks,
    phs.open_issues,
    phs.commits_last_month,
    phs.contributors_count,
    phs.issue_response_time_hours,
    phs.pr_merge_time_hours,
    phs.burnout_score,
    phs.scanned_at
FROM package_health_scores phs
JOIN tracked_packages tp ON phs.package_id = tp.id
WHERE tp.github_project_id IS NOT NULL
  -- Only migrate the most recent scan per package
  AND phs.scanned_at = (
      SELECT MAX(phs2.scanned_at)
      FROM package_health_scores phs2
      WHERE phs2.package_id = phs.package_id
  )
ON CONFLICT DO NOTHING;

-- Step 7: Update github_projects with latest health metrics
-- Populates the denormalized health fields from the most recent scan
-- Note: Only updates columns that were migrated in Step 6
UPDATE github_projects gp
SET
    health_score = latest.health_score,
    grade = latest.grade,
    risk_level = latest.risk_level,
    stars = latest.stars,
    forks = latest.forks,
    open_issues = latest.open_issues,
    commits_last_month = latest.commits_last_month,
    contributors_count = latest.contributors_count,
    issue_response_time_hours = latest.issue_response_time_hours,
    pr_merge_time_hours = latest.pr_merge_time_hours,
    burnout_score = latest.burnout_score,
    last_scanned_at = latest.scanned_at,
    updated_at = NOW()
FROM (
    SELECT
        github_project_id,
        health_score,
        grade,
        risk_level,
        stars,
        forks,
        open_issues,
        commits_last_month,
        contributors_count,
        issue_response_time_hours,
        pr_merge_time_hours,
        burnout_score,
        scanned_at
    FROM github_project_health_history
    WHERE (github_project_id, scanned_at) IN (
        SELECT github_project_id, MAX(scanned_at)
        FROM github_project_health_history
        GROUP BY github_project_id
    )
) latest
WHERE gp.id = latest.github_project_id;

-- Step 8: Create view for convenient package queries with health data
CREATE OR REPLACE VIEW package_with_health AS
SELECT
    tp.id as package_id,
    tp.purl,
    tp.name,
    tp.ecosystem,
    tp.repo_url,
    tp.github_project_id,

    -- Health metrics from GitHub project (shared across packages)
    gp.health_score,
    gp.grade,
    gp.risk_level,
    gp.stars,
    gp.forks,
    gp.open_issues,
    gp.commits_last_month,
    gp.contributors_count,
    gp.bus_factor,
    gp.pony_factor,
    gp.issue_response_time_hours,
    gp.pr_merge_time_hours,
    gp.burnout_score,
    gp.last_scanned_at,

    -- Package-specific data
    tp.created_at as package_created_at,
    tp.updated_at as package_updated_at,

    -- Vulnerability count (package-specific)
    (SELECT COUNT(*) FROM tracked_package_vulnerabilities WHERE package_id = tp.id) as vulnerability_count

FROM tracked_packages tp
LEFT JOIN github_projects gp ON tp.github_project_id = gp.id;

-- Verification queries (commented out - uncomment to test migration)
-- SELECT COUNT(*) as total_projects FROM github_projects;
-- SELECT COUNT(*) as packages_linked FROM tracked_packages WHERE github_project_id IS NOT NULL;
-- SELECT COUNT(*) as health_history_records FROM github_project_health_history;
-- SELECT github_project_id, COUNT(*) as package_count FROM tracked_packages WHERE github_project_id IS NOT NULL GROUP BY github_project_id ORDER BY package_count DESC;

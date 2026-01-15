-- Migration 019: Performance Indexes
-- Created: 2026-01-15
-- Purpose: Add missing indexes for improved query performance

-- Index for tracked_packages.repo_url (used in LIKE queries)
-- Improves performance of package lookups by repository URL
CREATE INDEX IF NOT EXISTS idx_tracked_packages_repo_url
ON tracked_packages(repo_url);

-- Trigram index for packages.name (used in ILIKE searches)
-- Enables fast case-insensitive pattern matching on package names
-- Requires pg_trgm extension
CREATE EXTENSION IF NOT EXISTS pg_trgm;
CREATE INDEX IF NOT EXISTS idx_packages_name_trgm
ON packages USING gin (name gin_trgm_ops);

-- Composite index for github_projects(owner, repo_name)
-- Improves performance of GitHub project lookups
CREATE INDEX IF NOT EXISTS idx_github_projects_owner_repo
ON github_projects(owner, repo_name);

-- Index for tracked_packages.purl (frequently queried)
-- Improves PURL-based lookups
CREATE INDEX IF NOT EXISTS idx_tracked_packages_purl
ON tracked_packages(purl);

-- Index for vulnerabilities.package_name with trigram
-- Enables fast case-insensitive search on vulnerability package names
CREATE INDEX IF NOT EXISTS idx_vulnerabilities_package_name_trgm
ON vulnerabilities USING gin (package_name gin_trgm_ops);

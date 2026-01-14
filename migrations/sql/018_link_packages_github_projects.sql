-- Migration 017: Link Packages to GitHub Projects
-- Phase 6.6: Package-GitHub Project Integration
-- Date: 2026-01-14

-- Add foreign key to link packages to github_projects
ALTER TABLE packages 
ADD COLUMN IF NOT EXISTS github_project_id INTEGER REFERENCES github_projects(id) ON DELETE SET NULL;

-- Create index for faster lookups
CREATE INDEX IF NOT EXISTS idx_packages_github_project_id ON packages(github_project_id);

-- Link existing packages to github_projects based on repo_url
UPDATE packages p
SET github_project_id = gp.id
FROM github_projects gp
WHERE p.repo_url IS NOT NULL 
  AND p.repo_url != ''
  AND gp.repo_url = p.repo_url
  AND p.github_project_id IS NULL;

-- Add comment
COMMENT ON COLUMN packages.github_project_id IS 'Foreign key to github_projects - packages inherit health scores from their GitHub project';

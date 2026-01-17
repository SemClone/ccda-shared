/*
Copyright (c) 2026 Oscar Valenzuela <oscar.valenzuela.b@gmail.com>
All Rights Reserved.

Migration 021: Security Advisories
Phase 7B: AI-Powered Advisory Generation (E.1, E.2, E.3)

This migration creates infrastructure for AI-generated security advisories:
- E.1 Remediation Synthesis - Fix recommendations from changelogs/releases
- E.2 Attack Vector Summary - Human-readable attack descriptions
- E.3 Affected Version Range - Version range detection

GitHub Issue: #40, #41
*/

-- Security advisories table for caching AI-generated content
CREATE TABLE IF NOT EXISTS security_advisories (
    id SERIAL PRIMARY KEY,
    vuln_id VARCHAR(100) NOT NULL UNIQUE,  -- Links to vulnerabilities.vuln_id
    cve_id VARCHAR(50),                    -- Normalized CVE ID if available

    -- E.1: Remediation Synthesis
    primary_fix JSONB,           -- {action, target_version, command, breaking_changes}
    workarounds JSONB,           -- [{description, effectiveness, instructions}]
    detection_method TEXT,       -- How to detect if affected
    unpatched_risk TEXT,         -- Risk assessment if no patch applied

    -- E.2: Attack Vector Summary
    attack_summary TEXT,         -- Non-technical explanation
    technical_summary TEXT,      -- Technical details for developers
    business_impact JSONB,       -- {confidentiality, integrity, availability, description}
    complexity VARCHAR(20),      -- low, medium, high
    network_exploitable BOOLEAN, -- Can be exploited over network
    requires_user_action BOOLEAN,-- Requires user interaction
    prerequisites JSONB,         -- [string] - Conditions needed for exploit

    -- E.3: Version Range
    affected_versions JSONB,     -- {range, semver_constraint, specific_versions[]}
    fixed_versions JSONB,        -- {branch: version}
    version_source VARCHAR(50),  -- osv, nvd, ai_extracted

    -- Metadata
    ai_provider VARCHAR(20),     -- openai, anthropic
    ai_model VARCHAR(50),        -- Model used for generation
    generation_tokens INTEGER,   -- Tokens used for generation
    generated_at TIMESTAMPTZ DEFAULT NOW(),
    github_data_used BOOLEAN DEFAULT FALSE,
    github_release_url TEXT,     -- URL of release notes if used

    -- Quality tracking
    generation_status VARCHAR(20) DEFAULT 'complete',  -- complete, partial, failed
    generation_error TEXT,       -- Error message if failed

    -- Timestamps
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Indexes for efficient queries
CREATE INDEX IF NOT EXISTS idx_advisories_vuln_id ON security_advisories(vuln_id);
CREATE INDEX IF NOT EXISTS idx_advisories_cve ON security_advisories(cve_id);
CREATE INDEX IF NOT EXISTS idx_advisories_generated ON security_advisories(generated_at DESC);
CREATE INDEX IF NOT EXISTS idx_advisories_status ON security_advisories(generation_status);

-- Trigger to update updated_at timestamp
CREATE OR REPLACE FUNCTION update_security_advisories_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER security_advisories_updated_at
    BEFORE UPDATE ON security_advisories
    FOR EACH ROW
    EXECUTE FUNCTION update_security_advisories_updated_at();

-- Add comments for documentation
COMMENT ON TABLE security_advisories IS 'AI-generated security advisories for vulnerabilities';
COMMENT ON COLUMN security_advisories.vuln_id IS 'Links to vulnerabilities.vuln_id - unique per vulnerability';
COMMENT ON COLUMN security_advisories.primary_fix IS 'JSON: {action, target_version, command, breaking_changes}';
COMMENT ON COLUMN security_advisories.workarounds IS 'JSON array: [{description, effectiveness, instructions}]';
COMMENT ON COLUMN security_advisories.business_impact IS 'JSON: {confidentiality, integrity, availability, description}';
COMMENT ON COLUMN security_advisories.affected_versions IS 'JSON: {range, semver_constraint, specific_versions[]}';
COMMENT ON COLUMN security_advisories.fixed_versions IS 'JSON: {branch: version}';
COMMENT ON COLUMN security_advisories.generation_status IS 'Generation status: complete, partial, or failed';

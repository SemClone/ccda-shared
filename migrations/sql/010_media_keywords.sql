-- ============================================================
-- Migration 010: Media Keywords Table
-- ============================================================
-- Purpose: Create table for managing inclusion/exclusion keywords for media filtering
-- Phase: Phase 6 - Media Monitoring
-- Date: 2026-01-11
-- Author: Phase 6 Implementation
--
-- Copyright (c) 2026 Oscar Valenzuela <oscar.valenzuela.b@gmail.com>
-- All Rights Reserved.
--
-- This file is part of CCDA, a proprietary commercial software project.
-- Unauthorized copying, distribution, or use is strictly prohibited.

-- ============================================================
-- MEDIA KEYWORDS TABLE
-- ============================================================

DROP TABLE IF EXISTS media_keywords CASCADE;

CREATE TABLE media_keywords (
    id SERIAL PRIMARY KEY,

    -- Keyword type: 'inclusion' (must match) or 'exclusion' (must NOT match)
    keyword_type VARCHAR(20) NOT NULL CHECK (keyword_type IN ('inclusion', 'exclusion')),

    -- The keyword text to match against media content
    keyword TEXT NOT NULL,

    -- Optional category for grouping keywords (e.g., 'security', 'licensing', 'ecosystem')
    category VARCHAR(50),

    -- Case-sensitive matching flag (default: case-insensitive)
    case_sensitive BOOLEAN DEFAULT false,

    -- Auto-queue for AI processing (bypasses manual review)
    -- When true, items matching this keyword go directly to ai_queue
    -- When false (default), items go to 'review' status for manual triage
    auto_queue_ai BOOLEAN DEFAULT false,

    -- Enable/disable keyword without deleting it
    enabled BOOLEAN DEFAULT true,

    -- Timestamps
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),

    -- Ensure unique keyword per type (can't have same keyword as both inclusion AND exclusion)
    UNIQUE(keyword_type, keyword)
);

-- ============================================================
-- INDEXES
-- ============================================================

-- Index on keyword_type for filtering by inclusion/exclusion
CREATE INDEX IF NOT EXISTS idx_keywords_type ON media_keywords(keyword_type);

-- Index on enabled for fast filtering of active keywords
CREATE INDEX IF NOT EXISTS idx_keywords_enabled ON media_keywords(enabled);

-- Index on auto_queue_ai for identifying auto-AI keywords
CREATE INDEX IF NOT EXISTS idx_keywords_auto_ai ON media_keywords(auto_queue_ai);

-- Index on category for grouping and filtering
CREATE INDEX IF NOT EXISTS idx_keywords_category ON media_keywords(category);

-- Composite index for common query: enabled keywords by type
CREATE INDEX IF NOT EXISTS idx_keywords_enabled_type ON media_keywords(enabled, keyword_type);

-- ============================================================
-- SEED DATA: Default Keywords
-- ============================================================

-- Inclusion keywords - Security-related terms
INSERT INTO media_keywords (keyword_type, keyword, category) VALUES
    ('inclusion', 'vulnerability', 'security'),
    ('inclusion', 'CVE-', 'security'),
    ('inclusion', 'security advisory', 'security'),
    ('inclusion', 'exploit', 'security'),
    ('inclusion', 'zero-day', 'security'),
    ('inclusion', 'RCE', 'security'),
    ('inclusion', 'SQL injection', 'security'),
    ('inclusion', 'XSS', 'security'),
    ('inclusion', 'CSRF', 'security'),
    ('inclusion', 'arbitrary code execution', 'security'),
    ('inclusion', 'remote code execution', 'security'),
    ('inclusion', 'privilege escalation', 'security'),
    ('inclusion', 'authentication bypass', 'security'),
    ('inclusion', 'security patch', 'security'),
    ('inclusion', 'security update', 'security')
ON CONFLICT DO NOTHING;

-- Inclusion keywords - Ecosystem-specific terms
INSERT INTO media_keywords (keyword_type, keyword, category) VALUES
    ('inclusion', 'npm', 'ecosystem'),
    ('inclusion', 'PyPI', 'ecosystem'),
    ('inclusion', 'Maven', 'ecosystem'),
    ('inclusion', 'RubyGems', 'ecosystem'),
    ('inclusion', 'crates.io', 'ecosystem'),
    ('inclusion', 'NuGet', 'ecosystem'),
    ('inclusion', 'Packagist', 'ecosystem'),
    ('inclusion', 'Go module', 'ecosystem')
ON CONFLICT DO NOTHING;

-- Inclusion keywords - License and ownership changes
INSERT INTO media_keywords (keyword_type, keyword, category) VALUES
    ('inclusion', 'license change', 'licensing'),
    ('inclusion', 'relicensed', 'licensing'),
    ('inclusion', 'acquisition', 'ownership'),
    ('inclusion', 'acquired', 'ownership'),
    ('inclusion', 'deprecated', 'maintenance'),
    ('inclusion', 'abandoned', 'maintenance'),
    ('inclusion', 'maintainer change', 'maintenance'),
    ('inclusion', 'fork', 'maintenance'),
    ('inclusion', 'supply chain', 'security')
ON CONFLICT DO NOTHING;

-- Inclusion keywords - General open source terms
INSERT INTO media_keywords (keyword_type, keyword, category) VALUES
    ('inclusion', 'open source', 'general'),
    ('inclusion', 'OSS', 'general'),
    ('inclusion', 'FOSS', 'general'),
    ('inclusion', 'dependency', 'general'),
    ('inclusion', 'package manager', 'general')
ON CONFLICT DO NOTHING;

-- Exclusion keywords - Spam and irrelevant content
INSERT INTO media_keywords (keyword_type, keyword, category) VALUES
    ('exclusion', 'job posting', 'spam'),
    ('exclusion', 'hiring', 'spam'),
    ('exclusion', 'sponsored', 'spam'),
    ('exclusion', 'advertisement', 'spam'),
    ('exclusion', 'crypto', 'spam'),
    ('exclusion', 'ICO', 'spam'),
    ('exclusion', 'airdrop', 'spam'),
    ('exclusion', 'giveaway', 'spam'),
    ('exclusion', 'discount code', 'spam'),
    ('exclusion', 'affiliate', 'spam')
ON CONFLICT DO NOTHING;

-- ============================================================
-- TRIGGER: Update updated_at timestamp
-- ============================================================

CREATE OR REPLACE FUNCTION update_media_keywords_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_update_media_keywords_updated_at
    BEFORE UPDATE ON media_keywords
    FOR EACH ROW
    EXECUTE FUNCTION update_media_keywords_updated_at();

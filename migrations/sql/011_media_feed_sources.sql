-- ============================================================
-- Migration 011: Media Feed Sources Table
-- ============================================================
-- Purpose: Create table for managing media feed sources (RSS, HackerNews, Reddit, Bluesky, etc.)
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
-- MEDIA FEED SOURCES TABLE
-- ============================================================

DROP TABLE IF EXISTS media_feed_sources CASCADE;

CREATE TABLE media_feed_sources (
    id SERIAL PRIMARY KEY,

    -- Feed identification
    feed_name VARCHAR(100) UNIQUE NOT NULL,
    feed_type VARCHAR(20) NOT NULL CHECK (feed_type IN ('rss', 'hackernews', 'reddit', 'bluesky', 'github_issues', 'email_list', 'forum')),
    feed_url VARCHAR(1000),  -- Can be NULL for API-based sources

    -- Feed status
    enabled BOOLEAN DEFAULT true,

    -- Collection configuration
    check_interval_minutes INTEGER DEFAULT 60,  -- How often to check for new items
    max_items_per_fetch INTEGER DEFAULT 50,     -- Maximum items to fetch per run

    -- Authentication (stored as JSONB for flexibility)
    -- Examples:
    --   RSS: {}
    --   Reddit: {}  (public JSON API)
    --   HackerNews: {}  (public API)
    --   Bluesky: {"username": "...", "app_password": "..."}
    --   GitHub: {"token": "..."}
    auth_config JSONB DEFAULT '{}'::jsonb,

    -- Feed-specific configuration (JSONB for extensibility)
    -- Examples:
    --   Reddit: {"subreddits": ["netsec", "security", "opensource"]}
    --   HackerNews: {"categories": ["top", "ask", "show"]}
    --   GitHub Issues: {"repos": ["owner/repo1", "owner/repo2"], "labels": ["security", "vulnerability"]}
    feed_config JSONB DEFAULT '{}'::jsonb,

    -- Statistics
    last_fetch_at TIMESTAMP,
    last_fetch_status VARCHAR(20),  -- 'success', 'error', 'rate_limited'
    last_fetch_error TEXT,

    items_fetched_total INTEGER DEFAULT 0,      -- Total items fetched since creation
    items_filtered_total INTEGER DEFAULT 0,     -- Total items that passed filters
    items_ai_processed_total INTEGER DEFAULT 0, -- Total items processed by AI

    -- Timestamps
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- ============================================================
-- INDEXES
-- ============================================================

-- Index on enabled for filtering active feeds
CREATE INDEX IF NOT EXISTS idx_feed_sources_enabled ON media_feed_sources(enabled);

-- Index on feed_type for filtering by source type
CREATE INDEX IF NOT EXISTS idx_feed_sources_type ON media_feed_sources(feed_type);

-- Index on last_fetch_at for scheduling (find feeds that need fetching)
CREATE INDEX IF NOT EXISTS idx_feed_sources_last_fetch ON media_feed_sources(last_fetch_at);

-- Composite index for active feeds that need fetching
CREATE INDEX IF NOT EXISTS idx_feed_sources_enabled_fetch ON media_feed_sources(enabled, last_fetch_at);

-- ============================================================
-- SEED DATA: Default RSS Feeds
-- ============================================================

-- Security news RSS feeds
INSERT INTO media_feed_sources (feed_name, feed_type, feed_url, check_interval_minutes) VALUES
    ('The Hacker News', 'rss', 'https://feeds.feedburner.com/TheHackersNews', 60),
    ('Krebs on Security', 'rss', 'https://krebsonsecurity.com/feed/', 120),
    ('Schneier on Security', 'rss', 'https://www.schneier.com/feed/atom/', 120),
    ('GitHub Security Advisories', 'rss', 'https://github.com/security-advisories.atom', 60),
    ('Dark Reading', 'rss', 'https://www.darkreading.com/rss_simple.asp', 120),
    ('Bleeping Computer', 'rss', 'https://www.bleepingcomputer.com/feed/', 60),
    ('The Register - Security', 'rss', 'https://www.theregister.com/security/headlines.atom', 120)
ON CONFLICT (feed_name) DO NOTHING;

-- HackerNews (API-based, no RSS URL needed)
INSERT INTO media_feed_sources (
    feed_name,
    feed_type,
    feed_url,
    check_interval_minutes,
    max_items_per_fetch,
    feed_config
) VALUES (
    'HackerNews',
    'hackernews',
    NULL,  -- API-based
    15,  -- Check every 15 minutes
    50,
    '{"categories": ["top", "ask", "show"]}'::jsonb
) ON CONFLICT (feed_name) DO NOTHING;

-- Reddit (public JSON API)
INSERT INTO media_feed_sources (
    feed_name,
    feed_type,
    feed_url,
    check_interval_minutes,
    max_items_per_fetch,
    feed_config
) VALUES (
    'Reddit Security',
    'reddit',
    NULL,  -- API-based
    30,  -- Check every 30 minutes
    50,
    '{"subreddits": ["netsec", "security", "opensource", "programming", "webdev"]}'::jsonb
) ON CONFLICT (feed_name) DO NOTHING;

-- Bluesky (disabled by default - requires credentials)
INSERT INTO media_feed_sources (
    feed_name,
    feed_type,
    feed_url,
    check_interval_minutes,
    max_items_per_fetch,
    enabled,
    feed_config,
    auth_config
) VALUES (
    'Bluesky Security',
    'bluesky',
    NULL,  -- API-based
    30,  -- Check every 30 minutes
    50,
    false,  -- Disabled until credentials configured
    '{"search_terms": ["security vulnerability", "CVE", "zero day", "exploit"]}'::jsonb,
    '{"username": "", "app_password": ""}'::jsonb  -- To be filled in via UI or env vars
) ON CONFLICT (feed_name) DO NOTHING;

-- ============================================================
-- TRIGGER: Update updated_at timestamp
-- ============================================================

CREATE OR REPLACE FUNCTION update_media_feed_sources_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_update_media_feed_sources_updated_at
    BEFORE UPDATE ON media_feed_sources
    FOR EACH ROW
    EXECUTE FUNCTION update_media_feed_sources_updated_at();

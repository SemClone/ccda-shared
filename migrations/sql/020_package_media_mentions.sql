/*
Copyright (c) 2026 Oscar Valenzuela <oscar.valenzuela.b@gmail.com>
All Rights Reserved.

Migration 020: Package-Media Mentions
Phase B: Package-Media Integration

This migration creates infrastructure to link AI-processed media items to tracked packages:
- Junction table for package-media relationships
- Indexes for efficient queries
- View for aggregated media statistics per package

GitHub Issue: #86
*/

-- Junction table: tracks which media items mention which packages
CREATE TABLE IF NOT EXISTS package_media_mentions (
    id SERIAL PRIMARY KEY,
    package_id INTEGER NOT NULL REFERENCES tracked_packages(id) ON DELETE CASCADE,
    media_item_id INTEGER NOT NULL REFERENCES media_items(id) ON DELETE CASCADE,
    
    -- Mention metadata
    mention_type TEXT NOT NULL,      -- 'package_name', 'purl', 'github_url'
    mention_text TEXT,               -- Actual text that matched
    confidence REAL DEFAULT 1.0,     -- Match confidence (0.0-1.0)
    
    -- Context
    context_snippet TEXT,            -- Surrounding text (±50 chars)
    
    -- Discovery tracking
    discovered_at TIMESTAMP DEFAULT NOW(),
    
    -- Ensure unique package-media pairs
    UNIQUE(package_id, media_item_id)
);

-- Indexes for efficient queries
CREATE INDEX IF NOT EXISTS idx_pkg_media_package_id ON package_media_mentions(package_id);
CREATE INDEX IF NOT EXISTS idx_pkg_media_media_id ON package_media_mentions(media_item_id);
CREATE INDEX IF NOT EXISTS idx_pkg_media_discovered ON package_media_mentions(discovered_at DESC);
CREATE INDEX IF NOT EXISTS idx_pkg_media_confidence ON package_media_mentions(confidence DESC);

-- View: Package media summary
-- Aggregates media mention statistics per package
CREATE OR REPLACE VIEW package_media_summary AS
SELECT
    p.id AS package_id,
    p.purl,
    p.name AS package_name,
    COUNT(DISTINCT pmm.media_item_id) AS total_media_mentions,
    COUNT(DISTINCT CASE WHEN m.sentiment = 'negative' THEN pmm.media_item_id END) AS negative_mentions,
    COUNT(DISTINCT CASE WHEN m.sentiment = 'positive' THEN pmm.media_item_id END) AS positive_mentions,
    COUNT(DISTINCT CASE WHEN m.sentiment = 'neutral' THEN pmm.media_item_id END) AS neutral_mentions,
    COUNT(DISTINCT CASE WHEN m.risk_score >= 70 THEN pmm.media_item_id END) AS high_risk_mentions,
    MAX(m.published) AS latest_mention_date,
    AVG(m.risk_score) AS avg_risk_score,
    AVG(pmm.confidence) AS avg_match_confidence
FROM tracked_packages p
LEFT JOIN package_media_mentions pmm ON p.id = pmm.package_id
LEFT JOIN media_items m ON pmm.media_item_id = m.id
GROUP BY p.id, p.purl, p.name;

-- Add comments for documentation
COMMENT ON TABLE package_media_mentions IS 'Links tracked packages to AI-processed media items that mention them';
COMMENT ON COLUMN package_media_mentions.mention_type IS 'Detection method: package_name, purl, or github_url';
COMMENT ON COLUMN package_media_mentions.confidence IS 'Match confidence score (0.0-1.0), minimum 0.7 saved';
COMMENT ON VIEW package_media_summary IS 'Aggregated media mention statistics per package for quick queries';

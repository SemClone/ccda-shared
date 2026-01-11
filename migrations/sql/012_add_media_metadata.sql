-- Migration 012: Add metadata column to media_items
-- Stores source-specific metadata in JSONB format
-- Examples: HackerNews (score, comments), Reddit (subreddit, author), Bluesky (engagement metrics)

ALTER TABLE media_items
ADD COLUMN IF NOT EXISTS metadata JSONB DEFAULT '{}'::jsonb;

-- Create GIN index for metadata queries
CREATE INDEX IF NOT EXISTS idx_media_items_metadata ON media_items USING GIN (metadata);

-- Add comment
COMMENT ON COLUMN media_items.metadata IS 'Source-specific metadata stored as JSON (HN score, Reddit subreddit, etc.)';

-- ============================================================
-- Migration 009: Media Enhancements for Phase 6
-- ============================================================
-- Purpose: Add filtering workflow columns for media monitoring pipeline
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
-- FILTER WORKFLOW COLUMNS
-- ============================================================

-- Add filter_action column for pipeline tracking
-- Values: pending, review, ai_queue, processing, processed, archive, excluded
ALTER TABLE media_items
ADD COLUMN IF NOT EXISTS filter_action VARCHAR(20) DEFAULT 'pending';

-- Add matched_keywords for tracking which keywords matched during filtering
ALTER TABLE media_items
ADD COLUMN IF NOT EXISTS matched_keywords JSONB DEFAULT '[]'::jsonb;

-- Add exclusion tracking columns
ALTER TABLE media_items
ADD COLUMN IF NOT EXISTS excluded_by VARCHAR(255);

ALTER TABLE media_items
ADD COLUMN IF NOT EXISTS exclusion_reason TEXT;

-- ============================================================
-- CONTENT EXTRACTION COLUMNS
-- ============================================================

-- Add external_urls for tracking URLs found in content
ALTER TABLE media_items
ADD COLUMN IF NOT EXISTS external_urls JSONB DEFAULT '[]'::jsonb;

-- Add word_count for minimum content filter
ALTER TABLE media_items
ADD COLUMN IF NOT EXISTS word_count INTEGER;

-- Add content_extracted flag to track processing status
ALTER TABLE media_items
ADD COLUMN IF NOT EXISTS content_extracted BOOLEAN DEFAULT false;

-- ============================================================
-- MANUAL OVERRIDE COLUMNS
-- ============================================================

-- Add manual override capability for user-flagged items
ALTER TABLE media_items
ADD COLUMN IF NOT EXISTS manual_override BOOLEAN DEFAULT false;

ALTER TABLE media_items
ADD COLUMN IF NOT EXISTS override_reason TEXT;

-- ============================================================
-- INDEXES FOR PERFORMANCE
-- ============================================================

-- Index on filter_action for fast filtering queries
CREATE INDEX IF NOT EXISTS idx_media_filter_action ON media_items(filter_action);

-- Index on word_count for content quality filtering
CREATE INDEX IF NOT EXISTS idx_media_word_count ON media_items(word_count);

-- Index on manual_override for displaying user-flagged items
CREATE INDEX IF NOT EXISTS idx_media_manual_override ON media_items(manual_override);

-- GIN index on matched_keywords for keyword-based queries
CREATE INDEX IF NOT EXISTS idx_media_matched_keywords ON media_items USING gin(matched_keywords);

-- Index on content_extracted for processing queue
CREATE INDEX IF NOT EXISTS idx_media_content_extracted ON media_items(content_extracted);

-- Composite index for common filter queries (filter_action + published date)
CREATE INDEX IF NOT EXISTS idx_media_filter_published ON media_items(filter_action, published DESC);

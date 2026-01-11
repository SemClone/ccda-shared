-- ============================================================
-- Migration 013: AI Processing Fields for Media Intelligence
-- ============================================================
-- Purpose: Add columns for AI-powered supply chain intelligence extraction
-- Phase: Phase 6.5 - AI Processing Pipeline
-- Date: 2026-01-11
-- Author: Phase 6 Implementation
--
-- Copyright (c) 2026 Oscar Valenzuela <oscar.valenzuela.b@gmail.com>
-- All Rights Reserved.
--
-- This file is part of CCDA, a proprietary commercial software project.
-- Unauthorized copying, distribution, or use is strictly prohibited.

-- ============================================================
-- AI PROCESSING STATUS COLUMNS
-- ============================================================

-- Flag to track if AI processing has been completed
ALTER TABLE media_items
ADD COLUMN IF NOT EXISTS ai_processed BOOLEAN DEFAULT false;

-- Flag to indicate if item is actionable (mentions specific packages/technologies)
ALTER TABLE media_items
ADD COLUMN IF NOT EXISTS actionable BOOLEAN DEFAULT false;

-- ============================================================
-- AI EXTRACTION RESULTS
-- ============================================================

-- Technologies/projects mentioned (JSONB array of strings)
-- Example: ["Kubernetes", "Linux Kernel", "OpenSSL"]
ALTER TABLE media_items
ADD COLUMN IF NOT EXISTS technologies_mentioned JSONB DEFAULT '[]'::jsonb;

-- ============================================================
-- AI SCORING COLUMNS
-- ============================================================

-- Confidence score from AI (0-100)
-- <40% = low confidence, mark for archive
ALTER TABLE media_items
ADD COLUMN IF NOT EXISTS confidence_score INTEGER CHECK (confidence_score >= 0 AND confidence_score <= 100);

-- ============================================================
-- RECOMMENDATIONS
-- ============================================================

-- AI-generated recommendations (JSONB array of strings)
-- Risk-based recommendations for security teams
ALTER TABLE media_items
ADD COLUMN IF NOT EXISTS recommendations JSONB DEFAULT '[]'::jsonb;

-- ============================================================
-- INDEXES FOR PERFORMANCE
-- ============================================================

-- Index on ai_processed for processing queue queries
CREATE INDEX IF NOT EXISTS idx_media_ai_processed ON media_items(ai_processed);

-- Index on actionable for filtering actionable intelligence
CREATE INDEX IF NOT EXISTS idx_media_actionable ON media_items(actionable);

-- Index on confidence_score for quality filtering
CREATE INDEX IF NOT EXISTS idx_media_confidence_score ON media_items(confidence_score);

-- Composite index for AI queue processing (filter_action + ai_processed)
CREATE INDEX IF NOT EXISTS idx_media_ai_queue ON media_items(filter_action, ai_processed) WHERE filter_action = 'ai_queue';

-- GIN index on technologies_mentioned for searching by technology
CREATE INDEX IF NOT EXISTS idx_media_technologies ON media_items USING gin(technologies_mentioned);

-- GIN index on recommendations for searching recommendations
CREATE INDEX IF NOT EXISTS idx_media_recommendations ON media_items USING gin(recommendations);

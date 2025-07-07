-- Dual-Model Schema Extension Migration
-- Generated: 2025-07-06T22:44:37.394827
-- Purpose: Add metadata support for dual-model VLM processing

-- Note: No schema changes required for PostgreSQL + Pensieve
-- The existing metadata_entries table supports the new dual-model fields

-- New metadata fields that will be used:

-- Field: llama3_session_result
-- Description: Llama3 session-level workflow analysis result
-- Data Type: json
-- Source Type: llama3
-- Example: {
  "workflow_type": "coding",
  "main_activities": [
    "editing_code",
    "testing"
  ],
  "efficiency": "high",
  "focus_level": "focused",
  "session_id": "session_1",
  "analysis_timestamp": "2025-01-01T12:00:00Z"
}

-- Field: workflow_analysis
-- Description: Overall workflow pattern analysis across sessions
-- Data Type: json
-- Source Type: dual_model
-- Example: {
  "primary_workflow_type": "mixed",
  "session_boundaries": [],
  "total_duration_minutes": 60,
  "productivity_indicators": {},
  "analysis_timestamp": "2025-01-01T12:00:00Z"
}

-- Field: session_id
-- Description: Session identifier for grouping related screenshots
-- Data Type: text
-- Source Type: dual_model
-- Example: "session_20250101_120000"

-- Field: dual_model_processed
-- Description: Flag indicating dual-model processing completion
-- Data Type: text
-- Source Type: dual_model
-- Example: "true"

-- Field: dual_model_version
-- Description: Version of dual-model processing used
-- Data Type: text
-- Source Type: dual_model
-- Example: "v1.0_minicpmv8b_llama3_8b"

-- Verification queries:

-- 1. Check for dual-model metadata entries
SELECT key, COUNT(*) as count
FROM metadata_entries 
WHERE key IN ('llama3_session_result', 'workflow_analysis', 'session_id', 'dual_model_processed', 'dual_model_version')
GROUP BY key;

-- 2. Sample dual-model entries
SELECT entity_id, key, LEFT(value::text, 100) as value_preview, source_type, created_at
FROM metadata_entries 
WHERE source_type IN ('llama3', 'dual_model')
ORDER BY created_at DESC 
LIMIT 10;

-- 3. Session grouping example
SELECT session_id_meta.value as session_id, COUNT(*) as screenshot_count
FROM metadata_entries session_id_meta
WHERE session_id_meta.key = 'session_id'
GROUP BY session_id_meta.value
ORDER BY screenshot_count DESC;

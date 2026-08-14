-- Additive/idempotent enrollment settings migration.
ALTER TYPE ingestion_mode ADD VALUE IF NOT EXISTS 'new_only';
ALTER TYPE ingestion_mode ADD VALUE IF NOT EXISTS 'last_3_months';
ALTER TYPE ingestion_mode ADD VALUE IF NOT EXISTS 'last_year';
ALTER TYPE ingestion_mode ADD VALUE IF NOT EXISTS 'all';
ALTER TYPE ingestion_mode ADD VALUE IF NOT EXISTS 'selected';

ALTER TABLE channels ADD COLUMN IF NOT EXISTS include_videos BOOLEAN DEFAULT TRUE;
ALTER TABLE channels ADD COLUMN IF NOT EXISTS include_lives BOOLEAN DEFAULT TRUE;
ALTER TABLE channels ADD COLUMN IF NOT EXISTS include_shorts BOOLEAN DEFAULT TRUE;
ALTER TABLE pipeline_items ALTER COLUMN channel_id DROP NOT NULL;

UPDATE channels SET ingestion_mode = 'new_only' WHERE ingestion_mode = 'auto';
UPDATE channels SET ingestion_mode = 'selected' WHERE ingestion_mode = 'review';

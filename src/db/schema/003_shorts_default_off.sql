-- Shorts are opt-in, not opt-out: pre-bridge discovery never enumerated the
-- Shorts tab, so a TRUE default would have started mass-ingesting shorts the
-- moment the DB-driven bridge went live. Applied to Banner 2026-08-16.
ALTER TABLE channels ALTER COLUMN include_shorts SET DEFAULT FALSE;
UPDATE channels SET include_shorts = FALSE;

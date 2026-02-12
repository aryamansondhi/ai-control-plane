-- Enable UUID generation
CREATE EXTENSION IF NOT EXISTS pgcrypto;

-- ============================================================
-- 1) Raw Vendor Payloads (Audit Layer)
-- ============================================================

CREATE TABLE IF NOT EXISTS raw_payloads (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    source TEXT NOT NULL,
    fetched_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    payload_json JSONB NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_raw_payloads_source_fetched_at
ON raw_payloads(source, fetched_at DESC);


-- ============================================================
-- 2) Canonical Immutable Event Store
-- ============================================================

CREATE TABLE IF NOT EXISTS events (
    event_id UUID PRIMARY KEY,
    event_type TEXT NOT NULL,
    source TEXT NOT NULL,
    entity_id TEXT,
    entity_type TEXT,
    occurred_at TIMESTAMPTZ NOT NULL,
    ingested_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    schema_version INT NOT NULL CHECK (schema_version >= 1),
    trace_id UUID NOT NULL,
    payload_json JSONB NOT NULL
);

-- Query Performance Indexes
CREATE INDEX IF NOT EXISTS idx_events_event_type_occurred_at
ON events(event_type, occurred_at DESC);

CREATE INDEX IF NOT EXISTS idx_events_entity
ON events(entity_id, entity_type);

CREATE INDEX IF NOT EXISTS idx_events_trace_id
ON events(trace_id);

CREATE INDEX IF NOT EXISTS idx_events_occurred_at
ON events(occurred_at DESC);

-- ============================================================
-- 3) Transactional Outbox
-- ============================================================

CREATE TABLE IF NOT EXISTS outbox (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    event_id UUID NOT NULL REFERENCES events(event_id) ON DELETE CASCADE,
    topic TEXT NOT NULL,
    payload_json JSONB NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    delivered_at TIMESTAMPTZ,
    delivery_attempts INT NOT NULL DEFAULT 0 CHECK (delivery_attempts >= 0),
    last_error TEXT
);

-- Fast retrieval of undelivered messages
CREATE INDEX IF NOT EXISTS idx_outbox_pending
ON outbox(created_at ASC)
WHERE delivered_at IS NULL;

-- Prevent duplicate publication rows per event/topic
CREATE UNIQUE INDEX IF NOT EXISTS uq_outbox_event_topic
ON outbox(event_id, topic);
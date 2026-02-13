# Canonical Event Contract

This document defines the immutable event schema for the AI Control Plane.

## Design Principles

- Events are immutable (append-only).
- All events are globally unique (UUID v4).
- All events are versioned.
- Payload is domain-specific and stored as JSONB.
- All events must be inserted transactionally alongside outbox records.

## Event Schema

Top-level fields:

- event_id (UUID) – globally unique
- event_type (TEXT)
- source (TEXT)
- entity_id (TEXT, optional)
- entity_type (TEXT, optional)
- occurred_at (TIMESTAMPTZ)
- ingested_at (TIMESTAMPTZ)
- schema_version (INT)
- trace_id (UUID)
- payload (JSON)

## Delivery Guarantees

We implement the Transactional Outbox pattern:

Ingestion must:
1. Insert raw payload
2. Insert canonical event
3. Insert outbox record
4. Commit transaction

This guarantees atomic persistence and at-least-once delivery.
# Development Log

## 📅 Day 32 — Canonical Event Contract + Transactional Outbox

**Focus:** Foundation & data integrity.

### What was implemented

**Designed canonical event schema:**
- `event_id`
- `event_type`
- `entity_id`
- `entity_type`
- `trace_id`
- `schema_version`
- `occurred_at`
- `payload_json`

**Database tables:**
- Created `raw_payloads` table for audit-level storage
- Created `events` table as immutable event store
- Implemented `outbox` table for reliable event delivery
- Applied Transactional Outbox pattern to prevent dual-write failures

### Architectural Outcome

- Atomic persistence boundary established
- Clear separation between:
  - Raw ingestion data
  - Canonical domain events
  - Delivery layer
- Foundation laid for deterministic event-driven architecture

---

## 📅 Day 33 — Ingestion Service (Atomic Triple Write)

**Focus:** Executable ingestion pipeline.

### What was implemented

- Integrated `yfinance` as external data source
- Built ingestion module:
  - Connector (data fetch)
  - Transformer (raw → canonical)
  - Repository (transaction boundary)
- Implemented atomic triple write inside a single DB transaction:
  - Insert raw payload
  - Insert canonical event
  - Insert outbox record
- Added `trace_id` propagation
- Dockerized PostgreSQL setup
- Migrated runtime to Python 3.11

### Architectural Outcome

- First live event successfully ingested
- Outbox populated deterministically
- No dual writes
- No silent failure window
- Control Plane transitioned from schema to execution

---

## 📅 Day 34 — Relay Worker + State Transition

**Focus:** Event delivery lifecycle.

### What was implemented

- Built relay worker module
- Implemented concurrency-safe polling:
  - `FOR UPDATE SKIP LOCKED`
- Added delivery state transition:
  - `delivered_at`
  - `delivery_attempts`
- Simulated publisher layer (replaceable transport abstraction)
- Verified end-to-end event lifecycle:
  - Ingestion → Outbox → Relay → Delivered

### Architectural Outcome

- System now supports event-driven flow
- Delivery is traceable and stateful
- Safe for horizontal worker scaling
- Outbox lifecycle operational

---

## 📅 Day 35 — Retry Lifecycle & Dead Lettering

**Focus:** Production-grade retry orchestration.

### What was implemented

Implemented production-grade retry orchestration inside the outbox relay:
- Exponential backoff scheduling
- Controlled retry ceiling (5 attempts)
- Dead-letter transition for terminal failures
- Deterministic event eligibility filtering
- Concurrency-safe row claiming with `SKIP LOCKED`
- Validated behavior via simulated publish failures

### Architectural Outcome

The relay now enforces safe retry semantics and prevents infinite retry loops.

---

## 📅 Day 36 — Structured Logging & Failure Observability

**Focus:** Production-grade observability & deterministic traceability.

### What was implemented

- Replaced ad-hoc prints with centralized structured logging
- Built custom `JsonFormatter` for machine-readable logs
- Implemented structured fields:
  - `event_id`
  - `attempt`
  - `topic`
  - `error`
- Added UUID-safe JSON serialization
- Ensured consistent ISO timestamping
- Integrated structured logging into relay lifecycle:
  - Publishing attempt
  - Delivery success
  - Delivery failure
- Validated log emission under simulated failure conditions

### Architectural Outcome

- Relay behavior is now observable and machine-parseable
- Failures are traceable with contextual metadata
- System ready for:
  - Log aggregation
  - Metrics extraction
  - Distributed tracing integration
- Transition from **"Working system"** to **"Inspectable system"**

The Control Plane now exposes deterministic operational signals.
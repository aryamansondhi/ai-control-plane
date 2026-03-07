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

---

## 📅 Day 37 — Metrics & Operational Observability

**Focus:** Making system behavior externally measurable.

### What was implemented

- Integrated Prometheus client for runtime metrics
- Created centralized metrics module:
  - `events_published_total`
  - `events_failed_total`
  - `events_dead_lettered_total`
- Instrumented relay worker:
  - Success increments `events_published_total`
  - Failure increments `events_failed_total`
- Ensured metrics increment **after** state transition commits
- Built FastAPI server exposing:
  - `/health` endpoint
  - `/metrics` endpoint (Prometheus-compatible)
- Resolved multi-process metrics isolation by executing relay within API process
- Validated counter increments under simulated publish failures

### Architectural Outcome

- System is now externally observable without direct database access
- Runtime behavior is measurable via standard monitoring tools
- Metrics accurately reflect delivery success and failure states
- Foundation established for:
  - Alerting
  - Dashboards
  - Latency instrumentation
  - Production deployment readiness
- Transition from **"Inspectable system"** to **"Monitorable system"**

The Control Plane now emits operational signals that can be scraped, graphed, and alerted on.

---

## 📅 Day 38 — Latency Instrumentation & Performance Telemetry

**Focus:** Measuring system performance, not just outcomes.

### What was implemented

- Added Prometheus `Histogram` for publish latency:
  - `publish_latency_seconds`
- Instrumented relay worker with high-precision timing:
  - Used `time.perf_counter()` for accurate duration measurement
  - Observed latency only on successful publish execution
- Wired latency observation into publish lifecycle before state transition commit
- Integrated `events_dead_lettered_total` metric increment on retry ceiling
- Validated histogram bucket distribution under simulated 20ms publish delay
- Confirmed counter and histogram behavior through `/metrics` endpoint

### Architectural Outcome

- System now exposes performance distribution, not just event counts
- Publish duration is measurable across latency buckets
- Control Plane supports:
  - Performance monitoring
  - SLO tracking
  - Capacity planning insights
- Dead-letter transitions are externally observable via metrics
- Transition from **"Monitorable system"** to **"Performance-aware system"**

The Control Plane now emits timing signals that enable real operational intelligence.

---

## 📅 Day 39 — Background Scheduler & Autonomous Relay

**Focus:** Making the Control Plane self-operating.

### What was implemented

- Integrated `APScheduler` into the FastAPI process
- Relay worker now executes automatically every 30 seconds
- Scheduler starts on application boot and shuts down cleanly on exit
- Manual `/run-relay` endpoint retained for on-demand triggering
- Verified autonomous delivery cycle without manual intervention

### Architectural Outcome

- Control Plane no longer requires human triggers to process events
- Relay operates as a continuous background service
- Scheduler lifecycle is bound to FastAPI application lifecycle
- Foundation established for fully autonomous event-driven execution
- Transition from **"Infrastructure you operate"** to **"Infrastructure that operates itself"**

The Control Plane now runs. Not when told to. Always.

---

## 📅 Day 40 — Dead-Letter Inspection API

**Focus:** Surfacing terminal failures without database access.

### What was implemented

- Added `GET /dead-letters` endpoint — lists all dead-lettered events
- Added `GET /dead-letters/{event_id}` endpoint — full forensic detail on a specific failure
- Queries join `outbox` and `events` tables to surface complete context:
  - `event_id`, `trace_id`, `topic`, `entity_id`
  - `delivery_attempts`, `last_error`, `dead_lettered_at`
  - Full `payload_json`
- Extended `repository.py` with `get_dead_letters()` and `get_dead_letter_by_id()`

### Architectural Outcome

- Terminal failures are now inspectable via API without touching the database
- Full event lifecycle is traceable end-to-end through `trace_id`
- Operators can identify, investigate, and act on dead-lettered events externally
- Transition from **"Infrastructure that operates itself"** to **"Infrastructure that explains itself"**

The Control Plane now surfaces its own failures.

---

## 📅 Day 41 — Event Lifecycle Trace Endpoint

**Focus:** Full end-to-end event introspection via API.

### What was implemented

- Added `GET /events/{event_id}/trace` endpoint
- Reconstructs the complete lifecycle of any event in a single API call:
  - Canonical event record (`event_type`, `entity_id`, `occurred_at`, `payload`)
  - Outbox delivery record (`delivery_attempts`, `next_attempt_at`, `delivered_at`, `dead_lettered_at`, `last_error`)
  - `final_state` — `DELIVERED`, `DEAD_LETTERED`, or `PENDING`
- `trace_id` surfaced at top level for cross-system correlation
- Guard added for events with no outbox record
- Extended `repository.py` with `get_event_trace()`

### Architectural Outcome

- Any event can be fully reconstructed without database access
- Ingestion → delivery → failure chain is inspectable end-to-end
- `trace_id` enables correlation across logs, metrics, and trace endpoint
- Transition from **"Infrastructure that explains itself"** to **"Infrastructure that is fully introspectable"**

The Control Plane now tells the complete story of every event.

---

## 📅 Day 42 — Dead-Letter Replay

**Focus:** Closing the reliability loop — from inspection to action.

### What was implemented

- Added `POST /dead-letters/{event_id}/replay` endpoint
- Requeues a dead-lettered event back into the outbox by resetting:
  - `dead_lettered_at` → `NULL`
  - `delivered_at` → `NULL`
  - `delivery_attempts` → `0`
  - `next_attempt_at` → `NOW()`
  - `last_error` → `NULL`
- Scheduler automatically picks up replayed events within 30 seconds
- Guard added for events that are not dead-lettered
- Extended `repository.py` with `replay_dead_letter()`

### Architectural Outcome

- Dead-lettered events are now recoverable without database access
- Full reliability loop established: ingest → deliver → fail → inspect → replay
- Operators can recover from failures via API after fixing underlying issues
- Transition from **"Infrastructure that is fully introspectable"** to **"Infrastructure that is self-recoverable"**

The Control Plane can now heal itself.

---

## 📅 Day 43 — Consumer Layer & Donna Integration

**Focus:** Closing the loop — connecting Donna to the Control Plane.

### What was implemented

- Created `app/consumers/donna_wolf_consumer.py`
- Implemented `get_latest_market_event(symbol)` — reads most recently delivered market event from the event store
- Implemented `get_portfolio_snapshot(symbols)` — batch consumer for multiple symbols
- Consumer queries join `events` and `outbox` tables, only reading successfully delivered events
- Verified live consumption of AAPL market data via trace_id

### Architectural Outcome

- `consumers/` folder active for the first time since Day 32
- Donna's Wolf no longer calls `yfinance` directly
- Market data is now consumed from reliable, structured, traceable canonical events
- Full pipeline is complete:
  - `yfinance → ingestion → events → outbox → relay → consumer → Donna`
- Transition from **"Infrastructure that is self-recoverable"** to **"Infrastructure with active consumers"**

The Control Plane now has a downstream. The two systems are one.

---

## 📅 Day 44 — System Status Endpoint

**Focus:** Turning `/health` into a genuine operational dashboard.

### What was implemented

- Upgraded `/health` from a simple ping to a full system status response
- Exposes real-time system state:
  - `scheduler` — running or stopped
  - `pending_events` — events waiting for delivery
  - `dead_lettered_events` — terminal failures awaiting inspection
  - `delivered_events` — successfully processed events
  - `last_delivered_at` — timestamp of most recent delivery
- Extended `repository.py` with `get_system_health()`
- Single endpoint gives complete operational picture without database access

### Architectural Outcome

- System state is immediately readable by any operator or monitoring tool
- Health check reflects real delivery pipeline state, not just process liveness
- Pairs with `/metrics`, `/dead-letters`, and `/events/{id}/trace` to form complete observability surface
- Transition from **"Infrastructure with active consumers"** to **"Infrastructure with operational visibility"**

The Control Plane now tells you exactly how it's doing.
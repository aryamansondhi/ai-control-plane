# AI Control Plane – Architecture Overview

## Objective

Build an observable, event-driven orchestration layer that enables deterministic AI workflows on top of non-deterministic models.

## Core Components

1. Ingestion Service
   - Fetches external data
   - Writes raw payload + canonical event + outbox in one transaction

2. Event Store (PostgreSQL)
   - Immutable canonical events
   - Transactional Outbox

3. Relay Worker
   - Publishes undelivered outbox messages to internal event stream

4. Consumers
   - Domain adapters (e.g., SignalLab)

Future Phases:
- Deterministic workflow engine
- Observability layer
- Governance (AI output validation)
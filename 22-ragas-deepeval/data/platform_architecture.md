# Aegis Platform — Architecture Overview

Aegis is the internal name for the edge-event ingestion and automation platform.
It ingests alarm and telemetry events from distributed edge nodes, classifies
them, and dispatches automated remediation.

## Ingestion tier
Events arrive over UDP/SNMP and HTTP. Two independent ingestion paths run in
parallel: an EC2-based daemon path for persistent UDP connections, and a
serverless Lambda-behind-ALB path for HTTP-delivered events. Both paths write
into the same downstream queue so that a failure in one path does not cause
data loss — the platform stays available as long as at least one path is
healthy.

## Backpressure
Ingestion is decoupled from processing through a message queue (SQS in
production, Redis Streams in this local demo). This means a slow or stalled
downstream consumer cannot cause the ingestion tier to drop new events; events
simply queue up until the consumer catches up.

## Dispatch and orchestration
A master-worker dispatcher reads a manifest of pending work each cycle and
launches parallel workers sized to the current batch. Batch size and worker
concurrency are recalculated every cycle because volume can swing by roughly
200x and per-item payload size can swing by roughly 265,000x between cycles.
Provisioning for peak capacity permanently would be wasteful; adaptive sizing
avoids that waste.

## Self-healing
Every completed unit of work is checkpointed to durable storage (S3 in
production, local disk in this demo) before being marked complete. If a
worker fails partway through a batch, the orchestrator re-invokes only the
failed portion on the next pass, rather than restarting the entire cycle.

REDIS_HOST = "localhost"
REDIS_PORT = 6380  # mapped from container's 6379, see docker-compose.yml

QUEUE_KEY = "aegis:ingest:queue"       # main work queue (Redis list, LPUSH/BRPOP)
DLQ_KEY = "aegis:ingest:dlq"           # dead-letter queue for exhausted-retry jobs
INFLIGHT_HASH = "aegis:ingest:inflight"  # job_id -> attempt count, for bounded retry

MAX_ATTEMPTS = 3
MIN_WORKERS = 1
MAX_WORKERS = 8
# worker count scales with queue depth: roughly 1 worker per SCALE_DIVISOR
# queued items, clamped to [MIN_WORKERS, MAX_WORKERS] — same idea as the
# resume's "dynamically sizing batches and scaling worker Lambda
# concurrency per cycle" bullet.
SCALE_DIVISOR = 25

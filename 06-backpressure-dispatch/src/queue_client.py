"""Thin wrapper around Redis primitives used as the backpressure boundary.
A producer LPUSHes and returns immediately regardless of queue depth or
consumer speed — this IS the backpressure isolation: the producer's success
is decoupled from the consumer's throughput, same as the resume's "Amazon
SQS... decoupled ingestion from downstream processing" bullet.
"""

import json
import time
import redis

from config import REDIS_HOST, REDIS_PORT, QUEUE_KEY, DLQ_KEY, INFLIGHT_HASH


def get_client() -> redis.Redis:
    return redis.Redis(host=REDIS_HOST, port=REDIS_PORT, decode_responses=True)


def enqueue(client: redis.Redis, job: dict) -> float:
    """Push a job and return how long the push itself took (should be near-
    instant regardless of how backed-up the queue is — that's the point)."""
    start = time.time()
    client.lpush(QUEUE_KEY, json.dumps(job))
    return time.time() - start


def queue_depth(client: redis.Redis) -> int:
    return client.llen(QUEUE_KEY)


def dequeue_blocking(client: redis.Redis, timeout: int = 1):
    result = client.brpop(QUEUE_KEY, timeout=timeout)
    if result is None:
        return None
    _, raw = result
    return json.loads(raw)


def send_to_dlq(client: redis.Redis, job: dict, reason: str):
    job = dict(job)
    job["dlq_reason"] = reason
    client.lpush(DLQ_KEY, json.dumps(job))


def dlq_depth(client: redis.Redis) -> int:
    return client.llen(DLQ_KEY)


def replay_dlq(client: redis.Redis) -> int:
    """Move every DLQ item back onto the main queue for reprocessing.
    Returns the number of items replayed."""
    count = 0
    while True:
        raw = client.rpop(DLQ_KEY)
        if raw is None:
            break
        job = json.loads(raw)
        job.pop("dlq_reason", None)
        job["replayed"] = True
        client.lpush(QUEUE_KEY, json.dumps(job))
        count += 1
    return count


def get_attempts(client: redis.Redis, job_id: str) -> int:
    val = client.hget(INFLIGHT_HASH, job_id)
    return int(val) if val else 0


def increment_attempts(client: redis.Redis, job_id: str) -> int:
    return client.hincrby(INFLIGHT_HASH, job_id, 1)


def clear_attempts(client: redis.Redis, job_id: str):
    client.hdel(INFLIGHT_HASH, job_id)


def flush_all(client: redis.Redis):
    """Test/demo helper."""
    client.delete(QUEUE_KEY, DLQ_KEY, INFLIGHT_HASH)

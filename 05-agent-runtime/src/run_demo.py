"""Runs four scenarios end to end against the compiled graph, demonstrating
each reliability property independently.
"""

from pathlib import Path
import sqlite3

from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.types import Command

from graph import build_graph
from idempotency_store import reset as reset_idempotency_store

DB_PATH = Path(__file__).resolve().parent.parent / "checkpoints.sqlite"


def fresh_checkpointer():
    """Simulates reconnecting after a process restart: a brand new
    connection to the same on-disk checkpoint DB."""
    conn = sqlite3.connect(str(DB_PATH), check_same_thread=False)
    return SqliteSaver(conn)


def demo_safe_action():
    print("\n=== Scenario 1: safe action, no approval needed ===")
    checkpointer = fresh_checkpointer()
    graph = build_graph(checkpointer)
    config = {"configurable": {"thread_id": "demo-safe-1"}}
    result = graph.invoke({
        "situation": "EC2 receiver failed 3 health checks, already drained.",
        "action": "restart_instance",
        "idempotency_key": "demo-safe-1-key",
        "attempt": 0,
    }, config=config)
    for line in result["log"]:
        print(" ", line)
    print("Final status:", result["status"])


def demo_human_in_the_loop():
    print("\n=== Scenario 2: risky action, interrupted for human approval, resumed later ===")
    checkpointer = fresh_checkpointer()
    graph = build_graph(checkpointer)
    config = {"configurable": {"thread_id": "demo-risky-1"}}

    result = graph.invoke({
        "situation": "No incident occurring; ad-hoc request to delete audit logs.",
        "action": "delete_data",
        "idempotency_key": "demo-risky-1-key",
        "attempt": 0,
    }, config=config)

    if "__interrupt__" in result:
        print("  Graph paused for human approval:", result["__interrupt__"][0].value["message"])
        print("  ... simulating a process restart before the human responds ...")

        # Reconnect with a brand new checkpointer instance, same thread_id —
        # proves the paused state survived process restart, not just
        # in-memory.
        checkpointer2 = fresh_checkpointer()
        graph2 = build_graph(checkpointer2)
        final = graph2.invoke(Command(resume=False), config=config)  # human REJECTS
        for line in final["log"]:
            print(" ", line)
        print("Final status:", final["status"])


def demo_idempotency():
    print("\n=== Scenario 3: idempotent execution — same key, called twice ===")
    reset_idempotency_store()
    checkpointer = fresh_checkpointer()
    graph = build_graph(checkpointer)

    for i in range(2):
        config = {"configurable": {"thread_id": f"demo-idempotent-{i}"}}
        result = graph.invoke({
            "situation": "Batch failed, checkpoint missing.",
            "action": "reprocess_batch",
            "idempotency_key": "shared-batch-key-42",  # SAME key both times
            "attempt": 0,
        }, config=config)
        print(f"  call #{i+1}:", result["log"][-1])


def demo_bounded_retry():
    print("\n=== Scenario 4: bounded retry — 2 simulated transient failures, succeeds on 3rd attempt ===")
    reset_idempotency_store()
    checkpointer = fresh_checkpointer()
    graph = build_graph(checkpointer)
    config = {"configurable": {"thread_id": "demo-retry-1"}}
    result = graph.invoke({
        "situation": "Flaky downstream dependency during execution.",
        "action": "scale_up_node_pool",
        "idempotency_key": "demo-retry-1-key",
        "attempt": 0,
        "simulate_failures": 2,
    }, config=config)
    for line in result["log"]:
        print(" ", line)
    print("Final status:", result["status"], "| total attempts:", result["attempt"])


if __name__ == "__main__":
    if DB_PATH.exists():
        DB_PATH.unlink()
    demo_safe_action()
    demo_human_in_the_loop()
    demo_idempotency()
    demo_bounded_retry()

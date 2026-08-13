import sys
import sqlite3
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.types import Command

from graph import build_graph
import idempotency_store


def make_checkpointer():
    conn = sqlite3.connect(":memory:", check_same_thread=False)
    return SqliteSaver(conn)


def test_safe_action_executes_without_approval():
    graph = build_graph(make_checkpointer())
    config = {"configurable": {"thread_id": "t1"}}
    result = graph.invoke({
        "situation": "routine", "action": "restart_instance",
        "idempotency_key": "t1-key", "attempt": 0,
    }, config=config)
    assert result["status"] == "executed"
    assert result["requires_approval"] is False


def test_risky_action_interrupts_and_blocks_on_rejection():
    graph = build_graph(make_checkpointer())
    config = {"configurable": {"thread_id": "t2"}}
    result = graph.invoke({
        "situation": "no incident", "action": "delete_data",
        "idempotency_key": "t2-key", "attempt": 0,
    }, config=config)
    assert "__interrupt__" in result

    final = graph.invoke(Command(resume=False), config=config)
    assert final["status"] == "blocked"


def test_risky_action_executes_on_approval():
    graph = build_graph(make_checkpointer())
    config = {"configurable": {"thread_id": "t3"}}
    graph.invoke({
        "situation": "no incident", "action": "delete_data",
        "idempotency_key": "t3-key", "attempt": 0,
    }, config=config)
    final = graph.invoke(Command(resume=True), config=config)
    assert final["status"] == "executed"


def test_idempotent_execution_does_not_rerun(tmp_path, monkeypatch):
    fake_store = tmp_path / "store.json"
    monkeypatch.setattr(idempotency_store, "STORE_PATH", fake_store)

    graph = build_graph(make_checkpointer())
    key = "shared-key"
    r1 = graph.invoke({"situation": "s", "action": "reprocess_batch", "idempotency_key": key, "attempt": 0},
                       config={"configurable": {"thread_id": "t4a"}})
    r2 = graph.invoke({"situation": "s", "action": "reprocess_batch", "idempotency_key": key, "attempt": 0},
                       config={"configurable": {"thread_id": "t4b"}})
    assert "idempotency hit" in r2["log"][-1]
    assert r1["status"] == r2["status"] == "executed"


def test_bounded_retry_gives_up_after_max_attempts(tmp_path, monkeypatch):
    fake_store = tmp_path / "store2.json"
    monkeypatch.setattr(idempotency_store, "STORE_PATH", fake_store)

    graph = build_graph(make_checkpointer())
    result = graph.invoke({
        "situation": "s", "action": "scale_up_node_pool",
        "idempotency_key": "always-fails-key", "attempt": 0,
        "simulate_failures": 99,  # never succeeds
    }, config={"configurable": {"thread_id": "t5"}})
    assert result["status"] == "failed"
    assert result["attempt"] == 3

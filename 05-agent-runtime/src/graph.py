"""LangGraph remediation agent with:
  - durable state via a SQLite checkpointer (survives process restart)
  - idempotent, bounded-retry execution (execute_action)
  - failure isolation (a failing attempt doesn't corrupt state for a retry)
  - human-in-the-loop approval gate for risky actions (interrupt())

Maps to the resume's "Self-Directed Agent Runtime" bullet and mirrors
CONDOR's "Checkpointed Self-Healing" / "Three-Pass Reconciliation with
TTL-Based Idempotency" bullets at agent-workflow scale.
"""

from typing import TypedDict, Optional

from langgraph.graph import StateGraph, END
from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.types import interrupt, Command

from idempotency_store import has_been_executed, get_result, mark_executed

MAX_ATTEMPTS = 3

# Actions requiring a human in the loop before execution — same idea as the
# deployment runbook's "AI-assisted automation changes... must pass the
# multi-model evaluation gate" but for actions with no independent judge
# model available, a human is the second check.
RISKY_ACTIONS = {"delete_data", "widen_network_access", "force_failover"}


class AgentState(TypedDict, total=False):
    situation: str
    action: str
    idempotency_key: str
    requires_approval: bool
    approved: Optional[bool]
    attempt: int
    status: str
    log: list[str]
    simulate_failures: int  # test hook: number of times execution should fail before succeeding


def check_situation(state: AgentState) -> dict:
    log = state.get("log", [])
    log = log + [f"checked situation: {state['situation'][:60]}"]
    return {"status": "checked", "log": log}


def decide_action(state: AgentState) -> dict:
    requires_approval = state["action"] in RISKY_ACTIONS
    log = state.get("log", []) + [
        f"decided action='{state['action']}' requires_approval={requires_approval}"
    ]
    return {"requires_approval": requires_approval, "log": log}


def route_after_decision(state: AgentState) -> str:
    return "human_approval" if state["requires_approval"] else "execute_action"


def human_approval(state: AgentState) -> dict:
    decision = interrupt({
        "message": f"Approve action '{state['action']}' for situation: {state['situation']}?",
        "action": state["action"],
    })
    log = state.get("log", []) + [f"human approval decision: {decision}"]
    return {"approved": bool(decision), "log": log}


def route_after_approval(state: AgentState) -> str:
    return "execute_action" if state.get("approved") else "blocked"


def blocked(state: AgentState) -> dict:
    log = state.get("log", []) + ["BLOCKED: human did not approve"]
    return {"status": "blocked", "log": log}


def execute_action(state: AgentState) -> dict:
    key = state["idempotency_key"]

    if has_been_executed(key):
        cached = get_result(key)
        log = state.get("log", []) + [f"idempotency hit: '{key}' already executed -> {cached}"]
        return {"status": "executed", "log": log}

    attempt = state.get("attempt", 0) + 1
    simulate_failures = state.get("simulate_failures", 0)

    if attempt <= simulate_failures:
        log = state.get("log", []) + [f"attempt {attempt}/{MAX_ATTEMPTS}: simulated transient failure"]
        if attempt >= MAX_ATTEMPTS:
            return {"status": "failed", "attempt": attempt, "log": log + ["giving up after max attempts"]}
        return {"status": "retrying", "attempt": attempt, "log": log}

    result = f"[SIMULATED EXECUTION] action='{state['action']}' executed on attempt {attempt}"
    mark_executed(key, result)
    log = state.get("log", []) + [result]
    return {"status": "executed", "attempt": attempt, "log": log}


def route_after_execute(state: AgentState) -> str:
    if state["status"] == "retrying":
        return "execute_action"
    return END


def build_graph(checkpointer):
    graph = StateGraph(AgentState)
    graph.add_node("check_situation", check_situation)
    graph.add_node("decide_action", decide_action)
    graph.add_node("human_approval", human_approval)
    graph.add_node("blocked", blocked)
    graph.add_node("execute_action", execute_action)

    graph.set_entry_point("check_situation")
    graph.add_edge("check_situation", "decide_action")
    graph.add_conditional_edges("decide_action", route_after_decision, {
        "human_approval": "human_approval",
        "execute_action": "execute_action",
    })
    graph.add_conditional_edges("human_approval", route_after_approval, {
        "execute_action": "execute_action",
        "blocked": "blocked",
    })
    graph.add_edge("blocked", END)
    graph.add_conditional_edges("execute_action", route_after_execute, {
        "execute_action": "execute_action",
        END: END,
    })

    return graph.compile(checkpointer=checkpointer)

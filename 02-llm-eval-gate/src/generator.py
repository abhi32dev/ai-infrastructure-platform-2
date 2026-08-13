"""The first model: proposes whether to take the automation action, with a
rationale. This model's judgment is NOT trusted on its own — that's the
whole point of the gate in judge.py.
"""

import json
from langchain_ollama import ChatOllama
from langchain_core.messages import SystemMessage, HumanMessage

from config import GEN_MODEL, GEN_TEMPERATURE

SYSTEM_PROMPT = (
    "You are an automation decision engine for a production infrastructure "
    "platform. Given a situation and a proposed action, decide whether to "
    "APPROVE or REJECT executing that action right now. "
    "Respond with ONLY a JSON object: "
    '{"decision": "APPROVE"|"REJECT", "rationale": "<one sentence>"}'
)


def propose(situation: str, proposed_action: str) -> dict:
    llm = ChatOllama(model=GEN_MODEL, temperature=GEN_TEMPERATURE, format="json")
    messages = [
        SystemMessage(content=SYSTEM_PROMPT),
        HumanMessage(content=f"Situation: {situation}\nProposed action: {proposed_action}"),
    ]
    raw = llm.invoke(messages).content
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError:
        parsed = {"decision": "REJECT", "rationale": f"unparsable generator output: {raw[:200]}"}
    return parsed


if __name__ == "__main__":
    from scenarios import SCENARIOS

    for sc in SCENARIOS:
        result = propose(sc["situation"], sc["proposed_action"])
        print(f"{sc['id']}: {result}")

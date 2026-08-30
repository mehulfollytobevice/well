"""LangGraph graph, nodes, and agent state."""

from wellground.agent.schemas import AgentResponse, Claim, RagEvidence, RouteDecision, SqlEvidence

__all__ = [
    "AgentResponse",
    "Claim",
    "RagEvidence",
    "RouteDecision",
    "SqlEvidence",
    "run_agent",
]


def __getattr__(name: str) -> object:
    if name == "run_agent":
        from wellground.agent.graph import run_agent

        return run_agent
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")

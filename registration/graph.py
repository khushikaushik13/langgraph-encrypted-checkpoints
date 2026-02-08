from typing import Any
from langgraph.graph import StateGraph, START, END

from registration.state import RegistrationState
from registration.validator import RegistrationValidator


class RegistrationGraphFactory:
    def __init__(self, validator: RegistrationValidator):
        self.validator = validator

    @staticmethod
    def collect_node(state: RegistrationState) -> RegistrationState:
        """
        No-op: graph.invoke(patch, config) already merges patch into state.
        """
        return state

    @staticmethod
    def registration_complete(state: RegistrationState) -> RegistrationState:
        """
        Final point. State is guaranteed complete because conditional edge only
        routes here when missing_fields == [].
        """
        return state

    def build(self) -> StateGraph:
        g = StateGraph(RegistrationState)

        g.add_node("collect", self.collect_node)
        g.add_node("validate", self.validator.validate_present_fields)
        g.add_node("missing", self.validator.compute_missing_fields)
        g.add_node("complete", self.registration_complete)

        g.add_edge(START, "collect")
        g.add_edge("collect", "validate")
        g.add_edge("validate", "missing")

        g.add_conditional_edges(
            "missing",
            self.validator.should_complete,
            {"end": END, "complete": "complete"},
        )
        g.add_edge("complete", END)

        return g

    def compile(self, checkpointer: Any):
        return self.build().compile(checkpointer=checkpointer)
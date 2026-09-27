"""PHASE 5 · Multi-agent orchestration with LangGraph.

Read first: notes Days 73 (frameworks), 74 (multi-agent), 67 (patterns). LangGraph docs: StateGraph.

The pipeline (you wire it in build_graph):

    START -> intake --(missing info and no answers yet)--> clarify -> END      (human in the loop)
                    \\--(otherwise)--> screen --+--> classify ------+--> obligations -> gaps -> write -> verify
                                               \\--> ml_prescreen --/                               |
                                                  (run in parallel)             <-- write (retry) --+ (failed, < 3 attempts)
                                                                                  finish -> END   <-+ (passed or out of attempts)

Each node is a small function that reads the shared state and returns the keys it updates.
The node functions are given (make_nodes); you write the two routing functions and build_graph.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from typing import Any, TypedDict

from app.agents import classifier, gaps, intake, obligations, rules, verifier, writer


class PipelineState(TypedDict, total=False):
    assessment_id: str
    description: str
    answers: dict  # answers to clarifying questions
    practices: dict  # obligation id -> "yes" | "partial" | "no"
    profile: Any  # SystemProfile
    flags: list
    ml_prediction: dict | None  # {"label": ..., "probability": ...} from the Phase 6 model
    assessment: Any  # RiskAssessment
    obligations: list
    gaps: list
    report: Any  # Report
    verification: Any  # VerificationResult
    attempts: int
    status: str  # "needs_input" | "done"
    questions: list


@dataclass
class PipelineDeps:
    provider: Any
    store: Any
    embedder: Any
    events: Any = None  # callable(stage, message), e.g. repo.add_event bound to an id
    ml_classifier: Any = None  # object with .predict(text) -> {"label", "probability"}
    today: date | None = None
    _known: set = field(default_factory=set)

    def emit(self, stage, message):
        if self.events:
            self.events(stage, message)

    @property
    def known_provisions(self) -> set:
        if not self._known:
            self._known = {cid.rsplit("-", 1)[0] for cid in self.store.all_ids()}
        return self._known


def make_nodes(deps: PipelineDeps) -> dict:
    """The agents as graph nodes (given)."""

    def intake_node(state):
        deps.emit("intake", "Reading the system description")
        return {
            "profile": intake.extract_profile(
                state["description"], deps.provider, state.get("answers") or {}
            ),
            "attempts": 0,
        }

    def clarify_node(state):
        deps.emit("clarify", "More information needed")
        return {"status": "needs_input", "questions": state["profile"].missing_info}

    def screen_node(state):
        flags = rules.screen(state["profile"])
        deps.emit("screen", f"Screening flags: {', '.join(flags) or 'none'}")
        return {"flags": flags}

    def ml_node(state):
        if deps.ml_classifier is None:
            return {"ml_prediction": None}
        pred = deps.ml_classifier.predict(state["profile"].purpose + " " + state["description"])
        deps.emit(
            "ml_prescreen", f"Model predicts Annex III area: {pred['label']} ({pred['probability']:.0%})"
        )
        return {"ml_prediction": pred}

    def classify_node(state):
        deps.emit("classify", "Searching the regulation and classifying")
        a = classifier.classify(state["profile"], state["flags"], deps.store, deps.embedder, deps.provider)
        deps.emit("classify", f"Category: {a.category} (confidence {a.confidence})")
        return {"assessment": a}

    def obligations_node(state):
        a = state["assessment"]
        pred = state.get("ml_prediction")
        if pred and pred["label"] != a.annex_iii_area and a.annex_iii_area not in ("unknown",):
            a = a.model_copy(update={"flags": sorted(set(a.flags) | {"ml_disagrees_with_llm"})})
        obs = obligations.lookup(a)
        deps.emit("obligations", f"{len(obs)} obligations apply")
        return {"assessment": a, "obligations": obs}

    def gaps_node(state):
        g = gaps.find_gaps(state["obligations"], state.get("practices") or {}, today=deps.today)
        deps.emit("gaps", f"{sum(x.priority == 'high' for x in g)} high-priority gaps")
        return {"gaps": g}

    def write_node(state):
        attempt = state.get("attempts", 0) + 1
        issues = (
            state["verification"].issues
            if state.get("verification") and not state["verification"].passed
            else None
        )
        deps.emit("write", f"Writing report (attempt {attempt})")
        report = writer.write_report(
            state["profile"],
            state["assessment"],
            state["obligations"],
            state["gaps"],
            deps.provider,
            feedback=issues,
        )
        return {"report": report, "attempts": attempt}

    def verify_node(state):
        v = verifier.verify_report(
            state["report"], state["assessment"], state["obligations"], deps.known_provisions
        )
        deps.emit("verify", "Report verified" if v.passed else f"Verifier found {len(v.issues)} issue(s)")
        return {"verification": v}

    def finish_node(state):
        return {"status": "done"}

    return {
        "intake": intake_node,
        "clarify": clarify_node,
        "screen": screen_node,
        "ml_prescreen": ml_node,
        "classify": classify_node,
        "obligations": obligations_node,
        "gaps": gaps_node,
        "write": write_node,
        "verify": verify_node,
        "finish": finish_node,
    }


MAX_WRITE_ATTEMPTS = 3


def route_after_intake(state: PipelineState) -> str:
    """Return "clarify" if the profile has missing_info AND no answers were given yet; else "screen"."""
    return "clarify" if state["profile"].missing_info and not state.get("answers") else "screen"


def route_after_verify(state: PipelineState) -> str:
    """Return "write" if verification failed and attempts < MAX_WRITE_ATTEMPTS; else "finish"."""
    return (
        "write"
        if not state["verification"].passed and state.get("attempts", 0) < MAX_WRITE_ATTEMPTS
        else "finish"
    )


def build_graph(deps: PipelineDeps):
    """Wire the graph drawn at the top of this file and return graph.compile().

        from langgraph.graph import StateGraph, START, END
        g = StateGraph(PipelineState)
        for name, fn in make_nodes(deps).items(): g.add_node(name, fn)
        g.add_edge(START, "intake")
        g.add_conditional_edges("intake", route_after_intake, {"clarify": "clarify", "screen": "screen"})
        ...
    Parallel branches: add two edges out of "screen" (to "classify" and "ml_prescreen"), then join
    them with g.add_edge(["classify", "ml_prescreen"], "obligations") so obligations waits for both.
    """
    from langgraph.graph import END, START, StateGraph

    g = StateGraph(PipelineState)
    for name, fn in make_nodes(deps).items():
        g.add_node(name, fn)
    g.add_edge(START, "intake")
    g.add_conditional_edges("intake", route_after_intake, {"clarify": "clarify", "screen": "screen"})
    g.add_edge("clarify", END)
    g.add_edge("screen", "classify")
    g.add_edge("screen", "ml_prescreen")
    g.add_edge(["classify", "ml_prescreen"], "obligations")
    g.add_edge("obligations", "gaps")
    g.add_edge("gaps", "write")
    g.add_edge("write", "verify")
    g.add_conditional_edges("verify", route_after_verify, {"write": "write", "finish": "finish"})
    g.add_edge("finish", END)
    return g.compile()


def run_pipeline(state: PipelineState, deps: PipelineDeps) -> PipelineState:
    """Run the whole graph once and return the final state. (Given.)"""
    return build_graph(deps).invoke(state)

from langgraph.graph import StateGraph, END
from agents.graph_state import DiscoveryState
from agents.deep_analysis_graph import deep_analysis_app
from typing import Dict, Any

# In a full migration, these nodes would wrap the orchestrator.py LLM logic.
# For the shallow migration, we define the strict edges and routing logic.

def extraction_node(state: DiscoveryState) -> Dict[str, Any]:
    print("Graph: Running Strict Extraction Node")
    return {"messages": ["Extraction complete"]}

def council_node(state: DiscoveryState) -> Dict[str, Any]:
    print("Graph: Running Strict Council Node")
    return {"messages": ["Council reviews complete"]}

def gap_node(state: DiscoveryState) -> Dict[str, Any]:
    print("Graph: Running Strict Gap Node")
    return {"messages": ["Gap analysis complete"]}

def trd_node(state: DiscoveryState) -> Dict[str, Any]:
    print("Graph: Running Strict TRD Node")
    return {"messages": ["TRD generated"]}

def backlog_node(state: DiscoveryState) -> Dict[str, Any]:
    print("Graph: Running Strict Backlog Node")
    return {"messages": ["Backlog generated"]}

def route_after_gap(state: DiscoveryState) -> str:
    modules = state.get("enabled_modules", [])
    if "trd" in modules:
        return "trd"
    elif "backlog" in modules:
        return "backlog"
    return END

def route_after_trd(state: DiscoveryState) -> str:
    modules = state.get("enabled_modules", [])
    if state.get("deep_analysis_enabled", False):
        return "deep_analysis"
    elif "backlog" in modules:
        return "backlog"
    return END

def route_after_deep_analysis(state: DiscoveryState) -> str:
    modules = state.get("enabled_modules", [])
    if "backlog" in modules:
        return "backlog"
    return END

builder = StateGraph(DiscoveryState)

# Define Nodes
builder.add_node("extraction", extraction_node)
builder.add_node("council", council_node)
builder.add_node("gap", gap_node)
builder.add_node("trd", trd_node)
builder.add_node("deep_analysis", deep_analysis_app)
builder.add_node("backlog", backlog_node)

# Entry Point
builder.set_entry_point("extraction")

# Strict Linear Edges
builder.add_edge("extraction", "council")
builder.add_edge("council", "gap")

# Strict Routing Logic (Guardrails to prevent infinite loops)
builder.add_conditional_edges("gap", route_after_gap, {"trd": "trd", "backlog": "backlog", END: END})
builder.add_conditional_edges("trd", route_after_trd, {"deep_analysis": "deep_analysis", "backlog": "backlog", END: END})
builder.add_conditional_edges("deep_analysis", route_after_deep_analysis, {"backlog": "backlog", END: END})
builder.add_edge("backlog", END)

discovery_strict_app = builder.compile()

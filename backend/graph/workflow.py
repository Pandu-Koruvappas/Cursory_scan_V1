from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import MemorySaver
from .state import AnalysisState
from .nodes import extraction_node, gaps_node, spec_node, reviews_node, backlog_node, test_cases_node

# 1. Initialize Graph
workflow = StateGraph(AnalysisState)

# 2. Add Nodes
workflow.add_node("extraction", extraction_node)
workflow.add_node("gaps", gaps_node)
workflow.add_node("spec", spec_node)
workflow.add_node("reviews", reviews_node)
workflow.add_node("backlog", backlog_node)
workflow.add_node("test_cases", test_cases_node)

# 3. Define Edges (Sequential for this Phase)
workflow.add_edge(START, "extraction")
workflow.add_edge("extraction", "gaps")

# Conditional Routing Example: 
# If there are gaps, we could route to END or a clarification node.
# For now, we will sequentially route to spec to keep the existing UI behavior.
workflow.add_edge("gaps", "spec")
workflow.add_edge("spec", "reviews")
workflow.add_edge("reviews", "backlog")
workflow.add_edge("backlog", "test_cases")
workflow.add_edge("test_cases", END)

# 4. Compile with MemorySaver
memory = MemorySaver()

# We can set a breakpoint before the backlog sync if we want HITL here.
# We set breakpoints before each major UI step to allow the frontend 
# to trigger them sequentially via the existing REST endpoints.
app = workflow.compile(
    checkpointer=memory,
    interrupt_before=["spec", "backlog", "test_cases"]
)

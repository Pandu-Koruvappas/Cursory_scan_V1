import json
from typing import Dict, Any
from langgraph.graph import StateGraph, END
from agents.graph_state import DebateState
from services.llm_service import LLMService

# Async functions so they can be awaited in the graph if needed, though LangGraph handles synchronous wrapping too.
# But since LLMService relies on async methods for Azure, we should define them as async. Wait, our LLMService `generate_with_azure` is synchronous in some versions or async? 
# Let me assume standard async pattern for our FastApi app.

def architect_node(state: DebateState) -> Dict[str, Any]:
    llm = LLMService()
    
    context = state.get("extraction_context", "")
    critique = ""
    messages = state.get("messages", [])
    if messages and len(messages) > 0:
        critique = messages[-1].get("content", "")
        
    prompt = f"""
    You are the Enterprise Software Architect.
    Requirement Context: {context}
    
    Current Draft: {state.get("trd_draft", "None")}
    
    Security Feedback to address: {critique}
    
    Update the Technical Requirements Document (TRD) to address the security feedback. If this is the first draft, just generate the TRD.
    Output ONLY valid JSON representing the TRD. Format: {{"architecture_overview": "...", "components": [], "data_model": []}}
    """
    
    # Make sure we use an async call or run in executor if it's sync. In our `llm_service.py`, `generate_with_azure` is synchronous (using standard client). 
    # LangGraph supports synchronous nodes natively.
    response = llm.generate_with_azure(
        system_prompt="You are an expert AI Architect.",
        user_prompt=prompt,
        is_json=True
    )
    
    # Message Compaction
    return {
        "trd_draft": response,
        "iteration_count": state.get("iteration_count", 0) + 1,
        "messages": [{"role": "architect", "content": "Updated TRD Draft."}]
    }

def security_node(state: DebateState) -> Dict[str, Any]:
    llm = LLMService()
    
    prompt = f"""
    You are the Enterprise Security Lead. Review this TRD draft for security flaws.
    Focus strictly on:
    - Zero Trust Architecture principles
    - OWASP Top 10 vulnerabilities (Injection, Broken Auth, etc.)
    - Data Privacy & Compliance (GDPR, PII handling)
    - Role-Based Access Control (RBAC) and Encryption at rest/transit.
    
    TRD Draft: {state.get("trd_draft", "")}
    
    If it meets all enterprise security standards, output EXACTLY the JSON: {{"approved": true, "feedback": "Secure"}}
    If it has flaws, output EXACTLY the JSON: {{"approved": false, "feedback": "Detailed explanation of flaws"}}
    """
    
    response = llm.generate_with_azure(
        system_prompt="You are a strict InfoSec AI.",
        user_prompt=prompt,
        is_json=True
    )
    
    try:
        parsed = json.loads(response)
        approved = parsed.get("approved", False)
        feedback = parsed.get("feedback", "Unspecified flaws.")
    except:
        approved = False
        feedback = "Failed to parse security review."
        
    return {
        "is_approved": approved,
        "messages": [{"role": "security", "content": feedback}]
    }

def should_continue(state: DebateState) -> str:
    # STRICT GUARDRAIL: Max 2 iterations to prevent infinite looping and runaway costs
    if state.get("is_approved", False) or state.get("iteration_count", 0) >= 2:
        return END
    return "architect"

builder = StateGraph(DebateState)
builder.add_node("architect", architect_node)
builder.add_node("security", security_node)

builder.set_entry_point("architect")
builder.add_edge("architect", "security")
builder.add_conditional_edges("security", should_continue)

deep_analysis_app = builder.compile()

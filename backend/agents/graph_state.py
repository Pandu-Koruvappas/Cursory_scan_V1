from typing import TypedDict, List, Dict, Any, Annotated

def merge_list(a: List, b: List) -> List:
    if not a: return b
    if not b: return a
    return a + b

class DiscoveryState(TypedDict):
    """State for the primary Discovery Swarm pipeline."""
    document_id: str
    document_content: str
    enabled_modules: List[str]
    extraction: Dict[str, Any]
    ambiguity_report: Dict[str, Any]
    council_reviews: Dict[str, Any]
    critic_feedback: Dict[str, Any]
    trd_draft: Dict[str, Any]
    backlog: Dict[str, Any]
    errors: Annotated[List[str], merge_list]
    deep_analysis_enabled: bool

class DebateState(TypedDict):
    """State for the Deep Analysis 'Architect vs Security' sub-graph."""
    document_id: str
    extraction_context: str
    trd_draft: str
    messages: Annotated[List[Dict[str, str]], merge_list]
    iteration_count: int
    is_approved: bool

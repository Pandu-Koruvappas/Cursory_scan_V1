from typing import TypedDict, Optional, Dict, Any, List

class AnalysisState(TypedDict):
    """
    Represents the state of the BA Agent orchestration.
    This persists throughout the entire Discovery Swarm lifecycle.
    """
    analysis_id: str
    original_text: str
    context_type: str
    
    # Generated Artifacts
    extraction: Optional[Dict[str, Any]]
    gaps: Optional[List[Any]]
    functional_spec: Optional[str]
    backlog: Optional[Dict[str, Any]]
    reviews: Optional[Dict[str, Any]]
    test_cases: Optional[str]
    
    # Flags and Routing
    has_gaps: bool
    is_approved: bool

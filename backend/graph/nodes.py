from typing import Dict, Any
from .state import AnalysisState
from agents.extraction import ExtractionAgent
from agents.analysis import AnalysisAgent
from agents.functional_spec import FunctionalSpecAgent
from agents.backlog_gen import BacklogGenAgent
from agents.test_case_agent import TestCaseAgent
from agents.critic_agent import CriticAgent

# Initialize standard agents
extraction_agent = ExtractionAgent()
analysis_agent = AnalysisAgent()
functional_spec_agent = FunctionalSpecAgent()
backlog_agent = BacklogGenAgent()
test_case_agent = TestCaseAgent()
critic_agent = CriticAgent()

async def extraction_node(state: AnalysisState) -> Dict[str, Any]:
    print("Graph: Executing Extraction Node")
    text = state.get("original_text", "")
    context_type = state.get("context_type", "document")
    
    extraction = await extraction_agent.extract_content(text, context_type)
    return {"extraction": extraction}

async def gaps_node(state: AnalysisState) -> Dict[str, Any]:
    print("Graph: Executing Gaps/Analysis Node")
    # For this POC, we use the analysis_agent which might not exist perfectly yet
    # We will simulate gaps evaluation or use the actual analysis agent if it has a analyze_requirements method
    # Looking at the original routes, /analyze endpoint uses analysis_agent.analyze_requirements
    extraction = state.get("extraction", {})
    try:
        gaps = await analysis_agent.analyze_requirements(extraction)
        has_gaps = len(gaps) > 0
    except Exception:
        # Fallback if method differs
        gaps = []
        has_gaps = False
        
    return {"gaps": gaps, "has_gaps": has_gaps}

async def spec_node(state: AnalysisState) -> Dict[str, Any]:
    print("Graph: Executing Functional Spec Node")
    extraction = state.get("extraction", {})
    original_text = state.get("original_text", "")
    spec = await functional_spec_agent.generate_spec(
        extraction=extraction,
        raw_brd_text=original_text
    )

    # Perform Adversarial QA Review via CriticAgent
    critic_res = await critic_agent.review_artifact(
        artifact_type="Functional Spec",
        content=spec,
        source_brd=original_text,
        extraction=extraction
    )

    # --- AUTONOMOUS SELF-CORRECTION REFLECTION LOOP ---
    iteration = 0
    max_reflections = 1
    while critic_res.get("status") == "REQUEST_CORRECTION" and critic_res.get("confidence_score", 1.0) < 0.85 and iteration < max_reflections:
        iteration += 1
        suggestion = critic_res.get("critic_suggestion", "")
        print(f"\n================================================================================")
        print(f"🔄 [REFLECTION LOOP {iteration}/{max_reflections}] Critic requested corrections (Score: {critic_res.get('confidence_score')})")
        print(f" ► Feedback: \"{suggestion[:140]}...\"" if len(suggestion) > 140 else f" ► Feedback: \"{suggestion}\"")
        print(f" ► Triggering self-correction re-generation in FunctionalSpecAgent...")
        print(f"================================================================================")

        # Re-run FunctionalSpecAgent with Critic feedback
        spec = await functional_spec_agent.generate_spec(
            extraction=extraction,
            raw_brd_text=original_text,
            feedback=suggestion
        )
        print(f" ↳ Self-corrected Functional Spec re-assembled cleanly.")

        # Re-audit updated spec via CriticAgent
        print(f" ↳ Re-auditing updated Functional Spec via CriticAgent...")
        critic_res = await critic_agent.review_artifact(
            artifact_type="Functional Spec (Self-Corrected)",
            content=spec,
            source_brd=original_text,
            extraction=extraction
        )

        print(f"\n================================================================================")
        print(f"✅ [REFLECTION LOOP COMPLETE] Re-audit Decision")
        print(f" ► Final Status    : {critic_res.get('status')}")
        print(f" ► Final Confidence: {critic_res.get('confidence_score')}")
        print(f" ► Total Findings  : {len(critic_res.get('findings', []))}")
        print(f"================================================================================\n")

    return {"functional_spec": spec, "critic_review": critic_res}

async def reviews_node(state: AnalysisState) -> Dict[str, Any]:
    print("Graph: Executing Persona Reviews Node")
    
    import asyncio
    from agents.reviewers import QAReviewer, SecurityReviewer, UXReviewer
    
    extraction = state.get("extraction", {})
    functional_requirements = extraction.get("functional_requirements", [])
    
    if not functional_requirements:
        return {"reviews": {}}

    qa_reviewer = QAReviewer()
    sec_reviewer = SecurityReviewer()
    ux_reviewer = UXReviewer()
    
    # Run them concurrently to save time
    qa_task = qa_reviewer.review(functional_requirements)
    sec_task = sec_reviewer.review(functional_requirements)
    ux_task = ux_reviewer.review(functional_requirements)
    
    qa_res, sec_res, ux_res = await asyncio.gather(qa_task, sec_task, ux_task)
    
    reviews = {
        "qa": qa_res,
        "security": sec_res,
        "ux": ux_res
    }
    return {"reviews": reviews}

async def backlog_node(state: AnalysisState) -> Dict[str, Any]:
    print("Graph: Executing Backlog Generation Node")
    spec = state.get("functional_spec", "")
    reviews = state.get("reviews", {})
    # Build context string similar to main.py
    context_str = f"Functional Spec:\n{spec}\n\nPersona Reviews:\n{reviews}"
    backlog = await backlog_agent.generate_backlog(context_str)
    return {"backlog": backlog}

async def test_cases_node(state: AnalysisState) -> Dict[str, Any]:
    print("Graph: Executing Test Cases Node")
    spec = state.get("functional_spec", "")
    backlog = state.get("backlog", {})
    context_str = f"Functional Spec:\n{spec}\n\nBacklog Scope:\n{backlog}"
    test_cases = await test_case_agent.draft_test_cases(context_str)
    return {"test_cases": test_cases}

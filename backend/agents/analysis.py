import json
from services.llm_service import LLMService

class AnalysisAgent:
    def __init__(self):
        self.llm = LLMService()

    async def analyze_gaps(self, extracted_data: dict, raw_text: str = "", answers: dict = None, context: str = "", institutional_memory: str = ""):
        """
        Uses Azure OpenAI (GPT-4o-mini) to identify gaps, risks, and ambiguities quickly.
        """
        clarification_context = ""
        if answers:
            clarification_context = f"\nUSER CLARIFICATIONS (Use these to resolve previous ambiguities):\n{json.dumps(answers, indent=2)}\n"

        project_dna = ""
        if context:
            project_dna = f"\nEXISTING PROJECT CONTEXT (What is already built/planned in ADO):\n{context}\n"
            
        memory_context = ""
        if institutional_memory:
            memory_context = f"\n{institutional_memory}\nCRITICAL INSTRUCTION: Ensure the requirements comply with the OFFICIAL P&C DOMAIN GUIDELINES above. Flag any violations as severe gaps or risks.\n"

        prompt = f"""
        Perform a deep gap analysis by comparing the summarized extraction against the full raw text.
        {clarification_context}
        {project_dna}
        {memory_context}
        
        CRITICAL: If EXISTING PROJECT CONTEXT is provided, highlight if new requirements are already covered in ADO.
        
        Identify requirements mentioned in the raw text that were NOT captured in the extraction, along with risks and ambiguities.
        
        Summarized Extraction:
        {json.dumps(extracted_data, indent=2)}
        
        Full Raw Text Content:
        {raw_text[:100000]}
        
        Return ONLY a JSON object:
        {{
            "gaps": [{{ "requirement": "", "reason": "", "impact": "" }}],
            "ambiguities": [{{ "text": "", "ambiguity_score": 0.8, "alternative_interpretations": [] }}],
            "risks": [{{ "type": "Technical/Business", "description": "", "severity": "" }}],
            "clarification_questions": [{{ "context": "", "question": "", "suggested_answer": "" }}],
            "overall_readiness_score": 0.7
        }}
        """
        
        response = await self.llm.call(prompt, provider="azure")

        from utils.json_extractor import extract_json_from_llm_response
        return extract_json_from_llm_response(response)

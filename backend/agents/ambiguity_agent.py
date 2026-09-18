import json
from services.llm_service import LLMService

class AmbiguityAgent:
    """
    Enterprise Ambiguity Detection Engine.
    Analyzes extracted requirements to identify vague statements, missing SLAs,
    unclear actors, and non-measurable objectives.
    """
    def __init__(self):
        self.llm = LLMService()

    async def detect_ambiguities(self, extraction_data: dict) -> dict:
        """
        Scans the extracted requirements for ambiguities.
        Returns a structured report of unclear items needing BA clarification.
        """
        prompt = f"""
        Act as an Expert Enterprise Business Analyst and Quality Assurance Reviewer.
        Review the following extracted requirements for ambiguity.
        
        Enterprise standards require all requirements to be:
        1. Measurable (No "fast", "reliable", "user-friendly" without metrics)
        2. Actionable (Clear actor and system response)
        3. Testable (Clear acceptance criteria can be derived)
        4. Complete (No missing SLAs, error states, or edge cases)
        
        Extracted Requirements:
        {json.dumps(extraction_data.get('functional_requirements', []), indent=2)}
        {json.dumps(extraction_data.get('non_functional_requirements', []), indent=2)}
        
        Analyze the requirements and identify ANY vague or ambiguous statements.
        
        Respond ONLY with a valid JSON object matching this schema:
        {{
            "is_ambiguous": boolean, // true if ANY major ambiguities are found
            "confidence_score": float, // 0.0 to 1.0, representing clarity of the original text
            "ambiguities": [
                {{
                    "requirement": "The original vague statement",
                    "issue": "Why it is ambiguous (e.g., missing SLA, unmeasurable)",
                    "clarification_question": "A specific question the BA should ask the stakeholder to clarify this"
                }}
            ],
            "summary_feedback": "A short sentence summarizing the overall clarity."
        }}
        """
        
        try:
            response = await self.llm.call(prompt, provider="azure", agent_name="AmbiguityAgent")
            
            if isinstance(response, str):
                start = response.find('{')
                end = response.rfind('}') + 1
                if start != -1 and end != 0:
                    response = json.loads(response[start:end])
                else:
                    response = json.loads(response)

            return response
        except Exception as e:
            print(f"WARN: Ambiguity Detection failed: {e}")
            return {
                "is_ambiguous": False,
                "confidence_score": 1.0,
                "ambiguities": [],
                "summary_feedback": "Failed to run ambiguity check.",
                "error": str(e)
            }

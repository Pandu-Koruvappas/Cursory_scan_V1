import json
from services.llm_service import LLMService

class QAReviewer:
    def __init__(self):
        self.llm = LLMService()

    async def review(self, requirements: list):
        """Checks for testability and generates edge cases."""
        prompt = f"""
        Act as a Senior QA Automation Lead. Review the following functional requirements.
        For each requirement, provide:
        1. Testability Score (1-10)
        2. Missing Edge Cases (unhappy paths)
        3. Automated Test Strategy (API/UI/Data)
        
        Requirements:
        {json.dumps(requirements, indent=2)}
        
        Return the output in JSON format:
        {{
          "qa_review": [
            {{
              "id": "FR-XXX",
              "testability_score": 8,
              "edge_cases": [],
              "test_strategy": ""
            }}
          ]
        }}
        """
        response = await self.llm.call(prompt, provider="azure")
        return self._parse_json(response)

    def _parse_json(self, response):
        try:
            start = response.find("{")
            end = response.rfind("}") + 1
            return json.loads(response[start:end])
        except:
            return {"error": "Failed to parse QA review"}

class SecurityReviewer:
    def __init__(self):
        self.llm = LLMService()

    async def review(self, requirements: list):
        """Checks for PII, Authentication, and Compliance risks."""
        prompt = f"""
        Act as a Cybersecurity Architect. Review the following requirements for security vulnerabilities.
        Identify:
        1. PII/Data Privacy concerns (GDPR/PII).
        2. Authentication/Authorization gaps.
        3. Compliance risks based on the description.
        
        Requirements:
        {json.dumps(requirements, indent=2)}
        
        Return the output in JSON format:
        {{
          "security_review": [
            {{
              "id": "FR-XXX",
              "risk_level": "High/Medium/Low",
              "concerns": [],
              "mitigation_recommendation": ""
            }}
          ]
        }}
        """
        response = await self.llm.call(prompt, provider="azure")
        return self._parse_json(response)

    def _parse_json(self, response):
        try:
            start = response.find("{")
            end = response.rfind("}") + 1
            return json.loads(response[start:end])
        except:
            return {"error": "Failed to parse Security review"}

class UXReviewer:
    def __init__(self):
        self.llm = LLMService()

    async def review(self, requirements: list):
        """Checks for user journey gaps and friction points."""
        prompt = f"""
        Act as a Principal UX Researcher. Review these requirements for user experience flow.
        Identify:
        1. User friction points.
        2. Steps missing in the user journey.
        3. Accessibility (WCAG) considerations.
        
        Requirements:
        {json.dumps(requirements, indent=2)}
        
        Return the output in JSON format:
        {{
          "ux_review": [
            {{
              "id": "FR-XXX",
              "friction_potential": "High/Medium/Low",
              "journey_gaps": [],
              "improvement_suggestion": ""
            }}
          ]
        }}
        """
        response = await self.llm.call(prompt, provider="azure")
        return self._parse_json(response)

    def _parse_json(self, response):
        try:
            start = response.find("{")
            end = response.rfind("}") + 1
            return json.loads(response[start:end])
        except:
            return {"error": "Failed to parse UX review"}

import json
from services.llm_service import LLMService

class GuardAgent:
    def __init__(self):
        self.llm = LLMService()

    async def validate_relevance(self, text: str):
        """
        Input Guardrail: Validates if the document is actually a business/technical requirement.
        """
        prompt = f"""
        Analyze the following text and determine if it is a business requirement document, 
        technical specification, or user story collection.
        
        If it is unrelated to software requirements (e.g., a recipe, fiction, casual conversation), 
        return "REJECTED".
        If it is a valid business requirement, return "ACCEPTED".
        
        TEXT:
        {text[:2000]}
        """
        result = await self.llm.call(prompt, provider="azure")
        return "ACCEPTED" in result.upper()

    def mask_pii(self, text: str):
        """
        Active Privacy Shield: Replaces sensitive PII with placeholders
        to ensure zero-knowledge communication with external providers.
        """
        import re
        patterns = {
            r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}': '[EMAIL_REDACTED]',
            r'\b\d{3}[-.]?\d{3}[-.]?\d{4}\b': '[PHONE_REDACTED]',
            r'(?i)(password|secret|key|token|auth)\s*[:=]\s*[^\s]+': r'\1: [SECRET_REDACTED]',
            r'\b(?:\d[ -]?){13,16}\b': '[CARD_REDACTED]' # Basic Credit Card pattern
        }
        
        masked_text = text
        for pattern, replacement in patterns.items():
            masked_text = re.sub(pattern, replacement, masked_text)
        
        return masked_text

    def detect_pii(self, text: str):
        """
        Privacy Guardrail: Detects potential PII (Emails, Phone Numbers, Credentials)
        to prevent data leaks to external providers.
        """
        import re
        patterns = {
            "email": r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}',
            "phone": r'\b\d{3}[-.]?\d{3}[-.]?\d{4}\b',
            "api_key": r'([a-zA-Z0-9]{32,})',
            "secret": r'(?i)(password|secret|key|token|auth)\s*[:=]\s*[^\s]+'
        }
        
        found = []
        for label, pattern in patterns.items():
            if re.search(pattern, text):
                found.append(label)
        
        return {
            "safe": len(found) == 0,
            "flagged_types": found
        }

    async def verify_backlog_integrity(self, backlog: dict, trd: str):
        """
        Structural Guardrail: Cross-references the backlog with the TRD.
        Returns a structured Integrity Report.
        """
        prompt = f"""
        Compare the BACKLOG (JSON) against the TRD.
        Rate the 'Integrity Score' (0-100) based on:
        1. Alignment: Do the stories match the TRD?
        2. Hallucinations: Are there features NOT in the TRD?
        3. Coverage: Is any core functional req missing?
        
        Return ONLY a JSON object:
        {{
            "integrity_score": 85,
            "hallucinations": [],
            "missing_coverage": [],
            "risk_level": "LOW/MEDIUM/HIGH",
            "summary": "Brief quality summary"
        }}
        
        TRD: {trd[:2000]}
        BACKLOG: {json.dumps(backlog, indent=2)[:2000]}
        """
        try:
            report_str = await self.llm.call(prompt, provider="azure")
            # Force JSON extraction
            start = report_str.find("{")
            end = report_str.rfind("}") + 1
            return json.loads(report_str[start:end])
        except:
            return {
                "integrity_score": 0, 
                "risk_level": "UNKNOWN", 
                "summary": "Integrity check failed to execute."
            }

    def check_schema_compliance(self, data: dict, expected_fields: list):
        """
        Operational Guardrail: Ensures the JSON structure is valid for the UI and ADO.
        """
        missing = [field for field in expected_fields if field not in data]
        return {
            "valid": len(missing) == 0,
            "missing_fields": missing
        }

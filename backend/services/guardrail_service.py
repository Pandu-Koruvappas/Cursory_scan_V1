import re

class GuardrailService:
    """
    Provides Enterprise data compliance by intercepting and scrubbing PII 
    (Personally Identifiable Information) before data hits external LLM APIs.
    Uses a high-performance regex approach to avoid the overhead of large NLP models.
    """
    
    def __init__(self):
        # High-performance regex patterns for common PII
        self.patterns = {
            "EMAIL": r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,7}\b',
            "PHONE": r'\b(\+\d{1,2}\s?)?1?\-?\.?\s?\(?\d{3}\)?[\s.-]?\d{3}[\s.-]?\d{4}\b',
            "SSN": r'\b\d{3}[-.\s]\d{2}[-.\s]\d{4}\b',
            "CREDIT_CARD": r'\b(?:\d{4}[ -]?){3}\d{4}\b'
        }

    def scrub_pii(self, text: str) -> str:
        """
        Scans text and replaces PII matches with safe placeholders.
        """
        if not isinstance(text, str):
            return text
            
        scrubbed = text
        for pii_type, pattern in self.patterns.items():
            scrubbed = re.sub(pattern, f"<{pii_type}>", scrubbed)
            
        return scrubbed

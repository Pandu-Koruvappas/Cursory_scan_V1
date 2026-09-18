import json
from services.llm_service import LLMService

class ArchitectureAgent:
    """
    Enterprise Solution Architecture Agent.
    Recommends technical patterns, microservice boundaries, and database strategies.
    """
    def __init__(self):
        self.llm = LLMService()

    async def recommend(self, requirements: list, context: str = "", institutional_memory: str = "") -> dict:
        """
        Analyzes requirements and provides architectural recommendations.
        """
        memory_context = ""
        if institutional_memory:
            memory_context = f"\nINSTITUTIONAL MEMORY (Past Project Patterns):\n{institutional_memory}\n"

        prompt = f"""
        Act as a Principal Solution Architect. Review the following requirements and provide technical architecture recommendations.
        
        {memory_context}
        {f"PROJECT CONTEXT: {context}" if context else ""}
        
        Requirements:
        {json.dumps(requirements, indent=2)}
        
        Your recommendations should focus on:
        1. Microservice/Module Boundaries.
        2. Data Persistence Strategy (Relational vs NoSQL).
        3. Integration Patterns (Sync vs Async/Event-Driven).
        4. Scalability and High-Availability considerations.
        
        Respond ONLY with a valid JSON object matching this schema:
        {{
            "architecture_review": [
                {{
                    "id": "FR-XXX",
                    "technical_pattern": "e.g., Event-Sourcing, Layered, Hexagonal",
                    "data_strategy": "e.g., Redis for caching, PostgreSQL for source of truth",
                    "integration_type": "e.g., Kafka for event-driven updates",
                    "architecture_notes": "A brief explanation of why this pattern fits this requirement."
                }}
            ],
            "global_recommendations": {{
                "stack_alignment": "Strategic alignment with existing tech stack.",
                "deployment_strategy": "Containerization, Serverless, etc."
            }}
        }}
        """
        
        try:
            response = await self.llm.call(prompt, provider="azure", agent_name="ArchitectureAgent")
            
            if isinstance(response, str):
                start = response.find('{')
                end = response.rfind('}') + 1
                if start != -1 and end != 0:
                    response = json.loads(response[start:end])
                else:
                    response = json.loads(response)

            return response
        except Exception as e:
            print(f"WARN: Architecture Agent failed: {e}")
            return {
                "architecture_review": [],
                "global_recommendations": {},
                "error": str(e)
            }

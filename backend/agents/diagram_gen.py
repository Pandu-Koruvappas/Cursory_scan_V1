import json
from services.llm_service import LLMService

class DiagramAgent:
    def __init__(self):
        self.llm = LLMService()

    async def generate_process_flow(self, requirements: list):
        """Generates a structured JSON process flow for HTML/CSS rendering."""
        prompt = f"""
        Act as a Business Process Architect. Based on the following requirements, generate a logical business process flow.
        Return the flow as a JSON object with a list of nodes.
        
        Requirements:
        {json.dumps(requirements, indent=2)}
        
        Format:
        {{
          "nodes": [
            {{ "id": "1", "label": "Start Process", "type": "start" }},
            {{ "id": "2", "label": "Validate Input", "type": "action" }},
            {{ "id": "3", "label": "Approved?", "type": "decision", "yes": "4", "no": "5" }},
            {{ "id": "4", "label": "Complete", "type": "end" }},
            {{ "id": "5", "label": "Reject", "type": "end" }}
          ]
        }}
        
        Return ONLY the JSON. No markdown backticks.
        """
        
        # Run diagramming through Kimi
        response = await self.llm.call(prompt, provider="kimi", agent_name="DiagramAgent")
        
        try:
            start = response.find("{")
            end = response.rfind("}") + 1
            return json.loads(response[start:end])
        except:
            return {"nodes": [{"id": "1", "label": "Error generating flow", "type": "end"}]}

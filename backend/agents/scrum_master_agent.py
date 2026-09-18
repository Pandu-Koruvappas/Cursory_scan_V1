import json
from services.llm_service import LLMService

class ScrumMasterAgent:
    def __init__(self):
        self.llm = LLMService()

    async def synthesize_standup(self, raw_notes: str, sprint_context: dict = None) -> dict:
        """
        Synthesizes raw notes or Slack transcripts into a structured standup summary.
        Extracts blockers and action items.
        """
        prompt = f"""
        Act as an Agile Scrum Master. Review the following raw team standup notes/transcript.
        
        Raw Notes:
        {raw_notes}
        
        Sprint Context:
        {json.dumps(sprint_context) if sprint_context else 'None provided.'}
        
        Your task is to synthesize this into a structured JSON payload with the following keys:
        - "summary": A brief, high-level summary of team progress.
        - "blockers": A list of explicit blockers mentioned, who is blocked, and what they need.
        - "action_items": A list of tasks that team members committed to doing.
        - "risk_level": "LOW", "MEDIUM", or "HIGH" based on the blockers and tone.
        
        Output ONLY valid JSON.
        """
        
        response = await self.llm.call(prompt, provider="azure")
        
        try:
            # Clean up markdown if any
            if "```json" in response:
                response = response.split("```json")[1].split("```")[0].strip()
            return json.loads(response)
        except Exception as e:
            return {
                "summary": "Failed to parse AI response into JSON.",
                "blockers": [],
                "action_items": [],
                "risk_level": "UNKNOWN",
                "raw": response
            }

    async def facilitate_retro(self, feedback_items: list) -> dict:
        """
        Clusters raw retro feedback into themes (What went well, what didn't, action items).
        """
        prompt = f"""
        Act as an Agile Scrum Master. Cluster the following raw retrospective feedback into themes.
        
        Feedback Items:
        {json.dumps(feedback_items)}
        
        Your task is to synthesize this into a structured JSON payload with the following keys:
        - "went_well": List of positive themes.
        - "needs_improvement": List of negative themes or areas for growth.
        - "action_items": Proposed concrete action items for the next sprint.
        
        Output ONLY valid JSON.
        """
        
        response = await self.llm.call(prompt, provider="azure")
        try:
            if "```json" in response:
                response = response.split("```json")[1].split("```")[0].strip()
            return json.loads(response)
        except Exception as e:
            return {"error": "Failed to parse", "raw": response}

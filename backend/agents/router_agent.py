import json
from services.llm_service import LLMService
from agents.ado_query_agent import ADOQueryAgent
from agents.knowledge_agent import KnowledgeAgent
from agents.test_case_agent import TestCaseAgent

class RouterAgent:
    def __init__(self):
        self.llm = LLMService()
        self.ado_agent = ADOQueryAgent()
        self.knowledge_agent = KnowledgeAgent()
        self.test_case_agent = TestCaseAgent()

    async def route_query(self, user_query: str, context: dict = None) -> dict:
        """
        Analyzes the user's intent and routes to the appropriate specialized agent.
        Returns a standardized JSON response for the frontend chat widget.
        """
        system_prompt = """You are the Omni-Channel Router Agent for a Business Analyst Copilot.
Your job is to analyze the user's query and classify it into one of three intents:
1. "ADO" - The user is asking about Azure DevOps (e.g., tasks, user stories, bugs, backlog, sprint).
2. "KNOWLEDGE" - The user is asking a domain question (e.g., insurance rules, company guidelines, past requirements, policy details).
3. "QA_TESTING" - The user is asking to generate test cases for a specific user story or requirement.
4. "GENERAL" - A general greeting, or a generic question not related to ADO or domain knowledge.

Respond ONLY with a JSON object in this format:
{
    "intent": "ADO|KNOWLEDGE|QA_TESTING|GENERAL",
    "reasoning": "brief explanation"
}
"""

        print(f" [Router Agent] Analyzing intent for: '{user_query}'")
        try:
            # We use groq for fast intent routing
            response = await self.llm.call(
                prompt=user_query,
                provider="azure",
                agent_name="RouterAgent",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_query}
                ]
            )
            
            # Parse the JSON response
            start = response.find("{")
            end = response.rfind("}") + 1
            if start != -1 and end != 0:
                intent_data = json.loads(response[start:end])
                intent = intent_data.get("intent", "GENERAL")
            else:
                intent = "GENERAL"
                
        except Exception as e:
            print(f" [Router Agent] Routing failed: {e}. Defaulting to GENERAL.")
            intent = "GENERAL"

        print(f" [Router Agent] Routed to intent: {intent}")

        # Execute based on intent
        if intent == "ADO":
            # ADOQueryAgent returns formatted markdown
            markdown_content = await self.ado_agent.process_query(user_query)
            return {
                "type": "markdown",
                "content": markdown_content
            }
            
        elif intent == "KNOWLEDGE":
            # KnowledgeAgent returns formatted markdown
            lob = context.get("lob", "General") if context else "General"
            markdown_content = await self.knowledge_agent.retrieve_relevant_context(user_query, lob=lob)
            return {
                "type": "markdown",
                "content": markdown_content
            }
            
        elif intent == "QA_TESTING":
            import re
            # Extract possible ID from user_query
            match = re.search(r'\b\d+\b', user_query)
            if match:
                item_id = match.group(0)
                markdown_content = await self.test_case_agent.generate_tests_for_workitem(item_id)
                return {
                    "type": "markdown",
                    "content": markdown_content
                }
            else:
                return {
                    "type": "markdown",
                    "content": "Please provide the Azure DevOps Work Item ID you want me to write tests for (e.g., 'Generate tests for Story 1234')."
                }
            
        else: # GENERAL
            general_prompt = "You are a helpful Business Analyst AI Assistant. Answer the user's general question concisely."
            markdown_content = await self.llm.call(
                prompt=user_query,
                provider="azure",
                agent_name="GeneralChatAgent",
                messages=[
                    {"role": "system", "content": general_prompt},
                    {"role": "user", "content": user_query}
                ]
            )
            return {
                "type": "markdown",
                "content": markdown_content
            }

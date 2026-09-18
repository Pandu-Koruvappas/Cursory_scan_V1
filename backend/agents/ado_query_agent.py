import json
from services.llm_service import LLMService
from services.ado_service import AzureDevOpsService

class ADOQueryAgent:
    def __init__(self):
        self.llm = LLMService()

    async def process_query(self, user_query: str) -> str:
        """
        Takes a natural language query, decides whether to read or write to ADO via tool calling,
        executes the action, and returns a formatted markdown response.
        """
        # Note: In the marketplace context, ADO credentials must be set in the environment before this runs.
        ado = AzureDevOpsService()
        
        system_prompt = """You are an Azure DevOps (ADO) Assistant for Business Analysts.
Your goal is to answer questions about the ADO board or update work items based on user requests.

IMPORTANT WIQL RULES:
- Always use standard WIQL syntax. 
- Always select [System.Id], [System.Title], [System.State], [System.AssignedTo], [System.WorkItemType]
- The FROM clause must be 'WorkItems'
- Always include: WHERE [System.TeamProject] = @project
- Use CONTAINS for string matching (e.g. [System.AssignedTo] CONTAINS 'John')
- Common Work Item Types: 'Epic', 'Feature', 'User Story', 'Task', 'Bug'.

If the user wants to know about tasks, stories, or items, use the `execute_wiql` tool to fetch the data.
If the user wants to change the state, assignment, or description of a work item, use the `update_work_item` tool.
"""

        tools = [
            {
                "type": "function",
                "function": {
                    "name": "execute_wiql",
                    "description": "Execute a raw WIQL query against Azure DevOps to find work items.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "wiql_query": {
                                "type": "string",
                                "description": "The strict WIQL query string. Must include WHERE [System.TeamProject] = @project"
                            }
                        },
                        "required": ["wiql_query"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "update_work_item",
                    "description": "Update an existing Azure DevOps work item.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "item_id": {
                                "type": "integer",
                                "description": "The integer ID of the work item to update."
                            },
                            "updates": {
                                "type": "object",
                                "description": "A dictionary of fields to update. Valid keys: 'status', 'assigned_to', 'title', 'description'."
                            }
                        },
                        "required": ["item_id", "updates"]
                    }
                }
            }
        ]

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_query}
        ]

        print(f" [ADO Query Agent] Analyzing intent for: '{user_query}'")
        
        # Pass 1: Determine Action
        response = await self.llm.call(
            prompt=user_query,
            provider="azure",
            agent_name="ADOQueryAgent",
            tools=tools,
            tool_choice="auto",
            messages=messages
        )

        if isinstance(response, str):
            # LLM just replied directly without tools
            return response
            
        if not getattr(response, 'tool_calls', None):
            # Fallback if object returned but no tool calls
            if hasattr(response, 'content'):
                return response.content
            return str(response)

        # Handle Tool Calls
        tool_call = response.tool_calls[0]
        
        # Safely convert the message object to a dict to prevent serialization/copy errors
        assistant_msg = {
            "role": "assistant",
            "content": response.content,
            "tool_calls": [
                {
                    "id": tc.id,
                    "type": "function",
                    "function": {
                        "name": tc.function.name,
                        "arguments": tc.function.arguments
                    }
                } for tc in response.tool_calls
            ] if response.tool_calls else None
        }
        messages.append(assistant_msg)
        
        if tool_call.function.name == "execute_wiql":
            args = json.loads(tool_call.function.arguments)
            wiql_query = args.get("wiql_query")
            print(f" [ADO Query Agent] Executing WIQL: {wiql_query}")
            
            try:
                results = await ado.execute_dynamic_wiql(wiql_query)
                tool_response = json.dumps(results)
            except Exception as e:
                tool_response = f"Error executing WIQL: {str(e)}"
                
        elif tool_call.function.name == "update_work_item":
            args = json.loads(tool_call.function.arguments)
            item_id = args.get("item_id")
            updates = args.get("updates")
            print(f" [ADO Query Agent] Updating Work Item {item_id} with {updates}")
            
            try:
                # ADO service expects item_id as string
                results = await ado.update_work_item(str(item_id), updates)
                tool_response = f"Successfully updated Work Item {item_id}."
            except Exception as e:
                tool_response = f"Error updating work item: {str(e)}"
        else:
            tool_response = "Unknown tool called."

        # Pass 2: Format Results
        messages.append({
            "role": "tool",
            "tool_call_id": tool_call.id,
            "name": tool_call.function.name,
            "content": tool_response
        })
        
        formatting_prompt = "Format the tool results into a clear, professional Markdown summary. Use tables or bullet points for readability."
        messages.append({"role": "user", "content": formatting_prompt})
        
        print(" [ADO Query Agent] Formatting results...")
        final_markdown = await self.llm.call(
            prompt=formatting_prompt,
            provider="azure",
            agent_name="ADOQueryAgent_Formatter",
            messages=messages
        )
        
        return final_markdown

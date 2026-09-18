import os
import httpx
import base64
import json
from dotenv import load_dotenv

dotenv_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), ".env")
if os.path.exists(dotenv_path):
    load_dotenv(dotenv_path, override=True)
load_dotenv(override=True)

import sys
from mcp.client.stdio import stdio_client, StdioServerParameters
from mcp.client.session import ClientSession

class AzureDevOpsService:
    def __init__(self):
        self.org_url = (os.getenv("ADO_ORGANIZATION") or os.getenv("ADO_ORG_URL") or "").strip()
        self.project = os.getenv("ADO_PROJECT", "").strip()
        self.credential = os.getenv("ADO_CREDENTIAL", "").strip()
        
        if self.org_url and not self.org_url.startswith("http"):
            self.org_url = f"https://{self.org_url}"
        
        self.org_url = self.org_url.rstrip("/")

        if not self.org_url or not self.project:
            print(f"CRITICAL ERROR: ADO_ORG_URL or ADO_PROJECT is missing. ORG: {self.org_url}, PROJ: {self.project}")
            
        self.auth = base64.b64encode(f":{self.credential}".encode()).decode()
        self.headers = {
            'Authorization': f'Basic {self.auth}',
            'Content-Type': 'application/json-patch+json'
        }

    async def _call_mcp_tool(self, name: str, args: dict):
        server_parameters = StdioServerParameters(
            command=sys.executable,
            args=[os.path.join(os.path.dirname(os.path.dirname(__file__)), "mcp_server.py")],
            env=os.environ.copy()
        )
        async with stdio_client(server_parameters) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                result = await session.call_tool(name, arguments=args)
                if result.content and len(result.content) > 0:
                    text = result.content[0].text
                    if text.startswith("Error executing"):
                        raise Exception(text)
                    if text.startswith("Created work item ID:"):
                        id_str = text.split("ID: ")[1].strip()
                        return {"id": int(id_str)}
                    try:
                        return json.loads(text)
                    except json.JSONDecodeError:
                        return text
                return None

    async def create_work_item(self, title: str, item_type: str, description: str, parent_id: int = None, tags: str = ""):
        args = {
            "title": title,
            "item_type": item_type,
            "description": description
        }
        if parent_id: args["parent_id"] = parent_id
        if tags: args["tags"] = tags
        
        return await self._call_mcp_tool("create_work_item", args)
    
    async def get_all_work_items(self):
        return await self._call_mcp_tool("get_all_work_items", {})

    async def get_work_item(self, item_id: str) -> dict:
        data = await self._call_mcp_tool("get_work_item", {"item_id": item_id})
        return data.get('fields', {}) if isinstance(data, dict) else {}

    async def update_work_item(self, item_id: str, updates: dict):
        return await self._call_mcp_tool("update_work_item", {"item_id": item_id, "updates": updates})

    async def get_project_members(self):
        return await self._call_mcp_tool("get_project_members", {})

    async def get_iterations(self):
        return await self._call_mcp_tool("get_iterations", {})

    async def search_work_items(self, title_query: str) -> list:
        return await self._call_mcp_tool("search_work_items", {"title_query": title_query})

    async def execute_dynamic_wiql(self, wiql_string: str) -> list:
        return await self._call_mcp_tool("execute_dynamic_wiql", {"wiql_string": wiql_string})

    async def get_unassigned_backlog(self) -> list:
        return await self._call_mcp_tool("get_unassigned_backlog", {})

    async def assign_to_sprint(self, sprint_path: str, item_ids: list) -> dict:
        return await self._call_mcp_tool("assign_to_sprint", {"sprint_path": sprint_path, "item_ids": item_ids})

    async def get_sprint_burndown_data(self, iteration_path: str = None) -> dict:
        args = {}
        if iteration_path:
            args["iteration_path"] = iteration_path
        return await self._call_mcp_tool("get_sprint_burndown_data", args)

    async def get_active_blockers(self) -> list:
        return await self._call_mcp_tool("get_active_blockers", {})

import os
import httpx
import base64
import json
from dotenv import load_dotenv

# Ensure environment variables are loaded
dotenv_path = os.path.join(os.path.dirname(__file__), ".env")
if os.path.exists(dotenv_path):
    load_dotenv(dotenv_path, override=True)
load_dotenv(override=True)

from mcp.server import Server
from mcp.types import Tool, TextContent
from azure.identity.aio import DefaultAzureCredential

# Initialize the MCP Server
app = Server("azure-devops-mcp")

async def get_ado_client():
    org_url = os.getenv("ADO_ORG_URL", "").rstrip("/")
    if not org_url:
        org_url = os.getenv("ADO_ORGANIZATION", "").rstrip("/")
        
    if not org_url.startswith("http"):
        org_url = f"https://{org_url}"
        
    headers = {'Content-Type': 'application/json-patch+json'}
    
    credential_value = os.getenv("ADO_CREDENTIAL", "").strip()
    if credential_value:
        auth = base64.b64encode(f":{credential_value}".encode()).decode()
        headers['Authorization'] = f'Basic {auth}'
    else:
        try:
            credential = DefaultAzureCredential()
            token = await credential.get_token("499b84ac-1321-427f-aa17-267ca6975798/.default")
            headers['Authorization'] = f'Bearer {token.token}'
        except Exception as e:
            print(f"Azure AD Credential Warning: {e}")
        
    return httpx.AsyncClient(headers=headers, timeout=30.0), org_url

@app.list_tools()
async def list_tools() -> list[Tool]:
    return [
        Tool(
            name="create_work_item",
            description="Create a work item in Azure DevOps",
            inputSchema={
                "type": "object",
                "properties": {
                    "title": {"type": "string"},
                    "item_type": {"type": "string"},
                    "description": {"type": "string"},
                    "parent_id": {"type": "integer"},
                    "tags": {"type": "string"}
                },
                "required": ["title", "item_type", "description"]
            }
        ),
        Tool(
            name="get_work_item",
            description="Get a work item from Azure DevOps",
            inputSchema={
                "type": "object",
                "properties": {
                    "item_id": {"type": "string"}
                },
                "required": ["item_id"]
            }
        ),
        Tool(
            name="get_all_work_items",
            description="Fetches all work items from the project",
            inputSchema={
                "type": "object",
                "properties": {},
                "required": []
            }
        ),
        Tool(
            name="update_work_item",
            description="Update a work item",
            inputSchema={
                "type": "object",
                "properties": {
                    "item_id": {"type": "string"},
                    "updates": {"type": "object"}
                },
                "required": ["item_id", "updates"]
            }
        ),
        Tool(
            name="get_project_members",
            description="Get project members",
            inputSchema={
                "type": "object",
                "properties": {},
                "required": []
            }
        ),
        Tool(
            name="get_iterations",
            description="Get iterations",
            inputSchema={
                "type": "object",
                "properties": {},
                "required": []
            }
        ),
        Tool(
            name="search_work_items",
            description="Search work items",
            inputSchema={
                "type": "object",
                "properties": {
                    "title_query": {"type": "string"}
                },
                "required": ["title_query"]
            }
        ),
        Tool(
            name="execute_dynamic_wiql",
            description="Execute dynamic WIQL",
            inputSchema={
                "type": "object",
                "properties": {
                    "wiql_string": {"type": "string"}
                },
                "required": ["wiql_string"]
            }
        ),
        Tool(
            name="get_unassigned_backlog",
            description="Get unassigned backlog",
            inputSchema={
                "type": "object",
                "properties": {},
                "required": []
            }
        ),
        Tool(
            name="assign_to_sprint",
            description="Assign to sprint",
            inputSchema={
                "type": "object",
                "properties": {
                    "sprint_path": {"type": "string"},
                    "item_ids": {"type": "array", "items": {"type": "string"}}
                },
                "required": ["sprint_path", "item_ids"]
            }
        ),
        Tool(
            name="get_sprint_burndown_data",
            description="Get sprint burndown data",
            inputSchema={
                "type": "object",
                "properties": {
                    "iteration_path": {"type": "string"}
                },
                "required": []
            }
        ),
        Tool(
            name="get_active_blockers",
            description="Get active blockers",
            inputSchema={
                "type": "object",
                "properties": {},
                "required": []
            }
        )
    ]

@app.call_tool()
async def call_tool(name: str, arguments: dict) -> list[TextContent]:
    project = os.getenv("ADO_PROJECT", "").strip()
    client, org_url = await get_ado_client()
    
    # helper for dynamic wiql since it's used multiple times
    async def _execute_wiql(wiql_string):
        url = f"{org_url}/{project}/_apis/wit/wiql?api-version=7.1"
        res = await client.post(url, json={"query": wiql_string}, headers={'Content-Type': 'application/json'})
        if res.status_code != 200:
            raise Exception(f"WIQL Error ({res.status_code}): {res.text}")
        work_items = res.json().get('workItems', [])
        if not work_items:
            return []
        
        all_details = []
        batch_size = 200
        for i in range(0, len(work_items), batch_size):
            batch_refs = work_items[i:i + batch_size]
            ids = ",".join([str(r['id']) for r in batch_refs])
            
            details_url = f"{org_url}/{project}/_apis/wit/workitems?ids={ids}&api-version=7.1"
            details_res = await client.get(details_url)
            
            if details_res.status_code == 200:
                all_details.extend(details_res.json().get('value', []))
        return [
            {
                "id": item['id'],
                "title": item['fields'].get('System.Title'),
                "type": item['fields'].get('System.WorkItemType'),
                "state": item['fields'].get('System.State'),
                "description": item['fields'].get('System.Description', ''),
                "assigned_to": item['fields'].get('System.AssignedTo', {}).get('displayName', 'Unassigned')
            } for item in all_details
        ]

    try:
        if name == "create_work_item":
            item_type = arguments["item_type"]
            url = f"{org_url}/{project}/_apis/wit/workitems/${item_type}?api-version=7.1"
            
            payload = [
                {"op": "add", "path": "/fields/System.Title", "value": arguments["title"]},
                {"op": "add", "path": "/fields/System.Description", "value": arguments["description"]}
            ]
            
            if arguments.get("tags"):
                payload.append({"op": "add", "path": "/fields/System.Tags", "value": arguments["tags"]})
                
            if arguments.get("parent_id"):
                payload.append({
                    "op": "add",
                    "path": "/relations/-",
                    "value": {
                        "rel": "System.LinkTypes.Hierarchy-Reverse",
                        "url": f"{org_url}/{project}/_apis/wit/workitems/{arguments['parent_id']}"
                    }
                })
                
            response = await client.post(url, json=payload)
            response.raise_for_status()
            data = response.json()
            return [TextContent(type="text", text=f"Created work item ID: {data.get('id')}")]
            
        elif name == "get_work_item":
            item_id = arguments["item_id"]
            url = f"{org_url}/{project}/_apis/wit/workitems/{item_id}?api-version=7.1"
            response = await client.get(url)
            response.raise_for_status()
            return [TextContent(type="text", text=response.text)]

        elif name == "get_all_work_items":
            wiql_url = f"{org_url}/{project}/_apis/wit/wiql?api-version=7.1"
            query = {
                "query": f"SELECT [System.Id] FROM workitems WHERE [System.TeamProject] = '{project}' ORDER BY [System.CreatedDate] DESC"
            }
            res = await client.post(wiql_url, json=query, headers={'Content-Type': 'application/json'})
            if res.status_code != 200: raise Exception(f"WIQL Error ({res.status_code}): {res.text}")
            
            work_item_refs = res.json().get('workItems', [])
            if not work_item_refs: return [TextContent(type="text", text=json.dumps([]))]
            
            all_details = []
            batch_size = 200
            for i in range(0, len(work_item_refs), batch_size):
                batch_refs = work_item_refs[i:i + batch_size]
                ids = ",".join([str(r['id']) for r in batch_refs])
                
                details_url = f"{org_url}/_apis/wit/workitems?ids={ids}&fields=System.Id,System.Title,System.WorkItemType,System.State,System.AssignedTo,System.Description,Microsoft.VSTS.Scheduling.Effort&api-version=7.1"
                details_res = await client.get(details_url)
                
                if details_res.status_code == 200:
                    all_details.extend(details_res.json().get('value', []))
            
            ret = [
                {
                    "id": str(f['fields']['System.Id']),
                    "title": f['fields']['System.Title'],
                    "type": f['fields']['System.WorkItemType'],
                    "status": f['fields']['System.State'],
                    "assigned_to": f['fields'].get('System.AssignedTo', {}).get('displayName', 'Unassigned'),
                    "effort": f['fields'].get('Microsoft.VSTS.Scheduling.Effort', 0),
                    "description": f['fields'].get('System.Description', '')
                } for f in all_details
            ]
            return [TextContent(type="text", text=json.dumps(ret))]

        elif name == "update_work_item":
            item_id = arguments["item_id"]
            updates = arguments["updates"]
            url = f"{org_url}/{project}/_apis/wit/workitems/{item_id}?api-version=7.1"
            payload = []
            if 'title' in updates:
                payload.append({"op": "replace", "path": "/fields/System.Title", "value": updates['title']})
            if 'description' in updates:
                payload.append({"op": "replace", "path": "/fields/System.Description", "value": updates['description']})
            if 'assigned_to' in updates:
                payload.append({"op": "replace", "path": "/fields/System.AssignedTo", "value": updates['assigned_to']})
            if 'status' in updates:
                payload.append({"op": "replace", "path": "/fields/System.State", "value": updates['status']})
                
            res = await client.patch(url, json=payload)
            if res.status_code == 200:
                return [TextContent(type="text", text=json.dumps(res.json()))]
            else:
                raise Exception(f"ADO Update Error: {res.text}")

        elif name == "get_project_members":
            proj_res = await client.get(f"{org_url}/_apis/projects/{project}?api-version=7.1")
            if proj_res.status_code != 200: return [TextContent(type="text", text=json.dumps([]))]
            proj_id = proj_res.json().get('id')

            team_res = await client.get(f"{org_url}/_apis/projects/{proj_id}/teams?api-version=7.1")
            if team_res.status_code != 200: return [TextContent(type="text", text=json.dumps([]))]
            teams = team_res.json().get('value', [])
            if not teams: return [TextContent(type="text", text=json.dumps([]))]
            
            team_id = teams[0]['id']
            members_url = f"{org_url}/_apis/projects/{proj_id}/teams/{team_id}/members?api-version=7.1"
            members_res = await client.get(members_url)
            
            if members_res.status_code == 200:
                members = members_res.json().get('value', [])
                ret = [
                    {
                        "display_name": m['identity']['displayName'],
                        "unique_name": m['identity']['uniqueName'],
                        "id": m['identity']['id']
                    } for m in members
                ]
                return [TextContent(type="text", text=json.dumps(ret))]
            return [TextContent(type="text", text=json.dumps([]))]

        elif name == "get_iterations":
            url = f"{org_url}/{project}/_apis/work/teamsettings/iterations?api-version=7.1"
            res = await client.get(url)
            if res.status_code != 200: return [TextContent(type="text", text=json.dumps([]))]
            ret = [
                {
                    "id": it['id'],
                    "name": it['name'],
                    "path": it['path'],
                    "attributes": it.get('attributes', {})
                } for it in res.json().get('value', [])
            ]
            return [TextContent(type="text", text=json.dumps(ret))]

        elif name == "search_work_items":
            title_query = arguments["title_query"]
            url = f"{org_url}/{project}/_apis/wit/wiql?api-version=7.1"
            safe_query = title_query.replace("'", "''")
            wiql_query = {
                "query": f"SELECT [System.Id], [System.Title], [System.WorkItemType] FROM WorkItems WHERE [System.TeamProject] = @project AND [System.Title] CONTAINS '{safe_query}' AND [System.State] <> 'Removed'"
            }
            res = await client.post(url, json=wiql_query, headers={"Content-Type": "application/json"})
            if res.status_code == 200:
                work_items = res.json().get('workItems', [])
                if not work_items:
                    return [TextContent(type="text", text=json.dumps([]))]
                
                ids = ",".join([str(wi['id']) for wi in work_items[:5]])
                details_url = f"{org_url}/{project}/_apis/wit/workitems?ids={ids}&api-version=7.1"
                details_res = await client.get(details_url)
                if details_res.status_code == 200:
                    ret = [
                        {
                            "id": item['id'],
                            "title": item['fields'].get('System.Title'),
                            "type": item['fields'].get('System.WorkItemType')
                        } for item in details_res.json().get('value', [])
                    ]
                    return [TextContent(type="text", text=json.dumps(ret))]
            return [TextContent(type="text", text=json.dumps([]))]

        elif name == "execute_dynamic_wiql":
            wiql_string = arguments["wiql_string"]
            ret = await _execute_wiql(wiql_string)
            return [TextContent(type="text", text=json.dumps(ret))]

        elif name == "get_unassigned_backlog":
            query = f"SELECT [System.Id], [System.Title], [System.IterationPath], [Microsoft.VSTS.Scheduling.StoryPoints], [Microsoft.VSTS.Scheduling.OriginalEstimate] FROM WorkItems WHERE [System.TeamProject] = @project AND [System.WorkItemType] = 'User Story' AND [System.State] NOT IN ('Removed', 'Closed', 'Done') AND [System.IterationPath] = '{project}'"
            items = await _execute_wiql(query)
            # Need to get more fields, but actually execute_dynamic_wiql only gets specific ones...
            # The original code re-fetched items using _execute_wiql, but then tried to access points and hours that weren't fetched.
            # Let's fix this slightly by just fetching them here.
            
            wiql_url = f"{org_url}/{project}/_apis/wit/wiql?api-version=7.1"
            res = await client.post(wiql_url, json={"query": query}, headers={'Content-Type': 'application/json'})
            if res.status_code != 200: raise Exception(f"WIQL Error: {res.text}")
            work_item_refs = res.json().get('workItems', [])
            if not work_item_refs: return [TextContent(type="text", text=json.dumps([]))]
            
            all_details = []
            batch_size = 200
            for i in range(0, len(work_item_refs), batch_size):
                batch_refs = work_item_refs[i:i + batch_size]
                ids = ",".join([str(r['id']) for r in batch_refs])
                
                details_url = f"{org_url}/{project}/_apis/wit/workitems?ids={ids}&fields=System.Id,System.Title,Microsoft.VSTS.Scheduling.StoryPoints,Microsoft.VSTS.Scheduling.OriginalEstimate&api-version=7.1"
                details_res = await client.get(details_url)
                
                if details_res.status_code == 200:
                    all_details.extend(details_res.json().get('value', []))

            mapped = []
            for item in all_details:
                pts_val = item.get("fields", {}).get("Microsoft.VSTS.Scheduling.StoryPoints", 0)
                hrs_val = item.get("fields", {}).get("Microsoft.VSTS.Scheduling.OriginalEstimate", 0)
                mapped.append({
                    "id": str(item["id"]),
                    "title": item.get("fields", {}).get("System.Title"),
                    "points": float(pts_val) if pts_val else 0,
                    "hours": float(hrs_val) if hrs_val else 0
                })
            return [TextContent(type="text", text=json.dumps(mapped))]

        elif name == "assign_to_sprint":
            sprint_path = arguments["sprint_path"]
            item_ids = arguments["item_ids"]
            if not item_ids:
                return [TextContent(type="text", text=json.dumps({"updated_count": 0, "errors": []}))]
            updates = []
            errors = []
            for wi_id in item_ids:
                payload = [{
                    "op": "add",
                    "path": "/fields/System.IterationPath",
                    "value": sprint_path
                }]
                url = f"{org_url}/{project}/_apis/wit/workitems/{wi_id}?api-version=7.1"
                response = await client.patch(url, json=payload)
                if response.status_code in [200, 201]:
                    updates.append(wi_id)
                else:
                    errors.append(f"ID {wi_id}: {response.text}")
            ret = {"updated_count": len(updates), "updated_ids": updates, "errors": errors}
            return [TextContent(type="text", text=json.dumps(ret))]

        elif name == "get_sprint_burndown_data":
            iteration_path = arguments.get("iteration_path")
            iteration_filter = f"AND [System.IterationPath] = '{iteration_path}'" if iteration_path else ""
            wiql = f"""
            SELECT [System.Id], [System.State], [Microsoft.VSTS.Scheduling.Effort], [Microsoft.VSTS.Scheduling.OriginalEstimate], [Microsoft.VSTS.Scheduling.RemainingWork]
            FROM workitems 
            WHERE [System.TeamProject] = '{project}' 
            {iteration_filter}
            AND [System.WorkItemType] IN ('User Story', 'Task', 'Bug')
            """
            
            wiql_url = f"{org_url}/{project}/_apis/wit/wiql?api-version=7.1"
            res = await client.post(wiql_url, json={"query": wiql}, headers={'Content-Type': 'application/json'})
            if res.status_code != 200: raise Exception(f"WIQL Error: {res.text}")
            
            work_item_refs = res.json().get('workItems', [])
            if not work_item_refs: 
                return [TextContent(type="text", text=json.dumps({"total_points": 0, "completed_points": 0, "velocity_percentage": 0}))]
            
            total_points = 0
            completed_points = 0
            total_hours = 0
            remaining_hours = 0
            
            ids = ",".join([str(r['id']) for r in work_item_refs])
            details_url = f"{org_url}/_apis/wit/workitems?ids={ids}&fields=System.Id,System.State,Microsoft.VSTS.Scheduling.StoryPoints,Microsoft.VSTS.Scheduling.OriginalEstimate,Microsoft.VSTS.Scheduling.RemainingWork&api-version=7.1"
            details_res = await client.get(details_url)
            
            if details_res.status_code == 200:
                for f in details_res.json().get('value', []):
                    state = f['fields'].get('System.State', '')
                    points = f['fields'].get('Microsoft.VSTS.Scheduling.StoryPoints', 0)
                    orig = f['fields'].get('Microsoft.VSTS.Scheduling.OriginalEstimate', 0)
                    rem = f['fields'].get('Microsoft.VSTS.Scheduling.RemainingWork', 0)
                    
                    if points:
                        total_points += points
                        if state in ['Closed', 'Done', 'Resolved']:
                            completed_points += points
                            
                    if orig:
                        total_hours += orig
                        remaining_hours += rem if state not in ['Closed', 'Done', 'Resolved'] else 0
                        
            ret = {
                "total_points": total_points,
                "completed_points": completed_points,
                "velocity_percentage": round((completed_points / total_points * 100) if total_points > 0 else 0, 1),
                "total_hours": total_hours,
                "remaining_hours": remaining_hours
            }
            return [TextContent(type="text", text=json.dumps(ret))]

        elif name == "get_active_blockers":
            wiql = f"""
            SELECT [System.Id] 
            FROM workitems 
            WHERE [System.TeamProject] = '{project}' 
            AND [System.State] NOT IN ('Closed', 'Done', 'Resolved', 'Removed')
            AND [System.Tags] CONTAINS 'Blocked'
            """
            ret = await _execute_wiql(wiql)
            return [TextContent(type="text", text=json.dumps(ret))]

        else:
            raise ValueError(f"Unknown tool: {name}")
            
    except Exception as e:
        return [TextContent(type="text", text=f"Error executing {name}: {str(e)}")]
    finally:
        await client.aclose()

import asyncio
from mcp.server.stdio import stdio_server

async def main():
    async with stdio_server() as (read_stream, write_stream):
        await app.run(
            read_stream,
            write_stream,
            app.create_initialization_options()
        )

if __name__ == "__main__":
    asyncio.run(main())

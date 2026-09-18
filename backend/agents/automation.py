from services.ado_service import AzureDevOpsService

class AutomationAgent:
    def __init__(self):
        self.ado = AzureDevOpsService()

    async def create_work_items(self, backlog: dict, db=None, analysis_id=None, target="ado"):
        """
        Actually creates or UPDATES work items in Azure DevOps based on selection.
        Supports 'Upsert' logic via remote_id tracking.
        """
        from models.models import AuditLog
        import json
        
        links = []
        try:
            epics = backlog.get("epics", [])
            for epic in epics:
                # 1. Handle Selection Logic
                if not epic.get("selected", True):
                    continue

                # 2. Agentic Duplicate Detection for Epic
                title = epic['title']
                desc = "<p>Auto-generated Epic from BA Agent Pro</p>"
                epic_id = epic.get("remote_id")
                
                if not epic_id:
                    # Use LLM to check for duplicates autonomously
                    from services.llm_service import LLMService
                    llm = LLMService()
                    
                    tools = [{
                        "type": "function",
                        "function": {
                            "name": "search_ado",
                            "description": "Searches Azure DevOps for existing Epics with similar titles to prevent duplicates.",
                            "parameters": {
                                "type": "object",
                                "properties": {"query": {"type": "string", "description": "The title to search for"}},
                                "required": ["query"]
                            }
                        }
                    }]
                    
                    messages = [
                        {"role": "system", "content": "You are an Azure DevOps automation agent. Your goal is to check if an Epic already exists before creating it. Call the search_ado tool with the Epic title."},
                        {"role": "user", "content": f"Does an Epic with the title '{title}' already exist? Call the tool to find out. If you don't find it, just say 'No'."}
                    ]
                    
                    llm_res = await llm.call(prompt=f"Check: {title}", provider="azure", agent_name="AutomationAgent", tools=tools, tool_choice="auto", messages=messages)
                    
                    # Full Tool Execution Loop
                    if not isinstance(llm_res, str) and getattr(llm_res, 'tool_calls', None):
                        tool_call = llm_res.tool_calls[0]
                        if tool_call.function.name == "search_ado":
                            import json
                            args = json.loads(tool_call.function.arguments)
                            search_query = args.get('query')
                            print(f" Agent actively searching ADO for: {search_query}")
                            
                            # Execute actual Search
                            search_results = await self.ado.search_work_items(search_query)
                            
                            # Feed results back to LLM to make final decision
                            messages.append(llm_res)
                            messages.append({
                                "role": "tool",
                                "tool_call_id": tool_call.id,
                                "name": tool_call.function.name,
                                "content": json.dumps(search_results) if search_results else "[]"
                            })
                            
                            messages.append({"role": "user", "content": "Based on the tool results, does it exist? Reply with just the ID if it exists, or 'No'."})
                            
                            final_res = await llm.call(prompt="Based on the tool results, does it exist? Reply with just the ID if it exists, or 'No'.", provider="azure", agent_name="AutomationAgent", messages=messages)
                            print(f" Agent final duplicate decision: {final_res}")
                            
                            # Parse final response
                            if final_res and final_res.strip().lower() != 'no' and final_res.strip().isdigit():
                                epic_id = int(final_res.strip())
                            else:
                                epic_id = None

                if epic_id:
                    await self.ado.update_work_items([{"id": epic_id, "title": title, "description": desc}])
                    links.append(f"Epic Updated: {epic_id} - {title}")
                else:
                    epic_res = await self.ado.create_work_item(title, "Epic", desc)
                    epic_id = epic_res['id']
                    epic["remote_id"] = epic_id
                    links.append(f"Epic Created: {epic_id} - {title}")
                
                for feature in epic.get("features", []):
                    if not feature.get("selected", True):
                        continue
                        
                    feat_title = feature['title']
                    feat_desc = "<p>Auto-generated Feature from BA Agent Pro</p>"
                    feat_id = feature.get("remote_id")
                    
                    if feat_id:
                        await self.ado.update_work_items([{"id": feat_id, "title": feat_title, "description": feat_desc}])
                        links.append(f"  Feature Updated: {feat_id} - {feat_title}")
                    else:
                        feat_res = await self.ado.create_work_item(feat_title, "Feature", feat_desc, parent_id=epic_id)
                        feat_id = feat_res['id']
                        feature["remote_id"] = feat_id
                        links.append(f"  Feature Created: {feat_id} - {feat_title}")
                    
                    for story in feature.get("user_stories", []):
                        if not story.get("selected", True):
                            continue
                            
                        story_title = story['title']
                        
                        # Azure DevOps requires HTML for rich text fields like System.Description
                        ac_html = "".join([f"<li>{ac}</li>" for ac in story.get('acceptance_criteria', [])])
                        story_desc = f"<p>{story.get('description', '')}</p><br/><b>Acceptance Criteria:</b><ul>{ac_html}</ul>"
                        
                        tags_str = f"{story.get('moscow', '')}; {story.get('release_phase', '')}"
                        story_id = story.get("remote_id")
                        
                        if story_id:
                            await self.ado.update_work_items([{"id": story_id, "title": story_title, "description": story_desc}])
                            links.append(f"Story Updated: {story_id} - {story_title}")
                        else:
                            story_res = await self.ado.create_work_item(
                                story_title, 
                                "User Story", 
                                story_desc, 
                                parent_id=feat_id,
                                tags=tags_str
                            )
                            story_id = story_res['id']
                            story["remote_id"] = story_id
                            links.append(f"Story Created: {story_id} [{tags_str}]")
                        
                        for task in story.get("tasks", []):
                            await self.ado.create_work_item(task, "Task", "Auto-generated Task", parent_id=story_id)

            # --- RECORD AUDIT LOG ---
            if db and analysis_id:
                new_log = AuditLog(
                    action="SYNC_TO_ADO",
                    details=json.dumps({
                        "summary": f"Synchronized {len(links)} items to Azure DevOps.",
                        "items": links[:20] # Store first 20 for quick preview
                    }),
                    analysis_id=analysis_id
                )
                db.add(new_log)
                db.commit()
                print(f" Governance Vault: Audit log recorded for Analysis {analysis_id}")

            return {
                "status": "Backlog Synchronized Successfully",
                "work_item_links": links,
                "updated_backlog": backlog
            }
        except Exception as e:
            import traceback
            traceback.print_exc()
            return {"error": str(e)}

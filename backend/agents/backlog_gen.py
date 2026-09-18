import json
from services.llm_service import LLMService

class BacklogGenAgent:
    def __init__(self):
        self.llm = LLMService()

    async def generate_backlog(self, trd_content: str, nfr_content: str = "", council_reviews: dict = None, raw_requirements: list = None):
        """
        Derives an enterprise Azure DevOps hierarchy (Epics ➔ Features ➔ User Stories ➔ Tasks)
        ingesting the synthesized Functional Spec (TRD), NFRs, Council Reviews, and complete raw extraction array.
        """
        from services.template_service import TemplateService
        ts = TemplateService()
        skill_prompt = ts.load_skill_prompt("backlog_architect")
        
        from utils.token_optimizer import TokenOptimizer
        compressed_trd = TokenOptimizer.compress_trd_for_backlog(trd_content, max_chars=35000)
        
        import re
        parsed_from_trd = []
        matches = re.findall(r'\[(REQ-\d+|FR-\d+)\]([^\n]*)', trd_content)
        for match in matches:
            req_id = match[0].upper().replace("FR-", "REQ-")
            rest = match[1].strip()
            if ":" in rest:
                req_title, req_desc = [x.strip() for x in rest.split(":", 1)]
            else:
                req_title, req_desc = rest, ""
            parsed_from_trd.append({
                "id": req_id,
                "title": req_title,
                "description": req_desc or req_title
            })

        effective_requirements = []
        if raw_requirements and isinstance(raw_requirements, list) and len(raw_requirements) > 0:
            for r in raw_requirements:
                if isinstance(r, dict):
                    raw_id = r.get("id") or r.get("req_id") or ""
                    req_id = raw_id.replace("FR-", "REQ-") if "FR-" in raw_id else raw_id
                    effective_requirements.append({
                        "id": req_id,
                        "title": r.get("title") or r.get("name") or "",
                        "description": r.get("description") or r.get("text") or ""
                    })

        if len(parsed_from_trd) > len(effective_requirements):
            effective_requirements = parsed_from_trd

        fr_tags = [r["id"] for r in effective_requirements]
        fr_tags = sorted(list(set(fr_tags)))

        raw_reqs_section = ""
        if effective_requirements:
            raw_reqs_section = f"\n\nCOMPLETE EXTRACTED FUNCTIONAL REQUIREMENTS ARRAY ({len(effective_requirements)} Requirements):\n"
            for r in effective_requirements:
                raw_reqs_section += f"- [{r['id']}] {r['title']}: {r['description']}\n"

        # --- SOLUTION: HIGH-LEVEL FEATURE CLUSTERING ARCHITECTURE (5 to 8 BUSINESS CAPABILITY FEATURES) ---
        if len(effective_requirements) > 0:
            print(f" [BacklogGenAgent] Executing High-Level Feature Clustering Architecture for {len(effective_requirements)} Requirements...")
            import asyncio
            from utils.json_extractor import extract_json_from_llm_response

            all_req_items_text = "\n".join([f"- [{r['id']}] {r['title']}: {r['description']}" for r in effective_requirements])
            all_req_ids = [r['id'] for r in effective_requirements]

            # Step 1: Cluster requirements into 5 to 8 High-Level Business Capability Features
            cluster_prompt = f"""
{skill_prompt}

ACT AS AN ENTERPRISE AGILE SOLUTION ARCHITECT.
You are given {len(effective_requirements)} Functional Requirements for a Commercial Property / Insurance System.

REQUIREMENTS LIST:
{all_req_items_text}

CRITICAL MANDATE:
Group ALL {len(effective_requirements)} requirements into EXACTLY 5 to 8 HIGH-LEVEL BUSINESS CAPABILITY FEATURES.
Each Feature MUST represent a broad business capability or functional sub-system (e.g., 'Property Intake & Management', 'Fire Protection & Life Safety Systems', 'Building Systems & Facility Operations', 'Warehouse & Storage Operations', 'Manufacturing Operations', 'Security & Access Control').
DO NOT create fine-grained or field-level features. Create 5 to 8 broad, high-level business capabilities.

Return valid JSON in this exact structure:
{{
  "feature_clusters": [
    {{
      "feature_title": "High-Level Business Capability Title",
      "description": "Comprehensive capability overview describing this functional domain.",
      "requirement_ids": ["REQ-001", "REQ-002", "REQ-003"]
    }}
  ]
}}
"""
            print(" [BacklogGenAgent] Step 1: Clustering requirements into 5-8 High-Level Features...")
            cluster_resp = await self.llm.call(cluster_prompt, provider="azure", agent_name="BacklogArchitect_Cluster")
            cluster_data = extract_json_from_llm_response(cluster_resp)

            feature_clusters = []
            if isinstance(cluster_data, dict) and "feature_clusters" in cluster_data and isinstance(cluster_data["feature_clusters"], list):
                feature_clusters = cluster_data["feature_clusters"]

            # Fallback if clustering failed or returned empty
            if not feature_clusters:
                print(" [BacklogGenAgent] Cluster fallback triggered: Partitioning into domain capability buckets.")
                bucket_size = max(4, (len(effective_requirements) + 5) // 6)
                domain_names = ["Property Management & Intake", "Fire Protection & Safety", "Warehouse & Storage Operations", "Facility & Building Systems", "Manufacturing & Industrial Operations", "Security & Access Control"]
                for i in range(0, len(effective_requirements), bucket_size):
                    chunk_reqs = effective_requirements[i:i + bucket_size]
                    chunk_ids = [r['id'] for r in chunk_reqs]
                    d_title = domain_names[(i // bucket_size) % len(domain_names)]
                    feature_clusters.append({
                        "feature_title": d_title,
                        "description": f"Domain capability for {d_title}.",
                        "requirement_ids": chunk_ids
                    })

            # Ensure 100% of requirement IDs are assigned to a cluster
            assigned_ids = set()
            for fc in feature_clusters:
                assigned_ids.update(fc.get("requirement_ids", []))

            unassigned = [r for r in effective_requirements if r['id'] not in assigned_ids]
            if unassigned and feature_clusters:
                feature_clusters[-1].setdefault("requirement_ids", []).extend([r['id'] for r in unassigned])

            print(f" [BacklogGenAgent] Step 1 Complete: Created {len(feature_clusters)} High-Level Feature Clusters.")

            # Step 2: Generate 3 to 8 User Stories per Feature Cluster in parallel
            req_by_id = {r['id']: r for r in effective_requirements}

            async def generate_stories_for_cluster(fc):
                f_title = fc.get("feature_title") or "Business Capability Feature"
                f_desc = fc.get("description") or ""
                fc_req_ids = fc.get("requirement_ids", [])
                fc_reqs = [req_by_id[rid] for rid in fc_req_ids if rid in req_by_id]
                if not fc_reqs: return None

                fc_reqs_text = "\n".join([f"- [{r['id']}] {r['title']}: {r['description']}" for r in fc_reqs])

                story_prompt = f"""
{skill_prompt}

ACT AS A SENIOR AGILE BUSINESS ANALYST.
You are writing User Stories for the High-Level Feature: "{f_title}".

FEATURE DESCRIPTION: {f_desc}

MAPPED FUNCTIONAL REQUIREMENTS ({len(fc_reqs)} items):
{fc_reqs_text}

CRITICAL MANDATES:
1. Generate between 3 and 8 User Stories for this Feature capability.
2. Group related requirements into User Stories (Many-to-One, e.g. "[REQ-001, REQ-002, REQ-003] Prefill, Edit & Retain Property Data") OR split complex requirements (One-to-Many).
3. Ensure EVERY requirement ID in this feature list ({', '.join([r['id'] for r in fc_reqs])}) is explicitly tagged in at least one User Story title.
4. User Story Title format: "[REQ-xxx, REQ-yyy] Short Story Title".
5. User Story Description format: "As a [persona], I want to [action], so that [value]".
6. Acceptance Criteria: Gherkin format (Given, When, Then).
7. Tasks: Engineering technical tasks.

Return valid JSON:
{{
  "title": "{f_title}",
  "description": "{f_desc}",
  "user_stories": [
    {{
      "requirement_id": "REQ-001, REQ-002",
      "title": "[REQ-001, REQ-002] Story Title",
      "description": "As a [persona], I want to [action], so that [value].",
      "acceptance_criteria": ["Given precondition\\nWhen action\\nThen result"],
      "story_points": 5,
      "priority": "1",
      "moscow": "Must Have",
      "release_phase": "MVP",
      "tasks": ["Task 1", "Task 2"]
    }}
  ]
}}
"""
                resp = await self.llm.call(story_prompt, provider="azure", agent_name=f"BacklogArchitect_Feature_{f_title[:15]}")
                parsed_story = extract_json_from_llm_response(resp)
                if isinstance(parsed_story, dict) and "user_stories" in parsed_story:
                    return {
                        "title": f_title,
                        "description": f_desc,
                        "user_stories": parsed_story.get("user_stories", [])
                    }
                return {
                    "title": f_title,
                    "description": f_desc,
                    "user_stories": []
                }

            story_tasks = [generate_stories_for_cluster(fc) for fc in feature_clusters]
            generated_features = await asyncio.gather(*story_tasks)
            generated_features = [f for f in generated_features if f and isinstance(f, dict)]

            consolidated_backlog = {
                "epics": [
                    {
                        "title": "Commercial Property Risk Assessment System",
                        "description": "Enterprise Line of Business intake and risk assessment platform.",
                        "features": generated_features
                    }
                ]
            }
            sanitized = self.sanitize_backlog_json(consolidated_backlog)
            print(f" [BacklogGenAgent] High-Level Backlog Generation Completed! Generated {len(generated_features)} Features with structured User Stories.")
            return sanitized

        max_retries = 2
        fallback_prompt = f"""
{skill_prompt}

ACT AS AN ENTERPRISE AGILE SOLUTION ARCHITECT.
Analyze the following document / requirements content and generate a complete Agile Engineering Backlog (Epics, Features, User Stories with Acceptance Criteria, and Tasks).

DOCUMENT CONTENT:
{compressed_trd}

Output MUST strictly adhere to standard JSON schema containing 'epics' or 'features'.
"""
        for attempt in range(max_retries):
            print(f" [BacklogArchitect] Structuring backlog from TRD ({len(trd_content)} chars)... (Attempt {attempt+1}/{max_retries})")
            response = await self.llm.call(fallback_prompt, provider="azure", agent_name="BacklogArchitect")
            print(f" [BacklogArchitect] LLM response received. Attempting JSON parse...")

            from utils.json_extractor import extract_json_from_llm_response
            parsed = extract_json_from_llm_response(response)

            if isinstance(parsed, dict) and "error" not in parsed:
                parsed = self.sanitize_backlog_json(parsed)
                num_items = len(parsed.get('epics', [])) or len(parsed.get('features', []))
                print(f" [BacklogArchitect] SUCCESS: Parsed & sanitized backlog from LLM response ({num_items} top-level nodes).")
                return parsed
            
            print(f" [BacklogArchitect] JSON PARSE ERROR: {parsed.get('error')}")
            if attempt == max_retries - 1:
                return parsed
            continue

    def sanitize_backlog_json(self, parsed_json: dict) -> dict:
        """
        Sanitizes user story titles and descriptions across adaptive backlog structures.
        Supports both top-level 'epics' and top-level 'features'.
        """
        if not isinstance(parsed_json, dict):
            return parsed_json

        import re

        def sort_requirement_tags(req_str: str) -> str:
            """
            Parses 'REQ-012, REQ-005, REQ-006, REQ-009, REQ-010'
            and returns numerically sorted 'REQ-005, REQ-006, REQ-009, REQ-010, REQ-012'.
            """
            found_nums = re.findall(r"(?:REQ|FR)-(\d+)", str(req_str), re.I)
            if not found_nums:
                return req_str
            
            sorted_nums = sorted(list(set([int(n) for n in found_nums])))
            return ", ".join([f"REQ-{str(n).zfill(3)}" for n in sorted_nums])

        def sanitize_story(story, feature_title=""):
            if not isinstance(story, dict): return
            title = story.get("title", "")
            desc = story.get("description", "")
            raw_req_id = story.get("requirement_id") or ""
            req_id = raw_req_id.replace("FR-", "REQ-") if "FR-" in raw_req_id else raw_req_id
            
            if req_id:
                req_id = sort_requirement_tags(req_id)
            story["requirement_id"] = req_id

            # 1. Clean Title if LLM put "As a ..." in title
            if re.match(r"^As\s+an?\s+", title, re.I):
                action_match = re.search(r"I\s+want\s+to\s+([^\s,.][^,.]*?)(?:\s+so\s+that|\.|$)", title, re.I)
                if action_match:
                    clean_action = action_match.group(1).strip()
                    clean_title = clean_action[0].upper() + clean_action[1:]
                else:
                    clean_title = re.sub(r"^As\s+an?\s+[^\s,][^,]*,\s*", "", title, flags=re.I)
                    clean_title = clean_title[0].upper() + clean_title[1:] if clean_title else "User Story"
                
                if req_id and not clean_title.startswith(f"[{req_id}]") and not clean_title.startswith(req_id):
                    clean_title = f"[{req_id}] {clean_title}"
                story["title"] = clean_title
            elif req_id and "FR-" in title:
                story["title"] = title.replace("FR-", "REQ-")

            # Re-order requirement tags inside title bracket numerically
            title_text = story.get("title", "")
            bracket_match = re.search(r"^\[(.*?)\]", title_text)
            if bracket_match:
                sorted_tags = sort_requirement_tags(bracket_match.group(1))
                story["title"] = re.sub(r"^\[.*?\]", f"[{sorted_tags}]", title_text)

            # 2. Extract clean INVEST statement ONLY
            full_text = f"{story.get('title', '')}\n{desc}"
            invest_match = re.search(r"As\s+an?\s+[^\s,.][^,.]*,\s*I\s+want\s+to\s+[^\s,.][^,.]*,\s*so\s+that\s+[^\s.\n][^.\n]*", full_text, re.I)
            if invest_match:
                clean_stmt = invest_match.group(0).strip()
                clean_stmt = re.sub(r"^\*\*\s*(?:User Story|Description)[^*]*\*\*:?\s*", "", clean_stmt, flags=re.I).strip()
                story["description"] = clean_stmt

            # 3. Format Acceptance Criteria to have Given, When, Then on separate lines
            acs = story.get("acceptance_criteria", [])
            formatted_acs = []
            for ac in acs:
                if isinstance(ac, str):
                    clean_ac = ac.replace("Given ", "Given ").replace(", When ", "\nWhen ").replace(", Then ", "\nThen ").replace(" When ", "\nWhen ").replace(" Then ", "\nThen ")
                    formatted_acs.append(clean_ac)
                else:
                    formatted_acs.append(ac)
            story["acceptance_criteria"] = formatted_acs

            # 4. Contextualize generic Technical Tasks
            tasks = story.get("tasks", [])
            cleaned_tasks = []
            story_feature_context = story.get("title", "").replace(f"[{req_id}]", "").strip() or feature_title
            for task in tasks:
                task_str = task if isinstance(task, str) else (task.get("title") if isinstance(task, dict) else str(task))
                if re.match(r"^(?:Implement|Handle|Populate|Build|Create|Update)\s*$", task_str, re.I):
                    task_str = f"{task_str} {story_feature_context} component logic"
                elif re.match(r"^(?:Implement|Handle|Populate)\s+(?:backend|frontend|api|database|ui|logic|service)\s*$", task_str, re.I):
                    task_str = f"{task_str} for {story_feature_context}"
                cleaned_tasks.append(task_str)
            story["tasks"] = cleaned_tasks

        def get_story_req_num(story):
            if not isinstance(story, dict): return 999
            req_id = story.get("requirement_id") or story.get("title") or ""
            nums = re.findall(r"(?:REQ|FR)-(\d+)", str(req_id), re.I) or re.findall(r"\d+", str(req_id))
            if nums:
                try:
                    return min([int(n) for n in nums])
                except Exception:
                    return 999
            return 999

        def get_feature_min_req_num(feature):
            if not isinstance(feature, dict): return 999
            stories = feature.get("user_stories", [])
            if not stories: return 999
            return min([get_story_req_num(s) for s in stories])

        def sanitize_feature(feature):
            if not isinstance(feature, dict): return
            f_title = feature.get("title", "")
            stories = feature.get("user_stories", [])
            for story in stories:
                sanitize_story(story, f_title)
            # Sort stories numerically by requirement ID (REQ-001 -> REQ-002 -> REQ-003)
            stories.sort(key=get_story_req_num)
            feature["user_stories"] = stories

        if "epics" in parsed_json and isinstance(parsed_json["epics"], list):
            for epic in parsed_json.get("epics", []):
                if not isinstance(epic, dict): continue
                features = epic.get("features", [])
                for feature in features:
                    sanitize_feature(feature)
                features.sort(key=get_feature_min_req_num)
                epic["features"] = features
        elif "features" in parsed_json and isinstance(parsed_json["features"], list):
            features = parsed_json.get("features", [])
            for feature in features:
                sanitize_feature(feature)
            features.sort(key=get_feature_min_req_num)
            parsed_json["features"] = features

        return parsed_json

    async def generate_backlog_from_brd(self, raw_brd_text: str):
        """
        Intelligently converts a raw BRD directly into a hierarchical ADO backlog without needing a TRD.
        """
        prompt = f"""
        Analyze the following raw Business Requirements Document (BRD) and architect a comprehensive Azure DevOps hierarchical backlog directly from it.
        The backlog must strictly reflect the functional and technical requirements described in the BRD.
        
        Structure:
        - Epics: High-level business initiatives.
        - Features: Technical capabilities.
        - User Stories: Granular requirements.
        - Tasks: Specific development steps.

        STRATEGIC GUIDELINES:
        1. DISTRIBUTION: Do NOT put everything in MVP. Assign at least 30% of features to Phase 2 or Phase 3.
        2. MOSCOW: Be critical. 'Must' is only for core functionality.
        3. INDUSTRY STANDARDS (INVEST): User stories must follow the INVEST framework (Independent, Negotiable, Valuable, Estimable, Small, Testable).
        4. DESCRIPTION FORMAT: Every user story description MUST strictly follow the format: "As a [persona], I want to [action], so that [value/benefit]."
        5. ACCEPTANCE CRITERIA (BDD): Every acceptance criterion MUST strictly follow the Behavior-Driven Development (BDD) Gherkin syntax: "Given [context], When [action], Then [outcome]."

        Provide the output in the following JSON format:
        {{
          "epics": [
            {{
              "title": "",
              "features": [
                {{
                  "title": "",
                  "user_stories": [
                    {{
                      "title": "",
                      "description": "As a [persona], I want to [action], so that [value].",
                      "acceptance_criteria": [
                        "Given [context], When [action], Then [outcome]",
                        "Given [context], When [action], Then [outcome]"
                      ],
                      "story_points": 5,
                      "priority": "1",
                      "moscow": "Must/Should/Could/Won't",
                      "release_phase": "MVP/Phase 2/Phase 3",
                      "tasks": ["Task A", "Task B"]
                    }}
                  ]
                }}
              ]
            }}
          ]
        }}
        
        Raw BRD Content:
        {raw_brd_text}
        """
        print(f" [DirectBacklogArchitect] Analyzing raw BRD context: {len(raw_brd_text)} chars")
        response = await self.llm.call(prompt, provider="azure", agent_name="DirectBacklogArchitect")
        print(f" [DirectBacklogArchitect] LLM response received. Length: {len(response) if isinstance(response, str) else 'Object'} chars. Attempting JSON parse...")

        try:
            start = response.find("{")
            end = response.rfind("}") + 1
            if start == -1 or end == 0:
                print(" [DirectBacklogArchitect] ERROR: No JSON bounds `{ ... }` found in LLM response.")
                return {"error": "No JSON found in response", "raw": response}
                
            parsed = json.loads(response[start:end])
            num_epics = len(parsed.get('epics', []))
            print(f" [DirectBacklogArchitect] SUCCESS: Successfully parsed {num_epics} Epics from raw BRD.")
            return parsed
        except Exception as e:
            print(f" [DirectBacklogArchitect] JSON PARSE ERROR: {str(e)}")
            print(f"--- RAW LLM RESPONSE PREVIEW (First 500 chars) ---")
            print(response[:500] if isinstance(response, str) else str(response))
            print("--------------------------------------------------")
            return {"error": f"Failed to parse LLM response: {str(e)}", "raw": response}

    async def generate_stories_for_epic(self, epic_data: dict):
        """
        Decomposes an existing ADO Epic or Feature into Features, User Stories, and Tasks.
        """
        prompt = f"""
        Act as a Senior Agile Business Analyst. You have been given an existing Azure DevOps Epic or Feature.
        Your task is to decompose this item into a structured hierarchy of Features (if it's an Epic), User Stories, and Tasks.
        
        Input Item:
        Title: {epic_data.get('title')}
        Type: {epic_data.get('type')}
        Description: {epic_data.get('description', 'No description provided')}
        
        Return the output strictly in the following JSON format:
        {{
            "epics": [
                {{
                    "id": "E-01",
                    "title": "{epic_data.get('title')}",
                    "description": "...",
                    "features": [
                        {{
                            "id": "F-01",
                            "title": "...",
                            "description": "...",
                            "user_stories": [
                                {{
                                    "id": "US-01",
                                    "title": "...",
                                    "description": "...",
                                    "acceptance_criteria": ["..."],
                                    "tasks": [
                                        {{"title": "...", "estimated_hours": 4}}
                                    ]
                                }}
                            ]
                        }}
                    ]
                }}
            ]
        }}
        """
        print(f" [BacklogArchitect] Generating stories for existing {epic_data.get('type')}: {epic_data.get('title')}")
        response = await self.llm.call(prompt, provider="azure", agent_name="BacklogArchitect")
        
        try:
            start = response.find("{")
            end = response.rfind("}") + 1
            return json.loads(response[start:end])
        except Exception as e:
            print(f" Error parsing generated stories: {e}")
            return {"error": "Failed to generate stories from ADO Epic."}

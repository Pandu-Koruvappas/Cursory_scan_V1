import sys
if sys.stdout and hasattr(sys.stdout, 'reconfigure'):
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass
if sys.stderr and hasattr(sys.stderr, 'reconfigure'):
    try:
        sys.stderr.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass

import uvicorn
from services.db_service import init_db, get_db
from models.models import Document, Analysis, Approval, ProjectStateModel
from agents.extraction import ExtractionAgent
from agents.analysis import AnalysisAgent
from agents.functional_spec import FunctionalSpecAgent
from agents.context_agent import ContextAgent
from agents.backlog_gen import BacklogGenAgent
from typing import Optional, Dict
from pydantic import BaseModel
from agents.approval import ApprovalAgent
from agents.automation import AutomationAgent
from agents.analytics_agent import AnalyticsAgent
from services.orchestrator import orchestrator
from services.storage_service import storage_service
from services.email_service import email_service
from agents.knowledge_agent import KnowledgeAgent
from agents.ado_query_agent import ADOQueryAgent
from agents.router_agent import RouterAgent
from agents.test_case_agent import TestCaseAgent

# Import new LangGraph orchestration
from graph.workflow import app as swarm_graph

from sqlalchemy.orm import Session
from dotenv import load_dotenv
load_dotenv(override=True)
from fastapi import FastAPI, UploadFile, File, HTTPException, Depends, Request, Form
from fastapi.middleware.cors import CORSMiddleware
import os
import uuid
import json
import aiofiles
import fitz # PyMuPDF
import markdown
from fastapi.responses import JSONResponse, HTMLResponse, Response, StreamingResponse

PDF_MIME_TYPE = "application/pdf"

class ADOQueryRequest(BaseModel):
    query: str

app = FastAPI(title="BA Agent Pro API")

# Enable CORS for frontend integration
allowed_origins = [
    "http://localhost:5173",
    "http://localhost:8000",
    "https://icy-rock-06fe5d40f.7.azurestaticapps.net"
]
env_origins = os.getenv("FRONTEND_URL")
if env_origins:
    allowed_origins.extend(env_origins.split(","))
    
# Remove duplicates and '*' if credentials are True
allowed_origins = list({o.strip() for o in allowed_origins if o.strip() and o.strip() != "*"})

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize DB and Knowledge Vault on startup
@app.on_event("startup")
async def startup_event():
    try:
        init_db()
        print(" Knowledge Vault sync is currently disabled per user request...")
        # asyncio.create_task(knowledge_agent.sync_vault())
        print(" Startup sequence complete.")
    except Exception as e:
        print(f"Startup Error: {e}")

# Global Exception Handler for Debugging
@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    import traceback
    print("CRITICAL SERVER ERROR:")
    traceback.print_exc()
    return JSONResponse(
        status_code=500,
        content={"error": str(exc), "trace": traceback.format_exc()},
    )

# Initialize Agents
extraction_agent = ExtractionAgent()
analysis_agent = AnalysisAgent()
functional_spec_agent = FunctionalSpecAgent()
backlog_agent = BacklogGenAgent()
approval_agent = ApprovalAgent()
automation_agent = AutomationAgent()
context_agent = ContextAgent()
analytics_agent = AnalyticsAgent()
knowledge_agent = KnowledgeAgent()
ado_query_agent = ADOQueryAgent()
router_agent = RouterAgent()
test_case_agent = TestCaseAgent()

# MS Teams Bot Initialization
from botbuilder.core import BotFrameworkAdapter, BotFrameworkAdapterSettings
from services.teams_bot import BATeamsBot

bot_settings = BotFrameworkAdapterSettings(
    app_id=os.environ.get("MICROSOFT_APP_ID", ""),
    app_password=os.environ.get("MICROSOFT_APP_PASSWORD", "")
)
bot_adapter = BotFrameworkAdapter(bot_settings)
teams_bot = BATeamsBot()



@app.get("/project-context", responses={400: {"description": "Bad Request"}, 404: {"description": "Not Found"}, 500: {"description": "Internal Server Error"}})
async def get_project_context(db: Session = Depends(get_db)):
    context = await context_agent.get_project_context(db=db)
    return {"context": context}

@app.get("/sprint-metrics", responses={400: {"description": "Bad Request"}, 404: {"description": "Not Found"}, 500: {"description": "Internal Server Error"}})
async def get_sprint_metrics():
    metrics = await analytics_agent.get_sprint_metrics()
    return metrics

@app.get("/documents", responses={400: {"description": "Bad Request"}, 404: {"description": "Not Found"}, 500: {"description": "Internal Server Error"}})
async def get_documents(project_id: str = None, db: Session = Depends(get_db)):
    query = db.query(Document)
    if project_id:
        query = query.filter(Document.project_id == project_id)
    return query.order_by(Document.upload_date.desc()).all()

@app.get("/analyses", responses={400: {"description": "Bad Request"}, 404: {"description": "Not Found"}, 500: {"description": "Internal Server Error"}})
async def get_analyses(project_id: str = None, db: Session = Depends(get_db)):
    query = db.query(Analysis)
    if project_id:
        query = query.filter(Analysis.project_id == project_id)
    return query.order_by(Analysis.date.desc()).all()

@app.get("/ado-work-items", responses={400: {"description": "Bad Request"}, 404: {"description": "Not Found"}, 500: {"description": "Internal Server Error"}})
async def get_ado_work_items():
    """Fetches real-time work items from Azure DevOps."""
    try:
        from services.ado_service import AzureDevOpsService
        service = AzureDevOpsService()
        items = await service.get_all_work_items()
        return items
    except Exception as e:
        import logging
        logging.exception("An error occurred")
        raise HTTPException(status_code=500, detail=f"Failed to fetch live ADO items: {str(e)}")

@app.get("/ado-iterations", responses={400: {"description": "Bad Request"}, 404: {"description": "Not Found"}, 500: {"description": "Internal Server Error"}})
async def get_ado_iterations():
    try:
        from services.ado_service import AzureDevOpsService
        service = AzureDevOpsService()
        iterations = await service.get_iterations()
        return iterations
    except Exception as e:
        import logging
        logging.exception("An error occurred")
        raise HTTPException(status_code=500, detail=f"Failed to fetch iterations: {str(e)}")

@app.get("/ado-team", responses={400: {"description": "Bad Request"}, 404: {"description": "Not Found"}, 500: {"description": "Internal Server Error"}})
async def get_ado_team():
    try:
        from services.ado_service import AzureDevOpsService
        service = AzureDevOpsService()
        members = await service.get_project_members()
        return members
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch ADO team: {str(e)}")

@app.patch("/update-ado-work-item", responses={400: {"description": "Bad Request"}, 404: {"description": "Not Found"}, 500: {"description": "Internal Server Error"}})
async def update_ado_work_item(payload: dict):
    try:
        item_id = payload.get("id")
        updates = payload.get("updates")
        if not item_id or not updates:
            raise HTTPException(status_code=400, detail="Missing ID or updates")
            
        from services.ado_service import AzureDevOpsService
        service = AzureDevOpsService()
        result = await service.update_work_item(item_id, updates)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to update ADO item: {str(e)}")


@app.get("/api/telemetry", responses={400: {"description": "Bad Request"}, 404: {"description": "Not Found"}, 500: {"description": "Internal Server Error"}})
async def get_telemetry(db: Session = Depends(get_db)):
    """
    Fetches the LLMOps Telemetry data for the Admin Dashboard.
    """
    from models.models import AgentTelemetry
    logs = db.query(AgentTelemetry).order_by(AgentTelemetry.timestamp.desc()).limit(100).all()
    
    return [{
        "id": log.id,
        "timestamp": log.timestamp.isoformat(),
        "agent_name": log.agent_name,
        "provider": log.provider,
        "model_name": log.model_name,
        "latency_ms": log.latency_ms,
        "prompt_tokens": log.prompt_tokens,
        "completion_tokens": log.completion_tokens,
        "total_cost": getattr(log, "total_cost", 0.0),
        "success": log.success,
        "error_message": log.error_message
    } for log in logs]

class SprintAssignRequest(BaseModel):
    sprint_path: str
    items: list[str]

@app.get("/api/sprint-planning/backlog", responses={400: {"description": "Bad Request"}, 404: {"description": "Not Found"}, 500: {"description": "Internal Server Error"}})
async def get_sprint_backlog():
    try:
        from services.ado_service import AzureDevOpsService
        ado = AzureDevOpsService()
        items = await ado.get_unassigned_backlog()
        return {"items": items}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/sprint-planning/iterations", responses={400: {"description": "Bad Request"}, 404: {"description": "Not Found"}, 500: {"description": "Internal Server Error"}})
async def get_sprint_iterations():
    try:
        from services.ado_service import AzureDevOpsService
        ado = AzureDevOpsService()
        sprints = await ado.get_iterations()
        return {"iterations": sprints}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/sprint-planning/assign", responses={400: {"description": "Bad Request"}, 404: {"description": "Not Found"}, 500: {"description": "Internal Server Error"}})
async def assign_sprint(req: SprintAssignRequest):
    try:
        from services.ado_service import AzureDevOpsService
        ado = AzureDevOpsService()
        result = await ado.assign_to_sprint(req.sprint_path, req.items)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/ingest", responses={400: {"description": "Bad Request"}, 404: {"description": "Not Found"}, 500: {"description": "Internal Server Error"}})
async def ingest_document(
    file: UploadFile = File(...), 
    channel: str = Form("document"),
    lob: str = Form("General"),
    db: Session = Depends(get_db)
):
    import hashlib

    # 1. Compute SHA-256 file hash for deterministic Azure AI Search vector upserting
    file_bytes = await file.read()
    file_hash = hashlib.sha256(file_bytes).hexdigest()
    
    doc_id = str(uuid.uuid4())
    temp_path = f"temp_{doc_id}_{file.filename}"

    print("\n" + "="*70)
    print(f" [API: /ingest] STARTING: Full Pipeline Ingestion for '{file.filename}'")
    print(f"   - Channel  : {channel} | LOB: {lob} | DocID: {doc_id}")
    print(f"   - File Size: {len(file_bytes)} bytes")
    print(f"   - SHA-256  : {file_hash}")
    print("   - Mode     : FULL PIPELINE EXECUTION (Document Intelligence + LLM + Vector Upsert)")
    print("="*70)

    async with aiofiles.open(temp_path, "wb") as buffer:
        await buffer.write(file_bytes)
    
    try:
        # Extract content based on channel and file type
        text_content = ""
        
        if channel == "visual":
            print("INFO: Visual Channel detected. Initializing Vision Agent...")
            from services.llm_service import LLMService
            llm = LLMService()
            vision_prompt = "Describe this wireframe or requirement image in detail. Extract all UI elements, data fields, and functional interactions visible."
            text_content = await llm.generate_with_vision(temp_path, vision_prompt)
        elif channel == "meeting":
            print("INFO: Meeting Channel detected. Processing transcript...")
            async with aiofiles.open(temp_path, "r", encoding="utf-8", errors="ignore") as f:
                text_content = await f.read()
        elif channel == "text":
            print("INFO: Direct Text Channel detected.")
            async with aiofiles.open(temp_path, "r", encoding="utf-8", errors="ignore") as f:
                text_content = await f.read()
        else:
            # Deep Document Parsing (PDF, DOCX, XLSX + Embedded)
            from services.document_parser import extract_all_text
            text_content = await extract_all_text(temp_path, file.filename)

        # Clean null bytes to prevent PostgreSQL crashes
        text_content = text_content.replace("\x00", "")

        # Persistence & Orchestration
        storage_service.upload_file(temp_path, file.filename)
        orchestrator.get_or_create_project(doc_id, lob=lob)
        
        # Run context-aware extraction passing file_hash for deterministic vector keying
        print(" [API: /ingest] Triggering Orchestrator for extraction analysis...")
        orchestrator_result = await orchestrator.run_extraction(doc_id, text_content, context_type=channel, file_hash=file_hash)
        data = orchestrator_result["extraction"]
        ambiguity_report = orchestrator_result.get("ambiguity_report", {})
        
        # Check for AI Errors
        if isinstance(data, dict) and "error" in data:
            raise HTTPException(status_code=400, detail=f"Extraction Error: {data['error']} | Raw: {data.get('raw', '')[:200]}")

        # Persist Document to DB
        new_doc = Document(
            id=doc_id,
            name=file.filename,
            file_type=file.content_type,
            file_path=temp_path,
            content=text_content,
            status="ingested",
            meta={
                "file_hash": file_hash,
                "extraction": data,
                "ambiguity_report": ambiguity_report
            },
            project_id=lob
        )
        db.add(new_doc)
        db.commit()
        
        print(" [API: /ingest] COMPLETED Successfully! Full pipeline executed & Azure Search vectors upserted.")
        return {"document_id": doc_id, "extraction": data, "ambiguity_report": ambiguity_report, "file_hash": file_hash}
    except Exception as e:
        db.rollback()
        print(f" [API: /ingest] ERROR: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/traceability/{document_id}", responses={400: {"description": "Bad Request"}, 404: {"description": "Not Found"}, 500: {"description": "Internal Server Error"}})
async def get_traceability(document_id: str, db: Session = Depends(get_db)):
    from services.storage_service import storage_service

    doc = db.query(Document).filter(Document.id == document_id).first()
    project = db.query(ProjectStateModel).filter(ProjectStateModel.document_id == document_id).first()
    
    import json
    def safe_parse(val):
        if not val: return {}
        if isinstance(val, (dict, list)): return val
        if isinstance(val, str):
            try: return json.loads(val)
            except Exception: return {}
        return {}

    extraction = storage_service.load_json_artifact(document_id, "extraction") or (safe_parse(doc.meta.get('extraction')) if doc and doc.meta else {}) or (safe_parse(project.extraction) if project else {})
    backlog = storage_service.load_json_artifact(document_id, "backlog") or (safe_parse(doc.meta.get('backlog')) if doc and doc.meta else {}) or (safe_parse(project.backlog) if project else {})
    test_cases_data = storage_service.load_json_artifact(document_id, "test_cases") or (safe_parse(doc.meta.get('test_cases')) if doc and doc.meta else {}) or (safe_parse(project.test_cases) if project else {})

    test_cases_list = []
    if isinstance(test_cases_data, dict):
        test_cases_list = test_cases_data.get('test_cases', [])
    elif isinstance(test_cases_data, list):
        test_cases_list = test_cases_data

    epics = []
    if isinstance(backlog, dict):
        epics = backlog.get('epics', [])
    elif isinstance(backlog, list):
        epics = backlog

    matrix = []

    req_list = extraction.get("functional_requirements", []) if isinstance(extraction, dict) else []
    if not req_list:
        # Fallback: Derive requirements from stories
        for epic in epics:
            for feat in epic.get('features', []):
                for story in feat.get('user_stories', []):
                    req_list.append({
                        "id": story.get('requirement_id') or story.get('id') or 'FR-001',
                        "description": story.get('source_requirement') or story.get('description') or story.get('title')
                    })

    for idx, fr in enumerate(req_list, 1):
        fr_id = fr.get("id") or f"FR-{String(idx).zfill(3)}" if hasattr(str, 'zfill') else f"FR-{idx}"
        fr_desc = fr.get("description") or fr.get("title") or "Functional Specification Requirement"

        linked_stories = []
        linked_test_cases = []
        similar_ado_items = []

        # Find linked User Stories in Backlog
        for epic in epics:
            for feat in epic.get("features", []):
                for story in feat.get("user_stories", []):
                    if story.get("requirement_id") == fr_id or fr_id in str(story.get("description", "")) or fr_id in str(story.get("title", "")):
                        remote_id = story.get("remote_id")
                        linked_stories.append({
                            "id": story.get("id"),
                            "title": story.get("title"),
                            "remote_id": remote_id,
                            "moscow": story.get("moscow", "Must Have")
                        })
                        if remote_id:
                            similar_ado_items.append(f"ADO #{remote_id}: {story.get('title')}")

        # Find linked Test Cases
        for tc in test_cases_list:
            tc_id = tc.get("test_case_id") or tc.get("id") or "TC-001"
            tc_title = tc.get("title") or tc.get("name") or "Test Scenario"
            req_ref = tc.get("requirement_id") or tc.get("user_story_id") or ""
            if req_ref == fr_id or fr_id in str(tc.get("description", "")) or any(s['title'] in tc_title for s in linked_stories):
                linked_test_cases.append({
                    "id": tc_id,
                    "title": tc_title,
                    "priority": tc.get("priority", "High")
                })

        # Fallback for ADO items if unsynced
        if not similar_ado_items and linked_stories:
            similar_ado_items.append(f"Similar Story: {linked_stories[0]['title']}")
        elif not similar_ado_items:
            similar_ado_items.append("Pending Sync (Azure DevOps)")

        matrix.append({
            "source_id": fr_id,
            "source_desc": fr_desc,
            "source_type": "Functional Requirement",
            "linked_stories": linked_stories,
            "linked_test_cases": linked_test_cases,
            "similar_ado_items": similar_ado_items
        })

    return {"document_id": document_id, "matrix": matrix}

@app.get("/knowledge/search", responses={400: {"description": "Bad Request"}, 404: {"description": "Not Found"}, 500: {"description": "Internal Server Error"}})
async def search_knowledge(q: str):
    """
    Semantic search across organizational memory.
    """
    from agents.knowledge_agent import KnowledgeAgent
    ka = KnowledgeAgent()
    results = await ka.retrieve_relevant_context(q, n_results=5)
    return {"results": results}

class PlaywrightExportPayload(BaseModel):
    document_id: str
    filename: Optional[str] = None
    script_code: str

@app.post("/playwright/export", responses={400: {"description": "Bad Request"}, 404: {"description": "Not Found"}, 500: {"description": "Internal Server Error"}})
async def export_playwright_script(payload: PlaywrightExportPayload):
    """
    Pushes generated Playwright TypeScript test scripts into repository tests directory & Azure Storage.
    """
    try:
        from services.storage_service import storage_service
        import os
        from datetime import datetime
        
        filename = payload.filename or f"e2e_{payload.document_id[:8]}.spec.ts"
        if not filename.endswith(".ts") and not filename.endswith(".js"):
            filename += ".spec.ts"
            
        tests_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "playwright_tests"))
        os.makedirs(tests_dir, exist_ok=True)
        
        file_path = os.path.join(tests_dir, filename)
        header = f"// [BA AGENT AUTO-GENERATED PLAYWRIGHT SPEC]\n// Document ID: {payload.document_id}\n// Pushed Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
        full_code = header + payload.script_code if not payload.script_code.startswith("// [BA AGENT") else payload.script_code

        async with aiofiles.open(file_path, "w", encoding="utf-8") as f:
            await f.write(full_code)
            
        storage_service.save_json_artifact(payload.document_id, "playwright_script", {
            "filename": filename,
            "script": full_code,
            "pushed_at": datetime.now().isoformat()
        })
        
        return {
            "success": True,
            "filename": filename,
            "file_path": file_path,
            "message": f"Successfully pushed Playwright test spec '{filename}' to repository."
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Playwright Export Failed: {str(e)}")

@app.post("/storage/sync-all-past-analyses", responses={400: {"description": "Bad Request"}, 404: {"description": "Not Found"}, 500: {"description": "Internal Server Error"}})
async def sync_all_past_analyses(db: Session = Depends(get_db)):
    """
    Backfills and synchronizes all past completed analysis sessions from database to Azure Blob Storage.
    """
    from services.storage_service import storage_service
    
    projects = db.query(ProjectStateModel).all()
    analyses = db.query(Analysis).all()
    docs = db.query(Document).all()

    synced_count = 0

    for p in projects:
        doc_id = p.document_id
        if not doc_id: continue
        for field, art in [('extraction', 'extraction'), ('gaps', 'gaps'), ('trd', 'functional_spec'), ('functional_spec', 'functional_spec'), ('backlog', 'backlog')]:
            val = getattr(p, field, None)
            if val:
                storage_service.save_json_artifact(doc_id, art, val)
                synced_count += 1

    for a in analyses:
        doc_id = a.document_id
        if not doc_id: continue
        for field, art in [('extraction', 'extraction'), ('gaps', 'gaps'), ('functional_spec', 'functional_spec'), ('backlog', 'backlog'), ('test_cases', 'test_cases')]:
            val = getattr(a, field, None)
            if val:
                storage_service.save_json_artifact(doc_id, art, val)
                synced_count += 1

    for d in docs:
        doc_id = d.id
        if d.meta and isinstance(d.meta, dict):
            for k in ['extraction', 'gaps', 'functional_spec', 'trd', 'backlog', 'test_cases']:
                val = d.meta.get(k)
                if val:
                    art_name = 'functional_spec' if k == 'trd' else k
                    storage_service.save_json_artifact(doc_id, art_name, val)
                    synced_count += 1

    return {
        "success": True,
        "message": f"Successfully synchronized {synced_count} historical artifacts across {len(projects)} projects, {len(analyses)} analyses, and {len(docs)} documents to Azure Storage.",
        "artifacts_synced": synced_count
    }

@app.get("/playwright/import", responses={400: {"description": "Bad Request"}, 404: {"description": "Not Found"}, 500: {"description": "Internal Server Error"}})
async def import_playwright_specs():
    """
    Scans and imports existing & pushed Playwright .spec.ts test scripts from repository tests folder.
    """
    import os
    import re
    from datetime import datetime
    
    tests_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "playwright_tests"))
    os.makedirs(tests_dir, exist_ok=True)
    
    # Seed a baseline existing repository spec if empty
    sample_path = os.path.join(tests_dir, "existing_user_auth.spec.ts")
    if not os.path.exists(sample_path) and len(os.listdir(tests_dir)) == 0:
        sample_code = """import { test, expect } from '@playwright/test';

// Existing Repository Spec: User Authentication Flow
test('Existing Test: Customer Login and Navigation', async ({ page }) => {
  await page.goto('https://app.valuemomentum.com/login');
  await page.fill('input[name="username"]', 'admin@valuemomentum.com');
  await page.fill('input[name="password"]', 'SecurePass123!');
  await page.click('button[type="submit"]');
  await expect(page).toHaveURL('https://app.valuemomentum.com/dashboard');
});
"""
        try:
            async with aiofiles.open(sample_path, "w", encoding="utf-8") as f:
                await f.write(sample_code)
        except Exception:
            pass

    specs = []
    for root, _, files in os.walk(tests_dir):
        for file in files:
            if file.endswith(".ts") or file.endswith(".js"):
                full_path = os.path.join(root, file)
                try:
                    async with aiofiles.open(full_path, "r", encoding="utf-8", errors="ignore") as f:
                        content = await f.read()
                        
                    test_titles = re.findall(r"test\s*\(\s*['\"]([^'\"]+)['\"]", content)
                    locators = re.findall(r"page\.(?:locator|fill|click|getByRole|getByText)\s*\(\s*['\"]([^'\"]+)['\"]", content)
                    is_pushed = "[BA AGENT AUTO-GENERATED PLAYWRIGHT SPEC]" in content
                    stat = os.stat(full_path)
                    
                    specs.append({
                        "filename": file,
                        "path": full_path,
                        "test_count": len(test_titles),
                        "test_titles": test_titles,
                        "locators": list(set(locators))[:5],
                        "is_pushed_from_ba_agent": is_pushed,
                        "file_size": f"{stat.st_size / 1024:.1f} KB",
                        "modified_at": datetime.fromtimestamp(stat.st_mtime).strftime('%Y-%m-%d %H:%M'),
                        "content": content
                    })
                except Exception as e:
                    print(f"WARN: Error reading spec file {file}: {e}")
                    
    return {"specs": specs, "total_files": len(specs)}

@app.get("/playwright/download/{document_id}", responses={400: {"description": "Bad Request"}, 404: {"description": "Not Found"}, 500: {"description": "Internal Server Error"}})
async def download_playwright_script(document_id: str, db: Session = Depends(get_db)):
    """
    Downloads Playwright TypeScript test file attachment.
    """
    from services.storage_service import storage_service
    from fastapi.responses import Response
    
    artifact = storage_service.load_json_artifact(document_id, "playwright_script")
    script_code = ""
    filename = f"playwright_test_{document_id[:8]}.spec.ts"
    
    if isinstance(artifact, dict):
        script_code = artifact.get("script", "")
        filename = artifact.get("filename", filename)
    elif isinstance(artifact, str):
        script_code = artifact
        
    if not script_code:
        tc_art = storage_service.load_json_artifact(document_id, "test_cases")
        if isinstance(tc_art, dict):
            script_code = tc_art.get("playwright_script", "")
            
    if not script_code:
        script_code = f"import {{ test, expect }} from '@playwright/test';\n\ntest('Sample E2E Test for {document_id}', async ({{ page }}) => {{\n  await page.goto('http://localhost:3000');\n}});"

    return Response(
        content=script_code,
        media_type="application/typescript",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )

@app.get("/reports/traceability/{document_id}", responses={400: {"description": "Bad Request"}, 404: {"description": "Not Found"}, 500: {"description": "Internal Server Error"}})
async def download_report(document_id: str, db: Session = Depends(get_db)):
    """
    Generates and returns a PDF Traceability Report.
    """
    from services.report_service import ReportService
    from services.audit_service import AuditService
    
    matrix_data = await get_traceability(document_id, db)
    audit_logs = AuditService.get_logs(document_id)
    pdf_buffer = ReportService.generate_traceability_report(matrix_data, audit_logs)
    
    from fastapi.responses import StreamingResponse
    return StreamingResponse(
        pdf_buffer, 
        media_type=PDF_MIME_TYPE,
        headers={"Content-Disposition": f"attachment; filename=Traceability_Report_{document_id}.pdf"}
    )

@app.get("/audit/logs/{document_id}", responses={400: {"description": "Bad Request"}, 404: {"description": "Not Found"}, 500: {"description": "Internal Server Error"}})
async def get_audit_logs(document_id: str):
    """
    Retrieves the immutable audit trail for a project.
    """
    from services.audit_service import AuditService
    logs = AuditService.get_logs(document_id)
    return {"document_id": document_id, "logs": logs}

@app.get("/analysis/{analysis_id}", responses={400: {"description": "Bad Request"}, 404: {"description": "Not Found"}, 500: {"description": "Internal Server Error"}})
async def get_analysis_details(analysis_id: str, db: Session = Depends(get_db)):
    analysis = db.query(Analysis).filter(Analysis.id == analysis_id).first()
    if not analysis:
        raise HTTPException(status_code=404, detail="Analysis not found")

    from utils.json_extractor import extract_json_from_llm_response
    from services.storage_service import storage_service

    res_dict = {
        "id": analysis.id,
        "document_id": analysis.document_id,
        "quality_score": getattr(analysis, 'quality_score', 0.0),
        "created_at": str(getattr(analysis, 'created_at', '')) if getattr(analysis, 'created_at', None) else None,
        "results": dict(analysis.results) if isinstance(analysis.results, dict) else {},
        "functional_spec": getattr(analysis, 'functional_spec', None),
        "backlog": getattr(analysis, 'backlog', None),
        "test_cases": getattr(analysis, 'test_cases', None)
    }

    doc_id = analysis.document_id
    if doc_id:
        stored_tc = storage_service.load_json_artifact(doc_id, "test_cases")
        if stored_tc:
            res_dict["test_cases"] = stored_tc
            if isinstance(res_dict["results"], dict):
                res_dict["results"]["test_cases"] = stored_tc

        stored_bl = storage_service.load_json_artifact(doc_id, "backlog")
        if stored_bl:
            res_dict["backlog"] = stored_bl
            if isinstance(res_dict["results"], dict):
                res_dict["results"]["backlog"] = stored_bl

        stored_spec = storage_service.load_json_artifact(doc_id, "functional_spec")
        if stored_spec:
            res_dict["functional_spec"] = stored_spec
            if isinstance(res_dict["results"], dict):
                res_dict["results"]["functional_spec"] = stored_spec

    # Auto-repair string JSON artifacts in results and top-level fields
    for field in ["test_cases", "backlog", "functional_spec"]:
        val = res_dict.get(field)
        if isinstance(val, str):
            parsed = extract_json_from_llm_response(val)
            if isinstance(parsed, (dict, list)) and "error" not in parsed:
                res_dict[field] = parsed

        if isinstance(res_dict.get("results"), dict):
            inner_val = res_dict["results"].get(field)
            if isinstance(inner_val, str):
                parsed = extract_json_from_llm_response(inner_val)
                if isinstance(parsed, (dict, list)) and "error" not in parsed:
                    res_dict["results"][field] = parsed

    return res_dict


@app.post("/analyze", responses={400: {"description": "Bad Request"}, 404: {"description": "Not Found"}, 500: {"description": "Internal Server Error"}})
async def analyze_requirements(payload: dict, db: Session = Depends(get_db)):
    doc_id = payload.get("document_id")
    enabled_modules = payload.get("enabled_modules")
    
    print("\n" + "="*50)
    print(f" [API: /analyze] STARTING: Analyzing Document {doc_id}")
    print(f"   - Enabled Modules: {enabled_modules}")
    print("="*50)
    
    # Trigger LangGraph for Extraction & Gaps
    try:
        print(" [API: /analyze] Triggering LangGraph Swarm...")
        
        # We start a new thread for this analysis
        analysis_id = str(uuid.uuid4())
        config = {"configurable": {"thread_id": analysis_id}}
        
        doc = db.query(Document).filter(Document.id == doc_id).first()
        lob = payload.get("lob") or payload.get("project_id") or (doc.project_id if doc and doc.project_id != "guest" else None) or "Commercial Property"
        if doc and payload.get("lob"):
            doc.project_id = payload.get("lob")
            try: db.commit()
            except Exception: pass
            
        initial_state = {"analysis_id": analysis_id, "original_text": doc.content, "context_type": "document", "lob": lob}
        
        # Run graph until it hits the first interrupt (spec)
        state_result = await swarm_graph.ainvoke(initial_state, config=config)
        
        results = {
            "extraction": state_result.get("extraction"),
            "gaps": state_result.get("gaps"),
            "quality_score": state_result.get("extraction", {}).get("quality_score", 0.0),
            "diagram": state_result.get("diagram"),
            "critic_review": state_result.get("critic_review"),
            "reviews": state_result.get("reviews")
        }
        
        # 2. Persist to DB
        doc = db.query(Document).filter(Document.id == doc_id).first()
        project_id = doc.project_id if doc else None
        
        new_analysis = Analysis(
            id=analysis_id,
            title=f"Intelligent Analysis for Doc {doc_id}",
            results=results, # Legacy compatibility
            extraction=state_result.get("extraction"),
            gaps=state_result.get("gaps"),
            diagram=state_result.get("diagram"),
            critic_review=state_result.get("critic_review"),
            reviews=state_result.get("reviews"),
            document_id=doc_id,
            project_id=project_id,
            status="completed"
        )
        db.add(new_analysis)
        
        # Update Document status
        doc = db.query(Document).filter(Document.id == doc_id).first()
        if doc:
            doc.status = "analyzed"
            
        db.commit()
        return {
            "analysis_id": analysis_id, 
            "results": results,
            "quality_score": results.get("quality_score", 0.0)
        }
        
    except Exception as e:
        db.rollback()
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Orchestrator Analysis Error: {str(e)}")

@app.post("/generate-functional-spec", responses={400: {"description": "Bad Request"}, 404: {"description": "Not Found"}, 500: {"description": "Internal Server Error"}})
async def generate_functional_spec(payload: dict, db: Session = Depends(get_db)):
    analysis_id = payload.get("analysis_id")
    
    print("\n" + "="*50)
    print(f" [API: /generate-functional-spec] STARTING: Functional Spec Generation for Analysis ID {analysis_id}")
    print("="*50)
    
    analysis = db.query(Analysis).filter(Analysis.id == analysis_id).first()
    if not analysis:
        print(" [API: /generate-functional-spec] ERROR: Analysis not found.")
        raise HTTPException(status_code=404, detail="Analysis not found")
        
    doc = db.query(Document).filter(Document.id == analysis.document_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Source document not found for this analysis. Please re-ingest.")
    
    # Use orchestrator or LangGraph for Functional Spec generation
    deep_analysis_enabled = payload.get("deep_analysis_enabled", False)
    
    if deep_analysis_enabled:
        from agents.deep_analysis_graph import deep_analysis_app
        import json
        print(" Invoking LangGraph Deep Analysis mode...")
        
        extraction_context = str(doc.meta.get("extraction", doc.content[:100000])) if doc.meta else doc.content[:100000]
        initial_state = {
            "document_id": doc.id,
            "extraction_context": extraction_context,
            "spec_draft": "",
            "messages": [],
            "iteration_count": 0,
            "is_approved": False
        }
        
        result = await deep_analysis_app.ainvoke(initial_state)
        spec_data = {"functional_spec": result.get("spec_draft", {})}
        if isinstance(spec_data["functional_spec"], str):
            try:
                spec_data["functional_spec"] = json.loads(spec_data["functional_spec"])
            except Exception:
                pass
    else:
        # Resume the Main LangGraph Swarm
        print(" Resuming LangGraph Swarm for Functional Spec...")
        config = {"configurable": {"thread_id": analysis_id}}
        try:
            state_result = await swarm_graph.ainvoke(None, config=config)
            spec_data = {
                "functional_spec": state_result.get("functional_spec"),
                "reviews": state_result.get("reviews"),
                "critic_review": state_result.get("critic_review")
            }
        except Exception as e:
            print(f" LangGraph state lost. Falling back to direct node invocation. ({str(e)})")
            from graph.nodes import spec_node, reviews_node
            state_mock = {
                "extraction": analysis.results.get("extraction", {}) if analysis and analysis.results else {},
                "original_text": analysis.original_text if analysis else ""
            }
            spec_res = await spec_node(state_mock)
            state_mock.update(spec_res)
            reviews_res = await reviews_node(state_mock)
            
            spec_data = {
                "functional_spec": spec_res.get("functional_spec"),
                "reviews": reviews_res.get("reviews"),
                "critic_review": spec_res.get("critic_review")
            }
    
    # Update analysis with Functional Spec content
    if analysis:
        if analysis.results is not None:
            results_copy = dict(analysis.results)
            results_copy["functional_spec"] = spec_data.get("functional_spec")
            results_copy["reviews"] = spec_data.get("reviews")
            results_copy["critic_review"] = spec_data.get("critic_review")
            analysis.results = results_copy
            
        analysis.functional_spec = spec_data.get("functional_spec")
        analysis.reviews = spec_data.get("reviews")
        analysis.critic_review = spec_data.get("critic_review")
        db.commit()
    
    print(" [API: /generate-functional-spec] COMPLETED Successfully!")
    return spec_data

@app.post("/generate-backlog", responses={400: {"description": "Bad Request"}, 404: {"description": "Not Found"}, 500: {"description": "Internal Server Error"}})
async def generate_backlog(payload: dict, db: Session = Depends(get_db)):
    analysis_id = payload.get("analysis_id")
    spec_content = payload.get("functional_spec")
    
    print("\n" + "="*50)
    print(" [API: /generate-backlog] STARTING: Backlog Generation")
    print(f"   - Analysis ID: {analysis_id}")
    print("="*50)
    
    document_id = payload.get("document_id")
    if not document_id and analysis_id:
        analysis = db.query(Analysis).filter(Analysis.id == analysis_id).first()
        if analysis:
            document_id = analysis.document_id
            
    if not document_id:
        print(" [API: /generate-backlog] ERROR: document_id not found.")
        raise HTTPException(status_code=400, detail="Missing document_id or analysis_id")
        
    print(" [API: /generate-backlog] Triggering LangGraph Swarm...")
    
    config = {"configurable": {"thread_id": analysis_id}}
    try:
        state_result = await swarm_graph.ainvoke(None, config=config)
        backlog_data = state_result.get("backlog")
    except Exception as e:
        print(f" LangGraph state lost. Falling back to direct node invocation. ({str(e)})")
        from graph.nodes import backlog_node
        analysis = db.query(Analysis).filter(Analysis.id == analysis_id).first()
        reviews = {}
        if analysis:
            if analysis.reviews:
                reviews = analysis.reviews
            elif analysis.results:
                reviews = analysis.results.get("reviews", {})
                
        state_mock = {
            "functional_spec": spec_content,
            "reviews": reviews
        }
        backlog_res = await backlog_node(state_mock)
        backlog_data = backlog_res.get("backlog")
    
    critic_review = None
    if analysis_id:
        analysis = db.query(Analysis).filter(Analysis.id == analysis_id).first()
        if analysis:
            if analysis.results is not None:
                results_copy = dict(analysis.results)
                results_copy["backlog"] = backlog_data
                analysis.results = results_copy
                
            analysis.backlog = backlog_data
            critic_review = analysis.critic_review
            db.commit()

    print(" [API: /generate-backlog] COMPLETED Successfully!")
    return {"backlog": backlog_data, "critic_review": critic_review}

@app.post("/generate-backlog-direct", responses={400: {"description": "Bad Request"}, 404: {"description": "Not Found"}, 500: {"description": "Internal Server Error"}})
async def generate_backlog_direct(
    file: UploadFile = File(...), 
    db: Session = Depends(get_db)
):
    """
    Directly converts a raw BRD file into an ADO Backlog and Test Cases, skipping the Functional Spec process.
    """
    print("\n" + "="*50)
    print(f" [API: /generate-backlog-direct] STARTING: Quick Backlog for '{file.filename}'")
    print("="*50)
    
    from pathlib import Path

    doc_id = uuid.uuid4()

    # Allow only expected file extensions
    original_filename = file.filename or ""
    extension = Path(original_filename).suffix.lower()

    allowed_extensions = {".pdf", ".docx", ".txt", ".pptx", "xlsx"}

    if extension not in allowed_extensions:
        raise HTTPException(
            status_code=400,
            detail="Unsupported file type"
        )

    temp_dir = Path("temp")
    temp_dir.mkdir(exist_ok=True)

    temp_path = temp_dir / f"temp_direct_{doc_id}{extension}"

    async with aiofiles.open(temp_path, "wb") as buffer:
        await buffer.write(await file.read())
        
    try:
        # 1. Extract raw text
        text_content = ""
        is_pdf = file.content_type == "application/pdf" or file.filename.lower().endswith(".pdf")
        if is_pdf:
            try:
                from services.adi_service import AzureDocIntelService
                adi = AzureDocIntelService()
                text_content = adi.extract_text(temp_path)
            except Exception:
                doc = fitz.open(temp_path)
                for page in doc: text_content += page.get_text()
                doc.close()
        else:
            async with aiofiles.open(temp_path, "r", encoding="utf-8", errors="ignore") as f:
                text_content = await f.read()
                
        # 2. Token Optimization & Compression
        import re
        # Clean basic whitespace bloat
        text_content = re.sub(r'\n{3,}', '\n\n', text_content)
        text_content = re.sub(r' {3,}', '  ', text_content)
        
        # If document is massive (>30,000 chars), intelligently compress it first
        if len(text_content) > 30000:
            print(f" [Token Optimization] Document is massive ({len(text_content)} chars). Condensing via fast model...")
            from services.llm_service import LLMService
            llm = LLMService()
            # We take up to ~80k chars to avoid hitting 4o-mini context limits
            compress_prompt = f"You are a Business Analyst. Extract ONLY the functional, technical, and business requirements from this raw document. Ignore boilerplate, Table of Contents, introductions, and filler. Output a dense, exhaustive bulleted list of requirements:\n\n{text_content[:80000]}"
            compressed_text = await llm.call(compress_prompt, provider="azure")
            if "Error" not in compressed_text:
                text_content = compressed_text
                print(f" [Token Optimization] Compressed down to {len(text_content)} chars!")
                
        # 3. Generate Backlog
        print(" [Direct Mode] Generating Backlog from BRD...")
        backlog_agent = BacklogGenAgent()
        backlog_data = await backlog_agent.generate_backlog_from_brd(text_content)
        
        if "error" in backlog_data:
            raise HTTPException(status_code=500, detail=backlog_data["error"])
            
        print(" [API: /generate-backlog-direct] COMPLETED Successfully!")
        return {
            "backlog": backlog_data,
            "test_cases": "Test cases are generating in the background..."
        }
    except Exception as e:
        import traceback
        traceback.print_exc()
        print(f" [API: /generate-backlog-direct] ERROR: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Direct Backlog Gen Error: {str(e)}")
    finally:
        if os.path.exists(temp_path):
            os.remove(temp_path)

@app.post("/generate-testcases-direct", responses={400: {"description": "Bad Request"}, 404: {"description": "Not Found"}, 500: {"description": "Internal Server Error"}})
async def generate_testcases_direct(payload: dict):
    """
    Generates test cases directly from a provided backlog JSON.
    """
    print("\n" + "="*50)
    print(" [API: /generate-testcases-direct] STARTING: Background Test Cases")
    try:
        backlog_data = payload.get("backlog")
        functional_spec = payload.get("functional_spec") or payload.get("trd") or ""
        doc_id = payload.get("document_id") or payload.get("doc_id")
        
        if not functional_spec and doc_id:
            loaded_spec = storage_service.load_json_artifact(doc_id, "functional_spec")
            if loaded_spec:
                functional_spec = loaded_spec

        if not backlog_data:
            raise HTTPException(status_code=400, detail="Missing backlog data")
            
        test_agent = TestCaseAgent()
        backlog_str = json.dumps(backlog_data) if isinstance(backlog_data, (dict, list)) else str(backlog_data)
        spec_str = json.dumps(functional_spec) if isinstance(functional_spec, (dict, list)) else str(functional_spec)

        test_cases = await test_agent.draft_test_cases(backlog_json=backlog_str, functional_spec=spec_str)
        
        if doc_id:
            storage_service.save_json_artifact(doc_id, "test_cases", test_cases)

        print(" [API: /generate-testcases-direct] COMPLETED Successfully!")
        return {"test_cases": test_cases}
    except Exception as e:
        print(f" [API: /generate-testcases-direct] ERROR: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Test Case Gen Error: {str(e)}")

@app.post("/prepare-approval", responses={400: {"description": "Bad Request"}, 404: {"description": "Not Found"}, 500: {"description": "Internal Server Error"}})
async def prepare_approval(payload: dict, db: Session = Depends(get_db)):
    print(" [API: /prepare-approval] Preparing...")
    analysis_id = payload.get("analysis_id")
    functional_spec = payload.get("functional_spec")
    backlog = payload.get("backlog")
    
    approval_data = approval_agent.prepare_approval_package(functional_spec, backlog)
    
    # Persist Approval to DB
    approval_id = str(uuid.uuid4())
    new_approval = Approval(
        id=approval_id,
        analysis_id=analysis_id,
        status="pending",
        results_summary=backlog
    )
    db.add(new_approval)
    db.commit()
    
    return {"approval_id": approval_id, "package": approval_data}

@app.post("/request-approval", responses={400: {"description": "Bad Request"}, 404: {"description": "Not Found"}, 500: {"description": "Internal Server Error"}})
async def request_approval(payload: dict, request: Request, db: Session = Depends(get_db)):
    print(" [API: /request-approval] Processing request...")
    analysis_id = payload.get("analysis_id")
    backlog = payload.get("backlog")
    reviewer_email = payload.get("reviewer_email")
    
    # 1. Create a unique approval session
    approval_id = str(uuid.uuid4())
    new_approval = Approval(
        id=approval_id,
        analysis_id=analysis_id,
        status="pending",
        results_summary=backlog
    )
    db.add(new_approval)
    db.commit()
    
    # 2. Prepare the email with Functional Spec content
    # We fetch the Functional Spec and Persona Reviews from the analysis record
    analysis = db.query(Analysis).filter(Analysis.id == analysis_id).first()
    spec_text = "Backlog ready for review."
    persona_reviews_text = "No Persona Reviews found."
    if analysis and analysis.results:
        spec_text = analysis.results.get("functional_spec", "No Functional Spec found.")
        reviews = analysis.results.get("reviews", {})
        if reviews:
            persona_reviews_text = "<ul>" + "".join([f"<li><strong>{k}</strong>: {v}</li>" for k, v in reviews.items()]) + "</ul>"

    # Convert Markdown Functional Spec to HTML for the email for better formatting
    functional_spec_html = markdown.markdown(spec_text[:2000] + "\n\n*(Truncated for email)*" if len(spec_text) > 2000 else spec_text, extensions=['extra', 'smarty'])
    
    backlog_json_str = json.dumps(backlog, indent=2)
    if len(backlog_json_str) > 2000:
        backlog_json_str = backlog_json_str[:2000] + "\n\n... (Truncated for email)"
    
    review_link = f"{request.base_url}review-approval/{approval_id}"
    email_body = f"""
    <div style="font-family: sans-serif; color: #333;">
        <h2 style="color: #00f2ff;">Strategic Backlog Review Required</h2>
        <p>A new engineering backlog has been generated and requires your formal approval before being synchronized to Azure DevOps.</p>
        <hr style="border: 0; border-top: 1px solid #eee;"/>
        
        <h3>1. Proposed Technical Scope (Functional Spec):</h3>
        <div style="background: #f9f9f9; padding: 15px; border-left: 4px solid #00f2ff;">
            {functional_spec_html}
        </div>
        
        <h3>2. Persona Reviews (Risk & Governance):</h3>
        <div style="background: #f9f9f9; padding: 15px; border-left: 4px solid #ff00f2;">
            {persona_reviews_text}
        </div>
        
        <h3>3. Backlog JSON (Epics, Features, Stories):</h3>
        <div style="background: #2b2b2b; color: #a9dc76; padding: 15px; border-radius: 5px; overflow-x: auto;">
            <pre style="margin: 0; font-family: monospace;">{backlog_json_str}</pre>
        </div>
        
        <hr style="border: 0; border-top: 1px solid #eee; margin-top: 20px;"/>
        <p>Please click the button below to review, approve, or reject this backlog.</p>
        <a href="{review_link}" style="background: #00f2ff; color: #121212; padding: 12px 24px; text-decoration: none; border-radius: 5px; font-weight: bold; display: inline-block;">Review Backlog</a>
    </div>
    """
    
    # 3. Send the formal review email
    try:
        email_service.send_approval_notification("GOVERNANCE: Backlog Approval Required", email_body, reviewer_email)
    except Exception as e:
        print(f"WARN: Approval email failed: {e}")

    return {"status": "Approval Request Sent", "approval_id": approval_id}

@app.get("/review-approval/{approval_id}", responses={400: {"description": "Bad Request"}, 404: {"description": "Not Found"}, 500: {"description": "Internal Server Error"}})
async def review_approval(approval_id: str, db: Session = Depends(get_db)):
    approval = db.query(Approval).filter(Approval.id == approval_id).first()
    if not approval:
        return HTMLResponse(content="<h1>Approval session not found</h1>", status_code=404)
    
    if approval.status == "approved":
        return HTMLResponse(content="<h1>This backlog has already been approved and synced.</h1>", status_code=400)
    if approval.status == "rejected":
        return HTMLResponse(content="<h1>This backlog was rejected and is being reworked.</h1>", status_code=400)

    # Return HTML form for Approve or Reject
    html_content = f"""
    <html>
        <head>
            <style>
                body {{ font-family: sans-serif; background: #121212; color: #fff; text-align: center; padding: 50px; }}
                .container {{ background: #1e1e1e; padding: 30px; border-radius: 10px; display: inline-block; text-align: left; max-width: 600px; width: 100%; box-shadow: 0 4px 6px rgba(0,0,0,0.3); }}
                h1 {{ color: #00f2ff; margin-top: 0; }}
                .btn {{ padding: 12px 24px; border: none; border-radius: 5px; font-weight: bold; cursor: pointer; margin-right: 10px; font-size: 16px; }}
                .btn-approve {{ background: #00b894; color: white; }}
                .btn-reject {{ background: #d63031; color: white; }}
                textarea {{ width: 100%; padding: 10px; border-radius: 5px; border: 1px solid #444; background: #2b2b2b; color: #fff; margin-top: 10px; margin-bottom: 20px; font-family: sans-serif; }}
                label {{ font-weight: bold; color: #aaa; }}
            </style>
            <script>
                async function submitDecision(action) {{
                    const reason = document.getElementById('reason').value;
                    if (action === 'reject' && !reason.trim()) {{
                        alert('Please provide a reason for rejection.');
                        return;
                    }}
                    document.getElementById('buttons').innerHTML = '<p>Processing...</p>';
                    const res = await fetch('/submit-approval-decision/{approval_id}', {{
                        method: 'POST',
                        headers: {{ 'Content-Type': 'application/json' }},
                        body: JSON.stringify({{ action: action, reason: reason }})
                    }});
                    if (res.ok) {{
                        const data = await res.json();
                        document.body.innerHTML = '<div class="container" style="text-align: center; margin: 0 auto;"><h1>Decision Recorded</h1><p>' + data.message + '</p></div>';
                    }} else {{
                        alert('Error submitting decision.');
                        location.reload();
                    }}
                }}
            </script>
        </head>
        <body>
            <div class="container">
                <h1>Review Backlog</h1>
                <p>Please review the Functional Spec and Backlog sent to your email.</p>
                <div style="margin-top: 30px;">
                    <label for="reason">Feedback / Reason for Rejection (Optional for Approval):</label>
                    <textarea id="reason" rows="4" placeholder="If rejecting, specify what needs to change..."></textarea>
                    
                    <div id="buttons">
                        <button class="btn btn-approve" onclick="submitDecision('approve')">Approve & Sync</button>
                        <button class="btn btn-reject" onclick="submitDecision('reject')">Reject & Request Changes</button>
                    </div>
                </div>
            </div>
        </body>
    </html>
    """
    return HTMLResponse(content=html_content)

from pydantic import BaseModel
class ApprovalDecision(BaseModel):
    action: str
    reason: str

@app.post("/submit-approval-decision/{approval_id}", responses={400: {"description": "Bad Request"}, 404: {"description": "Not Found"}, 500: {"description": "Internal Server Error"}})
async def submit_approval_decision(approval_id: str, decision: ApprovalDecision, db: Session = Depends(get_db)):
    approval = db.query(Approval).filter(Approval.id == approval_id).first()
    if not approval or approval.status != "pending":
        raise HTTPException(status_code=400, detail="Invalid or processed approval session.")
    
    analysis = db.query(Analysis).filter(Analysis.id == approval.analysis_id).first()
    
    if decision.action == "approve":
        result = await automation_agent.create_work_items(approval.results_summary)
        approval.status = "approved"
        approval.ado_result = result
        db.commit()
        return {"message": f"Successfully synchronized {len(result.get('created_items', []))} items to Azure DevOps."}
    
    elif decision.action == "reject":
        approval.status = "rejected"
        approval.approver_response = decision.reason
        
        # We need to trigger the agent to rethink
        if analysis:
            analysis.status = "reworking"
            if analysis.results:
                results_copy = dict(analysis.results)
                results_copy["rejection_feedback"] = decision.reason
                analysis.results = results_copy
        db.commit()
        
        # Background task: Re-run the functional spec agent or LangGraph with feedback
        # For this implementation, we will append feedback to a context text and let the user resume,
        # OR we can execute it right here.
        # Since it takes time, let's just mark it and the user can see it in UI, or we can run it in a background task.
        import asyncio
        if not hasattr(app, "bg_tasks"):
            app.bg_tasks = set()
        task = asyncio.create_task(rework_analysis(approval.analysis_id, decision.reason, db))
        app.bg_tasks.add(task)
        task.add_done_callback(app.bg_tasks.discard)
        
        return {"message": "Rejection noted. The BA Agent is reworking the specifications based on your feedback. You will receive a new email shortly."}
    
    raise HTTPException(status_code=400, detail="Invalid action")

async def rework_analysis(analysis_id: str, feedback: str, db: Session):
    print(f" Reworking Analysis {analysis_id} with feedback: {feedback}")
    try:
        
        # We need to inject the feedback into the agent.
        # Since we are not using a deep conversational graph by default, 
        # we will directly invoke the FunctionalSpecAgent to regenerate the spec, 
        # taking the feedback into account, and then update the DB.
        
        analysis = db.query(Analysis).filter(Analysis.id == analysis_id).first()
        extraction = analysis.extraction or {}
        original_spec = analysis.functional_spec or ""
        
        # Simple rework logic: Let functional_spec_agent generate a new spec
        from agents.functional_spec import FunctionalSpecAgent
        fsa = FunctionalSpecAgent()
        
        # We append the feedback to the extraction context to guide the prompt
        extraction["rejection_feedback"] = f"STAKEHOLDER FEEDBACK (MUST FIX): {feedback}\n\nORIGINAL SPEC:\n{original_spec}"
        
        new_spec = await fsa.generate_spec(extraction, analysis.original_text or "")
        
        # Update Analysis
        analysis.functional_spec = new_spec
        if analysis.results:
            r = dict(analysis.results)
            r["functional_spec"] = new_spec
            analysis.results = r
            
        # Re-run backlog generation
        from agents.backlog_gen import BacklogGenAgent
        from agents.reviewers import QAReviewer, SecurityReviewer, UXReviewer
        
        print(" Reworking Persona Reviews...")
        qa_reviewer = QAReviewer()
        sec_reviewer = SecurityReviewer()
        ux_reviewer = UXReviewer()
        qa_task = qa_reviewer.review(extraction.get("functional_requirements", []))
        sec_task = sec_reviewer.review(extraction.get("functional_requirements", []))
        ux_task = ux_reviewer.review(extraction.get("functional_requirements", []))
        qa_res, sec_res, ux_res = await asyncio.gather(qa_task, sec_task, ux_task)
        
        reviews = {"qa": qa_res, "security": sec_res, "ux": ux_res}
        analysis.reviews = reviews
        if analysis.results:
            r = dict(analysis.results)
            r["reviews"] = reviews
            analysis.results = r
            
        print(" Reworking Backlog...")
        bga = BacklogGenAgent()
        context_str = f"Functional Spec:\n{new_spec}\n\nFeedback Applied:\n{feedback}"
        new_backlog = await bga.generate_backlog(context_str)
        analysis.backlog = new_backlog
        analysis.status = "completed"
        
        db.commit()
        
        # Send new email
        print(" Dispatching new approval email...")
        from services.email_service import email_service
        approval_id = str(uuid.uuid4())
        new_approval = Approval(
            id=approval_id,
            analysis_id=analysis_id,
            status="pending",
            results_summary=new_backlog
        )
        db.add(new_approval)
        db.commit()
        
        import markdown
        import json
        functional_spec_html = markdown.markdown(new_spec[:2000] + "\n\n*(Truncated for email)*" if len(new_spec) > 2000 else new_spec, extensions=['extra', 'smarty'])
        persona_reviews_text = "<ul>" + "".join([f"<li><strong>{k}</strong>: {v}</li>" for k, v in reviews.items()]) + "</ul>"
        backlog_json_str = json.dumps(new_backlog, indent=2)
        if len(backlog_json_str) > 2000:
            backlog_json_str = backlog_json_str[:2000] + "\n\n... (Truncated for email)"
            
        # We need the request base_url. Since this is a background task, we don't have 'request'.
        # We will use an env variable or default localhost.
        import os
        base_url = os.getenv("API_BASE_URL", "http://127.0.0.1:8000/")
        review_link = f"{base_url}review-approval/{approval_id}"
        
        email_body = f"""
        <div style="font-family: sans-serif; color: #333;">
            <h2 style="color: #00f2ff;">Strategic Backlog REVISED & Ready for Review</h2>
            <p>The BA Agent has addressed your feedback ("{feedback}"). Please review the revised backlog.</p>
            <hr style="border: 0; border-top: 1px solid #eee;"/>
            
            <h3>1. Proposed Technical Scope (Functional Spec):</h3>
            <div style="background: #f9f9f9; padding: 15px; border-left: 4px solid #00f2ff;">
                {functional_spec_html}
            </div>
            
            <h3>2. Persona Reviews (Risk & Governance):</h3>
            <div style="background: #f9f9f9; padding: 15px; border-left: 4px solid #ff00f2;">
                {persona_reviews_text}
            </div>
            
            <h3>3. Backlog JSON:</h3>
            <div style="background: #2b2b2b; color: #a9dc76; padding: 15px; border-radius: 5px; overflow-x: auto;">
                <pre style="margin: 0; font-family: monospace;">{backlog_json_str}</pre>
            </div>
            
            <hr style="border: 0; border-top: 1px solid #eee; margin-top: 20px;"/>
            <p>Please click the button below to review, approve, or reject this backlog.</p>
            <a href="{review_link}" style="background: #00f2ff; color: #121212; padding: 12px 24px; text-decoration: none; border-radius: 5px; font-weight: bold; display: inline-block;">Review Revised Backlog</a>
        </div>
        """
        email_service.send_approval_notification("GOVERNANCE: Revised Backlog Ready for Approval", email_body)
        print(" Rework cycle complete!")
        
    except Exception as e:
        print(f" Error during rework loop: {e}")

@app.get("/api/ado/work-items", responses={400: {"description": "Bad Request"}, 404: {"description": "Not Found"}, 500: {"description": "Internal Server Error"}})
async def get_ado_work_items():
    print(" [API: /api/ado/work-items] Fetching existing Epics and Features...")
    try:
        from services.ado_service import AzureDevOpsService
        ado_svc = AzureDevOpsService()
        wiql = "SELECT [System.Id], [System.Title], [System.WorkItemType], [System.State], [System.Description] FROM WorkItems WHERE [System.TeamProject] = @project AND [System.WorkItemType] IN ('Epic', 'Feature') ORDER BY [System.Id] DESC"
        items = await ado_svc.execute_dynamic_wiql(wiql)
        return {"work_items": items}
    except Exception as e:
        print(f" Error fetching ADO work items: {e}")
        return JSONResponse(status_code=500, content={"error": str(e)})

@app.post("/api/ado/generate-stories", responses={400: {"description": "Bad Request"}, 404: {"description": "Not Found"}, 500: {"description": "Internal Server Error"}})
async def generate_ado_stories(payload: dict):
    epic_data = payload.get("epic", {})
    if not epic_data:
        return JSONResponse(status_code=400, content={"error": "No epic data provided."})
    
    print(f" [API: /api/ado/generate-stories] Generating backlog for {epic_data.get('title')}...")
    from agents.backlog_gen import BacklogGenAgent
    bga = BacklogGenAgent()
    result = await bga.generate_stories_for_epic(epic_data)
    
    if "error" in result:
        return JSONResponse(status_code=500, content={"error": result["error"]})
        
    return {"backlog": result}

@app.post("/sync-backlog", responses={400: {"description": "Bad Request"}, 404: {"description": "Not Found"}, 500: {"description": "Internal Server Error"}})
async def sync_backlog(payload: dict):
    project_id = payload.get("project_id")
    backlog = payload.get("backlog")
    
    print("\n" + "="*50)
    print(f" [API: /sync-backlog] STARTING: Synchronizing project {project_id} to ADO")
    print("="*50)
    
    if not project_id or not backlog:
        print(" [API: /sync-backlog] ERROR: Missing project_id or backlog.")
        raise HTTPException(status_code=400, detail="Missing project_id or backlog data")
    
    result = await orchestrator.run_backlog_sync(project_id, backlog)
    print(" [API: /sync-backlog] COMPLETED Successfully!")
    return result

@app.post("/automate", responses={400: {"description": "Bad Request"}, 404: {"description": "Not Found"}, 500: {"description": "Internal Server Error"}})
async def automate_backlog(payload: dict, db: Session = Depends(get_db)):
    # Keep this for legacy or manual sync if needed, but primary flow is now approval-based
    print("\n" + "="*50)
    print(" [API: /automate] STARTING: Direct ADO Publishing")
    print("="*50)
    backlog = payload.get("backlog")
    export_target = payload.get("export_target", "ado")
    result = await automation_agent.create_work_items(backlog, target=export_target)
    print(" [API: /automate] COMPLETED Successfully!")
    return result

@app.get("/download-spec/{doc_id}", responses={400: {"description": "Bad Request"}, 404: {"description": "Not Found"}, 500: {"description": "Internal Server Error"}})
async def download_functional_spec(doc_id: str, include_nfr = True, db: Session = Depends(get_db)):
    is_nfr_included = str(include_nfr).lower() not in ['false', '0', 'off', 'no']
    print(f"[API: /download-spec/{doc_id}] Requesting Full Discovery PDF export (include_nfr={is_nfr_included})...")
    
    # 1. Automatic doc_id resolution across Document, ProjectStateModel, and Analysis tables
    actual_doc_id = doc_id
    doc = db.query(Document).filter(Document.id == doc_id).first()
    project = db.query(ProjectStateModel).filter(ProjectStateModel.document_id == doc_id).first()
    analysis = db.query(Analysis).filter(Analysis.id == doc_id).first()
    
    if not doc and not project and analysis:
        actual_doc_id = analysis.document_id or doc_id
        doc = db.query(Document).filter(Document.id == actual_doc_id).first()
        project = db.query(ProjectStateModel).filter(ProjectStateModel.document_id == actual_doc_id).first()

    if not doc and not project:
        # Fallback to latest project state if doc_id was transient
        project = db.query(ProjectStateModel).order_by(ProjectStateModel.created_at.desc()).first()
        if project:
            actual_doc_id = project.document_id
            doc = db.query(Document).filter(Document.id == actual_doc_id).first()

    doc_id = actual_doc_id or doc_id

    import re
    raw_name = doc.name if doc else "Commercial Property Discovery Document"
    upload_date = str(doc.upload_date)[:10] if doc and doc.upload_date else "N/A"
    lob = (doc.project_id if doc and doc.project_id and doc.project_id != "guest" else None) or (analysis.project_id if analysis and analysis.project_id else None) or "Commercial Property"

    import json
    import os
    import markdown

    def safe_parse(val):
        if not val: return None
        if isinstance(val, (dict, list)): return val
        if isinstance(val, str):
            try: return json.loads(val)
            except Exception: return val
        return val

    from services.storage_service import storage_service

    functional_spec = storage_service.load_json_artifact(doc_id, "functional_spec") or storage_service.load_json_artifact(actual_doc_id, "functional_spec")
    gaps = storage_service.load_json_artifact(doc_id, "gaps") or storage_service.load_json_artifact(actual_doc_id, "gaps")
    backlog = storage_service.load_json_artifact(doc_id, "backlog") or storage_service.load_json_artifact(actual_doc_id, "backlog")
    test_cases = storage_service.load_json_artifact(doc_id, "test_cases") or storage_service.load_json_artifact(actual_doc_id, "test_cases")

    if not analysis:
        analysis = db.query(Analysis).filter((Analysis.document_id == doc_id) | (Analysis.document_id == actual_doc_id) | (Analysis.id == doc_id)).first()

    if not functional_spec and doc and doc.meta:
        functional_spec = doc.meta.get('functional_spec') or doc.meta.get('trd')
    if not gaps and doc and doc.meta:
        gaps = doc.meta.get('gaps') or doc.meta.get('reviews')
    if not backlog and doc and doc.meta:
        backlog = safe_parse(doc.meta.get('backlog'))
    if not test_cases and doc and doc.meta:
        test_cases = safe_parse(doc.meta.get('test_cases'))

    if project:
        if not functional_spec:
            functional_spec = getattr(project, 'trd', None) or getattr(project, 'functional_spec', None)
        if not gaps:
            gaps = safe_parse(getattr(project, 'gaps', None))
        if not backlog:
            backlog = safe_parse(getattr(project, 'backlog', None))
        if not test_cases:
            test_cases = safe_parse(getattr(project, 'test_cases', None))

    if analysis:
        if not functional_spec:
            functional_spec = getattr(analysis, 'functional_spec', None)
            if not functional_spec and isinstance(analysis.results, dict):
                functional_spec = analysis.results.get('functional_spec') or analysis.results.get('trd')
        if not gaps:
            gaps = safe_parse(getattr(analysis, 'gaps', None))
            if not gaps and isinstance(analysis.results, dict):
                gaps = safe_parse(analysis.results.get('gaps'))
        if not backlog:
            backlog = safe_parse(getattr(analysis, 'backlog', None))
            if not backlog and isinstance(analysis.results, dict):
                backlog = safe_parse(analysis.results.get('backlog'))
        if not test_cases:
            test_cases = safe_parse(getattr(analysis, 'test_cases', None))
            if not test_cases and isinstance(analysis.results, dict):
                test_cases = safe_parse(analysis.results.get('test_cases'))

    # Ultimate fallback: Check any recent Analysis record if doc_id was transient
    if not functional_spec and not gaps and not backlog and not test_cases:
        latest_analysis = db.query(Analysis).order_by(Analysis.date.desc()).first()
        if latest_analysis:
            functional_spec = getattr(latest_analysis, 'functional_spec', None) or (latest_analysis.results.get('functional_spec') if isinstance(latest_analysis.results, dict) else None)
            gaps = safe_parse(getattr(latest_analysis, 'gaps', None) or (latest_analysis.results.get('gaps') if isinstance(latest_analysis.results, dict) else None))
            backlog = safe_parse(getattr(latest_analysis, 'backlog', None) or (latest_analysis.results.get('backlog') if isinstance(latest_analysis.results, dict) else None))
            test_cases = safe_parse(getattr(latest_analysis, 'test_cases', None) or (latest_analysis.results.get('test_cases') if isinstance(latest_analysis.results, dict) else None))

    if not functional_spec and not gaps and not backlog and not test_cases:
        raise HTTPException(status_code=404, detail="No generated discovery artifacts (Functional Spec, Gaps, Backlog, or Test Cases) found for this document.")

    # Derive a meaningful, client-friendly document title from Executive Summary or Feature Overview
    doc_title_clean = ""
    if functional_spec and isinstance(functional_spec, str):
        title_m = re.search(r"(?im)^#{1,6}[ \t]*(?:Document Title|1\.[ \t]*Executive Summary|Project Overview):[ \t]*([^ \t\r\n][^\r\n]*)$", functional_spec) or re.search(r"(?m)^#[ \t]+([^ \t\r\n][^\r\n]*)$", functional_spec)
        if title_m:
            candidate = title_m.group(1).strip()
            if candidate and "Functional Specification Document" not in candidate and "IEEE" not in candidate and "temp_" not in candidate:
                doc_title_clean = candidate

    if not doc_title_clean:
        clean_file_name = re.sub(r"^temp_[a-f0-9\-]+_", "", raw_name, flags=re.I).replace(".pdf", "").replace(".docx", "").replace("_", " ").strip()
        if clean_file_name and clean_file_name.lower() not in ["commercial property discovery document", "business discovery document", "sample"]:
            doc_title_clean = f"{lob} - {clean_file_name} Specification"
        else:
            doc_title_clean = f"{lob} Building Information Intake & Policy Specification"

    doc_name = doc_title_clean

    # Load logo base64
    import base64
    logo_base64 = ""
    try:
        base_dir = os.path.dirname(os.path.abspath(__file__))
        logo_path = os.path.join(base_dir, "..", "frontend", "public", "assets", "Valuemomentum_logo_dark.png")
        if os.path.exists(logo_path):
            async with aiofiles.open(logo_path, "rb") as image_file:
                logo_base64 = base64.b64encode(await image_file.read()).decode('utf-8')
    except Exception as e:
        print(f"WARN: Logo encoding failed: {e}")

    # Build Sections
    sections_html = []

    # 1. Functional Specification Section
    if functional_spec:
        spec_text = functional_spec if isinstance(functional_spec, str) else json.dumps(functional_spec, indent=2)
        
        # Remove duplicate top-level title header if it repeats cover page title
        spec_text = re.sub(r"^[ \t]*#[ \t][^\n]*\n+", "", spec_text)

        if not is_nfr_included:
            # Strip Section 4 Non-Functional Requirements if user unchecks NFR inclusion
            lines = spec_text.split('\n')
            new_lines = []
            skip = False
            for line in lines:
                if re.match(r"(?i)^[ \t]*(?:##|#)[ \t]*4\.", line):
                    skip = True
                elif skip and re.match(r"^[ \t]*(?:##|#)[ \t]*\d+\.", line):
                    skip = False
                if not skip:
                    new_lines.append(line)
            spec_text = '\n'.join(new_lines)
            # Re-number Section 5 and Section 6 to Section 4 and Section 5 when NFRs are omitted
            spec_text = re.sub(r"##\s*5\.\s*", "## 4. ", spec_text)
            spec_text = re.sub(r"##\s*6\.\s*", "## 5. ", spec_text)

        # Terminology & Identifier alignment: REQ-xxx tags & Component Workflow
        spec_text = re.sub(r"\bFR([-\s]?\d+)\b", r"REQ\1", spec_text, flags=re.I)
        spec_text = re.sub(r"\[FR([-\s]?\d+)\]", r"[REQ\1]", spec_text, flags=re.I)
        spec_text = re.sub(r"\bBuilding\s+Information\s+(?:page\s+)?system\b", "Building Information component workflow", spec_text, flags=re.I)
        spec_text = re.sub(r"\bstandalone\s+system\b", "component workflow within the LOB ecosystem", spec_text, flags=re.I)

        # Ensure NFR sub-bullets are on separate lines for proper HTML rendering
        spec_text = re.sub(r"-\s*(\*\*[^*]+\*\*:)", r"\n- \1", spec_text)

        # Strip redundant introductory summary lines under Section 3
        spec_text = re.sub(r"(?i)The functional requirements will be grouped into the following sub-system modules:[^\n]*(?:\n(?!\n\n|\n###|\n[A-Z0-9])[^\n]*)*", "", spec_text)

        rendered_spec = markdown.markdown(spec_text, extensions=['extra', 'tables', 'fenced_code'])

        # HTML Export Post-Processing: 3-column filter & clean table consolidation without losing batches
        def format_export_spec_html(html_str: str) -> str:
            if not html_str: return ""
            
            # 1. Filter <tr> rows to keep ONLY first 3 cells (Req ID, Req Name, Description) -> Drop 4th, 5th, 6th columns
            def filter_tr(match):
                tr_open, tr_body, tr_close = match.group(1), match.group(2), match.group(3)
                cells = re.findall(r'<t[dh][^>]*>[\s\S]*?</t[dh]>', tr_body, re.I)
                if len(cells) > 3:
                    return f"{tr_open}{''.join(cells[:3])}{tr_close}"
                return match.group(0)

            html_str = re.sub(r'(<tr[^>]*>)([\s\S]*?)(</tr>)', filter_tr, html_str, flags=re.I)
            
            # 2. Clean batch markers and merge table blocks smoothly without losing requirement rows
            html_str = re.sub(r'<h3>BATCH \d+:[^<]*</h3>', '', html_str, flags=re.I)
            html_str = re.sub(r'<p>--- BATCH \d+:[^<]*</p>', '', html_str, flags=re.I)
            html_str = re.sub(r'</table>\s*<table[^>]*>\s*(?:<thead>[\s\S]*?</thead>)?\s*(?:<tbody>)?', '', html_str, flags=re.I)

            return html_str

        rendered_spec = format_export_spec_html(rendered_spec)

        # Output Section 1 directly starting with 1. Executive Summary...
        sections_html.append(f"""
        <div class="section-card page-break">
            <div class="section-content">
                {rendered_spec}
            </div>
        </div>
        """)

    # Initialize sequential section counter after Section 1 (which ends at Section 5)
    sec_counter = 6

    # 2. Persona Review & Gap Analysis Section
    if gaps:
        gap_items = []
        if isinstance(gaps, dict) and "gaps" in gaps:
            gap_items = gaps["gaps"]
        elif isinstance(gaps, list):
            gap_items = gaps
        
        if gap_items:
            gap_rows = ""
            for idx, g in enumerate(gap_items, 1):
                title = g.get('title') or g.get('requirement') or f"Gap #{idx}"
                desc = g.get('description') or ''
                rec = g.get('recommendation') or g.get('impact') or ''
                risk = g.get('risk_level') or g.get('severity') or 'Medium'
                
                gap_rows += f"""
                <tr style="page-break-inside: avoid;">
                    <td><strong>{title}</strong></td>
                    <td><span class="badge badge-risk">{risk}</span></td>
                    <td>{desc}</td>
                    <td>{rec}</td>
                </tr>
                """

            sections_html.append(f"""
            <div class="section-card page-break">
                <h2>{sec_counter}. Risk & Agentic Council Review (Gap Analysis)</h2>
                <div class="section-content">
                    <table>
                        <thead>
                            <tr>
                                <th style="width: 25%;">Requirement / Gap</th>
                                <th style="width: 15%;">Risk Level</th>
                                <th style="width: 30%;">Impact Description</th>
                                <th style="width: 30%;">Recommendation</th>
                            </tr>
                        </thead>
                        <tbody>
                            {gap_rows}
                        </tbody>
                    </table>
                </div>
            </div>
            """)
            sec_counter += 1

    # 3. Backlog Hierarchy Section
    if backlog:
        epics = []
        top_features = []
        if isinstance(backlog, dict):
            if "backlog" in backlog and isinstance(backlog["backlog"], dict):
                backlog = backlog["backlog"]
            epics = backlog.get('epics', [])
            top_features = backlog.get('features', [])
        elif isinstance(backlog, list):
            epics = backlog

        backlog_html = ""

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

        def render_feature_html(feature):
            feat_title = feature.get('title', 'Untitled Feature')
            stories_html = ""
            stories = feature.get('user_stories', [])
            stories_sorted = sorted(stories, key=get_story_req_num)
            for story in stories_sorted:
                story_raw_title = story.get('title', 'Untitled Story')
                story_clean_title = story_raw_title.replace("User Story:", "").strip()

                # Re-order requirement tags inside title bracket numerically (e.g. [REQ-012, REQ-005] -> [REQ-005, REQ-012])
                bracket_match = re.search(r"^\[(.*?)\]", story_clean_title)
                if bracket_match:
                    found_nums = re.findall(r"(?:REQ|FR)-(\d+)", bracket_match.group(1), re.I)
                    if found_nums:
                        sorted_nums = sorted({int(n) for n in found_nums})
                        sorted_tags = ", ".join([f"REQ-{str(n).zfill(3)}" for n in sorted_nums])
                        story_clean_title = re.sub(r"^\[[^\]]*\]", f"[{sorted_tags}]", story_clean_title)

                story_desc = story.get('description', '')
                moscow = story.get('moscow', 'Must Have')
                ac_list = story.get('acceptance_criteria', [])
                
                formatted_ac_list = []
                for ac in ac_list:
                    if isinstance(ac, str):
                        clean_ac = ac.replace("\r\n", "\n")
                        lines = [line.strip() for line in clean_ac.split("\n") if line.strip()]
                        formatted_ac = "<br/>".join(lines)
                        formatted_ac = re.sub(r"(?i)\b(when\s+|then\s+)", r"<br/>\1", formatted_ac)
                        formatted_ac = re.sub(r",\s*<br/>", r"<br/>", formatted_ac)
                        formatted_ac_list.append(formatted_ac)
                    else:
                        formatted_ac_list.append(str(ac))
                ac_bullets = "".join([f"<li style='margin-bottom:8px; line-height:1.4;'>{ac}</li>" for ac in formatted_ac_list]) if formatted_ac_list else "<li style='margin-bottom:8px; line-height:1.4;'>Given valid input,<br/>When submitted,<br/>Then system verifies.</li>"

                tasks_list = story.get('tasks', [])
                task_bullets = "".join([f"<li style='margin-bottom:4px;'>{t}</li>" for t in tasks_list]) if tasks_list else ""

                formatted_story_body = story_desc if isinstance(story_desc, str) else str(story_desc)
                invest_match = re.search(r"(?i)As an? [^,]+,[ \t]*I want to [^,]+,[ \t]*so that [^\r\n]+", formatted_story_body)
                if invest_match:
                    formatted_story_body = invest_match.group(0).strip()
                else:
                    formatted_story_body = re.sub(r"\*\*\s*(?:Business Context|Workflow Impact|Functional Rules)[^*]*\*\*:?[\s\S]*", "", formatted_story_body, flags=re.I).strip()
                formatted_story_body = re.sub(r"^\*\*\s*(?:User Story|Description)[^*]*\*\*:?\s*", "", formatted_story_body, flags=re.I).strip()

                stories_html += f"""
                <div class="story-card" style="margin-bottom:16px; padding:12px; background:#ffffff; border:1px solid #cbd5e1; border-radius:8px; page-break-inside: avoid;">
                    <div class="story-header" style="display:flex; justify-content:space-between; align-items:center; margin-bottom:6px;">
                        <strong style="font-size:1.02rem; color:#0f172a;">User Story: {story_clean_title}</strong>
                        <span class="badge badge-moscow">{moscow}</span>
                    </div>
                    <div class="desc-text" style="margin-bottom:12px; color:#334155; font-size:0.92rem;">
                        <strong>Description:</strong> {formatted_story_body}
                    </div>
                    <p style="margin-top:10px; margin-bottom:8px; font-weight:600; font-size:0.9rem; color:#0f172a;">Acceptance Criteria:</p>
                    <ul style="margin-top:4px; margin-bottom:12px; padding-left:20px; font-size:0.88rem; color:#334155;">{ac_bullets}</ul>
                    {f'<p style="margin-top:10px; margin-bottom:8px; font-weight:600; font-size:0.9rem; color:#0f172a;">Technical Tasks:</p><ul style="margin-top:4px; padding-left:20px; font-size:0.88rem; color:#334155;">{task_bullets}</ul>' if task_bullets else ''}
                </div>
                """

            return f"""
            <div class="feature-card" style="page-break-inside: avoid; margin-bottom:20px;">
                <h3>📦 Feature: {feat_title}</h3>
                {stories_html}
            </div>
            """

        if epics:
            for epic in epics:
                epic_title = epic.get('title', 'Untitled Epic')
                epic_desc = epic.get('description', '')
                features = epic.get('features', [])
                features_sorted = sorted(features, key=get_feature_min_req_num)
                features_html = "".join([render_feature_html(f) for f in features_sorted])
                backlog_html += f"""
                <div class="epic-card" style="page-break-inside: avoid; margin-bottom:24px;">
                    <h2>⚡ Epic: {epic_title}</h2>
                    <p style="color:#555; font-size:0.9em;">{epic_desc}</p>
                    {features_html}
                </div>
                """
        elif top_features:
            features_sorted = sorted(top_features, key=get_feature_min_req_num)
            features_html = "".join([render_feature_html(f) for f in features_sorted])
            backlog_html = f"""
            <div class="epic-card" style="page-break-inside: avoid;">
                <h2>📦 Enterprise Backlog Features</h2>
                {features_html}
            </div>
            """

        if backlog_html:
            sections_html.append(f"""
            <div class="section-card page-break">
                <h2>{sec_counter}. Agile Backlog & Work Breakdown Structure (DevOps Ready)</h2>
                <div class="section-content">
                    {backlog_html}
                </div>
            </div>
            """)
            sec_counter += 1

    # 4. Test Cases & Playwright Automation Section
    if test_cases:
        tc_list = []
        script_code = ""
        
        if isinstance(test_cases, dict):
            tc_list = test_cases.get('test_cases', [])
            script_code = test_cases.get('playwright_script', '')
        elif isinstance(test_cases, list):
            tc_list = test_cases

        tc_rows = ""
        for tc in tc_list:
            if not isinstance(tc, dict): continue
            tc_id = tc.get('test_case_id') or tc.get('id') or 'TC-001'
            title = tc.get('title') or tc.get('name') or 'Test Scenario'
            story_title = tc.get('user_story_title') or tc.get('user_story_name') or tc.get('user_story_id') or 'User Story'
            priority = tc.get('priority', 'High')
            test_type = tc.get('test_type', 'Functional')
            desc = tc.get('description') or tc.get('objective') or ''

            # Sanitize strings to strip escaped quotes, leading commas, or raw code leaks
            clean_title = str(title).strip(" \t\":,\\")
            clean_story = str(story_title).strip(" \t\":,\\")
            clean_desc = str(desc).strip(" \t\":,\\")

            if "page.goto" in clean_title or "async (" in clean_title:
                code_match = re.search(r"Verify[^\n'\"\\]+", clean_title, re.I)
                clean_title = code_match.group(0).strip() if code_match else "Verify requirement functionality"

            if "page.goto" in clean_desc or "async (" in clean_desc:
                code_match = re.search(r"Verify[^\n'\"\\]+", clean_desc, re.I)
                clean_desc = code_match.group(0).strip() if code_match else "Verify system behavior"

            steps = tc.get('steps', [])
            formatted_step_items = []
            if isinstance(steps, list):
                for i, s in enumerate(steps):
                    if isinstance(s, dict):
                        action = s.get('action') or s.get('step') or s.get('description') or ''
                        expected = s.get('expected_result') or s.get('expected') or ''
                        step_str = f"<b>Step {s.get('step_number', i+1)}:</b> {action}"
                        if expected:
                            step_str += f"<br/><span style='color:#475569;'><i>Expected:</i> {expected}</span>"
                        formatted_step_items.append(step_str)
                    else:
                        formatted_step_items.append(f"<b>Step {i+1}:</b> {s}")
                steps_formatted = "<br/><br/>".join(formatted_step_items)
            else:
                steps_formatted = str(steps)

            tc_rows += f"""
            <tr style="page-break-inside: avoid;">
                <td><strong>{tc_id}</strong></td>
                <td><strong>{clean_title}</strong><br/><small style="color:#64748b;">Story: {clean_story}</small></td>
                <td><span class="badge badge-priority">{priority}</span></td>
                <td>{test_type}</td>
                <td>{clean_desc}</td>
                <td style="font-size:0.85em; max-width:280px; word-wrap:break-word;">{steps_formatted}</td>
            </tr>
            """

        script_html = ""
        if script_code:
            script_html = f"""
            <h3 style="margin-top: 30px;">🎭 Automated Playwright TypeScript Suite</h3>
            <pre><code class="language-typescript">{script_code}</code></pre>
            """

        sections_html.append(f"""
        <div class="section-card page-break">
            <h2>{sec_counter}. QA Test Suite & Playwright Automation</h2>
            <div class="section-content">
                <table style="table-layout: fixed; width: 100%;">
                    <thead>
                        <tr>
                            <th style="width: 8%;">ID</th>
                            <th style="width: 22%;">Test Title & User Story</th>
                            <th style="width: 10%;">Priority</th>
                            <th style="width: 10%;">Type</th>
                            <th style="width: 22%;">Objective</th>
                            <th style="width: 28%;">Steps</th>
                        </tr>
                    </thead>
                    <tbody>
                        {tc_rows}
                    </tbody>
                </table>
                {script_html}
            </div>
        </div>
        """)
        sec_counter += 1

    all_body_content = "\n".join(sections_html)

    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8"/>
        <title>Discovery Package - {doc_name}</title>
        <style>
            @media print {{
                .no-print {{ display: none !important; }}
                body {{ padding: 0 !important; background: #fff !important; }}
                .page-break {{ page-break-before: always; }}
                tr {{ page-break-inside: avoid !important; break-inside: avoid !important; }}
                h1, h2, h3 {{ page-break-after: avoid !important; break-after: avoid !important; }}
                .story-card, .feature-card, .epic-card {{ page-break-inside: avoid !important; break-inside: avoid !important; }}
            }}
            body {{
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;
                padding: 40px 60px;
                line-height: 1.6;
                color: #1e293b;
                max-width: 1000px;
                margin: 0 auto;
                background: #f8fafc;
            }}
            .container {{
                background: #ffffff;
                padding: 40px;
                border-radius: 12px;
                box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06);
            }}
            .header {{
                display: flex;
                justify-content: space-between;
                align-items: center;
                margin-bottom: 40px;
                border-bottom: 2px solid #e2e8f0;
                padding-bottom: 20px;
            }}
            .title-banner {{
                background: linear-gradient(135deg, #1e3a8a 0%, #3b82f6 100%);
                color: white;
                padding: 24px 32px;
                border-radius: 10px;
                margin-bottom: 30px;
            }}
            .title-banner h1 {{
                margin: 0;
                font-size: 1.8rem;
                font-weight: 700;
            }}
            .title-banner p {{
                margin: 6px 0 0 0;
                opacity: 0.9;
                font-size: 0.95rem;
            }}
            .meta-grid {{
                display: grid;
                grid-template-columns: repeat(3, 1fr);
                gap: 16px;
                margin-bottom: 30px;
                background: #f1f5f9;
                padding: 16px 20px;
                border-radius: 8px;
            }}
            .meta-item label {{
                font-size: 0.75rem;
                text-transform: uppercase;
                color: #64748b;
                font-weight: 600;
                display: block;
            }}
            .meta-item span {{
                font-weight: 600;
                color: #0f172a;
                font-size: 0.95rem;
            }}
            h1, h2, h3 {{
                page-break-after: avoid !important;
                break-after: avoid !important;
            }}
            h2 {{
                color: #1e3a8a;
                border-bottom: 2px solid #cbd5e1;
                padding-bottom: 8px;
                margin-top: 40px;
                font-size: 1.4rem;
            }}
            h3 {{
                color: #2563eb;
                margin-top: 20px;
                font-size: 1.15rem;
            }}
            table {{
                width: 100%;
                border-collapse: collapse;
                margin: 20px 0;
                font-size: 0.9rem;
                page-break-inside: auto;
            }}
            tr {{
                page-break-inside: avoid !important;
                break-inside: avoid !important;
            }}
            th, td {{
                border: 1px solid #cbd5e1;
                padding: 10px 14px;
                text-align: left;
                vertical-align: top;
                word-wrap: break-word;
                overflow-wrap: break-word;
            }}
            th {{
                background-color: #f1f5f9;
                color: #1e293b;
                font-weight: 600;
            }}
            .badge {{
                display: inline-block;
                padding: 3px 8px;
                border-radius: 4px;
                font-size: 0.75rem;
                font-weight: 600;
            }}
            .badge-risk {{ background: #fee2e2; color: #991b1b; }}
            .badge-moscow {{ background: #dbeafe; color: #1e40af; }}
            .badge-priority {{ background: #fef3c7; color: #92400e; }}
            pre, code, pre code {{
                white-space: pre-wrap !important;
                word-wrap: break-word !important;
                word-break: break-word !important;
                max-width: 100% !important;
                background: #0f172a !important;
                color: #38bdf8 !important;
                padding: 14px !important;
                border-radius: 8px !important;
                font-family: Consolas, Monaco, 'Andale Mono', monospace !important;
                font-size: 0.85rem !important;
                display: block !important;
            }}
            .epic-card {{
                border: 1px solid #cbd5e1;
                border-radius: 8px;
                padding: 20px;
                margin-bottom: 24px;
                background: #fafafa;
                page-break-inside: avoid !important;
            }}
            .feature-card {{
                border-left: 4px solid #3b82f6;
                padding-left: 16px;
                margin: 16px 0;
                page-break-inside: avoid !important;
            }}
            .story-card {{
                background: #ffffff;
                border: 1px solid #e2e8f0;
                border-radius: 6px;
                padding: 14px;
                margin: 10px 0;
            }}
            .story-header {{
                display: flex;
                justify-content: space-between;
                align-items: center;
            }}
            pre {{
                background: #0f172a;
                color: #f8fafc;
                padding: 16px;
                border-radius: 8px;
                overflow-x: auto;
                font-size: 0.85rem;
            }}
            .no-print-bar {{
                position: fixed;
                top: 20px;
                right: 20px;
                z-index: 9999;
            }}
            .btn-print {{
                background: #2563eb;
                color: white;
                border: none;
                padding: 10px 20px;
                border-radius: 8px;
                font-weight: 600;
                cursor: pointer;
                box-shadow: 0 4px 12px rgba(37, 99, 235, 0.3);
            }}
        </style>
    </head>
    <body>
        <div class="no-print-bar no-print">
            <button onclick="window.print()" class="btn-print">🖨️ Print / Save to PDF</button>
        </div>

        <div class="container">
            <div class="header">
                <div class="logo">
                    {f'<img src="data:image/png;base64,{logo_base64}" style="height: 48px;" />' if logo_base64 else '<strong>ValueMomentum</strong>'}
                </div>
                <div class="meta-item" style="text-align: right;">
                    <label>GENERATED BY</label>
                    <span>BA Agent Pro Enterprise</span>
                </div>
            </div>

            <div class="title-banner">
                <h1>{doc_name}</h1>
            </div>

            <div class="meta-grid">
                <div class="meta-item">
                    <label>Document Name</label>
                    <span>{doc_name}</span>
                </div>
                <div class="meta-item">
                    <label>Line of Business (LOB)</label>
                    <span>{lob}</span>
                </div>
                <div class="meta-item">
                    <label>Export Date</label>
                    <span>{upload_date}</span>
                </div>
            </div>

            {all_body_content}
        </div>
    </body>
    </html>
    """
    import asyncio
    def _background_save_blob():
        try:
            storage_service.save_blob_artifact(doc_id, "discovery_package", html_content.encode('utf-8'), "html")
        except Exception as e:
            print(f"WARN: Saving HTML/PDF blob package failed: {e}")
            
    if not hasattr(app, "bg_tasks"):
        app.bg_tasks = set()
    task = asyncio.create_task(asyncio.to_thread(_background_save_blob))
    app.bg_tasks.add(task)
    task.add_done_callback(app.bg_tasks.discard)

    return HTMLResponse(content=html_content)

# MS Teams Bot Endpoint
from botbuilder.schema import Activity

@app.post("/api/messages", responses={400: {"description": "Bad Request"}, 404: {"description": "Not Found"}, 500: {"description": "Internal Server Error"}})
async def messages(req: Request):
    print(" [API: /api/messages] Incoming Teams activity...")
    if "application/json" in req.headers.get("Content-Type", ""):
        body = await req.json()
    else:
        return Response(status_code=415)
        
    activity = Activity().deserialize(body)
    auth_header = req.headers.get("Authorization", "")
    
    try:
        response = await bot_adapter.process_activity(activity, auth_header, teams_bot.on_turn)
        if response:
            return JSONResponse(content=response.body, status_code=response.status)
        return Response(status_code=201)
    except Exception as e:
        import traceback
        traceback.print_exc()
        print(f" [API: /api/messages] ERROR: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

# --- MARKETPLACE DECOUPLED AGENTS ---
from pydantic import BaseModel
from typing import Any, Optional

class ExtractRequest(BaseModel):
    document_id: str
    text_content: str

@app.post("/api/agents/extract", responses={400: {"description": "Bad Request"}, 404: {"description": "Not Found"}, 500: {"description": "Internal Server Error"}})
async def marketplace_extract(req: ExtractRequest):
    print(" [API: /api/agents/extract] Requesting extraction...")
    try:
        result = await orchestrator.run_extraction(req.document_id, req.text_content, "document")
        return result
    except Exception as e:
        print(f" [API: /api/agents/extract] ERROR: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

class AnalyzeGapsRequest(BaseModel):
    document_id: str
    extraction: Dict[str, Any]
    lob: str

@app.post("/api/agents/analyze-gaps", responses={400: {"description": "Bad Request"}, 404: {"description": "Not Found"}, 500: {"description": "Internal Server Error"}})
async def marketplace_analyze_gaps(req: AnalyzeGapsRequest):
    print(" [API: /api/agents/analyze-gaps] Requesting gap analysis...")
    try:
        db = next(get_db())
        context = await context_agent.get_project_context(db)
        memory = await knowledge_agent.retrieve_relevant_context(json.dumps(req.extraction), req.lob)
        result = await analysis_agent.analyze_gaps(req.extraction, "", {}, context, memory)
        return result
    except Exception as e:
        print(f" [API: /api/agents/analyze-gaps] ERROR: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

class GenerateFunctionalSpecRequest(BaseModel):
    extraction: Optional[Dict[str, Any]] = None
    gaps: Optional[Dict[str, Any]] = None
    lob: str
    brd_text: Optional[str] = None

@app.post("/api/agents/generate-functional-spec", responses={400: {"description": "Bad Request"}, 404: {"description": "Not Found"}, 500: {"description": "Internal Server Error"}})
async def marketplace_generate_functional_spec(req: GenerateFunctionalSpecRequest):
    print(" [API: /api/agents/generate-functional-spec] Requesting Functional Spec generation...")
    try:
        db = next(get_db())
        context = await context_agent.get_project_context(db)
        
        # If extraction is missing, pass an empty dict to memory agent (or pass brd_text)
        query_text = req.brd_text if req.brd_text else json.dumps(req.extraction)
        memory = await knowledge_agent.retrieve_relevant_context(query_text, req.lob)
        
        functional_spec_markdown = await functional_spec_agent.generate_spec(
            extraction=req.extraction, 
            gaps=req.gaps.get("gaps", []) if req.gaps else [], 
            lob=req.lob, 
            context=context, 
            memory=memory,
            raw_brd_text=req.brd_text
        )
        return {"functional_spec_markdown": functional_spec_markdown}
    except Exception as e:
        print(f" [API: /api/agents/generate-functional-spec] ERROR: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

class SyncADORequest(BaseModel):
    functional_spec_markdown: Optional[str] = None
    brd_text: Optional[str] = None
    ado_org: str
    ado_project: str
    ado_token: str

@app.post("/api/agents/sync-ado", responses={400: {"description": "Bad Request"}, 404: {"description": "Not Found"}, 500: {"description": "Internal Server Error"}})
async def marketplace_sync_ado(req: SyncADORequest):
    print(" [API: /api/agents/sync-ado] Requesting ADO sync...")
    try:
        from agents.backlog_gen import BacklogGenAgent
        backlog_agent = BacklogGenAgent()
        
        if req.brd_text:
            backlog = await backlog_agent.generate_backlog_from_brd(req.brd_text)
        elif req.functional_spec_markdown:
            backlog = await backlog_agent.generate_backlog(req.functional_spec_markdown)
        else:
            raise RuntimeError("Either functional_spec_markdown or brd_text must be provided")
            
        # Override environment temporarily for this sync
        os.environ["ADO_ORG_URL"] = f"https://dev.azure.com/{req.ado_org}/"
        os.environ["ADO_PROJECT"] = req.ado_project
        os.environ["ADO_CREDENTIAL"] = req.ado_token
        export_target = getattr(req, "export_target", "ado")
        result = await automation_agent.create_work_items(backlog, target=export_target)
        return result
    except Exception as e:
        print(f" [API: /api/agents/sync-ado] ERROR: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

class MemoryRequest(BaseModel):
    query: str

@app.post("/api/agents/memory", responses={400: {"description": "Bad Request"}, 404: {"description": "Not Found"}, 500: {"description": "Internal Server Error"}})
async def marketplace_memory(req: MemoryRequest):
    print(" [API: /api/agents/memory] Requesting knowledge recall...")
    try:
        # We query the knowledge agent using the provided query and default to General LOB
        result = await knowledge_agent.retrieve_relevant_context(req.query, lob="General")
        return {"retrieved_context": result}
    except Exception as e:
        print(f" [API: /api/agents/memory] ERROR: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

class ADOQueryRequest(BaseModel):
    query: str
    ado_org: str
    ado_project: str
    ado_token: str

@app.post("/api/agents/ado-query", responses={400: {"description": "Bad Request"}, 404: {"description": "Not Found"}, 500: {"description": "Internal Server Error"}})
async def marketplace_ado_query(req: ADOQueryRequest):
    try:
        # Override environment temporarily for this request context
        os.environ["ADO_ORG_URL"] = f"https://dev.azure.com/{req.ado_org}/"
        os.environ["ADO_PROJECT"] = req.ado_project
        os.environ["ADO_CREDENTIAL"] = req.ado_token
        
        result_markdown = await ado_query_agent.process_query(req.query)
        return {"response": result_markdown}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

class ChatRequest(BaseModel):
    message: str
    context: Optional[Dict[str, Any]] = None

@app.post("/api/chat", responses={400: {"description": "Bad Request"}, 404: {"description": "Not Found"}, 500: {"description": "Internal Server Error"}})
async def chat_endpoint(req: ChatRequest):
    try:
        response = await router_agent.route_query(req.message, req.context)
        return response
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

class DraftTestCasesRequest(BaseModel):
    backlog_json: Dict[str, Any]
    analysis_id: Optional[str] = None

@app.post("/api/agents/draft-test-cases", responses={400: {"description": "Bad Request"}, 404: {"description": "Not Found"}, 500: {"description": "Internal Server Error"}})
async def draft_test_cases_endpoint(req: DraftTestCasesRequest, db: Session = Depends(get_db)):
    try:
        config = {"configurable": {"thread_id": req.analysis_id}}
        try:
            state_result = await swarm_graph.ainvoke(None, config=config)
            markdown_content = state_result.get("test_cases")
        except Exception as e:
            print(f" LangGraph state lost. Falling back to direct node invocation. ({str(e)})")
            from graph.nodes import test_cases_node
            import json
            state_mock = {
                "backlog": json.loads(req.backlog_json) if isinstance(req.backlog_json, str) else req.backlog_json
            }
            res = await test_cases_node(state_mock)
            markdown_content = res.get("test_cases")
        
        if req.analysis_id:
            analysis = db.query(Analysis).filter(Analysis.id == req.analysis_id).first()
            if analysis:
                if analysis.results is not None:
                    results_copy = dict(analysis.results)
                    results_copy["test_cases"] = markdown_content
                    analysis.results = results_copy
                    
                analysis.test_cases = markdown_content
                db.commit()
                
        return {"test_cases": markdown_content}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
class RegenerateRequest(BaseModel):
    artifact_type: str # 'functional_spec', 'reviews', 'backlog', 'test_cases'
    current_content: str
    feedback: str
    analysis_id: str | None = None

@app.post("/api/agents/regenerate-artifact", responses={400: {"description": "Bad Request"}, 404: {"description": "Not Found"}, 500: {"description": "Internal Server Error"}})
async def regenerate_artifact(req: RegenerateRequest, db: Session = Depends(get_db)):
    try:
        prompt = f"""
You are an expert Business Analyst Agent. The user has provided feedback on an artifact. 
Please apply the user's feedback and rewrite the artifact.

USER FEEDBACK:
{req.feedback}

CURRENT CONTENT:
{req.current_content}

OUTPUT FORMAT:
Output ONLY the rewritten artifact, preserving its exact original structure (Markdown or JSON array). Do not include any conversational filler.
"""
        from services.llm_service import LLMService
        llm = LLMService()
        new_content = await llm.call(prompt, provider="azure", agent_name="RegenerationAgent")
        
        if req.analysis_id:
            analysis = db.query(Analysis).filter(Analysis.id == req.analysis_id).first()
            if analysis and analysis.results:
                results_copy = dict(analysis.results)
                
                # Try to parse if it's JSON backlog or test cases
                import json
                parsed_content = new_content
                if req.artifact_type in ['backlog', 'test_cases', 'reviews']:
                    try:
                        clean_str = new_content.strip()
                        if clean_str.startswith('```'):
                            import re
                            clean_str = re.sub(r'^```[a-z]*\n', '', clean_str, flags=re.I)
                            clean_str = re.sub(r'\n```$', '', clean_str).strip()
                        parsed_content = json.loads(clean_str)
                    except Exception:
                        pass # Fallback to string if parsing fails
                        
                results_copy[req.artifact_type] = parsed_content
                analysis.results = results_copy
                
                if req.artifact_type == "functional_spec": analysis.functional_spec = new_content
                if req.artifact_type == "test_cases": analysis.test_cases = new_content
                db.commit()
                
        return {"content": new_content}
    except Exception as e:
        print(f" Error regenerating artifact: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

class QAGenerateRequest(BaseModel):
    item_id: str

@app.post("/api/qa/generate", responses={400: {"description": "Bad Request"}, 404: {"description": "Not Found"}, 500: {"description": "Internal Server Error"}})
async def qa_generate_endpoint(req: QAGenerateRequest):
    try:
        markdown_content = await test_case_agent.generate_tests_for_workitem(req.item_id)
        return {"markdown": markdown_content}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

class QASyncRequest(BaseModel):
    parent_id: str
    markdown_content: str

@app.post("/api/qa/sync", responses={400: {"description": "Bad Request"}, 404: {"description": "Not Found"}, 500: {"description": "Internal Server Error"}})
async def qa_sync_endpoint(req: QASyncRequest):
    try:
        result = await test_case_agent.sync_tests_to_ado(req.parent_id, req.markdown_content)
        if result.get("status") == "error":
            raise RuntimeError(result.get("message"))
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/qa/generate-from-brd", responses={400: {"description": "Bad Request"}, 404: {"description": "Not Found"}, 500: {"description": "Internal Server Error"}})
async def qa_generate_from_brd(file: UploadFile = File(...)):
    """
    Generates QA test cases directly from an uploaded BRD file (PDF, DOCX, TXT)
    using Approach 3: Auto-Backlog Pipeline (BRD -> BacklogGenAgent -> TestCaseAgent).
    """
    from pathlib import Path

    doc_id = uuid.uuid4()

    original_filename = file.filename or ""
    extension = Path(original_filename).suffix.lower()

    allowed_extensions = {".pdf", ".docx", ".doc", ".txt",".pptx", ".xlsx", ".csv"}

    if extension not in allowed_extensions:
        raise HTTPException(
            status_code=400,
            detail="Unsupported file type"
        )

    temp_dir = Path("temp")
    temp_dir.mkdir(exist_ok=True)

    temp_path = temp_dir / f"temp_qa_brd_{doc_id}{extension}"

    async with aiofiles.open(temp_path, "wb") as buffer:
        await buffer.write(await file.read())
        
    try:
        # 1. Extract raw text
        text_content = ""
        is_pdf = file.content_type == "application/pdf" or file.filename.lower().endswith(".pdf")
        is_docx = file.filename.lower().endswith(".docx") or file.filename.lower().endswith(".doc")
        
        if is_pdf:
            try:
                from services.adi_service import AzureDocIntelService
                adi = AzureDocIntelService()
                text_content = adi.extract_text(temp_path)
            except Exception:
                doc = fitz.open(temp_path)
                for page in doc:
                    text_content += page.get_text()
                doc.close()
        elif is_docx:
            try:
                import docx
                doc = docx.Document(temp_path)
                text_content = "\n".join([p.text for p in doc.paragraphs if p.text])
            except Exception:
                async with aiofiles.open(temp_path, "r", encoding="utf-8", errors="ignore") as f:
                    text_content = await f.read()
        else:
            async with aiofiles.open(temp_path, "r", encoding="utf-8", errors="ignore") as f:
                text_content = await f.read()
                
        if not text_content or not text_content.strip():
            raise HTTPException(status_code=400, detail="Failed to extract text content from the uploaded BRD document.")

        # 2. Extract Functional Requirements
        from agents.extraction import ExtractionAgent
        extractor = ExtractionAgent()
        print(f" [API: /api/qa/generate-from-brd] Extracting functional requirements for '{file.filename}'...")
        extraction_res = await extractor.extract_content(text_content, context_type="document")
        raw_reqs = extraction_res.get("functional_requirements", [])

        # 3. Auto-Backlog Generation (Approach 3)
        from agents.backlog_gen import BacklogGenAgent
        backlog_agent = BacklogGenAgent()
        print(f" [API: /api/qa/generate-from-brd] Generating Auto-Backlog for '{file.filename}'...")
        backlog_data = await backlog_agent.generate_backlog(trd_content=text_content, raw_requirements=raw_reqs)
        
        # 4. Read Existing Repo Specs for Coverage Audit
        existing_specs = []
        try:
            repo_tests_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "playwright_tests")
            if os.path.exists(repo_tests_dir):
                for fname in os.listdir(repo_tests_dir):
                    if fname.endswith(".spec.ts") or fname.endswith(".spec.js"):
                        fpath = os.path.join(repo_tests_dir, fname)
                        async with aiofiles.open(fpath, "r", encoding="utf-8", errors="ignore") as f:
                            content = await f.read()
                            test_matches = re.findall(r"test\s*\(\s*['\"]([^'\"]+)['\"]", content)
                            existing_specs.append({
                                "filename": fname,
                                "test_titles": test_matches,
                                "test_count": len(test_matches)
                            })
        except Exception as ex:
            print(f"WARN: Could not read repo specs: {ex}")

        # 5. QA Test Case Generation
        from agents.test_case_agent import TestCaseAgent
        test_agent = TestCaseAgent()
        backlog_str = json.dumps(backlog_data) if isinstance(backlog_data, (dict, list)) else str(backlog_data)
        
        print(f" [API: /api/qa/generate-from-brd] Drafting Test Cases & Playwright Scripts for '{file.filename}'...")
        test_cases = await test_agent.draft_test_cases(backlog_json=backlog_str, functional_spec=text_content, existing_specs=existing_specs)
        
        return {"test_cases": test_cases}
    except Exception as e:
        print(f" [API: /api/qa/generate-from-brd] ERROR: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to generate test cases from BRD: {str(e)}")
    finally:
        if temp_path.exists():
            temp_path.unlink()

class QAPdfExportRequest(BaseModel):
    title: Optional[str] = "QA Test Suite"
    test_cases: Any

@app.post("/api/qa/export-pdf", responses={400: {"description": "Bad Request"}, 404: {"description": "Not Found"}, 500: {"description": "Internal Server Error"}})
async def qa_export_pdf(req: QAPdfExportRequest):
    """
    Generates a printable, styled HTML document for downloading QA Test Cases & Playwright scripts in PDF format.
    """
    from fastapi.responses import HTMLResponse
    import json
    import re
    import base64
    import os

    title = req.title or "QA Test Suite"
    raw_data = req.test_cases
    
    tc_list = []
    script_code = ""

    if isinstance(raw_data, str):
        try:
            raw_data = json.loads(raw_data)
        except Exception:
            pass

    if isinstance(raw_data, dict):
        tc_list = raw_data.get("test_cases") or raw_data.get("cases") or []
        script_code = raw_data.get("playwright_script") or raw_data.get("script") or ""
    elif isinstance(raw_data, list):
        tc_list = raw_data

    # Encode logo
    logo_base64 = ""
    try:
        base_dir = os.path.dirname(os.path.abspath(__file__))
        logo_path = os.path.join(base_dir, "..", "frontend", "public", "assets", "Valuemomentum_logo_dark.png")
        if os.path.exists(logo_path):
            async with aiofiles.open(logo_path, "rb") as img_f:
                logo_base64 = base64.b64encode(await img_f.read()).decode("utf-8")
    except Exception:
        pass

    covered_count = sum(1 for tc in tc_list if isinstance(tc, dict) and str(tc.get('coverage_status')).upper() == 'ALREADY_COVERED')
    total_count = len(tc_list)
    new_count = total_count - covered_count
    covered_pct = round((covered_count / total_count * 100)) if total_count > 0 else 0
    new_pct = 100 - covered_pct if total_count > 0 else 0

    tc_rows = ""
    for idx, tc in enumerate(tc_list, 1):
        if not isinstance(tc, dict): continue
        tc_id = tc.get('test_case_id') or tc.get('id') or f'TC-{str(idx).zfill(3)}'
        tc_title = tc.get('title') or tc.get('name') or 'Test Scenario'
        story_name = tc.get('user_story_title') or tc.get('user_story_name') or tc.get('user_story_id') or 'General Story'
        test_type = tc.get('type') or tc.get('test_type') or 'Functional'
        priority = tc.get('priority') or 'High'
        coverage_status = tc.get('coverage_status') or 'NEW_TEST_REQUIRED'
        
        coverage_badge = '<span class="badge badge-coverage-new">🆕 New Coverage</span>'
        if str(coverage_status).upper() == 'ALREADY_COVERED':
            coverage_badge = '<span class="badge badge-coverage-covered">🟢 Covered in Repo</span>'

        so = tc.get('scenario_outline')
        gherkin_text = tc.get('gherkin_scenario') or ''
        if gherkin_text and isinstance(so, dict) and 'headers' in so:
            for h in so.get('headers', []):
                gherkin_text = re.sub(r"''|\"\"", f'"<{h}>"', gherkin_text, count=1)

        gherkin_html = ""
        if gherkin_text:
            gherkin_html = f"<div style='margin-top:6px; background:#0f172a; color:#38bdf8; padding:8px 10px; border-radius:6px; font-family:Consolas, monospace; font-size:0.78rem; white-space:pre-wrap;'>{gherkin_text}</div>"

        # Scenario Outline Examples Table rendering
        outline_html = ""
        if isinstance(so, dict) and 'headers' in so and 'examples' in so:
            headers_th = "".join([f"<th style='padding:4px 8px; font-size:0.75rem;'>{h}</th>" for h in so.get('headers', [])])
            rows_tr = "".join([
                "<tr>" + "".join([f"<td style='padding:4px 8px; font-size:0.75rem;'>{cell}</td>" for cell in row]) + "</tr>"
                for row in so.get('examples', [])
            ])
            outline_html = f"""
            <div style="margin-top:6px;">
                <strong style="font-size:0.75rem; color:#475569;">Scenario Outline Examples:</strong>
                <table style="margin-top:4px; font-size:0.75rem; border:1px solid #cbd5e1;">
                    <thead><tr style="background:#f1f5f9;">{headers_th}</tr></thead>
                    <tbody>{rows_tr}</tbody>
                </table>
            </div>
            """

        steps = tc.get('steps') or []
        if isinstance(steps, list):
            steps_formatted = "<ol style='margin:0; padding-left:16px; font-size:0.82rem;'>" + "".join([f"<li>{s.get('action') if isinstance(s, dict) else s}</li>" for s in steps]) + "</ol>"
        else:
            steps_formatted = str(steps)

        expected = tc.get('expected_result') or 'Expected validation passes'

        tc_rows += f"""
        <tr style="page-break-inside: avoid;">
            <td><strong style="color:#0284c7;">{tc_id}</strong><br/>{coverage_badge}</td>
            <td><strong>{tc_title}</strong><br/><small style="color:#64748b;">🔗 {story_name}</small>{gherkin_html}{outline_html}</td>
            <td><span class="badge badge-priority">{priority}</span></td>
            <td><span class="badge badge-type">{test_type}</span></td>
            <td>{steps_formatted}</td>
            <td>{expected}</td>
        </tr>
        """

    script_html = ""
    if script_code:
        script_html = f"""
        <div style="margin-top: 30px; page-break-before: always;">
            <h2>🎭 Playwright TypeScript Automation Suite</h2>
            <pre><code>{script_code}</code></pre>
        </div>
        """

    html = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8"/>
    <title>QA Test Cases - {title}</title>
    <style>
        @media print {{
            .no-print {{ display: none !important; }}
            body {{ padding: 0 !important; background: #fff !important; }}
            .page-break {{ page-break-before: always; }}
            tr {{ page-break-inside: avoid !important; break-inside: avoid !important; }}
        }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;
            padding: 40px 60px;
            line-height: 1.6;
            color: #1e293b;
            max-width: 1100px;
            margin: 0 auto;
            background: #f8fafc;
        }}
        .header {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 24px;
            border-bottom: 2px solid #e2e8f0;
            padding-bottom: 16px;
        }}
        .title-banner {{
            background: linear-gradient(135deg, #0f172a 0%, #0284c7 100%);
            color: white;
            padding: 24px 32px;
            border-radius: 10px;
            margin-bottom: 20px;
        }}
        .title-banner h1 {{ margin: 0; font-size: 1.6rem; font-weight: 700; }}
        .title-banner p {{ margin: 4px 0 0 0; opacity: 0.9; font-size: 0.9rem; }}
        .coverage-summary-bar {{
            background: #f1f5f9;
            border: 1px solid #cbd5e1;
            border-radius: 8px;
            padding: 12px 20px;
            margin-bottom: 24px;
            display: flex;
            justify-content: space-between;
            align-items: center;
            font-size: 0.9rem;
            color: #0f172a;
        }}
        table {{
            width: 100%;
            border-collapse: collapse;
            margin: 20px 0;
            font-size: 0.88rem;
        }}
        th, td {{
            border: 1px solid #cbd5e1;
            padding: 10px 12px;
            text-align: left;
            vertical-align: top;
        }}
        th {{
            background-color: #f1f5f9;
            color: #0f172a;
            font-weight: 600;
        }}
        .badge {{
            display: inline-block;
            padding: 2px 8px;
            border-radius: 4px;
            font-size: 0.75rem;
            font-weight: 600;
        }}
        .badge-priority {{ background: #fef3c7; color: #92400e; }}
        .badge-type {{ background: #e0f2fe; color: #0369a1; }}
        .badge-coverage-covered {{ background: #dcfce7; color: #15803d; border: 1px solid #86efac; }}
        .badge-coverage-new {{ background: #e0f2fe; color: #0369a1; border: 1px solid #7dd3fc; }}
        pre {{
            background: #0f172a;
            color: #38bdf8;
            padding: 16px;
            border-radius: 8px;
            overflow-x: auto;
            font-family: Consolas, Monaco, monospace;
            font-size: 0.85rem;
            white-space: pre-wrap;
        }}
        .btn-print {{
            background: #0284c7;
            color: white;
            border: none;
            padding: 10px 20px;
            border-radius: 8px;
            font-weight: 600;
            cursor: pointer;
            box-shadow: 0 4px 12px rgba(2, 132, 199, 0.3);
            font-size: 0.9rem;
        }}
        .no-print-bar {{
            position: fixed;
            top: 20px;
            right: 20px;
            z-index: 9999;
        }}
    </style>
</head>
<body>
    <div class="no-print-bar no-print">
        <button onclick="window.print()" class="btn-print">🖨️ Save as PDF / Print</button>
    </div>

    <div class="header">
        <div class="logo">
            {f'<img src="data:image/png;base64,{logo_base64}" style="height: 44px;" />' if logo_base64 else '<strong style="font-size:1.2rem; color:#0284c7;">ValueMomentum</strong>'}
        </div>
        <div style="text-align: right; font-size: 0.8rem; color: #64748b;">
            <strong>QUALITY ASSURANCE SPECIFICATION</strong><br/>
            Generated by BA Agent QA Architect
        </div>
    </div>

    <div class="title-banner">
        <h1>QA Test Suite & Automation Specification</h1>
        <p>Target: {title} | Total Test Cases: {total_count}</p>
    </div>

    <div class="coverage-summary-bar">
        <span><strong>📊 Existing Test Coverage Audit:</strong> <span style="color:#15803d; font-weight:700;">{covered_count} Covered in Repo ({covered_pct}%)</span> &nbsp;|&nbsp; <span style="color:#0369a1; font-weight:700;">{new_count} New Coverage Required ({new_pct}%)</span></span>
        <span>Total Scenarios: {total_count}</span>
    </div>

    <h2>1. Manual BDD Test Cases</h2>
    <table>
        <thead>
            <tr>
                <th style="width: 10%;">TC ID</th>
                <th style="width: 25%;">Test Title & Story</th>
                <th style="width: 10%;">Priority</th>
                <th style="width: 12%;">Type</th>
                <th style="width: 23%;">Execution Steps</th>
                <th style="width: 20%;">Expected Result</th>
            </tr>
        </thead>
        <tbody>
            {tc_rows if tc_rows else '<tr><td colspan="6">No test cases generated.</td></tr>'}
        </tbody>
    </table>

    {script_html}

    <script>
        window.onload = function() {{
            setTimeout(function() {{
                window.print();
            }}, 500);
        }};
    </script>
</body>
</html>"""
    return HTMLResponse(content=html)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host=os.getenv("HOST", "0.0.0.0"), port=8000)



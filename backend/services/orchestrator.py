import uuid
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime

from models.models import ProjectStateModel
from services.db_service import SessionLocal

# Import existing agents
from agents.extraction import ExtractionAgent
from agents.analysis import AnalysisAgent
from agents.functional_spec import FunctionalSpecAgent
from agents.backlog_gen import BacklogGenAgent
from agents.reviewers import QAReviewer, SecurityReviewer, UXReviewer
from agents.diagram_gen import DiagramAgent
from agents.context_agent import ContextAgent
from agents.guard_agent import GuardAgent
from agents.automation import AutomationAgent
from agents.critic_agent import CriticAgent
from agents.knowledge_agent import KnowledgeAgent
from agents.ambiguity_agent import AmbiguityAgent
from agents.architecture_agent import ArchitectureAgent
from services.audit_service import AuditService
import asyncio

class RequifyOrchestrator:
    """
    Advanced Multi-Agent Orchestrator for Requify.
    Manages state transitions, agent handoffs, and quality guardrails.
    """
    def __init__(self):
        self.extraction_agent = ExtractionAgent()
        self.analysis_agent = AnalysisAgent()
        self.functional_spec_agent = FunctionalSpecAgent()
        self.backlog_agent = BacklogGenAgent()
        
        # Optimized Intelligence Agents
        self.diagram_agent = DiagramAgent()
        self.context_agent = ContextAgent()
        self.guard_agent = GuardAgent()
        self.critic_agent = CriticAgent()
        self.knowledge_agent = KnowledgeAgent()
        self.ambiguity_agent = AmbiguityAgent()
        self.architecture_agent = ArchitectureAgent()
        
        # Specialist Council
        self.qa_reviewer = QAReviewer()
        self.security_reviewer = SecurityReviewer()
        self.ux_reviewer = UXReviewer()

    def get_or_create_project(self, document_id: str, lob: str = "General") -> ProjectStateModel:
        db = SessionLocal()
        try:
            project = db.query(ProjectStateModel).filter(ProjectStateModel.document_id == document_id).first()
            if not project:
                project = ProjectStateModel(
                    project_id=str(uuid.uuid4()),
                    document_id=document_id,
                    lob=lob
                )
                db.add(project)
                db.commit()
                db.refresh(project)
            return project
        finally:
            db.close()
            
    def update_project_extraction(self, document_id: str, data: dict):
        db = SessionLocal()
        try:
            project = db.query(ProjectStateModel).filter(ProjectStateModel.document_id == document_id).first()
            if project:
                project.extraction = data
                project.quality_score = float(data.get("quality_score", 0.0))
                project.update_status("EXTRACTED", "Extraction completed.")
                db.commit()
        finally:
            db.close()

    async def run_extraction(self, document_id: str, text: str, context_type: str = "document", file_hash: str = None):
        db = SessionLocal()
        try:
            project = db.query(ProjectStateModel).filter(ProjectStateModel.document_id == document_id).first()
            if not project: raise Exception("Project not found")
            
            project.update_status("EXTRACTING", f"Starting extraction for LOB: {project.lob} via {context_type.upper()} channel.")
            db.commit()
            
            try:
                result = await self.extraction_agent.extract_content(text, context_type=context_type)
                project.extraction = result
                project.quality_score = float(result.get("quality_score", 0.0))
                
                # --- PHASE 1: Ambiguity Detection ---
                project.update_status("DETECTING_AMBIGUITY", "Ambiguity Agent is analyzing requirements for clarity.")
                db.commit()
                ambiguity_report = await self.ambiguity_agent.detect_ambiguities(result)
                project.ambiguity_report = ambiguity_report
                
                status_msg = f"Requirements orchestrated. BRD Quality: {project.quality_score}. "
                if ambiguity_report.get("is_ambiguous"):
                    status_msg += f" Ambiguities detected ({len(ambiguity_report.get('ambiguities', []))})."
                else:
                    status_msg += " No major ambiguities."
                    
                project.update_status("EXTRACTED", status_msg)
                db.commit()
                
                # --- PHASE 3: Memory Indexing ---
                project.update_status("INDEXING", "Indexing requirements into Organizational Memory (Azure AI Search).")
                db.commit()
                deterministic_proj_id = f"doc_{file_hash[:16]}" if file_hash else document_id
                indexed_count = await self.knowledge_agent.ingest_project_requirements(
                    document_id, result, lob=project.lob, project_id=deterministic_proj_id
                )
                print(f"--- [INFO] Indexed/Upserted {indexed_count} requirements to Azure Memory (Key: {deterministic_proj_id}). ---")

                # --- PHASE 4: Audit Logging (Governance) ---
                AuditService.log_action(
                    document_id=document_id,
                    agent_name="AmbiguityAgent",
                    action="STRESS_TEST_COMPLETE",
                    reasoning=f"Analyzed {len(result.get('functional_requirements', []))} requirements for clarity.",
                    payload=ambiguity_report
                )

                # Return combined result so frontend can display ambiguity
                from services.storage_service import storage_service
                storage_service.save_json_artifact(document_id, "extraction", result)

                print(f" [Orchestrator] Extraction completed for {document_id}")
                return {
                    "extraction": result,
                    "ambiguity_report": ambiguity_report,
                    "indexed_count": indexed_count
                }
            except Exception as e:
                project.update_status("FAILED", f"Extraction failed: {str(e)}")
                db.commit()
                raise
        finally:
            db.close()

            
    async def run_gap_analysis(self, document_id: str, answers: list = None, enabled_modules: list = None):
        """
        Executes modular analysis based on user selection.
        """
        if not enabled_modules:
            enabled_modules = ['gaps', 'functional_spec', 'flow', 'backlog'] # Default all

        db = SessionLocal()
        try:
            project = db.query(ProjectStateModel).filter(ProjectStateModel.document_id == document_id).first()
            if not project:
                raise Exception(f"Project for doc {document_id} not found.")

            project.update_status("ANALYZING", f"Agent initiating modular analysis: {', '.join(enabled_modules)}")
            db.commit()
            try:
                #  SECURITY GUARDRAIL: PII Detection & MASKING
                raw_text = str(project.extraction)
                pii_report = self.guard_agent.detect_pii(raw_text)
                if not pii_report["safe"]:
                    project.update_status("SECURITY_WARNING", f"Potential PII detected: {', '.join(pii_report['flagged_types'])}")
                    db.commit()
                    print(f" SECURITY GUARDRAIL: PII flagged in Analysis {project.document_id}. Applying Active Masking...")
                
                # Apply Masking
                masked_text = self.guard_agent.mask_pii(raw_text)
                # Create a sanitized context for agents
                sanitized_extraction = {**(project.extraction or {}), "text": masked_text}

                # --- PHASE 3: Institutional Memory Retrieval ---
                project.update_status("RECALLING", "Knowledge Agent is retrieving domain knowledge from Azure Search.")
                db.commit()
                
                reqs = (project.extraction or {}).get("functional_requirements", [])
                
                # Get semantic context based on the first few requirements
                memory_query = reqs[0].get("description", "") if reqs else "P&C Insurance Requirements"
                institutional_memory = await self.knowledge_agent.retrieve_relevant_context(memory_query, lob=project.lob)
                
                # Check if knowledge retrieval was successful or returned empty fallback message
                if "No domain guidelines" in institutional_memory:
                    print(f"WARN: No domain knowledge found for LOB {project.lob}. Applying low confidence penalty.")
                    project.quality_score = max(0.0, project.quality_score - 0.2) # Penalty for missing domain context
                
                # --- PHASE 2: Agentic Council (Swarm Architecture) ---
                project.update_status("COUNCIL_REVIEW", "Agentic Council (Security, UX, QA, Arch) is performing parallel analysis.")
                db.commit()
                
                # 1. DEFINE COUNCIL TASKS
                council_tasks = {
                    "qa": self.qa_reviewer.review(reqs),
                    "security": self.security_reviewer.review(reqs),
                    "ux": self.ux_reviewer.review(reqs),
                    "architecture": self.architecture_agent.recommend(reqs, context=masked_text[:1000], institutional_memory=institutional_memory),
                    "gaps": self.analysis_agent.analyze_gaps(sanitized_extraction, answers=answers, institutional_memory=institutional_memory) if 'gaps' in enabled_modules else asyncio.sleep(0, result={"reviews": {}, "gaps": []}),
                    "diagram": self.diagram_agent.generate_process_flow(reqs) if 'flow' in enabled_modules else asyncio.sleep(0, result={"nodes": [], "edges": []})
                }


                # 2. EXECUTE COUNCIL IN PARALLEL
                council_results = await asyncio.gather(*council_tasks.values(), return_exceptions=True)
                results_map = {}
                for key, result in zip(council_tasks.keys(), council_results):
                    if isinstance(result, Exception):
                        print(f" AGENT FAILURE : {key} failed with error: {str(result)}")
                        results_map[key] = {
                            "status": "DEGRADED",
                            "error": str(result),
                            "warning": f"The {key} agent went offline during analysis. Manual review required.",
                            "gaps": [] if key == "gaps" else None,
                            "reviews": {} if key == "gaps" else None,
                            "nodes": [] if key == "diagram" else None,
                            "edges": [] if key == "diagram" else None
                        }
                    else:
                        results_map[key] = result
                
                # 3. CONSOLIDATE RESULTS
                ana_res = results_map["gaps"]
                diag_res = results_map["diagram"]
                
                # Store full Council results in Project State
                project.reviews = {
                    "QA": results_map["qa"],
                    "Security": results_map["security"],
                    "UX": results_map["ux"],
                    "Architecture": results_map["architecture"],
                    "GapAnalysis": ana_res.get("reviews", {})
                }
                
                # --- PHASE 4: Audit Logging (Council Decision) ---
                AuditService.log_action(
                    document_id=document_id,
                    agent_name="AgenticCouncil",
                    action="CONSENSUS_REACHED",
                    reasoning="Parallel reviews complete for Security, UX, QA, and Architecture.",
                    payload=project.reviews
                )
                
                project.gaps = ana_res.get("gaps", [])
                project.diagram = diag_res
                db.commit()
                
                from services.storage_service import storage_service
                storage_service.save_json_artifact(document_id, "gaps", ana_res)
                storage_service.save_json_artifact(document_id, "reviews", project.reviews)
                
                # 3. RUN ADVERSARIAL CRITIC (Power Pillar #2)
                if 'gaps' in enabled_modules:
                    project.update_status("CRITIQUING", "Critic Agent performing adversarial QA on gaps.")
                    db.commit()
                    try:
                        critic_res = await self.critic_agent.review_artifact("Gap Analysis", ana_res, raw_text)
                    except Exception as e:
                        print(f" CRITIC FAILURE : {str(e)}")
                        critic_res = {
                            "status": "DEGRADED",
                            "error": str(e),
                            "critic_suggestion": "Critic offline. Gap Analysis accepted with Degraded status."
                        }
                    current_critic = dict(project.critic_reviews) if project.critic_reviews else {}
                    current_critic["gaps"] = critic_res
                    project.critic_reviews = current_critic
                    db.commit()

                project.update_status("ANALYZED", "Modular analysis suite and Critic review complete.")
                db.commit()
                return {
                    "gaps": ana_res,
                    "reviews": project.reviews,
                    "diagram": diag_res,
                    "critic_review": project.critic_reviews.get("gaps")
                }
            except Exception as e:
                project.update_status("FAILED", f"Deep Analysis failed: {str(e)}")
                db.commit()
                raise
        finally:
            db.close()

    async def run_functional_spec_generation(self, document_id: str, tech_context: str = None):
        db = SessionLocal()
        try:
            project = db.query(ProjectStateModel).filter(ProjectStateModel.document_id == document_id).first()
            if not project: raise Exception(f"Project state for {document_id} not found.")

            project.update_status("GENERATING_SPEC", "Architect Agent synthesizing the Functional Specification.")
            db.commit()
            try:
                project_dna = await self.context_agent.get_project_context(db=db)
                
                # Fetch structured DNA bits
                dna_vault = {
                    "TECH_STACK": self.context_agent.get_dna(db, "TECH_STACK"),
                    "USER_PREFERENCES": self.context_agent.get_dna(db, "PREFERENCES"),
                    "GLOSSARY": self.context_agent.get_dna(db, "GLOSSARY")
                }
                
                # PILLAR 6: Knowledge RAG (Vector Search)
                project.update_status("RECALLING", "Knowledge Agent is injecting domain context for Functional Spec generation.")
                db.commit()
                reqs = (project.extraction or {}).get("functional_requirements", [])
                memory_query = reqs[0].get("description", "") if reqs else "Technical Specification requirements"
                corporate_standards = await self.knowledge_agent.retrieve_relevant_context(memory_query, lob=project.lob)
                
                functional_spec = await self.functional_spec_agent.generate_spec(
                    project.extraction, 
                    project.gaps, 
                    project.lob, 
                    context=project_dna, 
                    dna=dna_vault,
                    corporate_standards=corporate_standards,
                    council_reviews=project.reviews,
                    tech_context=tech_context
                )

                #  Adversarial Review for Functional Spec (Initial)
                project.update_status("CRITIQUING", "Critic Agent performing adversarial QA on Technical Spec.")
                db.commit()
                critic_res = await self.critic_agent.review_artifact(
                    "Functional Spec", 
                    functional_spec, 
                    source_brd=raw_text, 
                    extraction=project.extraction
                )
                
                #  SELF-CORRECTION REFLECTION LOOP
                iteration = 0
                max_reflections = 1  # 1-pass reflection loop enabled for self-correction
                while critic_res.get("status") == "REQUEST_CORRECTION" and critic_res.get("confidence_score", 1.0) < 0.85 and iteration < max_reflections:
                    iteration += 1
                    print(f" [REFLECTION LOOP {iteration}] Critic found issues (Score: {critic_res.get('confidence_score')}). Self-correcting...")
                    
                    # Re-run Agent with feedback
                    functional_spec = await self.functional_spec_agent.generate_spec(
                        project.extraction, 
                        project.gaps, 
                        project.lob, 
                        context=project_dna, 
                        dna=dna_vault,
                        feedback=critic_res.get("critic_suggestion")
                    )
                    
                    # Re-review
                    critic_res = await self.critic_agent.review_artifact(
                        "Functional Spec", 
                        functional_spec, 
                        source_brd=raw_text, 
                        extraction=project.extraction
                    )
                
                project.functional_spec = functional_spec
                current_critic = dict(project.critic_reviews) if project.critic_reviews else {}
                current_critic["functional_spec"] = critic_res
                project.critic_reviews = current_critic
                
                project.update_status("COMPLETED", f"Functional Spec generated and self-corrected ({iteration} reflections).")
                db.commit()

                from services.storage_service import storage_service
                storage_service.save_json_artifact(document_id, "functional_spec", functional_spec)

                # --- PHASE 4: Audit Logging (Technical Specification) ---
                AuditService.log_action(
                    document_id=document_id,
                    agent_name="ArchitectAgent",
                    action="Functional Spec_SYNTHESIZED",
                    reasoning=f"Integrated council reviews and institutional memory into final Technical Spec with {iteration} self-correction reflections.",
                    payload={"lob": project.lob, "iterations": iteration}
                )

                
                print(f" [Orchestrator] Functional Spec Generation completed. Returning artifacts.")
                return {"functional_spec": functional_spec, "critic_review": critic_res, "reflections": iteration}
            except Exception as e:
                project.update_status("FAILED", f"Functional Spec generation failed: {str(e)}")
                db.commit()
                raise
        finally:
            db.close()

    async def run_backlog_generation(self, document_id: str, functional_spec_content: str):
        db = SessionLocal()
        try:
            project = db.query(ProjectStateModel).filter(ProjectStateModel.document_id == document_id).first()
            if not project: raise Exception(f"Project state for {document_id} not found.")
            
            project.update_status("GENERATING_BACKLOG", "Architect Agent deriving technical hierarchy from Functional Spec.")
            try:
                # 1. Generate Raw Backlog with TRD, NFRs, and Council Reviews
                nfr_content = str((project.extraction or {}).get("non_functional_requirements", []))
                council_reviews = getattr(project, "reviews", {})
                raw_reqs = (project.extraction or {}).get("functional_requirements", [])
                backlog = await self.backlog_agent.generate_backlog(
                    trd_content=functional_spec_content,
                    nfr_content=nfr_content,
                    council_reviews=council_reviews,
                    raw_requirements=raw_reqs
                )
                
                # 2. RUN GUARDRAIL: Integrity Verification
                project.update_status("VERIFYING", "GuardAgent performing Integrity & QA verification against Functional Spec.")
                db.commit()
                integrity_report = await self.guard_agent.verify_backlog_integrity(backlog, functional_spec_content)
                
                project.backlog = backlog
                db.commit()

                from services.storage_service import storage_service
                storage_service.save_json_artifact(document_id, "backlog", backlog)
                
                #  Adversarial Review for Backlog
                project.update_status("CRITIQUING", "Critic Agent performing adversarial QA on Engineering Backlog.")
                db.commit()
                critic_res = await self.critic_agent.review_artifact("Backlog", backlog, functional_spec_content)
                current_critic = dict(project.critic_reviews) if project.critic_reviews else {}
                current_critic["backlog"] = critic_res
                project.critic_reviews = current_critic
                db.commit()

                project.update_status("BACKLOG_READY", "Enterprise Backlog successfully synchronized and verified.")
                db.commit()

                # --- PHASE 4: Audit Logging (Engineering Backlog) ---
                AuditService.log_action(
                    document_id=document_id,
                    agent_name="BacklogAgent",
                    action="BACKLOG_GENERATED",
                    reasoning="Hierarchy derived from Functional Spec and verified for integrity by GuardAgent.",
                    payload={"epics_count": len(backlog.get("epics", []))}
                )
                
                return {
                    "backlog": backlog,
                    "integrity_report": integrity_report,
                    "critic_review": critic_res
                }
            except Exception as e:
                project.update_status("FAILED", f"Backlog generation failed: {str(e)}")
                db.commit()
                raise
        finally:
            db.close()

    async def run_backlog_sync(self, document_id: str, approved_backlog: Dict[str, Any]):
        """
        Formal Human-in-the-Loop Sync Gate.
        Pushes ONLY approved artifacts to Azure DevOps.
        """
        db = SessionLocal()
        try:
            # Note: The API may pass project_id or document_id, but we unified to document_id
            # Let's support both by checking if the ID passed matches project_id or document_id
            project = db.query(ProjectStateModel).filter(
                (ProjectStateModel.document_id == document_id) | (ProjectStateModel.project_id == document_id)
            ).first()
            if not project: raise Exception(f"Project state for {document_id} not found.")

            project.update_status("SYNCING", "Human-approved backlog hierarchy being synchronized to Azure DevOps.")
            db.commit()
            try:
                print(f"\n [Orchestrator] Starting ADO Synchronization Phase for {document_id}")
                result = await self.automation_agent.create_work_items(approved_backlog)
                project.update_status("SYNC_COMPLETE", f"Successfully synchronized {len(result.get('created_items', []))} items to ADO.")
                db.commit()

                # --- PHASE 4: Audit Logging (Governance Gate) ---
                AuditService.log_action(
                    document_id=document_id,
                    agent_name="GovernanceAgent",
                    action="ADO_SYNC_SUCCESS",
                    reasoning="Human-approved backlog successfully pushed to production SDLC (Azure DevOps).",
                    payload={"items_pushed": len(result.get('created_items', []))}
                )

                
                print(f" [Orchestrator] ADO Synchronization completed.")
                return result
            except Exception as e:
                project.update_status("SYNC_FAILED", f"Synchronization failed: {str(e)}")
                db.commit()
                raise
        finally:
            db.close()

    async def run_test_case_generation(self, document_id: str, functional_spec_content: str = "", backlog_content: Any = None):
        """
        Generates exhaustive test cases (15-35+ scenarios + Playwright TypeScript automation)
        ingesting BOTH the Functional Specification (TRD) AND the Backlog User Stories with Acceptance Criteria.
        """
        db = SessionLocal()
        try:
            project = db.query(ProjectStateModel).filter(ProjectStateModel.document_id == document_id).first()
            if project:
                project.update_status("GENERATING_TESTS", "QA Test Agent deriving comprehensive test suite from TRD + Backlog.")
                db.commit()

            from services.storage_service import storage_service
            if not functional_spec_content and document_id:
                loaded_spec = storage_service.load_json_artifact(document_id, "functional_spec") or (getattr(project, 'trd', None) if project else None)
                if loaded_spec:
                    functional_spec_content = loaded_spec if isinstance(loaded_spec, str) else json.dumps(loaded_spec, indent=2)

            if not backlog_content and document_id:
                loaded_backlog = storage_service.load_json_artifact(document_id, "backlog") or (getattr(project, 'backlog', None) if project else None)
                if loaded_backlog:
                    backlog_content = loaded_backlog

            backlog_str = json.dumps(backlog_content) if isinstance(backlog_content, (dict, list)) else str(backlog_content or "")
            spec_str = json.dumps(functional_spec_content) if isinstance(functional_spec_content, (dict, list)) else str(functional_spec_content or "")

            from agents.test_case_agent import TestCaseAgent
            test_agent = TestCaseAgent()
            test_cases = await test_agent.draft_test_cases(backlog_json=backlog_str, functional_spec=spec_str)

            if document_id:
                storage_service.save_json_artifact(document_id, "test_cases", test_cases)

            if project:
                project.update_status("TESTS_READY", "Comprehensive Test Suite and Playwright scripts generated.")
                db.commit()

            return {"test_cases": test_cases}
        except Exception as e:
            if project:
                project.update_status("FAILED", f"Test case generation failed: {str(e)}")
                db.commit()
            raise
        finally:
            db.close()

# Global shared orchestrator instance
orchestrator = RequifyOrchestrator()

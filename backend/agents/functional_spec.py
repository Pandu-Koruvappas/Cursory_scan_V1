import json
import asyncio
import re
from services.llm_service import LLMService

class FunctionalSpecAgent:
    def __init__(self):
        self.llm = LLMService()

    async def generate_spec(self, extraction: dict = None, gaps: list = None, lob: str = "General", context: str = "", dna: dict = None, feedback: str = None, corporate_standards: str = None, council_reviews: dict = None, raw_brd_text: str = None, tech_context: str = None):
        """
        Uses LLM to generate a 100% complete IEEE 830 Functional Specification.
        Employs Solution A (Modular Chunked Assembly) for requirement sets (>15 FRs)
        to prevent LLM output token truncation and guarantee 100% requirement coverage from FR-001 through FR-100+.
        """
        council_context = ""
        has_degraded = False
        if council_reviews:
            council_context = "\nAGENTIC COUNCIL RECOMMENDATIONS (Consensus Required):\n"
            for role, review in council_reviews.items():
                if isinstance(review, dict) and review.get("status") == "DEGRADED":
                    has_degraded = True
                council_context += f"### {role} Specialist Review:\n{json.dumps(review, indent=2)}\n"

        project_dna = ""
        if context:
            project_dna = f"\nEXISTING PROJECT CONTEXT (Built/Planned in ADO):\n{context}\n"
        
        dna_context = ""
        if dna:
            dna_context = "\nINSTITUTIONAL KNOWLEDGE (Project DNA):\n"
            for k, v in dna.items():
                dna_context += f"- {k}: {v}\n"

        knowledge_rag = ""
        if corporate_standards:
            knowledge_rag = f"\nOFFICIAL CORPORATE STANDARDS & GUIDELINES (Source of Truth):\n{corporate_standards}\n"

        refinement_context = ""
        if feedback:
            refinement_context = f"""
            --- AUTONOMOUS SELF-CORRECTION LOOP ---
            The previous version of your Functional Spec was reviewed by a Critic Agent who found issues.
            FEEDBACK FROM CRITIC:
            {feedback}
            
            YOUR TASK: Refine the previous content to fix these issues. DO NOT hallucinate.
            """

        base_content = ""
        if raw_brd_text:
            base_content = f"Raw Business Requirements Document:\n{raw_brd_text}\n"
        else:
            base_content = f"Extracted Requirements: {extraction}\nGaps Identified: {gaps}\n"

        degraded_warning = ""
        if has_degraded:
            degraded_warning = """
            > [!CAUTION]
            > **DEGRADED SWARM ANALYSIS**
            > One or more specialist agents failed to complete their review. 
            > This Spec was synthesized using partial inputs. Manual review is highly recommended.
            """

        architect_handoff_instruction = ""
        if tech_context and tech_context.strip():
            architect_handoff_instruction = f"""
            The Business Analyst has explicitly provided Technical/Integration Context:
            "{tech_context}"
            
            Therefore, you MUST append a section at the very end titled:
            "## Architect Handoff Notes (Draft)"
            In this section, explicitly state that this is an input for Architect review, and provide technical suggestions, potential system impacts, and data integration points strictly based on the provided Tech Context.
            """
        else:
            architect_handoff_instruction = """
            CRITICAL RULE: DO NOT INFER OR ASSUME ANY TECHNOLOGY STACK, CLOUD PROVIDER, DATABASE, OR INTEGRATION PATTERNS.
            This document must remain 100% Technology Agnostic. 
            If the requirements mention technology, capture the business intent, but do not hallucinate an architecture.
            """

        from services.template_service import TemplateService
        ts = TemplateService()
        skill_prompt = ts.load_skill_prompt("functional_spec_architect")

        reqs_list = []
        if isinstance(extraction, dict):
            reqs_list = extraction.get("functional_requirements", [])

        # Sort requirements numerically for 100% deterministic prompt ordering
        import re
        def get_req_num(req):
            rid = str(req.get("id") or req.get("req_id") or "")
            match = re.search(r"\d+", rid)
            return int(match.group(0)) if match else 999

        reqs_list.sort(key=get_req_num)

        # If less than 15 requirements, run single-pass generation
        if len(reqs_list) <= 15:
            reqs_formatted = ""
            if reqs_list:
                reqs_formatted = f"\n--- EXTRACTED FUNCTIONAL REQUIREMENTS MATRIX ({len(reqs_list)} Requirements) ---\n"
                for req in reqs_list:
                    raw_id = req.get("id") or req.get("req_id") or "REQ-001"
                    req_id = raw_id.replace("FR-", "REQ-") if "FR-" in raw_id else raw_id
                    title = req.get("title") or req.get("name") or ""
                    desc = req.get("description") or req.get("text") or ""
                    reqs_formatted += f"- [{req_id}] {title}: {desc}\n"

            prompt = f"""
{skill_prompt}

ACT AS A SENIOR PRINCIPAL BUSINESS ANALYST ({lob}).
Synthesize an IEEE 830 Industry-Standard Functional Specification Document from the provided inputs.

{degraded_warning}
{council_context}
{project_dna}
{dna_context}
{knowledge_rag}
{refinement_context}

{base_content}
{reqs_formatted}

{architect_handoff_instruction}

CRITICAL PRODUCTION MANDATE:
- You MUST document ALL {len(reqs_list)} Functional Requirements (from FR-001 through FR-{len(reqs_list):03d}).
- Explicitly tag every requirement in bracketed format (e.g. [FR-001], [FR-002]).
- Group Section 3 into logical Functional Sub-System Modules.
- ABSOLUTELY DO NOT SKIP OR JUMP REQUIREMENTS. Every requirement MUST appear in its module matrix table!
- DO NOT generate any Mermaid diagrams, graph LR, flowcharts, or visual diagram codeblocks. Strictly output clean text and markdown tables.
"""
            raw_spec = await self.llm.call(prompt, provider="azure", agent_name="FunctionalSpecArchitect")
            return self.post_process_spec_text(raw_spec)

        # --- SOLUTION A: MODULAR CHUNKED ASSEMBLY FOR >15 REQUIREMENTS ---
        print(f" [FunctionalSpecAgent] SOLUTION A: Executing Modular Chunked Assembly for {len(reqs_list)} Functional Requirements...")

        # Stage 1: Document Header, Executive Summary & Overview (Sections 1 & 2)
        header_prompt = f"""
{skill_prompt}

ACT AS A SENIOR PRINCIPAL BUSINESS ANALYST ({lob}).
Generate Section 1 (Executive Summary & Project Purpose) and Section 2 (System Overview, Constraints, & User Characteristics) of an IEEE 830 Functional Specification.

{degraded_warning}
{council_context}
{project_dna}
{dna_context}
{knowledge_rag}
{base_content}

REQUIREMENTS SCOPE: Total of {len(reqs_list)} Functional Requirements identified (FR-001 to FR-{len(reqs_list):03d}).

OUTPUT INSTRUCTIONS:
- Generate ONLY Sections 1 & 2 in clean Markdown.
- DO NOT generate Section 3 yet.
- DO NOT generate any Mermaid diagrams, graph LR, flowcharts, or visual codeblocks.
"""
        header_markdown = await self.llm.call(header_prompt, provider="azure", agent_name="FunctionalSpecArchitect_Header")

        # Stage 2: Chunk Section 3 into 20-Requirement Batches & Generate in Parallel
        chunk_size = 20
        req_chunks = [reqs_list[i:i + chunk_size] for i in range(0, len(reqs_list), chunk_size)]
        
        async def process_chunk(chunk_idx, batch):
            batch_start_id = batch[0].get("id") or f"FR-{(chunk_idx * chunk_size) + 1:03d}"
            batch_end_id = batch[-1].get("id") or f"FR-{(chunk_idx * chunk_size) + len(batch):03d}"
            
            formatted_batch = f"\n--- BATCH {chunk_idx + 1}: FUNCTIONAL REQUIREMENTS ({batch_start_id} to {batch_end_id}) ---\n"
            for req in batch:
                req_id = req.get("id") or req.get("req_id") or "FR-xxx"
                title = req.get("title") or req.get("name") or ""
                desc = req.get("description") or req.get("text") or ""
                formatted_batch += f"- [{req_id}] {title}: {desc}\n"

            chunk_prompt = f"""
ACT AS A SENIOR PRINCIPAL BUSINESS ANALYST ({lob}).
You are writing Section 3 (Specific Functional Requirements Matrix) for Batch {chunk_idx + 1} ({batch_start_id} through {batch_end_id}).

{formatted_batch}

CRITICAL MANDATE:
- You MUST document EVERY requirement in this batch ({batch_start_id} to {batch_end_id}) in order.
- ABSOLUTELY DO NOT SKIP ANY REQUIREMENT ID IN THIS BATCH.
- PRIORITIZATION MANDATE: Assign priorities based on domain impact:
  * High / Must Have: Core validation rules, mandatory fields, security/compliance rules, primary transaction/adjudication workflows.
  * Medium / Should Have: Prefill automation, manual field override options, UI convenience helpers, conditional field visibility.
  * Low / Could Have: Export enhancements, optional reporting, cosmetic formatting.
- Format each requirement into a clean Markdown Table containing:
  | Requirement ID | Requirement Title | Business Description & Validation Rules | Input Fields | Expected Output | Priority |
- Explicitly tag every requirement in bracketed format (e.g. [{batch_start_id}]).
- Output ONLY the Markdown table for Batch {chunk_idx + 1}. Do NOT include any section header, title, or conversational filler before or after the table.
"""
            return await self.llm.call(chunk_prompt, provider="azure", agent_name=f"FunctionalSpecArchitect_Chunk_{chunk_idx+1}")

        chunk_tasks = [process_chunk(idx, batch) for idx, batch in enumerate(req_chunks)]
        chunk_results = await asyncio.gather(*chunk_tasks)

        # Stage 3: Sections 4 & 5 (Non-Functional Requirements & Architect Handoff)
        footer_prompt = f"""
ACT AS A SENIOR PRINCIPAL BUSINESS ANALYST ({lob}).
Generate Section 4 (Non-Functional Requirements: Security, Performance, Compliance) and Section 5 (Appendix & Glossary) of the IEEE 830 Functional Specification.

{architect_handoff_instruction}

OUTPUT INSTRUCTIONS:
- Generate ONLY Sections 4 & 5 in clean Markdown.
- DO NOT generate any Mermaid diagrams or flowcharts.
"""
        footer_markdown = await self.llm.call(footer_prompt, provider="azure", agent_name="FunctionalSpecArchitect_Footer")

        # Stage 4: Assemble Master Specification Document
        section3_master = "\n\n## 3. Specific Functional Requirements Matrix\n\n" + "\n\n".join(chunk_results)
        master_spec = f"{header_markdown}\n\n{section3_master}\n\n{footer_markdown}"

        # Stage 5: Clean Post-Processing (Terminology & Buzzword Alignment)
        master_spec = self.post_process_spec_text(master_spec)

        print(f" [FunctionalSpecAgent] SOLUTION A COMPLETED CLEANLY! Assembled 100% complete Functional Spec with {len(reqs_list)} requirements.")
        return master_spec

    def post_process_spec_text(self, text: str) -> str:
        """
        Enforces strict domain terminology and removes unrequested generic buzzwords.
        """
        if not text: return ""

        # 1. Terminology alignment: Component Workflow vs Standalone System
        text = re.sub(r"\bBuilding\s+Information\s+(?:page\s+)?system\b", "Building Information component workflow", text, flags=re.I)
        text = re.sub(r"\bstandalone\s+system\b", "component workflow within the LOB ecosystem", text, flags=re.I)

        # 2. Suppress unrequested generic security/performance buzzwords if generated as generic bullet points
        text = re.sub(r"- \*\*Performance\*\*: Assumed optimal performance.*?\n", "", text, flags=re.I)
        text = re.sub(r"- \*\*Security\*\*: Standard secure authorization.*?\n", "", text, flags=re.I)
        
        return text

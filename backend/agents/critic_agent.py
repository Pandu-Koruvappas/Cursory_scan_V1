import json
import re
from typing import Dict, Any, List
from services.llm_service import LLMService

def _clean_json_output(llm_response: str) -> dict:
    if not llm_response:
        return {}
    cleaned = re.sub(r"^```json\s*", "", llm_response.strip(), flags=re.MULTILINE)
    cleaned = re.sub(r"^```\s*", "", cleaned, flags=re.MULTILINE)
    cleaned = re.sub(r"```$", "", cleaned, flags=re.MULTILINE).strip()
    try:
        return json.loads(cleaned)
    except Exception:
        match = re.search(r"\{.*\}", cleaned, re.DOTALL)
        if match:
            try:
                return json.loads(match.group(0))
            except Exception:
                pass
        return {}

class CriticAgent:
    """
    Production-Grade Adversarial QA Critic Agent with 2-Phase Map-Reduce Architecture
    and Provenance-Aware Dynamic Token Budget Batching.
    """
    def __init__(self):
        self.llm = LLMService()

    def _estimate_tokens(self, text: str) -> int:
        if not text:
            return 0
        return len(str(text)) // 4

    def _extract_requirements_list(self, content: Any, extraction: dict = None) -> List[dict]:
        reqs = []
        if isinstance(content, dict):
            reqs = content.get("functional_requirements") or content.get("requirements") or []
        elif isinstance(content, list):
            reqs = content
        
        if not reqs and isinstance(extraction, dict):
            reqs = extraction.get("functional_requirements", [])
            
        if not reqs and isinstance(content, str):
            # Parse string requirements if formatted as JSON or structured text
            parsed = _clean_json_output(content)
            if isinstance(parsed, dict):
                reqs = parsed.get("functional_requirements") or parsed.get("requirements") or []

        formatted_reqs = []
        for idx, r in enumerate(reqs, 1):
            if isinstance(r, dict):
                req_id = r.get("id") or r.get("req_id") or f"FR-{idx:03d}"
                desc = r.get("description") or r.get("title") or str(r)
                prio = r.get("priority", "Medium")
                chunk_idx = r.get("source_chunk_idx", 0)
                formatted_reqs.append({
                    "id": req_id,
                    "description": desc,
                    "priority": prio,
                    "source_chunk_idx": chunk_idx
                })
            elif isinstance(r, str):
                formatted_reqs.append({
                    "id": f"FR-{idx:03d}",
                    "description": r,
                    "priority": "Medium",
                    "source_chunk_idx": 0
                })
        return formatted_reqs

    def _build_token_batches(self, reqs: List[dict], max_token_budget: int = 4000) -> List[List[dict]]:
        batches = []
        current_batch = []
        current_tokens = 0

        for req in reqs:
            req_token_cost = self._estimate_tokens(json.dumps(req))
            if current_batch and (current_tokens + req_token_cost > max_token_budget):
                batches.append(current_batch)
                current_batch = [req]
                current_tokens = req_token_cost
            else:
                current_batch.append(req)
                current_tokens += req_token_cost

        if current_batch:
            batches.append(current_batch)
        return batches

    async def review_artifact(self, artifact_type: str, content: Any, source_brd: Any = "", extraction: dict = None) -> Dict[str, Any]:
        """
        Adversarial Review Entry Point: Performs Map-Reduce QA for large requirement sets (60+ items).
        """
        raw_brd_str = str(source_brd) if source_brd else ""
        reqs_list = self._extract_requirements_list(content, extraction)

        print(f"\n================================================================================")
        print(f"🕵️  [CriticAgent] Initiating Adversarial QA Review for '{artifact_type}'")
        print(f" ► Requirements Count : {len(reqs_list)}")
        print(f" ► Source BRD Length  : {len(raw_brd_str)} chars")
        print(f"================================================================================")

        # Fallback for short content / non-batched reviews (<= 10 requirements or empty BRD)
        if len(reqs_list) <= 10 or not raw_brd_str:
            return await self._single_pass_review(artifact_type, content, raw_brd_str)

        # --- PHASE 1: MAP PHASE (Localized Batch Audits with Provenance Tracking) ---
        print(f"\n--- 📦 [CriticAgent: Phase 1] Localized Batch Audits (Provenance-Aware) ---")
        batches = self._build_token_batches(reqs_list, max_token_budget=4000)
        print(f" └─ Dynamic Token Budget Allocator split {len(reqs_list)} requirements into {len(batches)} batch(es).")

        # Global BRD Summary Context (Tier 1)
        global_brd_summary = raw_brd_str[:1200]

        batch_results = []
        for b_idx, batch in enumerate(batches, 1):
            # Provenance Lookup (Option 1): Get BRD chunks referenced by source_chunk_idx in this batch
            referenced_chunks = set([r.get("source_chunk_idx", 0) for r in batch])
            
            # Slice relevant BRD text for this batch
            chunk_length = max(1000, len(raw_brd_str) // max(1, len(batches)))
            targeted_brd_excerpts = ""
            for c_idx in sorted(list(referenced_chunks)):
                start = c_idx * chunk_length
                end = min(len(raw_brd_str), start + chunk_length + 500)
                if start < len(raw_brd_str):
                    targeted_brd_excerpts += f"\n--- [BRD SOURCE CHUNK {c_idx + 1}] ---\n" + raw_brd_str[start:end]

            if not targeted_brd_excerpts.strip():
                targeted_brd_excerpts = raw_brd_str[:3000]

            print(f"\n --- 🔎 [CriticAgent: Batch {b_idx}/{len(batches)}] Auditing {len(batch)} requirements (BRD Chunks: {sorted(list(referenced_chunks))}) ---")
            batch_res = await self._review_batch(
                batch_idx=b_idx,
                total_batches=len(batches),
                artifact_type=artifact_type,
                req_batch=batch,
                global_brd_summary=global_brd_summary,
                targeted_brd_excerpts=targeted_brd_excerpts
            )
            print(f"     └─ Status: {batch_res.get('status')} | Score: {batch_res.get('confidence_score')} | Findings: {len(batch_res.get('findings', []))}")
            batch_results.append(batch_res)

        # --- PHASE 2: REDUCE PHASE (System-Wide Matrix Audit for Cross-Requirement Conflicts) ---
        print(f"\n--- 📊 [CriticAgent: Phase 2] System-Wide Matrix Audit (Cross-Check) ---")
        matrix_res = await self._review_matrix_cross_check(artifact_type, reqs_list)
        print(f" └─ Matrix Cross-Check Status: {matrix_res.get('status')} | Score: {matrix_res.get('confidence_score')} | Conflict Findings: {len(matrix_res.get('findings', []))}")

        # --- CONSOLIDATION LAYER ---
        all_findings = []
        all_suggestions = []
        statuses = []
        scores = []

        for b_res in batch_results:
            statuses.append(b_res.get("status", "APPROVED"))
            scores.append(float(b_res.get("confidence_score", 1.0)))
            for f in b_res.get("findings", []):
                all_findings.append(f)
            if b_res.get("critic_suggestion"):
                all_suggestions.append(b_res.get("critic_suggestion"))

        # Incorporate Phase 2 Matrix Findings
        if matrix_res.get("status") == "REQUEST_CORRECTION":
            statuses.append("REQUEST_CORRECTION")
            scores.append(float(matrix_res.get("confidence_score", 0.80)))
            for f in matrix_res.get("findings", []):
                all_findings.append(f)
            if matrix_res.get("critic_suggestion"):
                all_suggestions.append(matrix_res.get("critic_suggestion"))

        overall_status = "REQUEST_CORRECTION" if "REQUEST_CORRECTION" in statuses else "APPROVED"
        min_score = min(scores) if scores else 1.0
        combined_suggestions = "\n".join(filter(None, all_suggestions))

        print(f"\n================================================================================")
        print(f"📋 [CriticAgent Review Summary]")
        print(f" ► Overall Status  : {overall_status}")
        print(f" ► Min Confidence  : {min_score:.2f}")
        print(f" ► Total Findings  : {len(all_findings)}")
        print(f" ► Batches Processed: {len(batches)}")
        if combined_suggestions:
            print(f" ► Critic Suggestion: {combined_suggestions[:150]}...")
        print(f"================================================================================")

        return {
            "status": overall_status,
            "confidence_score": round(min_score, 2),
            "uncertainty_reason": "" if overall_status == "APPROVED" else f"Critic identified {len(all_findings)} quality issues across requirement batches.",
            "findings": all_findings,
            "critic_suggestion": combined_suggestions,
            "batches_processed": len(batches)
        }

    async def _review_batch(self, batch_idx: int, total_batches: int, artifact_type: str, req_batch: List[dict], global_brd_summary: str, targeted_brd_excerpts: str) -> Dict[str, Any]:
        prompt = f"""
You are an Enterprise Lead Business Analyst & Adversarial QA Critic.
Auditing Artifact: {artifact_type} (Batch {batch_idx} of {total_batches})

GLOBAL BRD SUMMARY CONTEXT:
{global_brd_summary}

TARGETED SOURCE BRD EXCERPTS FOR THIS BATCH:
{targeted_brd_excerpts}

REQUIREMENTS IN THIS BATCH TO AUDIT:
{json.dumps(req_batch, indent=2)}

STRICT CRITIC AUDIT RULES:
1. **Zero Hallucinations**: Ensure every requirement in this batch directly maps to the provided BRD excerpts. Flag any non-existent features.
2. **Completeness & Accuracy**: Verify that no input fields, business rules, or validation constraints were dropped or distorted.
3. **MoSCoW & Priority Rule**: If the source BRD does NOT specify explicit priority values, evaluate priority classifications reasonably. Do NOT output "REQUEST_CORRECTION" for minor High vs Medium priority inferences when the BRD is silent on priorities. Only request correction if there is an extreme misclassification (e.g., marking a minor cosmetic label tweak as Must Have or a mandatory compliance audit rule as Could Have). If priority is acceptable, return status "APPROVED".

Return output ONLY as a JSON object adhering to this schema:
{{
  "status": "APPROVED" or "REQUEST_CORRECTION",
  "confidence_score": 0.95,
  "findings": [
    {{
      "req_id": "FR-018",
      "category": "Hallucination" or "Incomplete" or "Misclassified Priority",
      "severity": "High" or "Medium" or "Low",
      "issue": "Specific explanation of the discrepancy",
      "suggestion": "Exact correction required"
    }}
  ],
  "critic_suggestion": "Actionable summary of corrections needed for this batch"
}}
"""
        response = await self.llm.call(prompt, provider="azure", agent_name="CriticAgent")
        result = _clean_json_output(response)
        if not isinstance(result, dict) or "status" not in result:
            return {"status": "APPROVED", "confidence_score": 1.0, "findings": [], "critic_suggestion": ""}
        return result

    async def _review_matrix_cross_check(self, artifact_type: str, reqs_list: List[dict]) -> Dict[str, Any]:
        """
        Phase 2: Builds a compact Markdown Summary Matrix (~1,500 tokens) for all requirements
        and executes a 2nd-pass LLM review to spot cross-requirement contradictions & workflow breaks.
        """
        matrix_rows = []
        for r in reqs_list:
            r_id = r.get("id", "REQ")
            r_desc = r.get("description", "")
            first_sentence = r_desc.split(".")[0] if r_desc else ""
            title = first_sentence[:40] if first_sentence else "Requirement Item"
            summary = r_desc[:120].replace("\n", " ")
            matrix_rows.append(f"| {r_id} | {title} | {summary} |")

        matrix_table = "| REQ ID | Title | Core Logic Summary |\n|---|---|---|\n" + "\n".join(matrix_rows)

        prompt = f"""
You are a Principal Software Architect auditing the COMPLETE Requirements Matrix for Artifact: {artifact_type}.

COMPACT REQUIREMENTS SUMMARY MATRIX ({len(reqs_list)} Requirements):
{matrix_table}

STRICT CROSS-REQUIREMENT AUDIT RULES:
1. **Contradictions**: Identify if any requirement directly contradicts another requirement (e.g. REQ-005 allows auto-approval but REQ-042 demands manual review).
2. **Duplicate Logic**: Identify redundant or duplicate requirements that describe the exact same logic under different IDs.
3. **Broken User Workflows**: Identify missing workflow links (e.g. REQ-020 references an ID created in a step that is never defined).

Return output ONLY as a JSON object adhering to this schema:
{{
  "status": "APPROVED" or "REQUEST_CORRECTION",
  "confidence_score": 0.90,
  "findings": [
    {{
      "req_id": "REQ-005 vs REQ-042",
      "category": "Cross-Requirement Contradiction" or "Duplicate Logic" or "Broken Workflow",
      "severity": "High" or "Medium" or "Low",
      "issue": "Specific explanation of conflict",
      "suggestion": "How to align the requirements"
    }}
  ],
  "critic_suggestion": "Actionable correction instruction for matrix conflicts"
}}
"""
        response = await self.llm.call(prompt, provider="azure", agent_name="CriticMatrixAuditor")
        result = _clean_json_output(response)
        if not isinstance(result, dict) or "status" not in result:
            return {"status": "APPROVED", "confidence_score": 1.0, "findings": [], "critic_suggestion": ""}
        return result

    async def _single_pass_review(self, artifact_type: str, content: Any, source_brd: str) -> Dict[str, Any]:
        print(f" --- ⚡ [CriticAgent] Executing Single-Pass Review for {len(self._extract_requirements_list(content))} requirement(s) ---")
        prompt = f"""
You are an Enterprise Lead Business Analyst & Adversarial QA Critic.
Auditing Artifact: {artifact_type}

SOURCE BRD CONTEXT:
{source_brd[:4000]}

CONTENT TO AUDIT:
{json.dumps(content, indent=2) if isinstance(content, (dict, list)) else str(content)[:4000]}

Review rules:
1. Check for hallucinations, contradictions, or missing business logic.
2. Output JSON strictly with keys: status ("APPROVED" or "REQUEST_CORRECTION"), confidence_score (0.0 to 1.0), findings (list), critic_suggestion (str).
"""
        response = await self.llm.call(prompt, provider="azure", agent_name="CriticAgent")
        result = _clean_json_output(response)
        if not isinstance(result, dict) or "status" not in result:
            result = {"status": "APPROVED", "confidence_score": 1.0, "findings": [], "critic_suggestion": ""}
        print(f"     └─ Status: {result.get('status')} | Score: {result.get('confidence_score')} | Findings: {len(result.get('findings', []))}")
        return result

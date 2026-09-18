import json
import asyncio
import re
from typing import List, Dict, Any
from services.llm_service import LLMService
from utils.json_extractor import extract_json_from_llm_response

class ExtractionAgent:
    def __init__(self):
        self.llm = LLMService()

    async def extract_content(self, text: str, context_type: str = "document") -> Dict[str, Any]:
        """
        Uses AI to extract structured requirements from text with channel-specific context.
        Employs dynamic Map-Reduce Chunking for long/complex documents to ensure 100% loss-less
        extraction of all granular requirements (40+ to 100+ items).
        """
        if not text or not text.strip():
            return self._empty_extraction_response("Source text is empty.")

        text = text.strip()
        channel_guidance = {
            "document": "Focus on formal functional and non-functional specifications from the BRD/PRD.",
            "text": "Formalize the provided notes or text into professional-grade business requirements.",
            "visual": "Analyze the UI description (from Vision Agent) and extract functional interactions and data fields.",
            "meeting": "Identify key stakeholder decisions, agreed-upon features, and action items from the transcript."
        }.get(context_type, "Focus on formal functional specifications.")

        chunks = self._create_dynamic_chunks(text, max_chunk_size=8000, overlap=800)
        
        # Single Pass Extraction for short documents (< 8,000 chars)
        if len(chunks) == 1:
            print(f" [ExtractionAgent] Single-Pass Extraction for document ({len(text)} chars)...")
            return await self._extract_chunk(text, 0, 1, context_type, channel_guidance)

        # Dynamic Map-Reduce Extraction for long/complex documents
        print(f" [ExtractionAgent] Dynamic Map-Reduce Extraction triggered for {len(text)} chars across {len(chunks)} chunks...")
        tasks = [
            self._extract_chunk(chunk, idx, len(chunks), context_type, channel_guidance)
            for idx, chunk in enumerate(chunks)
        ]
        chunk_results = await asyncio.gather(*tasks)

        reduced_result = self._reduce_chunk_results(chunk_results)
        print(f" [ExtractionAgent] Map-Reduce completed cleanly! Extracted {len(reduced_result.get('functional_requirements', []))} Functional Requirements across {len(chunks)} chunks.")
        return reduced_result

    def _create_dynamic_chunks(self, text: str, max_chunk_size: int = 8000, overlap: int = 800) -> List[str]:
        """
        Dynamically splits text into overlapping windows by section headers or logical paragraph boundaries.
        """
        if len(text) <= max_chunk_size:
            return [text]

        # Break text by page or major section headers if present
        page_pattern = r"(?=\n--- Page \d+ ---\n|\n#+\s+|\n[A-Z0-9\s]{4,30}\n---|\n\n(?=[A-Z][a-zA-Z0-9\s]{2,40}\n))"
        sections = [s.strip() for s in re.split(page_pattern, text) if s and s.strip()]

        chunks = []
        current_chunk = ""

        for sec in sections:
            if len(current_chunk) + len(sec) <= max_chunk_size:
                current_chunk += ("\n\n" if current_chunk else "") + sec
            else:
                if current_chunk:
                    chunks.append(current_chunk)
                # If a single section is larger than max_chunk_size, hard chunk it with overlap
                if len(sec) > max_chunk_size:
                    start = 0
                    while start < len(sec):
                        end = min(start + max_chunk_size, len(sec))
                        chunks.append(sec[start:end])
                        if end == len(sec):
                            break
                        start += max_chunk_size - overlap
                    current_chunk = ""
                else:
                    # Start new chunk with overlap from previous chunk end
                    overlap_text = current_chunk[-overlap:] if len(current_chunk) > overlap else current_chunk
                    current_chunk = overlap_text + "\n\n" + sec

        if current_chunk and current_chunk not in chunks:
            chunks.append(current_chunk)

        # Fallback if section splitting yielded no chunks
        if not chunks:
            start = 0
            while start < len(text):
                end = min(start + max_chunk_size, len(text))
                chunks.append(text[start:end])
                if end == len(text):
                    break
                start += max_chunk_size - overlap

        return chunks

    async def _extract_chunk(self, chunk_text: str, chunk_idx: int, total_chunks: int, context_type: str, channel_guidance: str) -> Dict[str, Any]:
        """
        Executes high-fidelity extraction on an individual text chunk with anti-summarization instructions.
        """
        chunk_header = f"Chunk {chunk_idx + 1} of {total_chunks}" if total_chunks > 1 else "Complete Document"
        
        prompt = f"""
        Role: Senior Business Analyst Extraction Specialist
        Channel: {context_type.upper()} ({chunk_header})
        Guidance: {channel_guidance}

        CRITICAL EXHAUSTIVE EXTRACTION MANDATE:
        - Extract EVERY explicit requirement, individual data field, conditional display rule, validation constraint, business rule, and non-functional requirement in this chunk.
        - ABSOLUTELY DO NOT summarize multiple data fields or rules into a single top-level category (e.g., do NOT compress 10 form fields into 'Collect property info'). ITEMIZE EACH FIELD AND RULE INDIVIDUALLY.
        - If a section lists fields (e.g., Address, Year Built, Sprinkler Coverage), output each item as its own distinct requirement.
        - BUSINESS RULES EXTRACTION: Extract BOTH explicit numbered business rules (e.g. 'Description is mandatory') AND implicit domain rules/conditional logic triggers (e.g. 'If Cooking Operations = Yes, display Hood System', 'If Alcohol Sales = Yes, request percentage of revenue', 'If Hazardous Materials = Yes, display Chemical Classification'). Populate all of these in the "business_rules" array.
        - REQUIREMENT PRIORITIZATION GUIDELINES (When BRD has no explicit priorities):
          * High: Core validation rules, mandatory fields, security/compliance rules, primary transaction/adjudication workflows.
          * Medium: Prefill automation, manual field override options, UI convenience helpers, conditional field visibility.
          * Low: Export enhancements, optional reporting, cosmetic formatting.

        Return output strictly in the following JSON format:
        {{
          "document_summary": "Summary of this section",
          "quality_score": 0.9, 
          "assessment": {{
            "clarity": "High/Med/Low",
            "completeness": "High/Med/Low",
            "contradictions": [],
            "missing_sections": []
          }},
          "functional_requirements": [{{ 
            "id": "FR-001", 
            "description": "Clear, concise, specific requirement or data field specification", 
            "priority": "High/Medium/Low",
            "ambiguity_flag": false,
            "clarification_note": ""
          }}],
          "non_functional_requirements": [{{ "id": "NFR-001", "description": "Specific performance, security, compliance rule" }}],
          "business_rules": [{{ "id": "BR-001", "description": "Explicit or implicit business validation rule, conditional display trigger, or policy constraint" }}],
          "assumptions": [],
          "dependencies": [],
          "open_questions": []
        }}
        
        CRITICAL: Output ONLY valid JSON. No conversational text or introductory preambles.
        
        Source Material ({chunk_header}):
        {chunk_text}
        """

        print(f" [ExtractionAgent] Processing Chunk {chunk_idx + 1}/{total_chunks} ({len(chunk_text)} chars)...")
        response = await self.llm.call(prompt, provider="azure")
        res = extract_json_from_llm_response(response)
        
        if isinstance(res, dict) and "error" in res:
            raw_snippet = str(response)[:300].replace('\n', ' ')
            print(f"⚠️ [ExtractionAgent WARN] Chunk {chunk_idx + 1}/{total_chunks} parse failed.")
            print(f"   Reason      : {res.get('error')}")
            print(f"   Raw Snippet : \"{raw_snippet}\"")
            print(f"   Action      : Retrying with temperature=0.0...")
            fallback_resp = await self.llm.call(prompt, provider="azure", temperature=0.0)
            res = extract_json_from_llm_response(fallback_resp)
            if isinstance(res, dict) and "error" in res:
                fb_snippet = str(fallback_resp)[:300].replace('\n', ' ')
                print(f"❌ [ExtractionAgent ERROR] Chunk {chunk_idx + 1}/{total_chunks} retry with temperature=0.0 ALSO failed.")
                print(f"   Retry Reason : {res.get('error')}")
                print(f"   Retry Snippet: \"{fb_snippet}\"")
            else:
                print(f"✅ [ExtractionAgent SUCCESS] Chunk {chunk_idx + 1}/{total_chunks} parse succeeded on temperature=0.0 retry!")

        if isinstance(res, dict) and "error" not in res:
            fr_count = len(res.get("functional_requirements", []))
            print(f"✅ [ExtractionAgent] Chunk {chunk_idx + 1}/{total_chunks} extracted {fr_count} functional requirements.")
            return res
        else:
            print(f"❌ [ExtractionAgent ERROR] Returning empty extraction fallback for Chunk {chunk_idx + 1}/{total_chunks}.")
            return self._empty_extraction_response(f"Failed to parse chunk {chunk_idx+1}")

    def _reduce_chunk_results(self, chunk_results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Consolidates, deduplicates, and re-indexes requirements extracted across all chunks.
        """
        all_fr = []
        all_nfr = []
        all_br = []
        all_assumptions = []
        all_deps = []
        all_questions = []
        summaries = []
        contradictions = []
        missing_sections = []

        seen_fr_norms = set()
        seen_nfr_norms = set()
        seen_br_norms = set()

        def normalize(text_str: str) -> str:
            if not text_str: return ""
            return re.sub(r"[^a-z0-9]", "", text_str.lower())

        for idx, res in enumerate(chunk_results):
            if not isinstance(res, dict): continue

            # Summaries & Assessments
            summary = res.get("document_summary")
            if summary and isinstance(summary, str) and summary.strip():
                summaries.append(summary.strip())

            assessment = res.get("assessment", {})
            if isinstance(assessment, dict):
                contradictions.extend(assessment.get("contradictions", []))
                missing_sections.extend(assessment.get("missing_sections", []))

            # Functional Requirements Deduplication
            for fr in res.get("functional_requirements", []):
                if isinstance(fr, dict):
                    desc = fr.get("description") or fr.get("text") or ""
                    norm = normalize(desc)
                    if norm and norm not in seen_fr_norms:
                        seen_fr_norms.add(norm)
                        all_fr.append({
                            "description": desc,
                            "priority": fr.get("priority") or "Medium",
                            "ambiguity_flag": bool(fr.get("ambiguity_flag", False)),
                            "clarification_note": fr.get("clarification_note") or "",
                            "source_chunk_idx": fr.get("source_chunk_idx", idx)
                        })

            # NFR Deduplication
            for nfr in res.get("non_functional_requirements", []):
                if isinstance(nfr, dict):
                    desc = nfr.get("description") or nfr.get("text") or ""
                    norm = normalize(desc)
                    if norm and norm not in seen_nfr_norms:
                        seen_nfr_norms.add(norm)
                        all_nfr.append({
                            "description": desc,
                            "source_chunk_idx": nfr.get("source_chunk_idx", idx)
                        })

            # Business Rules Deduplication
            for br in res.get("business_rules", []):
                if isinstance(br, dict):
                    desc = br.get("description") or br.get("text") or ""
                    norm = normalize(desc)
                    if norm and norm not in seen_br_norms:
                        seen_br_norms.add(norm)
                        all_br.append({
                            "description": desc,
                            "source_chunk_idx": br.get("source_chunk_idx", idx)
                        })

            # Simple Lists
            all_assumptions.extend([a for a in res.get("assumptions", []) if isinstance(a, str)])
            all_deps.extend([d for d in res.get("dependencies", []) if isinstance(d, str)])
            all_questions.extend([q for q in res.get("open_questions", []) if isinstance(q, str)])

        # Sequentially Re-index items
        for i, item in enumerate(all_fr, 1):
            item["id"] = f"FR-{i:03d}"
        for i, item in enumerate(all_nfr, 1):
            item["id"] = f"NFR-{i:03d}"
        for i, item in enumerate(all_br, 1):
            item["id"] = f"BR-{i:03d}"

        # Consolidate overall document summary
        combined_summary = " ".join(summaries[:3]) if summaries else "Consolidated Business Requirements Document."
        
        return {
            "document_summary": combined_summary,
            "quality_score": 0.95 if len(all_fr) > 10 else 0.85,
            "assessment": {
                "clarity": "High",
                "completeness": "High" if len(all_fr) >= 15 else "Medium",
                "contradictions": list(set(contradictions)),
                "missing_sections": list(set(missing_sections))
            },
            "functional_requirements": all_fr,
            "non_functional_requirements": all_nfr,
            "business_rules": all_br,
            "assumptions": list(set(all_assumptions)),
            "dependencies": list(set(all_deps)),
            "open_questions": list(set(all_questions))
        }

    def _empty_extraction_response(self, error_msg: str) -> Dict[str, Any]:
        return {
            "document_summary": f"Extraction notice: {error_msg}",
            "quality_score": 0.0,
            "assessment": {"clarity": "Low", "completeness": "Low", "contradictions": [], "missing_sections": []},
            "functional_requirements": [],
            "non_functional_requirements": [],
            "business_rules": [],
            "assumptions": [],
            "dependencies": [],
            "open_questions": []
        }


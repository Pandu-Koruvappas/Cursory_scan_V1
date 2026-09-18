import os
import json
import asyncio
import math
from services.llm_service import LLMService
from services.vector_service import VectorSearchService

class KnowledgeAgent:
    """
    The 'Hidden Brain' of Requify.
    Manages Organizational Memory and Domain Knowledge via Azure AI Search.
    """
    def __init__(self):
        self.llm = LLMService()
        self.vector_store = VectorSearchService()
        print("--- [SUCCESS] KnowledgeAgent initialized with Azure AI Search Integration ---")

    async def _get_embedding(self, text: str) -> list:
        """
        Generates a vector embedding for the text using Azure OpenAI.
        """
        embedding = await self.llm.get_embeddings(text)
        if embedding and len(embedding) > 0 and not math.isclose(sum(embedding), 0.0, abs_tol=1e-9):
            print(f"--- 🧬 [KnowledgeAgent] Generated {len(embedding)}-dim vector embedding for text ({len(text)} chars) ---")
        else:
            print(f"--- ⚠️ [KnowledgeAgent] Vector embedding generation failed or returned zero vector! ---")
        return embedding

    async def ingest_project_requirements(self, doc_id: str, extraction: dict, lob: str = "General", project_id: str = None):
        """
        Indexes extracted requirements into organizational memory using deterministic upsert keys.
        """
        if not self.vector_store.endpoint: 
            print("--- [WARN] KnowledgeAgent: Vector Store endpoint is MISSING. Indexing skipped. ---")
            return 0
        
        reqs = extraction.get("functional_requirements", [])
        effective_project_id = project_id or doc_id
        print(f"--- 📥 [KnowledgeAgent] Ingesting {len(reqs)} requirements for Project/Doc: {effective_project_id} (LOB: {lob}) into Azure AI Search ---")
        indexed_count = 0
        
        for req in reqs:
            content = req.get("description", "")
            req_id = req.get("id", "UNKNOWN")
            
            # Generate Embedding
            vector = await self._get_embedding(content)
            
            # Index to Azure with deterministic key
            try:
                self.vector_store.index_requirement(
                    doc_id=doc_id,
                    req_id=req_id,
                    content=content,
                    lob=lob,
                    vector=vector,
                    project_id=effective_project_id
                )
                indexed_count += 1
                print(f"  └─ Upserted Req [{req_id}] -> Key [{effective_project_id}_{req_id}] ({len(content)} chars)")
            except Exception as e:
                print(f"--- [ERROR] KnowledgeAgent: Failed to index requirement {req_id}: {e} ---")
                
            # Rate limiting delay to avoid 429 Too Many Requests from Azure AI Search
            await asyncio.sleep(0.5)
            
        print(f"--- ✅ [SUCCESS] KnowledgeAgent: Successfully indexed/upserted {indexed_count}/{len(reqs)} requirements to Azure AI Search. ---")
        return indexed_count

    async def sync_vault(self):
        """
        Migrates existing requirements from the DB to Azure AI Search.
        This is a 'Catch-up' mechanism to ensure the index is always populated.
        """
        if not self.vector_store.endpoint: return
        
        from services.db_service import SessionLocal
        from models.models import Document
        
        db = SessionLocal()
        try:
            docs = db.query(Document).all()
            print(f"--- [INFO] Syncing Vault: Found {len(docs)} documents to re-index. ---")
            
            total_indexed = 0
            for doc in docs:
                if doc.meta and "extraction" in doc.meta:
                    extraction = doc.meta["extraction"]
                    # We pass 'General' as fallback LOB if not found in doc
                    lob = doc.meta.get("lob", "General")
                    count = await self.ingest_project_requirements(doc.id, extraction, lob=lob)
                    total_indexed += count
            
            print(f"--- [SUCCESS] Vault Synchronization Complete. Total requirements indexed: {total_indexed} ---")
        except Exception as e:
            print(f"--- [ERROR] Vault Sync Failed: {e} ---")
        finally:
            db.close()

    async def retrieve_relevant_context(self, query_text: str, lob: str = "General", n_results: int = 3):
        """
        Searches both past requirements AND official P&C domain guidelines.
        Returns a unified markdown context block.
        """
        print(f"\n================================================================================")
        print(f"🔍 [KnowledgeAgent RAG Retrieval Started]")
        print(f" ► Query Text : \"{query_text[:120]}...\"" if len(query_text) > 120 else f" ► Query Text : \"{query_text}\"")
        print(f" ► Target LOB : \"{lob}\"")
        print(f" ► Top Results: {n_results}")
        print(f"================================================================================")

        if not self.vector_store.endpoint: 
            print("--- ⚠️ [KnowledgeAgent] Vector Store endpoint missing. RAG memory disabled. ---")
            return "Organizational Memory is currently disabled (Missing Azure Search Config)."
        
        query_vector = await self._get_embedding(query_text)
        
        # Check if the embedding silently failed (returned all zeros)
        if math.isclose(sum(query_vector), 0.0, abs_tol=1e-9):
            print("--- ❌ [KnowledgeAgent ERROR] Search embedding vector returned all zeros! ---")
            return "ERROR: Failed to generate search embedding. Please verify your EMBEDDING_CREDENTIAL and AZURE_OPENAI_EMBEDDING_DEPLOYMENT in the Azure App Service Environment Variables."
        
        # 1. Search Past Requirements (Institutional Memory)
        print(f"\n--- 📦 Searching Index: 'requirement-memory' (Historical Reqs) ---")
        past_reqs = self.vector_store.search_memory(query_vector, top=n_results)
        print(f" ► Found {len(past_reqs)} matching historical requirement(s).")
        for idx, req in enumerate(past_reqs, 1):
            r_lob = req.get('lob', 'General')
            r_id = req.get('requirement_id', 'Unknown')
            r_doc = req.get('doc_id', 'UnknownDoc')
            r_content = req.get('content', '').strip().replace('\n', ' ')
            print(f"   [{idx}] Source Index: requirement-memory | Doc ID: {r_doc} | LOB: {r_lob} | Req ID: {r_id}")
            print(f"       Snippet: \"{r_content[:150]}...\"" if len(r_content) > 150 else f"       Snippet: \"{r_content}\"")

        # 2. Search Domain Guidelines (P&C Insurance Rules)
        print(f"\n--- 📚 Searching Index: 'insurance-guidelines' (LOB Filter: '{lob}') ---")
        guidelines = self.vector_store.search_guidelines(query_vector, lob=lob, top=n_results)
        print(f" ► Found {len(guidelines)} matching domain guideline(s).")
        for idx, rule in enumerate(guidelines, 1):
            g_doc = rule.get('doc_id', 'Manual/Slide')
            g_lob = rule.get('lob', 'General')
            g_cat = rule.get('category', 'N/A')
            g_content = rule.get('content', '').strip().replace('\n', ' ')
            print(f"   [{idx}] Source Index: insurance-guidelines | Source File: {g_doc} | LOB: {g_lob} | Category: {g_cat}")
            print(f"       Snippet: \"{g_content[:150]}...\"" if len(g_content) > 150 else f"       Snippet: \"{g_content}\"")
        
        context = ""
        found_knowledge = False
        
        if past_reqs:
            found_knowledge = True
            context += "\n### RELEVANT INSTITUTIONAL MEMORY (Similar Past Projects)\n"
            for req in past_reqs:
                context += f"- [{req.get('lob', 'General')}] Req {req.get('requirement_id', 'Unknown')}: {req.get('content', '')}\n"
                
        if guidelines:
            found_knowledge = True
            context += "\n### OFFICIAL P&C DOMAIN GUIDELINES\n"
            for rule in guidelines:
                file_name = rule.get('doc_id', 'Manual')
                context += f"- [Source: {file_name}] {rule.get('content', '')}\n"
                
        if not found_knowledge:
            print("--- ℹ️ [KnowledgeAgent] No relevant context retrieved from Azure AI Search. ---")
            print("================================================================================\n")
            return "No domain guidelines or similar past requirements found in memory."
        
        print(f"\n--- 💡 [KnowledgeAgent] Retaining Unified RAG Context ({len(past_reqs)} Reqs + {len(guidelines)} Guidelines) ---")

        # Format the raw text into a readable response using the LLM
        formatting_prompt = f"""
        You are an expert Property & Casualty Insurance Knowledge Assistant.
        The user asked: "{query_text}"
        
        Here is the raw information retrieved from the enterprise knowledge base:
        {context}
        
        Please synthesize and format this information into a clean, highly readable Markdown response. 
        - Directly answer the user's question using ONLY the provided text.
        - Remove any repetitive or messy proprietary disclaimers (e.g. "All Information contained herein is proprietary & confidential...").
        - Use bolding, bullet points, and headers to make the text easy to read.
        - Clearly cite the [Source: File Name] at the bottom.
        """
        
        try:
            print("--- 🤖 Synthesizing RAG response with Azure OpenAI... ---")
            formatted_response = await self.llm.call(formatting_prompt, provider="azure")
            print("--- ✅ [KnowledgeAgent RAG Retrieval Completed Successfully] ---")
            print("================================================================================\n")
            return formatted_response
        except Exception as e:
            # Fallback to raw text if LLM formatting fails
            print(f"WARN: LLM formatting failed, returning raw text: {e}")
            print("================================================================================\n")
            return context

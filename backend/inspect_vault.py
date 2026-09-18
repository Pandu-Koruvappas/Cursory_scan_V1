import os
import chromadb
from chromadb.utils import embedding_functions
import numpy as np

def vector_lab():
    print("\n--- BA Agent Pro: Vector Intelligence Lab ---")
    
    db_path = os.path.join(os.getcwd(), "knowledge_db")
    if not os.path.exists(db_path):
        print("--- Error: Knowledge database not found. ---")
        return

    client = chromadb.PersistentClient(path=db_path)
    embedding_fn = embedding_functions.SentenceTransformerEmbeddingFunction(model_name="all-MiniLM-L6-v2")
    
    try:
        collection = client.get_collection(name="corporate_standards", embedding_function=embedding_fn)
        
        # 1. Show Data Integrity & Embeddings
        print("\n[STEP 1: DATABASE INSPECTION]")
        results = collection.get(include=['embeddings', 'documents', 'metadatas'])
        
        ids = results['ids']
        documents = results['documents']
        embeddings = results['embeddings']
        
        print(f"--- Total Knowledge Chunks: {len(ids)} ---")
        
        for i in range(min(2, len(ids))): # Show first 2 for brevity
            print(f"\nCHUNK ID: {ids[i]}")
            print(f"CONTENT: {documents[i][:100]}...")
            
            # Show a snippet of the high-dimensional vector
            vec_snippet = [round(float(x), 4) for x in embeddings[i][:10]]
            print(f"RAW EMBEDDING (First 10 of 384 dimensions): {vec_snippet}")
        
        # 2. Semantic Similarity Test
        print("\n[STEP 2: SEMANTIC SIMILARITY TEST]")
        print("This proves the agent uses 'Proximity of Ideas' rather than keyword matching.")
        
        test_queries = [
            "What are the P&C domain rules?",
            "How do we handle Azure DevOps sync?",
            "What is the tech stack standard?"
        ]
        
        for query in test_queries:
            print(f"\nQUERY: '{query}'")
            # Perform query
            query_res = collection.query(
                query_texts=[query],
                n_results=1,
                include=['distances', 'documents']
            )
            
            distance = query_res['distances'][0][0]
            matched_text = query_res['documents'][0][0][:100]
            
            # Lower distance = closer meaning
            print(f"MATHEMATICAL DISTANCE: {distance:.4f}")
            print(f"MATCHED KNOWLEDGE: {matched_text}...")
            
        print("\n--- Lab Analysis Complete ---")
        
    except Exception as e:
        print(f"--- Error in Vector Lab: {e} ---")

if __name__ == "__main__":
    vector_lab()

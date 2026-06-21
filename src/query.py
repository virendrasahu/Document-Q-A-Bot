import os
import argparse
import google.generativeai as genai
import chromadb
from dotenv import load_dotenv

# Import configurations
try:
    from src.config import DB_DIR, COLLECTION_NAME, EMBEDDING_MODEL, GENERATIVE_MODEL, CustomGeminiEmbeddingFunction
except ImportError:
    from config import DB_DIR, COLLECTION_NAME, EMBEDDING_MODEL, GENERATIVE_MODEL, CustomGeminiEmbeddingFunction

load_dotenv()

def query_rag_pipeline(user_query: str, db_path: str = DB_DIR, k: int = 3, temperature: float = 0.0, api_key: str = None) -> dict:
    """
    Searches the database for relevant context, builds a grounded prompt, and queries Gemini.
    """
    if not api_key:
        api_key = os.getenv("GEMINI_API_KEY")
    
    if not api_key:
        return {
            "answer": "Error: GEMINI_API_KEY is not set. Please set it in your environment or .env file.",
            "citations": [],
            "raw_context": []
        }

    # Configure Gemini SDK
    genai.configure(api_key=api_key)

    try:
        # Create persistent ChromaDB client
        client = chromadb.PersistentClient(path=str(db_path))

        # Initialize the Gemini embedding function
        embedding_fn = CustomGeminiEmbeddingFunction(
            api_key=api_key,
            model_name=EMBEDDING_MODEL
        )

        # Get the existing collection
        collection = client.get_collection(
            name=COLLECTION_NAME,
            embedding_function=embedding_fn
        )
    except Exception as e:
        return {
            "answer": f"Error loading vector database: {e}. Has the ingestion pipeline been run? Please ensure documents are indexed.",
            "citations": [],
            "raw_context": []
        }

    # Query collection for top k closest results
    try:
        results = collection.query(
            query_texts=[user_query],
            n_results=k
        )
    except Exception as e:
        return {
            "answer": f"Error performing database search: {e}",
            "citations": [],
            "raw_context": []
        }

    # If no results found
    if not results or not results['documents'] or not results['documents'][0]:
        return {
            "answer": "I am sorry, but the database search returned no matching documents.",
            "citations": [],
            "raw_context": []
        }

    # Format the retrieved documents as background context
    context_blocks = []
    citations = []

    for doc, meta in zip(results['documents'][0], results['metadatas'][0]):
        source_name = meta.get('source', 'Unknown')
        page_num = meta.get('page', 'Unknown')
        citation_str = f"Source: {source_name}, Page: {page_num}"

        context_blocks.append(f"[{citation_str}]\nContext: {doc}")
        citations.append(citation_str)

    context_payload = "\n\n---\n\n".join(context_blocks)

    # Set up strict grounding system prompt
    system_prompt = """
You are a professional and precise document Q&A assistant.

ANSWER FORMATTING RULES — ALWAYS FOLLOW:
1. Use clear Markdown headings (## for main, ### for sub)
2. Use bullet points (- ) for lists
3. Use **bold** for key terms and important facts
4. Add a "Sources" section at the end with all citations
5. Keep paragraphs short (2-3 lines max)

ANSWER STRUCTURE TO FOLLOW:

## Answer
[Main answer in 2-3 lines]

### Key Points
- **Point 1:** explanation
- **Point 2:** explanation

### Details
[Additional explanation with inline citations like (filename.pdf, Page X)]

## Sources Used
- Source: filename.pdf, Page: X
- Source: filename.pdf, Page: Y

STRICT RULES:
- Use ONLY the provided document context
- Always cite sources inline
- If answer not found, say: "The provided documents do not contain information about this topic."
- NEVER use your own knowledge outside the documents
"""

    prompt = (
        f"{system_prompt}\n\n"
        f"CONTEXT INFORMATION:\n{context_payload}\n\n"
        f"USER QUESTION: {user_query}\n\n"
        f"GROUNDED ANSWER:"
    )

    # Call Gemini to generate the answer
    try:
        # Create generation config
        generation_config = genai.types.GenerationConfig(
            temperature=temperature
        )
        model = genai.GenerativeModel(GENERATIVE_MODEL)
        response = model.generate_content(prompt, generation_config=generation_config)
        answer = response.text
    except Exception as e:
        answer = f"Error generating answer with Gemini: {e}"

    return {
        "answer": answer,
        "citations": citations,
        "raw_context": results['documents'][0],
        "metadatas": results['metadatas'][0],
        "distances": results['distances'][0] if 'distances' in results and results['distances'] else []
    }

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Query the BookExpert RAG pipeline.")
    parser.add_argument("--test", type=str, help="The query text to run against the pipeline.")
    parser.add_argument("--k", type=int, default=3, help="Number of retrieved chunks (default: 3).")
    args = parser.parse_args()

    if args.test:
        print(f"Querying pipeline for: '{args.test}'")
        res = query_rag_pipeline(args.test, k=args.k)
        print("\n--- ANSWER ---")
        print(res["answer"])
        print("\n--- SOURCES ---")
        for source in res["citations"]:
            print(f"- {source}")
    else:
        print("Use --test \"your question\" to test the query pipeline from the command line.")

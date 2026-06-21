import os
from pathlib import Path

# Base directories
BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
DB_DIR = BASE_DIR / "db"

# Ensure directories exist
DATA_DIR.mkdir(parents=True, exist_ok=True)
DB_DIR.mkdir(parents=True, exist_ok=True)

# ChromaDB Collection configurations
COLLECTION_NAME = "document_knowledge_base"
EMBEDDING_MODEL = "models/gemini-embedding-2"

# Gemini LLM configurations
# Standard models: gemini-2.5-flash-preview-09-2025 or gemini-1.5-flash
GENERATIVE_MODEL = "models/gemini-2.5-flash"

# Text chunking configurations
CHUNK_SIZE = 1000
CHUNK_OVERLAP = 200

# Custom Embedding Function using native Google Generative AI SDK
from chromadb.api.types import Documents, Embeddings, EmbeddingFunction

class CustomGeminiEmbeddingFunction(EmbeddingFunction):
    def __init__(self, api_key: str, model_name: str = EMBEDDING_MODEL):
        self.api_key = api_key
        self.model_name = model_name
        import google.generativeai as genai
        genai.configure(api_key=self.api_key)

    def __call__(self, input: Documents) -> Embeddings:
        import google.generativeai as genai
        embeddings = []
        batch_size = 100
        for i in range(0, len(input), batch_size):
            batch = input[i:i + batch_size]
            response = genai.embed_content(
                model=self.model_name,
                content=batch,
                task_type="retrieval_document"
            )
            embeddings.extend(response['embedding'])
        return embeddings


import os
import re
from pathlib import Path
from pypdf import PdfReader
from docx import Document
import chromadb
from dotenv import load_dotenv
from tqdm import tqdm

# Import configuration
try:
    from src.config import DATA_DIR, DB_DIR, COLLECTION_NAME, EMBEDDING_MODEL, CHUNK_SIZE, CHUNK_OVERLAP, CustomGeminiEmbeddingFunction
except ImportError:
    from config import DATA_DIR, DB_DIR, COLLECTION_NAME, EMBEDDING_MODEL, CHUNK_SIZE, CHUNK_OVERLAP, CustomGeminiEmbeddingFunction

load_dotenv()

def extract_pdf_pages(file_path: str) -> list[dict]:
    """
    Extracts text page-by-page from a PDF, tracking page numbers and file source.
    """
    extracted_data = []
    file_name = os.path.basename(file_path)

    try:
        reader = PdfReader(file_path)
        for index, page in enumerate(reader.pages):
            text = page.extract_text()
            if text and text.strip():
                # Clean up multiple whitespaces and leading/trailing spaces
                clean_text = " ".join(text.split())
                extracted_data.append({
                    "text": clean_text,
                    "metadata": {
                        "source": file_name,
                        "page": index + 1  # 1-indexed for reader readability
                    }
                })
    except Exception as e:
        print(f"Error reading PDF {file_name}: {e}")

    return extracted_data

def extract_docx_pages(file_path: str) -> list[dict]:
    """
    Extracts text from a Word (.docx) document.
    Since Word documents don't have explicit pages, we group text paragraphs
    into logical page-like blocks (approx. 1500 characters) to keep metadata uniform.
    """
    extracted_data = []
    file_name = os.path.basename(file_path)

    try:
        doc = Document(file_path)
        current_page_text = []
        current_length = 0
        page_num = 1

        for para in doc.paragraphs:
            text = para.text.strip()
            if not text:
                continue
            
            clean_text = " ".join(text.split())
            current_page_text.append(clean_text)
            current_length += len(clean_text) + 1  # include space/newline separator

            # If we reach around 1500 characters, we yield this as a "page"
            if current_length >= 1500:
                full_page_text = "\n".join(current_page_text)
                extracted_data.append({
                    "text": full_page_text,
                    "metadata": {
                        "source": file_name,
                        "page": page_num
                    }
                })
                current_page_text = []
                current_length = 0
                page_num += 1

        # Yield remaining text
        if current_page_text:
            full_page_text = "\n".join(current_page_text)
            extracted_data.append({
                "text": full_page_text,
                "metadata": {
                    "source": file_name,
                    "page": page_num
                }
            })
    except Exception as e:
        print(f"Error reading DOCX {file_name}: {e}")

    return extracted_data

def extract_txt_pages(file_path: str) -> list[dict]:
    """
    Extracts text from a plain text (.txt) file.
    Groups text into logical page-like blocks (approx. 1500 characters).
    """
    extracted_data = []
    file_name = os.path.basename(file_path)

    try:
        with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
            content = f.read()
        
        # Clean up excessive newlines/spaces
        content = re.sub(r'\s+', ' ', content).strip()
        
        # Break into page chunks of 1500 characters
        page_size = 1500
        for index, start in enumerate(range(0, len(content), page_size)):
            chunk = content[start : start + page_size]
            if chunk.strip():
                extracted_data.append({
                    "text": chunk,
                    "metadata": {
                        "source": file_name,
                        "page": index + 1
                    }
                })
    except Exception as e:
        print(f"Error reading TXT {file_name}: {e}")

    return extracted_data

def extract_file_content(file_path: str) -> list[dict]:
    """
    Identifies the file type and extracts the pages.
    """
    suffix = Path(file_path).suffix.lower()
    if suffix == ".pdf":
        return extract_pdf_pages(file_path)
    elif suffix == ".docx":
        return extract_docx_pages(file_path)
    elif suffix in [".txt", ".md"]:
        return extract_txt_pages(file_path)
    else:
        print(f"Unsupported file format: {suffix} for {file_path}")
        return []

def split_text_recursive(text: str, separators: list[str], chunk_size: int, chunk_overlap: int) -> list[str]:
    """
    Splits text recursively using a list of separators (e.g. paragraphs, newlines, spaces).
    Keeps chunks below chunk_size while maintaining semantic boundaries.
    """
    if not separators:
        # Fallback to direct character slice if no separators are left
        return [text[i : i + chunk_size] for i in range(0, len(text), chunk_size - chunk_overlap)]
    
    separator = separators[0]
    next_separators = separators[1:]
    
    # Split text by current separator
    if separator == "":
        # Split into characters
        splits = list(text)
    else:
        splits = text.split(separator)
        
    chunks = []
    current_chunk = []
    current_len = 0
    
    for split in splits:
        # If the split segment itself is too large, recursively split it using next separators
        if len(split) > chunk_size:
            if current_chunk:
                chunks.append(separator.join(current_chunk))
                current_chunk = []
                current_len = 0
            
            recursed_splits = split_text_recursive(split, next_separators, chunk_size, chunk_overlap)
            chunks.extend(recursed_splits)
        else:
            # If adding this split exceeds chunk_size, save current chunk and start new one
            # (making sure to account for separator length)
            separator_len = len(separator) if current_chunk else 0
            if current_len + len(split) + separator_len > chunk_size:
                chunks.append(separator.join(current_chunk))
                
                # Backtrack for overlap
                # We need to find how many previous items we can keep to respect overlap
                overlap_chunk = []
                overlap_len = 0
                for item in reversed(current_chunk):
                    item_sep_len = len(separator) if overlap_chunk else 0
                    if overlap_len + len(item) + item_sep_len <= chunk_overlap:
                        overlap_chunk.insert(0, item)
                        overlap_len += len(item) + item_sep_len
                    else:
                        break
                
                current_chunk = overlap_chunk
                current_len = overlap_len
                
            current_chunk.append(split)
            current_len += len(split) + (len(separator) if len(current_chunk) > 1 else 0)
            
    if current_chunk:
        chunks.append(separator.join(current_chunk))
        
    # Clean up empty chunks and strip white spaces
    return [c.strip() for c in chunks if c.strip()]

def chunk_extracted_pages(pages: list[dict], chunk_size: int = 1000, chunk_overlap: int = 200) -> list[dict]:
    """
    Splits page-level documents into smaller, overlapping chunks.
    Ensures that source metadata is carried over to every individual chunk.
    """
    chunks = []
    separators = ["\n\n", "\n", " ", ""]

    for page in pages:
        text = page["text"]
        metadata = page["metadata"]

        # Run recursive character splitting on page text
        split_segments = split_text_recursive(text, separators, chunk_size, chunk_overlap)

        for index, chunk_text in enumerate(split_segments):
            # Calculate a general offset range for context tracking
            start_idx = text.find(chunk_text[:30]) if len(chunk_text) > 30 else 0
            end_idx = start_idx + len(chunk_text)
            
            chunks.append({
                "text": chunk_text,
                "metadata": {
                    "source": metadata["source"],
                    "page": metadata["page"],
                    "chunk_range": f"{start_idx}-{end_idx}"
                }
            })

    return chunks

def save_to_vector_db(chunks: list[dict], db_path: str = "./db", api_key: str = None):
    """
    Embeds text chunks and saves them into a persistent disk-based ChromaDB.
    """
    if not api_key:
        api_key = os.getenv("GEMINI_API_KEY")
    
    if not api_key:
        raise ValueError("GEMINI_API_KEY not found. Please set it in your environment or .env file.")

    # Create persistent ChromaDB client
    client = chromadb.PersistentClient(path=str(db_path))

    # Initialize the Gemini embedding function
    embedding_fn = CustomGeminiEmbeddingFunction(
        api_key=api_key,
        model_name=EMBEDDING_MODEL
    )

    # Create or fetch collection
    collection = client.get_or_create_collection(
        name=COLLECTION_NAME,
        embedding_function=embedding_fn,
        metadata={"hnsw:space": "cosine"} # Use Cosine Distance
    )

    # Prepare batch data
    ids = [f"{chunk['metadata']['source']}_p{chunk['metadata']['page']}_c{i}" for i, chunk in enumerate(chunks)]
    documents = [chunk["text"] for chunk in chunks]
    metadatas = [chunk["metadata"] for chunk in chunks]

    # Batch upload to ChromaDB
    # ChromaDB automatically handles embedding generation via the custom embedding function
    collection.add(
        ids=ids,
        documents=documents,
        metadatas=metadatas
    )
    print(f"Successfully indexed {len(chunks)} chunks in the vector database.")

def ingest_directory(data_dir: str = DATA_DIR, db_path: str = DB_DIR, api_key: str = None) -> int:
    """
    Finds all files in the directory, processes them, chunks them, and stores in the DB.
    """
    data_path = Path(data_dir)
    if not data_path.exists():
        print(f"Data directory {data_dir} does not exist. Creating it.")
        data_path.mkdir(parents=True, exist_ok=True)
        return 0

    all_files = []
    for ext in ["*.pdf", "*.docx", "*.txt", "*.md"]:
        all_files.extend(list(data_path.glob(ext)))
    
    if not all_files:
        print("No files found to ingest.")
        return 0

    all_pages = []
    print(f"Found {len(all_files)} files. Starting text extraction...")
    for file_path in tqdm(all_files, desc="Extracting text"):
        pages = extract_file_content(str(file_path))
        all_pages.extend(pages)
        
    if not all_pages:
        print("No text could be extracted from files.")
        return 0

    print(f"Extracted {len(all_pages)} total pages/sections. Chunking text...")
    chunks = chunk_extracted_pages(all_pages, CHUNK_SIZE, CHUNK_OVERLAP)
    
    if not chunks:
        print("No chunks generated.")
        return 0

    print(f"Generated {len(chunks)} chunks. Saving to persistent ChromaDB at {db_path}...")
    save_to_vector_db(chunks, db_path, api_key)
    return len(chunks)

if __name__ == "__main__":
    print("Running standalone ingestion pipeline...")
    try:
        num_chunks = ingest_directory()
        print(f"Ingestion completed. Total chunks indexed: {num_chunks}")
    except Exception as e:
        print(f"Ingestion failed: {e}")

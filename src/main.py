import os
import shutil
from pathlib import Path
import streamlit as st
from dotenv import load_dotenv

# Set page configuration first (must be the first Streamlit command)
st.set_page_config(
    page_title="BookExpert Q&A Bot",
    page_icon="📚",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Import local pipeline code
try:
    from src.config import BASE_DIR, DATA_DIR, DB_DIR, COLLECTION_NAME
    from src.ingest import ingest_directory
    from src.query import query_rag_pipeline
except ImportError:
    from config import BASE_DIR, DATA_DIR, DB_DIR, COLLECTION_NAME
    from ingest import ingest_directory
    from query import query_rag_pipeline

load_dotenv()
api_key = os.getenv("GEMINI_API_KEY")

# Initialize session states
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []
if "ingest_status" not in st.session_state:
    st.session_state.ingest_status = None

# Custom CSS for rich aesthetics and responsiveness
custom_css = """
<style>
    /* Google Fonts Import */
    @import url('https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;500;600;700&family=Plus+Jakarta+Sans:wght@300;400;500;600;700&display=swap');
    
    /* Global styles override */
    html, body, [class*="css"] {
        font-family: 'Plus Jakarta Sans', sans-serif;
    }
    
    h1, h2, h3 {
        font-family: 'Outfit', sans-serif;
        font-weight: 700;
    }
    
    /* Header Gradient */
    .main-header {
        background: linear-gradient(135deg, #1E3A8A 0%, #0D9488 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        font-size: 2.8rem;
        margin-bottom: 0.5rem;
        text-align: left;
    }
    
    .subheader {
        color: #4B5563;
        font-size: 1.1rem;
        margin-bottom: 2rem;
    }
    
    /* Cards and Containers styling */
    .stCard {
        background-color: #F8FAFC;
        border-radius: 12px;
        padding: 1.5rem;
        border: 1px solid #E2E8F0;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05);
        margin-bottom: 1rem;
        transition: transform 0.2s, box-shadow 0.2s;
    }
    .stCard:hover {
        transform: translateY(-2px);
        box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.1);
    }
    
    /* Chat message container styling */
    .chat-bubble {
        padding: 1rem 1.25rem;
        border-radius: 16px;
        margin-bottom: 1rem;
        max-width: 85%;
        line-height: 1.5;
        font-size: 0.95rem;
        display: inline-block;
    }
    
    .user-bubble {
        background-color: #EEF2F6;
        color: #1E293B;
        border-bottom-right-radius: 4px;
        float: right;
        clear: both;
        border: 1px solid #E2E8F0;
    }
    
    .bot-bubble {
        background: linear-gradient(180deg, #FFFFFF 0%, #F8FAFC 100%);
        color: #0F172A;
        border-bottom-left-radius: 4px;
        float: left;
        clear: both;
        border-left: 4px solid #0D9488;
        border-top: 1px solid #E2E8F0;
        border-right: 1px solid #E2E8F0;
        border-bottom: 1px solid #E2E8F0;
        box-shadow: 0 2px 4px rgba(0,0,0,0.02);
    }
    
    .chat-container {
        padding: 1rem;
        border-radius: 16px;
        background-color: #FFFFFF;
        min-height: 400px;
    }
    
    .citation-badge {
        background-color: #E0F2FE;
        color: #0369A1;
        padding: 0.15rem 0.5rem;
        border-radius: 9999px;
        font-size: 0.75rem;
        font-weight: 600;
        border: 1px solid #BAE6FD;
        display: inline-flex;
        align-items: center;
        margin-right: 0.5rem;
        margin-top: 0.25rem;
    }
    
    .citation-badge-icon {
        margin-right: 4px;
    }
    
    /* Button Custom Hover Animations */
    div.stButton > button {
        background: linear-gradient(135deg, #1E3A8A 0%, #0D9488 100%);
        color: white;
        border: none;
        padding: 0.6rem 1.5rem;
        border-radius: 8px;
        font-weight: 600;
        transition: all 0.3s ease;
        box-shadow: 0 4px 6px rgba(13, 148, 136, 0.15);
    }
    
    div.stButton > button:hover {
        background: linear-gradient(135deg, #1E40AF 0%, #0F766E 100%);
        color: white;
        transform: translateY(-1px);
        box-shadow: 0 6px 12px rgba(13, 148, 136, 0.25);
    }
    
    /* Settings Section */
    .settings-panel {
        background-color: #F8FAFC;
        border-radius: 12px;
        padding: 1rem;
        border: 1px solid #E2E8F0;
        margin-top: 1rem;
    }
    
    /* Sidebar Logo */
    .sidebar-logo {
        text-align: center;
        padding: 1rem 0;
        font-size: 2.2rem;
        font-weight: 800;
        background: linear-gradient(135deg, #1E3A8A 0%, #0D9488 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        border-bottom: 2px solid #F1F5F9;
        margin-bottom: 1.5rem;
    }
</style>
"""
st.markdown(custom_css, unsafe_allow_html=True)

# Helper function to clear database
def clear_db():
    if DB_DIR.exists():
        shutil.rmtree(DB_DIR)
        DB_DIR.mkdir(parents=True, exist_ok=True)
    st.session_state.ingest_status = None
    st.session_state.chat_history = []
    st.success("Database successfully cleared!")

# Helper to verify index status
def get_indexed_documents():
    """
    Scans the data directory and estimates index status
    """
    if not DATA_DIR.exists():
        return []
    files = []
    for ext in ["*.pdf", "*.docx", "*.txt", "*.md"]:
        files.extend(list(DATA_DIR.glob(ext)))
    return [f.name for f in files]

# ================= SIDEBAR =================
with st.sidebar:
    st.markdown('<div class="sidebar-logo">📚 BookExpert</div>', unsafe_allow_html=True)
    st.markdown("### 🔑 API Status")
    if api_key:
        st.success("✅ API Connected")
    else:
        st.error("❌ API Key Missing")

    st.markdown("---")
    st.markdown("### 📁 Document Library Management")
    
    # Upload new files
    uploaded_files = st.file_uploader(
        "Upload Source Documents",
        type=["pdf", "docx", "txt", "md"],
        accept_multiple_files=True,
        help="Upload PDF, DOCX, or text documents to include in the search knowledge base."
    )
    
    if uploaded_files:
        for uploaded_file in uploaded_files:
            target_path = DATA_DIR / uploaded_file.name
            if not target_path.exists():
                with open(target_path, "wb") as f:
                    f.write(uploaded_file.getbuffer())
                st.toast(f"Saved {uploaded_file.name} to data library!", icon="💾")
                st.session_state.ingest_status = None # reset status to force re-run
    
    # List current files in library
    current_files = get_indexed_documents()
    if current_files:
        st.markdown(f"**Current Documents ({len(current_files)}):**")
        for f_name in current_files:
            suffix_emoji = "📄"
            if f_name.endswith(".pdf"):
                suffix_emoji = "📕"
            elif f_name.endswith(".docx"):
                suffix_emoji = "📘"
            st.caption(f"{suffix_emoji} {f_name}")
    else:
        st.info("No documents found in the database. Please upload documents or run sample generator.")

    # Trigger indexing
    st.markdown("")
    col_ingest, col_clear = st.columns(2)
    with col_ingest:
        if st.button("🚀 Index Docs", use_container_width=True):
            if not api_key:
                st.error("GEMINI_API_KEY is not set. Add it to your .env file.")
            else:
                with st.spinner("Analyzing and embedding documents..."):
                    try:
                        num_chunks = ingest_directory(api_key=api_key)
                        st.session_state.ingest_status = f"Successfully indexed {num_chunks} chunks!"
                        st.toast("Database updated!", icon="✅")
                    except Exception as e:
                        st.error(f"Ingestion failed: {e}")
    with col_clear:
        if st.button("🗑️ Clear DB", use_container_width=True, help="Wipes ChromaDB local vectors"):
            clear_db()
            
    if st.session_state.ingest_status:
        st.success(st.session_state.ingest_status)

    st.markdown("---")
    st.markdown("### ⚙️ Pipeline Parameters")
    k_param = st.slider("Retrieve Chunks (k)", min_value=1, max_value=10, value=4, step=1, help="Number of semantic fragments retrieved to answer the question.")
    temp_param = st.slider("Temperature", min_value=0.0, max_value=1.0, value=0.0, step=0.1, help="Generation randomness. Set to 0.0 for strict, grounded answers.")


# ================= MAIN BODY =================

st.markdown('<div class="main-header">BookExpert Q&A Assistant</div>', unsafe_allow_html=True)
st.markdown('<div class="subheader">Ask questions about your private PDF, DOCX, and text documents. The system returns grounded responses verified by direct citations.</div>', unsafe_allow_html=True)

# Define Tabs
tab_qa, tab_library, tab_explorer = st.tabs(["💬 Grounded Chat", "📂 Library Preview", "🔍 Vector Search Explorer"])

# Tab 1: Grounded Q&A Chat
with tab_qa:
    if not api_key:
        st.warning("⚠️ Warning: GEMINI_API_KEY is missing. Add it to your .env file to enable Q&A capabilities.")

    # Container for Chat Bubbles
    chat_placeholder = st.container()
    
    # Display previous chat messages
    with chat_placeholder:
        for chat in st.session_state.chat_history:
            # User Message
            st.markdown(
                f'<div class="chat-bubble user-bubble">{chat["query"]}</div>',
                unsafe_allow_html=True
            )
            
            # Bot Answer Card
            bot_html = f'<div class="chat-bubble bot-bubble">{chat["answer"]}<br>'
            if chat["citations"]:
                bot_html += '<div style="margin-top: 8px; border-top: 1px solid #E2E8F0; padding-top: 8px;">'
                # Render clean source badges
                unique_citations = list(set(chat["citations"]))
                for source in unique_citations:
                    bot_html += f'<span class="citation-badge"><span class="citation-badge-icon">📍</span>{source}</span>'
                bot_html += '</div>'
            bot_html += '</div>'
            
            st.markdown(bot_html, unsafe_allow_html=True)

    # Chat Input Field
    st.markdown("<div style='clear: both; margin-bottom: 2rem;'></div>", unsafe_allow_html=True)
    
    # Form for chat input (clears upon submit)
    with st.form("chat_form", clear_on_submit=True):
        user_input = st.text_input("Ask your documents a question:", placeholder="e.g. What was Acme Corp's net income in Q1 2026?", label_visibility="collapsed")
        col_sub, col_clr_chat = st.columns([6, 1])
        with col_sub:
            submit_button = st.form_submit_type = st.form_submit_button("Send Question")
        with col_clr_chat:
            clear_chat_button = st.form_submit_button("Clear Chat 🗑️")

    if clear_chat_button:
        st.session_state.chat_history = []
        st.rerun()

    if submit_button and user_input:
        if not api_key:
            st.error("GEMINI_API_KEY is not set. Add it to your .env file.")
        else:
            with st.spinner("Searching document database and generating response..."):
                response = query_rag_pipeline(
                    user_query=user_input,
                    db_path=DB_DIR,
                    k=k_param,
                    temperature=temp_param,
                    api_key=api_key
                )
                
                # Append to history
                st.session_state.chat_history.append({
                    "query": user_input,
                    "answer": response["answer"],
                    "citations": response["citations"]
                })
                
                st.rerun()

# Tab 2: Document Library Preview
with tab_library:
    st.markdown("### Document Repository Preview")
    st.markdown("Below is the list of active documents stored in your `./data` directory. Click to generate mock documents if none are present.")
    
    if st.button("🔧 Generate Sample Data Documents", help="Creates 4 realistic test PDF and DOCX documents automatically"):
        with st.spinner("Generating document package..."):
            try:
                import sys
                import subprocess
                # Run the generate_dummy_docs.py script
                script_path = BASE_DIR / "generate_dummy_docs.py"
                result = subprocess.run([sys.executable, str(script_path)], capture_output=True, text=True)
                if result.returncode == 0:
                    st.success("Sample documents generated successfully!")
                    st.toast("Generated 4 sample files", icon="📁")
                    st.rerun()
                else:
                    st.error(f"Error generating documents: {result.stderr}")
            except Exception as e:
                st.error(f"Exception raised: {e}")

    # Display files and details
    if current_files:
        for index, f_name in enumerate(current_files):
            file_path = DATA_DIR / f_name
            file_size_kb = file_path.stat().st_size / 1024
            
            with st.expander(f"📄 {f_name} (Size: {file_size_kb:.2f} KB)"):
                st.caption(f"Path: {os.path.basename(file_path)}")
                # Provide download button
                with open(file_path, "rb") as f:
                    st.download_button(
                        label=f"Download {f_name}",
                        data=f,
                        file_name=f_name,
                        key=f"dl_{index}"
                    )
    else:
        st.info("No documents are currently stored in `./data`. Use the sidebar or click 'Generate Sample Data Documents' above.")

# Tab 3: Vector Search Explorer
with tab_explorer:
    st.markdown("### Real-Time Vector Similarity Explorer")
    st.markdown("Type a search term below to query ChromaDB directly and inspect the raw text chunks retrieved along with their distance metrics.")
    
    explore_query = st.text_input("Enter testing query:", placeholder="e.g. superconductor applications")
    
    if explore_query:
        if not api_key:
            st.error("GEMINI_API_KEY is not set. Add it to your .env file.")
        else:
            try:
                # Query ChromaDB using the pipeline helper but return metadata
                response = query_rag_pipeline(
                    user_query=explore_query,
                    db_path=DB_DIR,
                    k=k_param,
                    api_key=api_key
                )
                
                # Check for errors in answer
                if "Error" in response["answer"] and not response["raw_context"]:
                    st.error(response["answer"])
                else:
                    st.success(f"Retrieved {len(response['raw_context'])} matches from ChromaDB:")
                    
                    for i, (doc, meta) in enumerate(zip(response['raw_context'], response['metadatas'])):
                        distance = response['distances'][i] if i < len(response['distances']) else "N/A"
                        # Cosine similarity is 1 - Cosine Distance
                        similarity = 1.0 - distance if isinstance(distance, (int, float)) else "N/A"
                        
                        st.markdown(f"#### Match #{i+1} — `{meta.get('source')}` (Page {meta.get('page')})")
                        col1, col2 = st.columns(2)
                        with col1:
                            st.caption(f"**Chunk Offset Range:** {meta.get('chunk_range', 'N/A')}")
                        with col2:
                            if isinstance(similarity, float):
                                st.caption(f"**Semantic Similarity Score:** `{similarity:.4f}` (Cosine Distance: `{distance:.4f}`)")
                            else:
                                st.caption(f"**Semantic Distance:** `{distance}`")
                                
                        st.info(doc)
            except Exception as e:
                st.error(f"Error exploring database: {e}")

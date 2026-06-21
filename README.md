# 📚 BookExpert Q&A Assistant

> An advanced, premium-designed **Retrieval-Augmented Generation (RAG)** Document Q&A Bot powered by **Google Gemini**, **ChromaDB**, and **Streamlit**.

![Python](https://img.shields.io/badge/Python-3.11+-blue)
![Streamlit](https://img.shields.io/badge/Streamlit-1.30+-red)
![ChromaDB](https://img.shields.io/badge/ChromaDB-0.4.22+-green)
![Gemini](https://img.shields.io/badge/Google_Gemini-2.5_Flash-orange)
![License](https://img.shields.io/badge/License-MIT-yellow)

---

## 🎯 What is BookExpert?

BookExpert is an intelligent Document Q&A platform that lets users upload **private PDF, DOCX, and TXT files** and ask natural language questions about them. The system returns **structured, grounded answers with direct inline citations** — preventing AI hallucinations by restricting the LLM to answer **only** from ingested documents.

---

## ✨ Features

- 📄 **Multi-format Support** — PDF, DOCX, and TXT files (up to 200MB per file)
- 🔍 **Semantic Vector Search** — Cosine similarity search using `text-embedding-004`
- 🤖 **Hallucination-Free Answers** — Gemini LLM strictly answers from your documents only
- 📌 **Inline Citations** — Every fact is mapped to its source file and page number
- 🗄️ **Persistent Vector DB** — ChromaDB saves embeddings to disk — index once, use forever
- 🔒 **Secure API Handling** — API key loaded from `.env`, never exposed in UI
- 🧭 **Vector Search Explorer** — Inspect raw ChromaDB chunks with cosine similarity scores
- 📁 **Library Preview** — View and download all indexed documents
- ⚙️ **Configurable Pipeline** — Adjust Retrieve Chunks (k) and Temperature from sidebar
- 🎨 **Premium UI** — Slate-blue gradients, custom fonts, expandable source badges

---

## 🏗️ Architecture & Pipeline Flow

The system separates concerns between **indexing** (offline ingestion) and **querying** (real-time answering):

```
                                 +--------------------+
                                 |  Custom Documents  |
                                 | (PDF, DOCX, TXT)   |
                                 +---------+----------+
                                           |
                                           v
+-------------------+            +---------+----------+            +------------------+
|    User Query     +----------->|   Vector Database  +----------->| Retrieved Chunks |
+---------+---------+            |  (Semantic Search) |            +--------+---------+
          |                      +--------------------+                     |
          |                                                                 v
          |                      +--------------------+            +--------+---------+
          +--------------------->| Prompt Formulator  |<-----------+  Source Citations|
                                 +---------+----------+            +------------------+
                                           |
                                           v
                                 +---------+----------+
                                 |  Language Model    |
                                 |  (Gemini 2.5 Flash)|
                                 +---------+----------+
                                           |
                                           v
                                 +---------+----------+
                                 | Grounded Answer &  |
                                 |    Citations       |
                                 +--------------------+
```

### 1. 📄 Document Extraction & Parsing
- **PDFs** — Parsed page-by-page using `pypdf`, tracking exact page numbers
- **DOCXs** — Parsed paragraph-by-paragraph using `python-docx`, aggregated into ~1500 character page-like blocks
- **TXTs** — Divided into logical ~1500 character chunks

### 2. ✂️ Recursive Character Splitting
Text is split using a prioritized separator hierarchy (`\n\n` → `\n` → ` ` → `""`), preserving paragraph and sentence boundaries. Chunks are sized up to **1000 characters** with **200 character overlap** for contextual continuity.

### 3. 🧠 Embeddings & Persistence
Text chunks are embedded using Google's **`text-embedding-004`** model. Vectors are saved in a disk-persistent **ChromaDB** database (`./db`) — no repeated embedding costs on restart.

### 4. 🔎 Semantic Search & Grounded Generation
1. Query is embedded using `text-embedding-004`
2. Cosine similarity search retrieves top **k** chunks from ChromaDB
3. Strict system prompt forces Gemini to reply **only** from retrieved fragments
4. Inline citations like `[business_doc.pdf, Page 1]` injected next to every fact
5. If answer is not found → fallback message returned, no hallucination

---

## 📂 Project Structure

```
document-qa-bot/
├── .env                        # API keys (never commit this!)
├── .gitignore                  # Ignores venv, db/, .env
├── README.md                   # Project documentation
├── requirements.txt            # Dependencies with pinned versions
├── generate_dummy_docs.py      # Script to generate 4 mock documents for testing
├── data/                       # Source documents directory
│   ├── business_doc.pdf
│   ├── policy_doc.pdf
│   ├── science_paper.pdf
│   └── factsheet.docx
├── db/                         # ChromaDB persistent vector store (auto-generated)
└── src/
    ├── __init__.py
    ├── config.py               # App configurations and constants
    ├── ingest.py               # Document ingestion pipeline
    ├── query.py                # RAG query + answer generation pipeline
    └── main.py                 # Premium Streamlit UI entry point
```

---

## ⚡ Setup & Installation

### Prerequisites
- **Python 3.11+** (Tested on Python 3.13.12)
- A valid **Google Gemini API Key** — get one free from [Google AI Studio](https://aistudio.google.com)

### Step 1: Clone the Repository
```bash
git clone https://github.com/your-username/document-qa-bot.git
cd document-qa-bot
```

### Step 2: Create Virtual Environment
```bash
python -m venv venv
```

Activate it:
```bash
# Windows (PowerShell)
.\venv\Scripts\Activate.ps1

# Windows (Command Prompt)
venv\Scripts\activate

# macOS / Linux
source venv/bin/activate
```

### Step 3: Install Dependencies
```bash
pip install -r requirements.txt
```

### Step 4: Configure API Key
Create a `.env` file in the root directory:
```env
GEMINI_API_KEY=your_gemini_api_key_here
```

---

## 🚀 Running the Project

### Step 1: Generate Mock Test Documents (Optional)
If you don't have documents ready, generate 4 comprehensive mock documents:
```bash
python generate_dummy_docs.py
```

### Step 2: Index the Documents
```bash
python src/ingest.py
```
This parses files, splits them recursively, and stores embeddings in ChromaDB.

### Step 3: Test via Command Line (Optional)
```bash
python src/query.py --test "What was Acme Corp's revenue in Q1 2026?"
```

### Step 4: Launch the Web App
```bash
streamlit run src/main.py
```
Open [http://localhost:8501](http://localhost:8501) in your browser.

---

## 🎨 UI Features

| Feature | Description |
|---|---|
| **API Status Indicator** | Shows ✅ API Connected — key never visible in UI |
| **Document Upload** | Drag & drop PDF, DOCX, TXT files directly in sidebar |
| **Index Docs Button** | One-click ingestion and embedding of all documents |
| **Grounded Chat** | Structured answers with headings, bullet points, citations |
| **Library Preview** | View all indexed documents with download buttons |
| **Vector Search Explorer** | Query ChromaDB directly, inspect chunks + cosine scores |
| **Pipeline Parameters** | Adjust Retrieve Chunks (k) and Temperature via sliders |
| **Premium Styling** | Slate-blue gradients, custom fonts, expandable source badges |

---

## 📊 Pipeline Parameters

| Parameter | Default | Range | Description |
|---|---|---|---|
| **Retrieve Chunks (k)** | 4 | 1–10 | Number of document chunks retrieved per query |
| **Temperature** | 0.10 | 0.0–1.0 | 0 = factual & precise, 1 = creative |

---

## 🔒 Security

- API key is **never shown** in the UI — only `✅ API Connected` status displayed
- Loaded securely from `.env` file using `python-dotenv`
- `.env` and `db/` are excluded from Git via `.gitignore`

---

## 📦 Dependencies

```
google-generativeai>=0.3.0
chromadb>=0.4.22
pypdf>=4.0.0
python-docx>=1.1.0
python-dotenv>=1.0.1
streamlit>=1.30.0
tqdm>=4.66.0
```

---

## 🙋 FAQ

**Q: What if I ask something not in the documents?**
> The bot responds: *"The provided documents do not contain information about this topic."* — No hallucinations, ever.

**Q: Do I need to re-index every time I restart the app?**
> No! ChromaDB persists embeddings to `./db` folder. Index once, use forever.

**Q: Which file formats are supported?**
> PDF, DOCX, and TXT files up to 200MB each.

**Q: Can I use a different LLM instead of Gemini?**
> The system is built around the Gemini API. Switching requires modifying `query.py` and `ingest.py`.

---

## 📹 Demo

> 🎬 [Screen Recording] — Add your Loom / YouTube link here

## 🌐 Live Demo

> 🌍 [Deployed App] — [https://document-q-a-bot.streamlit.app/](https://document-q-a-bot.streamlit.app/)

---

## 👨‍💻 Author - Virendra Sahu

Made with ❤️ as part of the **BookExpert AI Engineering Internship Assignment**

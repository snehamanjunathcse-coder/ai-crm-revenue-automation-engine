# Enterprise AI Knowledge & Document Intelligence

A portfolio-grade Retrieval-Augmented Generation (RAG) system for enterprise policies, SOPs, handbooks, and internal knowledge.

## Business problem

Companies store critical knowledge across PDFs, handbooks, policies, SOPs, spreadsheets, and documentation. Employees often waste time searching manually, and generic AI assistants can hallucinate answers that are not supported by company policy.

This system demonstrates an enterprise-safe approach:

**Documents → extraction → chunking → retrieval → grounded LLM answer → citations → confidence → audit trail**

## Core features

- PDF / DOCX / TXT / MD / CSV ingestion
- text extraction
- document chunking with overlap
- local hybrid retrieval
- optional Gemini semantic embeddings
- Gemini answer synthesis
- answers restricted to retrieved company evidence
- inline source-number citations
- confidence scoring
- unsupported-question refusal
- source/evidence viewer
- document inventory
- knowledge analytics
- benchmark grounding tests
- query logging
- audit trail
- zero-cost fallback mode
- recruiter-ready demo documents

## Architecture

```text
Enterprise documents
        ↓
Text extraction
        ↓
Chunking
        ↓
Knowledge index
        ↓
Question
        ↓
Hybrid / semantic retrieval
        ↓
Top evidence passages
        ↓
Gemini grounded-answer layer
        ↓
Answer + citations + confidence
        ↓
Query log + audit trail
```

## Why this is more than a chatbot

The assistant does not answer from general model memory.

It:
1. retrieves relevant enterprise evidence,
2. restricts the model to that evidence,
3. requires citations,
4. returns "I don't know based on the indexed documents" when evidence is insufficient,
5. exposes retrieved passages for human verification.

## Tech stack

- Python
- Streamlit
- Gemini API
- optional Gemini embeddings
- NumPy
- SQLite
- pypdf
- python-docx
- GitHub
- Streamlit Community Cloud

## Zero-cost mode

Without an API key, the system uses:
- local hybrid retrieval
- extractive grounded answers

With the same Gemini key used by the other portfolio projects, it adds:
- LLM grounded answer synthesis
- semantic embeddings when the configured embedding model is available

## Streamlit secrets

```toml
GEMINI_API_KEY = "your-key"
GEMINI_MODEL = "gemini-2.5-flash-lite"
GEMINI_EMBEDDING_MODEL = "gemini-embedding-001"
```

If the embedding endpoint/model is unavailable, the application automatically falls back to local retrieval rather than failing.

## Production extensions

A real organization could extend this architecture with:

- PostgreSQL + pgvector / Supabase
- Qdrant / Pinecone / Weaviate
- SSO and role-based access
- SharePoint / Google Drive / Confluence connectors
- n8n ingestion workflows
- document versioning
- access-control-aware retrieval
- PII redaction
- reranking models
- scheduled evaluation suites
- feedback-based retrieval improvement
- observability and latency/cost monitoring

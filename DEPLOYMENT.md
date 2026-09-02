# Free Deployment

## GitHub repository

Create:

`enterprise-ai-knowledge-intelligence`

Upload the project files so:
- `app.py`
- `rag_core.py`
- `requirements.txt`

are at the repository root.

## Streamlit

Deploy:
- Repository: `<username>/enterprise-ai-knowledge-intelligence`
- Branch: `main`
- Main file: `app.py`

## Secrets

Use the same Gemini key:

```toml
GEMINI_API_KEY = "your-key"
GEMINI_MODEL = "gemini-2.5-flash-lite"
GEMINI_EMBEDDING_MODEL = "gemini-embedding-001"
```

If the embedding model is unavailable, the project automatically falls back to the local retrieval engine.

## End-to-end test

1. Confirm the three demo documents appear in Document Library.
2. Ask: `What is the P1 response target?`
3. Confirm a grounded answer with evidence.
4. Ask: `How many weeks of parental leave are provided?`
5. Confirm the system refuses to invent the answer.
6. Upload a TXT or PDF and ask something contained in that file.

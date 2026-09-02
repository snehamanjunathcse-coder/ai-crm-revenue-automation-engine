# Architecture

```mermaid
flowchart LR
    A[PDF / DOCX / TXT / MD / CSV] --> B[Document Extractor]
    B --> C[Chunker + Metadata]
    C --> D[Knowledge Index]
    E[User Question] --> F[Retriever]
    D --> F
    F --> G[Top Evidence Passages]
    G --> H[Grounded Gemini Answer]
    H --> I[Answer + Citations]
    H --> J[Confidence + Guardrail]
    I --> K[Human Verification]
    J --> L[Query Log]
    F --> L
```

## Retrieval strategy

The project is deployment-safe by design:

1. Attempt Gemini semantic embeddings when configured and available.
2. If embeddings fail or are unavailable, automatically use a local hybrid lexical retrieval engine.
3. The answer layer still receives only retrieved evidence.

## Production architecture

```mermaid
flowchart LR
    A[Google Drive / SharePoint / Confluence] --> B[n8n Ingestion]
    B --> C[Parser + Metadata]
    C --> D[Embedding Service]
    D --> E[pgvector / Qdrant]
    F[Enterprise User] --> G[SSO / RBAC]
    G --> H[RAG API]
    E --> H
    H --> I[Reranker]
    I --> J[LLM Grounded Answer]
    J --> K[Citations]
    J --> L[Evaluation + Observability]
```

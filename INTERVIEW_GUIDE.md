# Interview Guide

## Tell me about the project

I built an enterprise document-intelligence system using Retrieval-Augmented Generation. Users can upload policies, SOPs and other internal documents. The system extracts text, chunks it, retrieves the most relevant passages for a user question, and asks Gemini to answer strictly from that evidence. It exposes source passages, requires citations, reports confidence, and refuses unsupported questions.

## Why RAG?

A generic LLM may answer from general knowledge or hallucinate. Enterprise questions require grounding in the organization's actual documents. RAG gives the model relevant private context at query time without retraining the entire model.

## How do you reduce hallucinations?

I use several layers:
- retrieval before generation,
- a strict system prompt limiting answers to evidence,
- citation requirements,
- relevance thresholds,
- an explicit "I don't know based on the indexed documents" behavior,
- visible evidence for human verification,
- benchmark questions including unsupported queries.

## How does retrieval work?

The portfolio app can use Gemini embeddings for semantic retrieval. It also includes a local hybrid lexical retrieval engine as a resilient fallback, so a third-party embedding issue does not take down the whole demo.

## Why include a fallback?

Production AI systems need graceful degradation. The core knowledge workflow should not become unavailable solely because an embedding endpoint or model changes.

## How would you productionize this?

I would use a proper vector store such as pgvector or Qdrant, add document versioning, access-control-aware retrieval, SSO/RBAC, SharePoint/Drive/Confluence connectors, automated ingestion through n8n, reranking, evaluation pipelines, observability and PII controls.

## What did you learn?

I learned that good enterprise AI work is not only about calling an LLM. Retrieval quality, chunking, metadata, guardrails, evidence visibility, evaluation and failure handling are equally important.

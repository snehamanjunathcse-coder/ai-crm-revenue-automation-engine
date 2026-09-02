import os
import io
import re
import json
import math
import sqlite3
import hashlib
from pathlib import Path
from datetime import datetime

import numpy as np

DB_PATH = Path("knowledge_intelligence.db")

def get_conn():
    conn = sqlite3.connect(DB_PATH, check_same_thread=False, timeout=30)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_conn()
    conn.executescript("""
    CREATE TABLE IF NOT EXISTS documents (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        created_at TEXT NOT NULL,
        filename TEXT NOT NULL,
        file_hash TEXT UNIQUE,
        file_type TEXT,
        page_count INTEGER DEFAULT 1,
        chunk_count INTEGER DEFAULT 0,
        status TEXT DEFAULT 'Indexed'
    );

    CREATE TABLE IF NOT EXISTS chunks (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        document_id INTEGER NOT NULL,
        filename TEXT NOT NULL,
        page_number INTEGER,
        chunk_index INTEGER NOT NULL,
        content TEXT NOT NULL,
        FOREIGN KEY(document_id) REFERENCES documents(id)
    );

    CREATE TABLE IF NOT EXISTS query_log (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        created_at TEXT NOT NULL,
        question TEXT NOT NULL,
        answer TEXT,
        confidence REAL,
        grounded INTEGER,
        source_count INTEGER,
        retrieval_engine TEXT
    );

    CREATE TABLE IF NOT EXISTS audit_log (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        created_at TEXT NOT NULL,
        action TEXT NOT NULL,
        details TEXT
    );
    """)
    conn.commit()
    conn.close()

def audit(action, details=""):
    conn = get_conn()
    conn.execute(
        "INSERT INTO audit_log(created_at, action, details) VALUES(?,?,?)",
        (datetime.now().isoformat(timespec="seconds"), action, details)
    )
    conn.commit()
    conn.close()

def clean_text(text):
    text = (text or "").replace("\x00", " ")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()

def extract_text_from_bytes(filename, data):
    ext = Path(filename).suffix.lower()
    pages = []

    if ext == ".pdf":
        from pypdf import PdfReader
        reader = PdfReader(io.BytesIO(data))
        for i, page in enumerate(reader.pages, start=1):
            pages.append((i, clean_text(page.extract_text() or "")))
    elif ext in (".txt", ".md", ".csv"):
        text = data.decode("utf-8", errors="ignore")
        pages.append((1, clean_text(text)))
    elif ext == ".docx":
        from docx import Document
        doc = Document(io.BytesIO(data))
        text = "\n".join(p.text for p in doc.paragraphs)
        pages.append((1, clean_text(text)))
    else:
        raise ValueError("Unsupported file type. Use PDF, DOCX, TXT, MD, or CSV.")

    pages = [(p, t) for p, t in pages if t.strip()]
    if not pages:
        raise ValueError("No readable text was found in this file.")
    return pages

def chunk_text(text, chunk_size=950, overlap=180):
    text = clean_text(text)
    if not text:
        return []
    chunks = []
    start = 0
    n = len(text)
    while start < n:
        end = min(start + chunk_size, n)
        chunk = text[start:end]

        if end < n:
            cut = max(chunk.rfind(". "), chunk.rfind("\n"))
            if cut > chunk_size * 0.55:
                end = start + cut + 1
                chunk = text[start:end]

        chunks.append(clean_text(chunk))
        if end >= n:
            break
        start = max(end - overlap, start + 1)
    return [c for c in chunks if c]

def file_hash(data):
    return hashlib.sha256(data).hexdigest()

def index_document(filename, data):
    init_db()
    h = file_hash(data)
    conn = get_conn()
    existing = conn.execute("SELECT id FROM documents WHERE file_hash=?", (h,)).fetchone()
    if existing:
        conn.close()
        return {"status": "duplicate", "document_id": existing["id"]}

    pages = extract_text_from_bytes(filename, data)
    cur = conn.execute(
        """INSERT INTO documents(created_at, filename, file_hash, file_type, page_count, chunk_count, status)
           VALUES(?,?,?,?,?,?,?)""",
        (
            datetime.now().isoformat(timespec="seconds"),
            filename, h, Path(filename).suffix.lower(), len(pages), 0, "Indexing"
        )
    )
    doc_id = cur.lastrowid
    count = 0

    for page_num, text in pages:
        for idx, chunk in enumerate(chunk_text(text)):
            conn.execute(
                """INSERT INTO chunks(document_id, filename, page_number, chunk_index, content)
                   VALUES(?,?,?,?,?)""",
                (doc_id, filename, page_num, idx, chunk)
            )
            count += 1

    conn.execute(
        "UPDATE documents SET chunk_count=?, status='Indexed' WHERE id=?",
        (count, doc_id)
    )
    conn.commit()
    conn.close()
    audit("DOCUMENT_INDEXED", f"{filename}; pages={len(pages)}; chunks={count}")
    return {"status": "indexed", "document_id": doc_id, "pages": len(pages), "chunks": count}

def tokenize(text):
    return re.findall(r"[a-zA-Z0-9][a-zA-Z0-9_-]+", (text or "").lower())

def local_retrieve(question, top_k=5):
    conn = get_conn()
    rows = conn.execute("SELECT id, document_id, filename, page_number, chunk_index, content FROM chunks").fetchall()
    conn.close()
    if not rows:
        return [], "local-hybrid"

    q_tokens = tokenize(question)
    q_set = set(q_tokens)
    if not q_tokens:
        return [], "local-hybrid"

    docs_tokens = [tokenize(r["content"]) for r in rows]
    N = len(rows)

    df = {}
    for toks in docs_tokens:
        for term in set(toks):
            df[term] = df.get(term, 0) + 1

    def score(tokens, content):
        if not tokens:
            return 0.0
        tf = {}
        for t in tokens:
            tf[t] = tf.get(t, 0) + 1

        bm = 0.0
        for term in q_tokens:
            if term not in tf:
                continue
            idf = math.log((N + 1) / (df.get(term, 0) + 1)) + 1.0
            bm += (1 + math.log(tf[term])) * idf

        overlap = len(q_set.intersection(set(tokens))) / max(len(q_set), 1)
        phrase_bonus = 0.0
        lower = content.lower()
        meaningful = [t for t in q_tokens if len(t) > 4]
        for term in meaningful:
            if term in lower:
                phrase_bonus += 0.10

        return bm + overlap * 3.0 + phrase_bonus

    scored = []
    for row, toks in zip(rows, docs_tokens):
        s = score(toks, row["content"])
        if s > 0:
            scored.append((s, row))
    scored.sort(key=lambda x: x[0], reverse=True)

    if not scored:
        return [], "local-hybrid"

    max_score = scored[0][0] or 1.0
    results = []
    for raw, row in scored[:top_k]:
        results.append({
            "chunk_id": row["id"],
            "document_id": row["document_id"],
            "filename": row["filename"],
            "page_number": row["page_number"],
            "chunk_index": row["chunk_index"],
            "content": row["content"],
            "score": round(float(raw / max_score), 4)
        })
    return results, "local-hybrid"

def gemini_embedding_retrieve(question, top_k=5):
    key = os.getenv("GEMINI_API_KEY", "").strip()
    if not key:
        return None

    try:
        from google import genai
        client = genai.Client(api_key=key)
        embedding_model = os.getenv("GEMINI_EMBEDDING_MODEL", "gemini-embedding-001")

        conn = get_conn()
        rows = conn.execute(
            "SELECT id, document_id, filename, page_number, chunk_index, content FROM chunks"
        ).fetchall()
        conn.close()
        if not rows:
            return [], "gemini-embeddings"

        q_resp = client.models.embed_content(
            model=embedding_model,
            contents=question
        )
        q_vec = np.array(q_resp.embeddings[0].values, dtype=float)

        results = []
        # Batch small demo sets to stay simple and safe.
        for row in rows:
            d_resp = client.models.embed_content(
                model=embedding_model,
                contents=row["content"]
            )
            d_vec = np.array(d_resp.embeddings[0].values, dtype=float)
            denom = (np.linalg.norm(q_vec) * np.linalg.norm(d_vec))
            sim = float(np.dot(q_vec, d_vec) / denom) if denom else 0.0
            results.append({
                "chunk_id": row["id"],
                "document_id": row["document_id"],
                "filename": row["filename"],
                "page_number": row["page_number"],
                "chunk_index": row["chunk_index"],
                "content": row["content"],
                "score": round(sim, 4)
            })
        results.sort(key=lambda x: x["score"], reverse=True)
        return results[:top_k], "gemini-embeddings"
    except Exception:
        return None

def retrieve(question, top_k=5):
    # Prefer semantic embeddings when available. Fall back to local retrieval.
    embedded = gemini_embedding_retrieve(question, top_k=top_k)
    if embedded is not None:
        return embedded
    return local_retrieve(question, top_k=top_k)

def answer_with_context(question, sources):
    if not sources:
        return {
            "answer": "I don't know based on the indexed documents.",
            "confidence": 0.0,
            "grounded": False,
            "reason": "No relevant source passages were retrieved."
        }, "guardrail"

    max_score = max(float(s.get("score", 0)) for s in sources)
    if max_score < 0.12:
        return {
            "answer": "I don't know based on the indexed documents.",
            "confidence": round(max_score, 2),
            "grounded": False,
            "reason": "Retrieved passages were too weakly related to the question."
        }, "guardrail"

    context_blocks = []
    for i, s in enumerate(sources, start=1):
        context_blocks.append(
            f"[SOURCE {i}] File: {s['filename']} | Page: {s.get('page_number') or 1}\n{s['content']}"
        )
    context = "\n\n".join(context_blocks)

    key = os.getenv("GEMINI_API_KEY", "").strip()
    if key:
        try:
            from google import genai
            client = genai.Client(api_key=key)
            model = os.getenv("GEMINI_MODEL", "gemini-2.5-flash-lite")
            prompt = f"""
You are an enterprise knowledge assistant.

RULES:
1. Answer ONLY from the supplied source passages.
2. If the answer is not supported, say: "I don't know based on the indexed documents."
3. Do not invent policies, numbers, dates, or procedures.
4. Every factual claim must cite source numbers in square brackets like [1] or [2].
5. Keep the answer concise and operationally useful.
6. If sources conflict, explicitly say so.

QUESTION:
{question}

SOURCE PASSAGES:
{context}

Return ONLY valid JSON:
{{
  "answer": "grounded answer with [1] citations",
  "confidence": number from 0.0 to 1.0,
  "grounded": true or false,
  "reason": "short explanation of grounding quality"
}}
"""
            response = client.models.generate_content(model=model, contents=prompt)
            raw = (response.text or "").strip().replace("```json", "").replace("```", "").strip()
            data = json.loads(raw)
            data["confidence"] = float(max(0.0, min(float(data.get("confidence", max_score)), 1.0)))
            return data, "gemini"
        except Exception:
            pass

    # Deterministic fallback: return strongest evidence snippet.
    best = sources[0]
    excerpt = best["content"][:700]
    return {
        "answer": f"Based on the strongest retrieved source: {excerpt} [1]",
        "confidence": round(float(max_score), 2),
        "grounded": True,
        "reason": "Fallback extractive answer from the highest-ranked source."
    }, "fallback"

def ask(question, top_k=5):
    sources, retrieval_engine = retrieve(question, top_k=top_k)
    answer, answer_engine = answer_with_context(question, sources)

    conn = get_conn()
    conn.execute(
        """INSERT INTO query_log(
            created_at, question, answer, confidence, grounded, source_count, retrieval_engine
        ) VALUES(?,?,?,?,?,?,?)""",
        (
            datetime.now().isoformat(timespec="seconds"),
            question,
            answer["answer"],
            float(answer.get("confidence", 0)),
            1 if answer.get("grounded") else 0,
            len(sources),
            retrieval_engine
        )
    )
    conn.commit()
    conn.close()

    audit(
        "QUESTION_ANSWERED",
        f"retrieval={retrieval_engine}; answer={answer_engine}; confidence={answer.get('confidence')}"
    )
    return answer, sources, retrieval_engine, answer_engine

def delete_document(doc_id):
    conn = get_conn()
    row = conn.execute("SELECT filename FROM documents WHERE id=?", (doc_id,)).fetchone()
    conn.execute("DELETE FROM chunks WHERE document_id=?", (doc_id,))
    conn.execute("DELETE FROM documents WHERE id=?", (doc_id,))
    conn.commit()
    conn.close()
    audit("DOCUMENT_DELETED", row["filename"] if row else str(doc_id))

def seed_demo_documents():
    init_db()
    conn = get_conn()
    count = conn.execute("SELECT COUNT(*) c FROM documents").fetchone()["c"]
    conn.close()
    if count:
        return

    demo_docs = {
        "Customer_Support_Policy.txt": """
CUSTOMER SUPPORT POLICY

Priority Levels
P1 Critical: Complete service outage, major security incident, or inability for enterprise users to access a production system. Initial response target: 30 minutes.
P2 High: Significant degradation or a business-critical function is unavailable for some users. Initial response target: 2 hours.
P3 Standard: General product questions, minor defects, feature guidance, or requests without immediate business impact. Initial response target: 1 business day.

Escalation
P1 incidents must be escalated immediately to the Incident Manager and Engineering On-Call. Customer Operations owns customer communication until resolution.
P2 incidents should be routed to the relevant product or engineering owner and tracked to closure.

Communication
For P1 incidents, customer updates should be sent at least every 60 minutes until service is restored.
""",
        "Remote_Work_and_Security_Handbook.txt": """
REMOTE WORK AND SECURITY HANDBOOK

Employees may work remotely from approved locations. Company confidential information must only be accessed using company-managed devices with multi-factor authentication enabled.

Sensitive customer data must not be copied into personal cloud storage, personal email, or unapproved AI tools.

If a company device is lost or stolen, the employee must notify Security and their manager immediately and no later than one hour after discovery.

Passwords must never be shared. MFA is mandatory for company email, source-code repositories, finance systems, and administrative consoles.
""",
        "Expense_and_Travel_Policy.txt": """
EXPENSE AND TRAVEL POLICY

Employees should obtain manager approval before booking international business travel.

Airfare should normally be booked in economy class. Premium economy may be approved for flights longer than eight hours with manager approval.

Hotel expenses are reimbursable up to EUR 220 per night in major European cities unless an exception is approved in writing.

Meal expenses are reimbursable up to EUR 65 per day during approved business travel.

Receipts are required for any single expense above EUR 25. Expense reports should be submitted within 15 calendar days after the trip ends.
"""
    }

    for name, text in demo_docs.items():
        index_document(name, text.strip().encode("utf-8"))

def system_stats():
    conn = get_conn()
    stats = {
        "documents": conn.execute("SELECT COUNT(*) FROM documents").fetchone()[0],
        "chunks": conn.execute("SELECT COUNT(*) FROM chunks").fetchone()[0],
        "queries": conn.execute("SELECT COUNT(*) FROM query_log").fetchone()[0],
        "grounded": conn.execute("SELECT COUNT(*) FROM query_log WHERE grounded=1").fetchone()[0],
    }
    conn.close()
    return stats

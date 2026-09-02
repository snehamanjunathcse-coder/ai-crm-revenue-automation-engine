import os
from datetime import datetime
import pandas as pd
import streamlit as st

from rag_core import (
    init_db, seed_demo_documents, index_document, ask, get_conn,
    delete_document, system_stats
)

st.set_page_config(
    page_title="Enterprise AI Knowledge Intelligence",
    page_icon="🧠",
    layout="wide"
)

init_db()
seed_demo_documents()

st.title("🧠 Enterprise AI Knowledge & Document Intelligence")
st.caption(
    "Grounded RAG · document ingestion · semantic retrieval · source citations · confidence scoring · hallucination guardrails · auditability"
)

with st.sidebar:
    st.subheader("System status")
    st.write(f"**Answer engine:** {'Gemini API' if os.getenv('GEMINI_API_KEY') else 'Extractive Demo Mode'}")
    st.write(
        f"**Retrieval:** {'Semantic embeddings + fallback' if os.getenv('GEMINI_API_KEY') else 'Local hybrid retrieval'}"
    )
    st.write("**Human verification:** Supported")
    st.write("**Demo cost:** ₹0")
    st.divider()
    stats = system_stats()
    st.metric("Indexed documents", stats["documents"])
    st.metric("Knowledge chunks", stats["chunks"])
    st.metric("Questions asked", stats["queries"])

tabs = st.tabs([
    "💬 Ask Knowledge Base",
    "📚 Document Library",
    "⬆️ Upload & Index",
    "📊 Intelligence Dashboard",
    "🧪 Grounding Tests",
    "🧾 Audit Trail"
])

with tabs[0]:
    st.subheader("Ask a grounded question")
    st.info("The assistant is instructed to answer only from indexed documents and cite its evidence.")

    example = st.selectbox(
        "Quick examples",
        [
            "",
            "What is the response target for a P1 critical incident?",
            "What should happen if a company laptop is stolen?",
            "How much can an employee spend on a hotel in a major European city?",
            "Can I store customer data in my personal Google Drive?",
            "What is the company's parental leave policy?"
        ]
    )
    question = st.text_area(
        "Question",
        value=example,
        height=100,
        placeholder="Ask a policy, SOP, process, or knowledge question..."
    )

    top_k = st.slider("Evidence passages to retrieve", 3, 8, 5)

    if st.button("🔎 Retrieve & answer", type="primary", use_container_width=True):
        if question.strip():
            with st.spinner("Searching enterprise knowledge..."):
                answer, sources, retrieval_engine, answer_engine = ask(question.strip(), top_k=top_k)

            c1, c2, c3 = st.columns(3)
            c1.metric("Confidence", f"{answer.get('confidence', 0)*100:.0f}%")
            c2.metric("Grounded", "Yes" if answer.get("grounded") else "No")
            c3.metric("Sources", len(sources))

            if answer.get("grounded"):
                st.success(answer["answer"])
            else:
                st.warning(answer["answer"])

            st.caption(
                f"Retrieval engine: {retrieval_engine} · Answer engine: {answer_engine} · {answer.get('reason','')}"
            )

            if sources:
                st.subheader("Evidence")
                for i, s in enumerate(sources, start=1):
                    with st.expander(
                        f"[{i}] {s['filename']} · page {s.get('page_number') or 1} · relevance {float(s.get('score',0))*100:.0f}%"
                    ):
                        st.write(s["content"])

with tabs[1]:
    conn = get_conn()
    docs = pd.read_sql_query(
        "SELECT id, created_at, filename, file_type, page_count, chunk_count, status FROM documents ORDER BY id DESC",
        conn
    )
    conn.close()

    st.subheader("Indexed knowledge library")
    st.dataframe(docs, use_container_width=True, hide_index=True)

    if not docs.empty:
        doc_id = st.selectbox(
            "Manage document",
            docs["id"].tolist(),
            format_func=lambda x: f"#{x} — {docs.loc[docs['id']==x,'filename'].iloc[0]}"
        )
        if st.button("Delete selected document"):
            delete_document(int(doc_id))
            st.success("Document removed from the knowledge index.")
            st.rerun()

with tabs[2]:
    st.subheader("Upload enterprise documents")
    st.write("Supported: **PDF, DOCX, TXT, MD, CSV**")

    uploaded = st.file_uploader(
        "Upload one or more documents",
        type=["pdf", "docx", "txt", "md", "csv"],
        accept_multiple_files=True
    )

    if uploaded and st.button("⚡ Index documents", use_container_width=True):
        results = []
        for f in uploaded:
            try:
                result = index_document(f.name, f.getvalue())
                results.append({"file": f.name, **result})
            except Exception as e:
                results.append({"file": f.name, "status": "error", "error": str(e)})
        st.dataframe(pd.DataFrame(results), use_container_width=True, hide_index=True)
        st.success("Indexing workflow complete.")

with tabs[3]:
    stats = system_stats()
    c1,c2,c3,c4 = st.columns(4)
    c1.metric("Documents", stats["documents"])
    c2.metric("Chunks", stats["chunks"])
    c3.metric("Queries", stats["queries"])
    grounded_rate = (stats["grounded"] / stats["queries"] * 100) if stats["queries"] else 0
    c4.metric("Grounded-answer rate", f"{grounded_rate:.0f}%")

    conn = get_conn()
    logs = pd.read_sql_query(
        "SELECT created_at, question, confidence, grounded, source_count, retrieval_engine FROM query_log ORDER BY id DESC",
        conn
    )
    docs = pd.read_sql_query(
        "SELECT filename, chunk_count, page_count FROM documents ORDER BY chunk_count DESC",
        conn
    )
    conn.close()

    a,b = st.columns(2)
    with a:
        st.subheader("Knowledge volume")
        if not docs.empty:
            chart = docs.set_index("filename")["chunk_count"]
            st.bar_chart(chart)
    with b:
        st.subheader("Recent query confidence")
        if not logs.empty:
            chart = logs.head(20).copy()
            chart["confidence_pct"] = chart["confidence"] * 100
            st.bar_chart(chart.set_index("question")["confidence_pct"])

    st.subheader("Recent knowledge queries")
    st.dataframe(logs.head(30), use_container_width=True, hide_index=True)

with tabs[4]:
    st.subheader("Grounding & hallucination tests")
    st.write("These benchmark questions demonstrate both **answering** and **refusing unsupported questions**.")

    tests = [
        ("P1 response target", "What is the response target for a P1 critical incident?", "Supported"),
        ("Lost laptop procedure", "What should I do if my company laptop is stolen?", "Supported"),
        ("Hotel reimbursement", "What is the hotel reimbursement limit in major European cities?", "Supported"),
        ("Unsupported HR policy", "How many weeks of parental leave does the company provide?", "Should refuse"),
    ]

    if st.button("▶ Run benchmark"):
        out = []
        for name, q, expectation in tests:
            ans, sources, retrieval_engine, answer_engine = ask(q, top_k=4)
            out.append({
                "test": name,
                "expectation": expectation,
                "answer": ans["answer"],
                "grounded": ans["grounded"],
                "confidence": round(float(ans["confidence"]), 2),
                "sources": len(sources)
            })
        st.dataframe(pd.DataFrame(out), use_container_width=True, hide_index=True)

with tabs[5]:
    conn = get_conn()
    audit = pd.read_sql_query(
        "SELECT * FROM audit_log ORDER BY id DESC LIMIT 300",
        conn
    )
    conn.close()
    st.subheader("Knowledge-system audit trail")
    st.dataframe(audit, use_container_width=True, hide_index=True)

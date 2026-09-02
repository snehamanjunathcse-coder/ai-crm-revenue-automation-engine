# 90-Second Recruiter Demo

## 0–15 sec — business problem

"Companies have important answers scattered across policies, SOPs and PDFs. Employees waste time searching them manually, while generic AI tools can hallucinate company policy."

## 15–35 sec — grounded RAG answer

Ask:

`What is the response target for a P1 critical incident?`

Show:
- grounded answer
- confidence
- cited sources
- actual evidence passage

Explain:
"The answer is generated from retrieved company evidence rather than unrestricted model memory."

## 35–55 sec — security question

Ask:

`Can customer data be stored in a personal cloud drive?`

Show policy-grounded answer and evidence.

## 55–70 sec — hallucination guardrail

Ask:

`How many weeks of parental leave does the company provide?`

The demo documents do not contain a parental-leave policy.

Show that the system refuses to invent an answer.

## 70–90 sec — architecture

Open Document Library / Dashboard / Audit Trail.

Close with:

"This project demonstrates RAG, document ingestion, retrieval, LLM grounding, source citations, hallucination guardrails, evaluation and enterprise AI product thinking."

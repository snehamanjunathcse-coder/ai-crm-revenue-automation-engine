# AI Revenue Operations Workspace

[![Live App](https://img.shields.io/badge/Live%20App-Streamlit-FF4B4B?logo=streamlit&logoColor=white)](https://ai-crm-revenue-automation-engine-szzgzixhhpdwstdochywrk.streamlit.app/)
![Python](https://img.shields.io/badge/Python-3.12+-3776AB?logo=python&logoColor=white)
![Gemini](https://img.shields.io/badge/AI-Gemini-4285F4)

An AI-assisted revenue operations workspace for lead qualification, outreach preparation, reply intelligence and pipeline visibility.

## Problem

Revenue teams repeatedly review new leads, decide priority, draft outreach, remember follow-ups, interpret replies and update pipeline stages. Manual handling slows response time and creates inconsistent execution.

## Workflow

`Lead → AI qualification → score → Hot/Warm/Cold → outreach draft → human approval → follow-up → reply analysis → pipeline update → forecast`

## Key capabilities

- 0–100 lead scoring and Hot/Warm/Cold segmentation
- Business-fit and pain-point analysis
- Personalized outreach drafting
- Human approval before customer-facing actions
- Follow-up scheduling
- Reply intent and sentiment analysis
- CRM-style pipeline stage management
- Opportunity-value and weighted-pipeline reporting
- CSV export and audit logging
- Rules-based fallback when the LLM is unavailable

## Stack

Python · Streamlit · Gemini API · SQLite · pandas

## Design decisions

**Commercial relevance.** AI outputs are connected to concrete pipeline decisions rather than presented as a standalone chatbot.

**Human approval.** Customer-facing communication remains reviewable before it changes workflow state.

**Persistent workflow state.** Lead data, pipeline stages, replies and audit events are stored so the system behaves like an operations tool, not a one-off prompt.

## Run locally

```bash
python -m venv .venv
# Windows
.venv\Scripts\activate
# macOS/Linux
source .venv/bin/activate

pip install -r requirements.txt
streamlit run app.py
```

Optional Gemini configuration:

```text
GEMINI_API_KEY=your_key_here
GEMINI_MODEL=gemini-2.5-flash-lite
```

## Production roadmap

A production version could connect HubSpot/Salesforce, Gmail/Outlook, calendars and lead sources through APIs or n8n, with authentication, scheduled jobs and conversion analytics.

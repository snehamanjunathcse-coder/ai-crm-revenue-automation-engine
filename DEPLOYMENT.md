# Free Deployment

## GitHub
Create:
`ai-crm-revenue-automation-engine`

Upload the project so `app.py` and `requirements.txt` are at the repository root.

## Streamlit
- Repository: `<your-username>/ai-crm-revenue-automation-engine`
- Branch: `main`
- Main file: `app.py`

## Gemini
Streamlit → Manage app → Settings → Secrets:
```toml
GEMINI_API_KEY = "your-key"
GEMINI_MODEL = "gemini-2.5-flash-lite"
```

## Smoke test
1. Confirm sidebar says Gemini API.
2. Create a SaaS lead with clear automation pain.
3. Verify score + temperature + outreach.
4. Approve outreach.
5. Paste a meeting-request reply.
6. Verify reply intent and stage.
7. Check dashboard and audit trail.

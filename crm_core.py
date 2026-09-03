import os, json, sqlite3
from datetime import datetime, timedelta
from pathlib import Path

DB_PATH = Path("crm_engine.db")
STAGES = ["New","Qualified","Contacted","Engaged","Meeting","Proposal","Won","Lost"]

def get_conn():
    c=sqlite3.connect(DB_PATH, check_same_thread=False, timeout=30); c.row_factory=sqlite3.Row; return c

def init_db():
    c=get_conn()
    c.executescript("""
    CREATE TABLE IF NOT EXISTS leads(
      id INTEGER PRIMARY KEY AUTOINCREMENT, created_at TEXT NOT NULL,
      company TEXT NOT NULL, contact_name TEXT, email TEXT, role TEXT,
      industry TEXT, company_size TEXT, country TEXT, source TEXT, notes TEXT,
      estimated_value REAL DEFAULT 0, score INTEGER, temperature TEXT,
      fit_summary TEXT, pain_points TEXT, outreach_subject TEXT,
      outreach_message TEXT, recommended_next_step TEXT,
      stage TEXT DEFAULT 'New', owner TEXT DEFAULT 'Revenue Operations',
      next_follow_up TEXT, last_activity TEXT);
    CREATE TABLE IF NOT EXISTS replies(
      id INTEGER PRIMARY KEY AUTOINCREMENT, created_at TEXT NOT NULL,
      lead_id INTEGER NOT NULL, reply_text TEXT NOT NULL, intent TEXT,
      sentiment TEXT, summary TEXT, recommended_action TEXT, stage_after TEXT);
    CREATE TABLE IF NOT EXISTS audit_log(
      id INTEGER PRIMARY KEY AUTOINCREMENT, created_at TEXT NOT NULL,
      action TEXT NOT NULL, lead_id INTEGER, details TEXT);
    """)
    c.commit(); c.close()

def log_action(action,lead_id=None,details=""):
    c=get_conn(); c.execute("INSERT INTO audit_log(created_at,action,lead_id,details) VALUES(?,?,?,?)",
        (datetime.now().isoformat(timespec="seconds"),action,lead_id,details)); c.commit(); c.close()

def fallback_score(lead):
    notes=(lead.get("notes") or "").lower(); role=(lead.get("role") or "").lower()
    industry=(lead.get("industry") or "").lower(); size=(lead.get("company_size") or "").lower()
    score=45
    if any(k in role for k in ["head","director","vp","founder","manager","chief"]): score+=15
    if any(k in notes for k in ["manual","automation","slow","repetitive","crm","follow-up","ai","pipeline"]): score+=20
    if any(k in size for k in ["51-200","201-500","501-1000","1000+"]): score+=10
    if any(k in industry for k in ["saas","software","technology","consulting","healthcare","finance"]): score+=5
    score=max(0,min(score,100)); temp="Hot" if score>=75 else "Warm" if score>=55 else "Cold"
    return {
      "score":score,"temperature":temp,
      "fit_summary":f"{temp} lead with a {score}/100 fit score based on role seniority, business pain, and company profile.",
      "pain_points":"Manual lead handling, inconsistent follow-up, and limited pipeline visibility.",
      "recommended_next_step":"Prepare personalized outreach and route for human approval.",
      "outreach_subject":f"Reducing manual revenue operations at {lead.get('company','your team')}",
      "outreach_message":f"""Hi {lead.get('contact_name') or 'there'},

I noticed {lead.get('company','your team')} may be dealing with manual or repetitive revenue workflows. I work on AI-assisted automation for lead qualification, follow-ups, routing, and pipeline visibility. If improving that workflow is a priority, I’d be happy to share a short example of how it could be streamlined.

Best,
Sneha""",
      "owner":"Revenue Operations"}

def gemini_json(prompt):
    key=os.getenv("GEMINI_API_KEY","").strip()
    if not key: return None,"demo"
    try:
        from google import genai
        client=genai.Client(api_key=key)
        model=os.getenv("GEMINI_MODEL","gemini-2.5-flash-lite")
        r=client.models.generate_content(model=model,contents=prompt)
        raw=(r.text or "").strip().replace("```json","").replace("```","").strip()
        return json.loads(raw),"gemini"
    except Exception:
        return None,"fallback"

def score_lead(lead):
    prompt=f"""You are an AI Revenue Operations Analyst.
Evaluate this B2B lead for an AI automation / operations solution.

Company: {lead.get('company')}
Contact: {lead.get('contact_name')}
Role: {lead.get('role')}
Industry: {lead.get('industry')}
Company size: {lead.get('company_size')}
Country: {lead.get('country')}
Source: {lead.get('source')}
Estimated opportunity value: {lead.get('estimated_value')}
Notes: {lead.get('notes')}

Return ONLY valid JSON with:
score: integer 0-100
temperature: Hot, Warm, or Cold
fit_summary: <=45 words
pain_points: <=45 words
recommended_next_step: <=35 words
outreach_subject: concise email subject
outreach_message: personalized B2B outreach email <=120 words
owner: suggested team or role

Consider decision-maker seniority, explicit pain, urgency, company fit,
automation value, and commercial likelihood. Do not invent facts."""
    data,engine=gemini_json(prompt)
    if not data: data=fallback_score(lead)
    data["score"]=max(0,min(int(data.get("score",50)),100))
    data["temperature"]=data.get("temperature","Warm")
    return data,engine

def classify_reply(text):
    prompt=f"""You are an AI Revenue Operations Analyst.
Classify this prospect reply:
{text}
Return ONLY valid JSON with:
intent: one of Interested, Meeting Request, Question, Not Now, Not Interested, Referral, Unclear
sentiment: Positive, Neutral, or Negative
summary: <=30 words
recommended_action: <=35 words
stage_after: one of New, Qualified, Contacted, Engaged, Meeting, Proposal, Won, Lost"""
    data,engine=gemini_json(prompt)
    if data: return data,engine
    t=text.lower()
    if any(k in t for k in ["book","meeting","calendar","call","tomorrow","next week"]):
        return {"intent":"Meeting Request","sentiment":"Positive","summary":text[:180],
                "recommended_action":"Send scheduling options and prepare a concise discovery agenda.","stage_after":"Meeting"},"fallback"
    if any(k in t for k in ["interested","tell me more","sounds useful","yes"]):
        return {"intent":"Interested","sentiment":"Positive","summary":text[:180],
                "recommended_action":"Respond with a tailored value summary and propose a short discovery call.","stage_after":"Engaged"},"fallback"
    if any(k in t for k in ["not interested","remove me","no thanks"]):
        return {"intent":"Not Interested","sentiment":"Negative","summary":text[:180],
                "recommended_action":"Close the opportunity respectfully and stop follow-up.","stage_after":"Lost"},"fallback"
    if any(k in t for k in ["later","quarter","not now","next month"]):
        return {"intent":"Not Now","sentiment":"Neutral","summary":text[:180],
                "recommended_action":"Set a future follow-up date and record the timing context.","stage_after":"Engaged"},"fallback"
    return {"intent":"Question","sentiment":"Neutral","summary":text[:180],
            "recommended_action":"Answer the question clearly and keep the conversation moving toward qualification.","stage_after":"Engaged"},"fallback"

def default_followup(temp):
    return (datetime.now()+timedelta(days=1 if temp=="Hot" else 3 if temp=="Warm" else 7)).date().isoformat()

def seed_demo():
    c = get_conn()
    try:
        if c.execute("SELECT COUNT(*) c FROM leads").fetchone()["c"]:
            return

        demo = [
          ("Northstar SaaS","Maya Chen","maya@example.com","Head of Revenue Operations","SaaS","201-500","Netherlands","LinkedIn",18000,
           "Sales team manually qualifies inbound leads, updates CRM fields, and sends follow-ups. Leadership wants better pipeline visibility."),
          ("Helio Health","Daniel Brooks","daniel@example.com","Operations Director","Healthcare","501-1000","Australia","Referral",25000,
           "Teams spend significant time moving information between forms, spreadsheets, and internal systems. Interested in reducing repetitive admin."),
          ("BrightLedger","Sofia Weber","sofia@example.com","Finance Manager","Finance","51-200","Germany","Website",12000,
           "Exploring automation but no urgent project. Interested in reporting and workflow standardization."),
          ("Orbit Consulting","Liam Patel","liam@example.com","Founder","Consulting","11-50","United Kingdom","Outbound",9000,
           "Founder personally handles lead follow-up and proposal reminders. Wants a lightweight AI-assisted process."),
          ("Maple Works","Emma Roy","emma@example.com","Operations Coordinator","Manufacturing","51-200","Canada","Event",7000,
           "General curiosity about AI. No defined business case or timeline yet."),
          ("CloudPeak","Noah Jensen","noah@example.com","VP Sales","Software","201-500","Denmark","LinkedIn",22000,
           "Lead response time is slow and reps forget follow-ups. Looking for automated qualification, routing, and meeting booking.")
        ]

        created = []
        now = datetime.now().isoformat(timespec="seconds")
        for row in demo:
            lead = {
                "company": row[0], "contact_name": row[1], "email": row[2], "role": row[3],
                "industry": row[4], "company_size": row[5], "country": row[6],
                "source": row[7], "estimated_value": row[8], "notes": row[9]
            }
            scored = fallback_score(lead)
            stage = "Qualified" if scored["temperature"] in ("Hot", "Warm") else "New"
            follow_up = default_followup(scored["temperature"])
            cur = c.execute(
                """INSERT INTO leads(
                    created_at,company,contact_name,email,role,industry,company_size,
                    country,source,estimated_value,notes,score,temperature,fit_summary,
                    pain_points,outreach_subject,outreach_message,recommended_next_step,
                    stage,owner,next_follow_up,last_activity
                ) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                (
                    now, *row, scored["score"], scored["temperature"], scored["fit_summary"],
                    scored["pain_points"], scored["outreach_subject"], scored["outreach_message"],
                    scored["recommended_next_step"], stage, scored["owner"], follow_up, now
                )
            )
            created.append((cur.lastrowid, row[0]))

        # Write audit rows using the SAME transaction/connection to avoid DB locks.
        for lead_id, company in created:
            c.execute(
                "INSERT INTO audit_log(created_at,action,lead_id,details) VALUES(?,?,?,?)",
                (now, "DEMO_LEAD_CREATED", lead_id, company)
            )

        c.commit()
    finally:
        c.close()

def reset_demo():
    c=get_conn()
    for t in ["replies","leads","audit_log"]: c.execute(f"DELETE FROM {t}")
    c.commit(); c.close(); seed_demo()

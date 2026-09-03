import os
from datetime import datetime, timedelta
import pandas as pd
import streamlit as st

from crm_core import (
    get_conn, init_db, seed_demo, reset_demo, score_lead, classify_reply,
    default_followup, log_action, STAGES
)

st.set_page_config(page_title="AI CRM & Revenue Automation Engine", page_icon="💰", layout="wide")
init_db(); seed_demo()

def load_leads():
    c=get_conn(); df=pd.read_sql_query("SELECT * FROM leads ORDER BY id DESC",c); c.close(); return df

def load_replies():
    c=get_conn(); df=pd.read_sql_query("SELECT * FROM replies ORDER BY id DESC",c); c.close(); return df

def process_lead(lead_id):
    c=get_conn(); row=c.execute("SELECT * FROM leads WHERE id=?",(lead_id,)).fetchone(); c.close()
    if not row: return None,"missing"
    result,engine=score_lead(dict(row))
    follow=default_followup(result["temperature"])
    stage="Qualified" if result["temperature"] in ("Hot","Warm") else "New"
    c=get_conn()
    c.execute("""UPDATE leads SET score=?,temperature=?,fit_summary=?,pain_points=?,outreach_subject=?,
    outreach_message=?,recommended_next_step=?,owner=?,stage=?,next_follow_up=?,last_activity=? WHERE id=?""",
    (result["score"],result["temperature"],result["fit_summary"],result["pain_points"],
     result["outreach_subject"],result["outreach_message"],result["recommended_next_step"],
     result.get("owner","Revenue Operations"),stage,follow,datetime.now().isoformat(timespec="seconds"),lead_id))
    c.commit(); c.close()
    log_action("AI_LEAD_SCORED",lead_id,f"engine={engine}; score={result['score']}; temp={result['temperature']}")
    return result,engine

def process_all():
    df=load_leads()
    for lead_id in df[df["score"].isna()]["id"].tolist(): process_lead(int(lead_id))

def weighted_pipeline(df):
    weights={"New":0.05,"Qualified":0.15,"Contacted":0.25,"Engaged":0.40,"Meeting":0.55,"Proposal":0.75,"Won":1.0,"Lost":0}
    return sum(float(r["estimated_value"] or 0)*weights.get(r["stage"],0) for _,r in df.iterrows()) if not df.empty else 0

def overdue_followups(df):
    today=datetime.now().date(); count=0
    for _,r in df.iterrows():
        if r["next_follow_up"] and r["stage"] not in ("Won","Lost"):
            try:
                if datetime.fromisoformat(r["next_follow_up"]).date()<today: count+=1
            except: pass
    return count

st.title("💰 AI Revenue Operations Workspace")
st.caption("AI lead scoring · personalized outreach · follow-up automation · reply intelligence · pipeline visibility · revenue forecasting")

with st.sidebar:
    st.subheader("System status")
    st.write(f"**AI engine:** {'Gemini API' if os.getenv('GEMINI_API_KEY') else 'Demo AI Mode'}")
    st.write("**CRM datastore:** SQLite")
    st.write("**Human approval:** Enabled")
    st.divider()
    if st.button("⚡ Score all unprocessed leads",use_container_width=True):
        process_all(); st.success("Lead scoring complete."); st.rerun()
    if st.button("↻ Reset sample data",use_container_width=True):
        reset_demo(); st.success("Sample data restored."); st.rerun()

tabs=st.tabs(["📊 Revenue Dashboard","➕ Lead Intake","🎯 Lead Intelligence","✉️ Outreach Studio","💬 Reply Intelligence","🧭 Pipeline","🧾 Audit Trail"])

with tabs[0]:
    df=load_leads()
    total=len(df); qualified=len(df[df["temperature"].isin(["Hot","Warm"])])
    meetings=len(df[df["stage"]=="Meeting"]); won=len(df[df["stage"]=="Won"])
    total_pipe=float(df[df["stage"]!="Lost"]["estimated_value"].fillna(0).sum()) if not df.empty else 0
    weighted=weighted_pipeline(df); overdue=overdue_followups(df)
    c1,c2,c3,c4,c5,c6=st.columns(6)
    c1.metric("Leads",total); c2.metric("Hot/Warm",qualified); c3.metric("Meetings",meetings)
    c4.metric("Won",won); c5.metric("Pipeline",f"${total_pipe:,.0f}"); c6.metric("Weighted",f"${weighted:,.0f}")
    if overdue: st.warning(f"{overdue} follow-up(s) are overdue.")
    a,b,c=st.columns(3)
    with a:
        st.subheader("Lead temperature")
        if df["temperature"].notna().any(): st.bar_chart(df["temperature"].value_counts())
        else: st.info("Score leads to populate this chart.")
    with b:
        st.subheader("Pipeline stages"); st.bar_chart(df["stage"].value_counts())
    with c:
        st.subheader("Top opportunities")
        top=df.sort_values("estimated_value",ascending=False).head(6)
        st.dataframe(top[["company","temperature","stage","estimated_value"]],hide_index=True,use_container_width=True)

with tabs[1]:
    st.subheader("Create a new B2B lead")
    with st.form("lead_form"):
        c1,c2,c3=st.columns(3)
        company=c1.text_input("Company"); contact_name=c2.text_input("Contact name"); email=c3.text_input("Email")
        c4,c5,c6=st.columns(3)
        role=c4.text_input("Role / title")
        industry=c5.selectbox("Industry",["SaaS","Software","Technology","Consulting","Healthcare","Finance","E-commerce","Manufacturing","Other"])
        company_size=c6.selectbox("Company size",["1-10","11-50","51-200","201-500","501-1000","1000+"])
        c7,c8,c9=st.columns(3)
        country=c7.text_input("Country")
        source=c8.selectbox("Source",["LinkedIn","Website","Referral","Outbound","Event","Partner","Other"])
        value=c9.number_input("Estimated opportunity value ($)",min_value=0.0,value=10000.0,step=1000.0)
        notes=st.text_area("Business pain / context",height=140,placeholder="Describe the workflow problem, urgency, current process, or commercial context.")
        submitted=st.form_submit_button("✨ Create & AI-score")
    if submitted and company.strip():
        c=get_conn()
        cur=c.execute("""INSERT INTO leads(created_at,company,contact_name,email,role,industry,company_size,country,source,notes,estimated_value,stage,last_activity)
        VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)""",
        (datetime.now().isoformat(timespec="seconds"),company,contact_name,email,role,industry,company_size,country,source,notes,value,"New",datetime.now().isoformat(timespec="seconds")))
        c.commit(); c.close(); lead_id=cur.lastrowid
        log_action("LEAD_CREATED",lead_id,company)
        result,engine=process_lead(lead_id)
        st.success(f"Lead #{lead_id} scored and routed using {engine}."); st.json(result)

    st.divider()
    st.subheader("Bulk lead intake from CSV")
    uploaded=st.file_uploader("Upload lead CSV",type=["csv"],key="bulk_leads")
    st.caption("Expected columns: company, contact_name, email, role, industry, company_size, country, source, estimated_value, notes.")
    if uploaded is not None:
        bulk=pd.read_csv(uploaded)
        st.dataframe(bulk.head(10),hide_index=True,use_container_width=True)
        if st.button("⚡ Import & AI-score CSV leads"):
            required={"company"}
            if not required.issubset(set(bulk.columns)):
                st.error("CSV must contain at least the `company` column.")
            else:
                imported=0
                for _,row in bulk.fillna("").iterrows():
                    if not str(row.get("company","")).strip(): continue
                    c=get_conn()
                    cur=c.execute("""INSERT INTO leads(created_at,company,contact_name,email,role,industry,company_size,country,source,notes,estimated_value,stage,last_activity)
                    VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                    (datetime.now().isoformat(timespec="seconds"),str(row.get("company","")),str(row.get("contact_name","")),
                     str(row.get("email","")),str(row.get("role","")),str(row.get("industry","Other")),str(row.get("company_size","")),
                     str(row.get("country","")),str(row.get("source","Other")),str(row.get("notes","")),
                     float(row.get("estimated_value",0) or 0),"New",datetime.now().isoformat(timespec="seconds")))
                    c.commit(); c.close()
                    log_action("CSV_LEAD_IMPORTED",cur.lastrowid,str(row.get("company","")))
                    process_lead(cur.lastrowid); imported+=1
                st.success(f"Imported and scored {imported} lead(s)."); st.rerun()

with tabs[2]:
    df=load_leads(); st.subheader("AI lead qualification")
    c1,c2,c3=st.columns(3)
    temp_filter=c1.multiselect("Temperature",["Hot","Warm","Cold"],default=["Hot","Warm","Cold"])
    stage_filter=c2.multiselect("Stage",STAGES,default=STAGES); search=c3.text_input("Search company / contact")
    view=df.copy()
    if temp_filter: view=view[view["temperature"].isin(temp_filter)|view["temperature"].isna()]
    if stage_filter: view=view[view["stage"].isin(stage_filter)]
    if search:
        s=search.lower()
        view=view[view["company"].fillna("").str.lower().str.contains(s)|view["contact_name"].fillna("").str.lower().str.contains(s)]
    for _,r in view.iterrows():
        score_label="Unscored" if pd.isna(r["score"]) else f"{int(r['score'])}/100"
        with st.expander(f"#{r['id']} · {r['company']} · {r['temperature'] or 'Unscored'} · {score_label}"):
            st.write(f"**Contact:** {r['contact_name']} — {r['role']}")
            st.write(f"**Industry:** {r['industry']} | **Country:** {r['country']} | **Value:** ${float(r['estimated_value'] or 0):,.0f}")
            st.write(f"**Fit:** {r['fit_summary'] or 'Not scored yet'}")
            st.write(f"**Pain points:** {r['pain_points'] or r['notes']}")
            st.write(f"**Next step:** {r['recommended_next_step'] or 'Score this lead first.'}")
            if st.button("Re-score",key=f"rescore_{r['id']}"):
                process_lead(int(r["id"])); st.rerun()

with tabs[3]:
    df=load_leads(); scored=df[df["score"].notna()]
    st.subheader("AI-generated outreach with human approval")
    if scored.empty: st.info("Score at least one lead first.")
    else:
        lead_id=st.selectbox("Select lead",scored["id"].tolist(),format_func=lambda x:f"#{x} — {scored.loc[scored['id']==x,'company'].iloc[0]}")
        r=scored[scored["id"]==lead_id].iloc[0]
        st.write(f"**Lead score:** {int(r['score'])}/100 ({r['temperature']})")
        subject=st.text_input("Subject",value=r["outreach_subject"] or "",key="out_subject")
        body=st.text_area("Outreach draft",value=r["outreach_message"] or "",height=220,key="out_body")
        st.caption("Human approval is required before a customer-facing action is recorded.")
        c1,c2=st.columns(2)
        if c1.button("✅ Approve & mark contacted",use_container_width=True):
            c=get_conn()
            c.execute("""UPDATE leads SET outreach_subject=?,outreach_message=?,stage='Contacted',last_activity=?,next_follow_up=? WHERE id=?""",
            (subject,body,datetime.now().isoformat(timespec="seconds"),(datetime.now()+timedelta(days=2)).date().isoformat(),int(lead_id)))
            c.commit(); c.close(); log_action("OUTREACH_APPROVED",int(lead_id),subject)
            st.success("Outreach approved and CRM stage updated to Contacted."); st.rerun()
        if c2.button("📝 Keep as draft",use_container_width=True):
            c=get_conn(); c.execute("UPDATE leads SET outreach_subject=?,outreach_message=? WHERE id=?",(subject,body,int(lead_id)))
            c.commit(); c.close(); log_action("OUTREACH_DRAFT_UPDATED",int(lead_id),subject); st.success("Draft saved.")

with tabs[4]:
    df=load_leads(); st.subheader("Prospect reply intelligence")
    if df.empty: st.info("No leads available.")
    else:
        lead_id=st.selectbox("Lead",df["id"].tolist(),key="reply_lead",format_func=lambda x:f"#{x} — {df.loc[df['id']==x,'company'].iloc[0]}")
        reply=st.text_area("Paste prospect reply",height=150,placeholder="This sounds useful. Can you send times for a 20-minute call next week?")
        if st.button("🧠 Analyze reply") and reply.strip():
            result,engine=classify_reply(reply)
            c=get_conn()
            c.execute("""INSERT INTO replies(created_at,lead_id,reply_text,intent,sentiment,summary,recommended_action,stage_after) VALUES(?,?,?,?,?,?,?,?)""",
            (datetime.now().isoformat(timespec="seconds"),int(lead_id),reply,result["intent"],result["sentiment"],result["summary"],result["recommended_action"],result["stage_after"]))
            c.execute("UPDATE leads SET stage=?,last_activity=?,next_follow_up=? WHERE id=?",
            (result["stage_after"],datetime.now().isoformat(timespec="seconds"),(datetime.now()+timedelta(days=1)).date().isoformat(),int(lead_id)))
            c.commit(); c.close(); log_action("REPLY_ANALYZED",int(lead_id),f"engine={engine}; intent={result['intent']}; stage={result['stage_after']}")
            st.success(f"Reply analyzed using {engine}."); st.json(result)
        replies=load_replies()
        if not replies.empty:
            st.divider(); st.subheader("Recent reply events")
            st.dataframe(replies[["created_at","lead_id","intent","sentiment","summary","stage_after"]].head(15),hide_index=True,use_container_width=True)

with tabs[5]:
    df=load_leads(); st.subheader("CRM pipeline control")
    if df.empty: st.info("No leads.")
    else:
        c1,c2=st.columns([1,2])
        lead_id=c1.selectbox("Select opportunity",df["id"].tolist(),key="pipeline_lead",format_func=lambda x:f"#{x} — {df.loc[df['id']==x,'company'].iloc[0]}")
        r=df[df["id"]==lead_id].iloc[0]
        new_stage=c1.selectbox("Stage",STAGES,index=STAGES.index(r["stage"]) if r["stage"] in STAGES else 0)
        followup=c1.date_input("Next follow-up",value=datetime.fromisoformat(r["next_follow_up"]).date() if r["next_follow_up"] else (datetime.now()+timedelta(days=2)).date())
        if c1.button("Update opportunity",use_container_width=True):
            c=get_conn(); c.execute("UPDATE leads SET stage=?,next_follow_up=?,last_activity=? WHERE id=?",
            (new_stage,followup.isoformat(),datetime.now().isoformat(timespec="seconds"),int(lead_id)))
            c.commit(); c.close(); log_action("PIPELINE_UPDATED",int(lead_id),f"stage={new_stage}; followup={followup.isoformat()}")
            st.success("CRM updated."); st.rerun()
        with c2:
            st.write(f"### {r['company']}")
            st.write(f"**Contact:** {r['contact_name']} — {r['role']}")
            st.write(f"**Score:** {int(r['score']) if not pd.isna(r['score']) else 'N/A'} | **Temperature:** {r['temperature'] or 'N/A'}")
            st.write(f"**Opportunity value:** ${float(r['estimated_value'] or 0):,.0f}")
            st.write(f"**AI next step:** {r['recommended_next_step'] or 'Not scored'}")
            if r["stage"]=="Meeting":
                st.success("Meeting-ready opportunity. Prepare discovery questions and scheduling options.")
                st.write("#### Meeting handoff")
                meeting_date=st.date_input("Meeting date",value=(datetime.now()+timedelta(days=3)).date(),key=f"meet_date_{lead_id}")
                meeting_time=st.time_input("Meeting time",value=datetime.now().replace(hour=15,minute=0,second=0,microsecond=0).time(),key=f"meet_time_{lead_id}")
                start=datetime.combine(meeting_date,meeting_time)
                end=start+timedelta(minutes=30)
                def ics_dt(dt): return dt.strftime("%Y%m%dT%H%M%S")
                ics=f"""BEGIN:VCALENDAR
VERSION:2.0
PRODID:-//AI CRM Revenue Engine//EN
BEGIN:VEVENT
UID:lead-{int(lead_id)}-{ics_dt(start)}@revenue-workspace.local
DTSTAMP:{ics_dt(datetime.now())}
DTSTART:{ics_dt(start)}
DTEND:{ics_dt(end)}
SUMMARY:Discovery Call - {r['company']}
DESCRIPTION:AI automation discovery call with {r['contact_name']} ({r['role']}).
END:VEVENT
END:VCALENDAR
"""
                st.download_button("📅 Download meeting invite (.ics)",ics.encode("utf-8"),
                    file_name=f"{str(r['company']).lower().replace(' ','_')}_discovery_call.ics",
                    mime="text/calendar",key=f"ics_{lead_id}")
    st.divider()
    st.subheader("Follow-up queue")
    follow=load_leads()
    follow=follow[(follow["next_follow_up"].notna()) & (~follow["stage"].isin(["Won","Lost"]))]
    if not follow.empty:
        follow=follow.sort_values("next_follow_up")
        st.dataframe(follow[["company","contact_name","temperature","stage","next_follow_up","recommended_next_step"]],
                     hide_index=True,use_container_width=True)
    else:
        st.info("No pending follow-ups.")

    st.divider()
    export=load_leads()
    st.download_button("⬇️ Export CRM pipeline CSV",export.to_csv(index=False).encode("utf-8"),file_name="crm_pipeline_export.csv",mime="text/csv")

with tabs[6]:
    c=get_conn(); audit=pd.read_sql_query("SELECT * FROM audit_log ORDER BY id DESC LIMIT 250",c); c.close()
    st.subheader("Automation audit trail"); st.dataframe(audit,hide_index=True,use_container_width=True)

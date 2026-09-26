"""Streamlit UI (given). Talks to the API only, like any other client.

    make ui            (docker, http://localhost:8501)
    or: API_URL=http://localhost:8000 streamlit run ui/streamlit_app.py
"""

import json
import os
import time

import httpx
import streamlit as st

API = os.environ.get("API_URL", "http://localhost:8000")
HEADERS = {"X-API-Key": os.environ.get("API_KEY", "")}

st.set_page_config(page_title="EU AI Act Copilot", layout="wide")
st.title("EU AI Act Compliance Copilot")
st.caption("Decision support, not legal advice. Always have a qualified person review the results.")

tab_ask, tab_assess = st.tabs(["Ask the AI Act", "Assess an AI system"])

with tab_ask:
    q = st.text_input("Question", placeholder="Do I have to tell users they are talking to a chatbot?")
    if st.button("Ask", type="primary") and q:
        with st.spinner("Searching the regulation..."):
            r = httpx.post(f"{API}/chat", json={"question": q}, headers=HEADERS, timeout=180)
        if r.status_code != 200:
            st.error(r.text)
        else:
            data = r.json()
            st.markdown(data["answer"])
            if not data["citations_valid"]:
                st.warning("Some citations could not be verified against the retrieved text.")
            with st.expander("Sources"):
                for s in data["sources"]:
                    st.write(f"[{s['n']}] {s['citation']} · {s['title']}")
            c1, c2 = st.columns(2)
            if c1.button("👍 Helpful"):
                httpx.post(f"{API}/feedback", json={"target": f"chat:{data['trace_id']}", "rating": 1}, headers=HEADERS)
            if c2.button("👎 Not helpful"):
                httpx.post(f"{API}/feedback", json={"target": f"chat:{data['trace_id']}", "rating": -1}, headers=HEADERS)

with tab_assess:
    desc = st.text_area("Describe the AI system", height=160,
                        placeholder="What it does, who builds it, who uses it, and which decisions about people it affects.")
    if st.button("Run assessment", type="primary") and desc:
        r = httpx.post(f"{API}/assessments", json={"description": desc}, headers=HEADERS, timeout=30)
        if r.status_code != 202:
            st.error(r.text)
        else:
            st.session_state["aid"] = r.json()["id"]
    aid = st.session_state.get("aid")
    if aid:
        box = st.empty()
        for _ in range(600):
            item = httpx.get(f"{API}/assessments/{aid}", headers=HEADERS, timeout=30).json()
            box.info(f"Status: {item['status']}")
            if item["status"] in ("done", "failed", "needs_input"):
                break
            time.sleep(2)
        if item["status"] == "needs_input":
            st.subheader("A few questions first")
            answers = {qq: st.text_input(qq, key=qq) for qq in item["result"]["questions"]}
            if st.button("Continue"):
                r = httpx.post(f"{API}/assessments/{aid}/answers", json={"answers": answers}, headers=HEADERS)
                st.session_state["aid"] = r.json()["id"]
                st.rerun()
        elif item["status"] == "done":
            res = item["result"]
            a = res["assessment"]
            st.metric("Category", a["category"].replace("_", " "), help=f"confidence: {a['confidence']}")
            if a["flags"]:
                st.write("Flags: " + ", ".join(a["flags"]))
            st.markdown(res["report"]["markdown"])
            with st.expander("Gaps"):
                st.table(res["gaps"])
            with st.expander("Raw result"):
                st.code(json.dumps(res, indent=2)[:20000])
        elif item["status"] == "failed":
            st.error(item["error"])

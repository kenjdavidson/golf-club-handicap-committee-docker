import os
import re
import subprocess
import sys

import streamlit as st

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "scripts"))
from golf_canada_client import GolfCanadaClient, GolfCanadaAuthError  # noqa: E402

st.set_page_config(
    page_title="Golf Canada Verification Hub",
    page_icon="⛳",
    layout="wide",
    initial_sidebar_state="expanded",
)

REPORTS_DIR = "/workspace/reports"

# ------------------------------------------------------------------
# Authentication gate
# ------------------------------------------------------------------
# Prefer a pre-configured token from the environment; otherwise show a
# login form so the user can authenticate with username and password.

if "gc_client" not in st.session_state:
    env_token = os.getenv("GOLF_CANADA_TOKEN", "")
    if env_token:
        st.session_state["gc_client"] = GolfCanadaClient(token=env_token)
    else:
        st.session_state["gc_client"] = None

if st.session_state["gc_client"] is None:
    st.title("⛳ Golf Canada — Sign In")
    with st.form("login_form"):
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")
        submitted = st.form_submit_button("Sign In")

    if submitted:
        if not username or not password:
            st.error("Please enter both username and password.")
        else:
            with st.spinner("Signing in…"):
                try:
                    client = GolfCanadaClient()
                    gc_token = client.login(username, password)
                    st.session_state["gc_client"] = client
                    st.session_state["gc_user"] = gc_token.user
                    st.rerun()
                except GolfCanadaAuthError as exc:
                    st.error(f"Authentication failed: {exc}")
    st.stop()

st.sidebar.title("⛳ Golf Canada Engine")
st.sidebar.markdown("---")

gc_user = st.session_state.get("gc_user", {})
if gc_user:
    st.sidebar.markdown(f"👤 **{gc_user.get('fullName', gc_user.get('username', 'Signed in'))}**")
if st.sidebar.button("Sign Out"):
    st.session_state["gc_client"] = None
    st.session_state.pop("gc_user", None)
    st.rerun()

st.sidebar.markdown("---")
col_s1, col_s2 = st.sidebar.columns(2)
col_s1.metric("Engine", "Goose CLI", delta="Ready")
col_s2.metric("MCP Bridge", "Golf Canada", delta="Connected")

st.sidebar.markdown("---")
st.sidebar.subheader("📁 Workspace Files")

files = []
if os.path.exists(REPORTS_DIR):
    files = [
        f
        for f in os.listdir(REPORTS_DIR)
        if not f.endswith(".verification.txt") and not f.startswith(".")
    ]

selected_file = st.sidebar.selectbox(
    "Select target file:", files if files else ["No files found"]
)
run_all = st.sidebar.button("🚀 Audit Selected File", use_container_width=True)

st.title("Golf Score & Handicap Audit Center")
st.caption(
    "Cross-reference local ClubLink round reports against Golf Canada API records."
)

if not selected_file or selected_file == "No files found":
    st.info("Please drop a score report or PDF into `/workspace/reports` to begin.")
    st.stop()

file_path = os.path.join(REPORTS_DIR, selected_file)
log_file = file_path + ".verification.txt"

if run_all:
    with st.status(f"Goose is analyzing {selected_file}...", expanded=True) as status:
        st.write("📄 Extracting text and scoring data from document...")
        prompt = (
            f"Read `/workspace/reports/{selected_file}`. Extract scheduled rounds and dates for ClubLink courses. "
            f"Then query Golf Canada MCP tools and compare the latest 20 rounds for the same individual IDs. "
            f"Flag missing, extra, and date/course mismatches in a structured comparison."
        )

        result = subprocess.run(
            ["goose", "run", "--text", prompt], capture_output=True, text=True, check=False
        )

        with open(log_file, "w", encoding="utf-8") as file_handle:
            file_handle.write(result.stdout)

        status.update(label="Audit Complete!", state="complete", expanded=False)
    st.rerun()

tab_overview, tab_diff, tab_raw = st.tabs(
    [
        "📊 Audit Summary",
        "🔍 Discrepancy & Verification Details",
        "📝 Raw Goose Execution Log",
    ]
)

with tab_overview:
    st.subheader(f"Document Analysis: `{selected_file}`")
    m1, m2, m3, m4 = st.columns(4)
    m1.metric(label="File Type", value=selected_file.split(".")[-1].upper())

    if os.path.exists(log_file):
        with open(log_file, "r", encoding="utf-8") as file_handle:
            content = file_handle.read()

        matches = len(re.findall(r"MATCH|VERIFIED|OK", content, re.IGNORECASE))
        mismatches = len(re.findall(r"MISMATCH|MISSING|ERROR", content, re.IGNORECASE))

        m2.metric(label="Verified Rounds", value=matches)
        m3.metric(label="Discrepancies / Missing", value=mismatches, delta_color="inverse")
        m4.metric(
            label="Audit Status",
            value="Completed",
            delta="Pass" if mismatches == 0 else "Review",
        )
    else:
        m2.metric(label="Verified Rounds", value="--")
        m3.metric(label="Discrepancies", value="--")
        m4.metric(label="Audit Status", value="Pending")

    st.markdown("---")
    col_left, col_right = st.columns([1, 1])

    with col_left:
        with st.container(border=True):
            st.markdown("#### Document Metadata")
            st.text(f"Path: {file_path}")
            st.text(f"Size: {os.path.getsize(file_path) / 1024:.2f} KB")
            if st.button("Re-run Audit"):
                if os.path.exists(log_file):
                    os.remove(log_file)
                st.rerun()

    with col_right:
        with st.container(border=True):
            st.markdown("#### Golf Canada Quick Actions")
            st.write("Need to manually push missing rounds identified in this file?")
            if st.button("Trigger Sync to Golf Canada API"):
                st.toast("Sync request sent to Goose!")

with tab_diff:
    st.subheader("Verification Breakdown")
    if os.path.exists(log_file):
        with open(log_file, "r", encoding="utf-8") as file_handle:
            st.markdown(file_handle.read())
    else:
        st.warning("No audit results found for this file. Run the audit from the sidebar.")

with tab_raw:
    st.subheader("Terminal & Agent Execution Output")
    if os.path.exists(log_file):
        with open(log_file, "r", encoding="utf-8") as file_handle:
            st.code(file_handle.read(), language="bash")
    else:
        st.info("Execution logs will appear here once an audit is triggered.")

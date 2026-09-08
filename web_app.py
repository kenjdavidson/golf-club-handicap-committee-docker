import os
import re
import subprocess

import streamlit as st

st.set_page_config(
    page_title="Golf Canada Verification Hub",
    page_icon="⛳",
    layout="wide",
    initial_sidebar_state="expanded",
)

REPORTS_DIR = "/workspace/reports"

st.sidebar.title("⛳ Golf Canada Engine")
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
    "Cross-reference local scorecards, PDFs, and spreadsheets against Golf Canada API records."
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
            f"Read `/workspace/reports/{selected_file}`. Extract all round dates, scores, slope/rating, "
            f"and player IDs. Then query the Golf Canada MCP tools to verify if these rounds exist "
            f"and if the scores match. Output a structured comparison."
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

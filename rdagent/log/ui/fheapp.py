"""
FHE Challenge Streamlit app entry point.

Usage:
    streamlit run rdagent/log/ui/fheapp.py
or via CLI:
    rdagent fhe_ui
"""

import streamlit as st
from streamlit import session_state as state
from pathlib import Path

st.set_page_config(
    layout="wide",
    page_title="FHE Challenge Traces",
    page_icon="🔐",
    initial_sidebar_state="expanded",
)

trace_page = st.Page("fhe_trace.py", title="Trace", icon="📈")
st.navigation([trace_page]).run()

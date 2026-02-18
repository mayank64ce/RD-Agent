"""
FHE Challenge Trace Viewer - Streamlit page.

Shows per-loop details for FHE challenge RD-Agent runs:
  - Summary table (build, run, accuracy, decision per loop)
  - Accuracy progression chart
  - Latest generated C++ code (even when all attempts failed)
  - Per-loop: algorithm plan, generated code, Docker output, feedback

Usage (via fheapp.py entry point):
    streamlit run rdagent/log/ui/fheapp.py
"""

from __future__ import annotations

import argparse
from collections import defaultdict
from pathlib import Path

import pandas as pd
import streamlit as st
from streamlit import session_state as state

from rdagent.log.storage import FileStorage
from rdagent.log.utils import extract_loopid_func_name, is_valid_session

# Lazy imports of FHE classes so that missing optional deps give a clear error
try:
    from rdagent.core.proposal import ExperimentFeedback
    from rdagent.scenarios.fhe_challenge.experiment import FHEExperiment
    from rdagent.scenarios.fhe_challenge.proposal import FHEHypothesis
except ImportError as _e:
    st.error(f"Failed to import FHE classes: {_e}")
    st.stop()


# ---------------------------------------------------------------------------
# Parse --log_dir passed via  streamlit run fheapp.py -- --log_dir=<path>
# ---------------------------------------------------------------------------

_parser = argparse.ArgumentParser(add_help=False)
_parser.add_argument("--log_dir", type=str, default="")
_args, _ = _parser.parse_known_args()


# ---------------------------------------------------------------------------
# Session state init  (pre-populate from CLI arg on first load)
# ---------------------------------------------------------------------------

if "fhe_data" not in state:
    state.fhe_data = {}
if "fhe_log_path" not in state:
    state.fhe_log_path = None
if "fhe_log_folder" not in state:
    state.fhe_log_folder = Path(_args.log_dir) if _args.log_dir else Path("./log")


# ---------------------------------------------------------------------------
# Data loading
# ---------------------------------------------------------------------------


def _convert_defaultdict(d):
    if isinstance(d, defaultdict):
        return {k: _convert_defaultdict(v) for k, v in d.items()}
    return d


def load_fhe_data(log_path: Path) -> dict:
    """
    Load FHE run data from a FileStorage log path.

    Returns a nested dict::

        {
            "settings": {"FHE_SETTINGS": <dict>},   # global settings
            "scenario": <FHEScenario | None>,         # scenario object
            <loop_id: int>: {
                "direct_exp_gen": {
                    "hypothesis": <FHEHypothesis>,
                    "experiment": <FHEExperiment>,    # before coding
                },
                "coding": {
                    "coded_experiment": <FHEExperiment>,  # with file_dict
                },
                "running": {
                    "run_experiment": <FHEExperiment>,    # with results
                },
                "feedback": {
                    "feedback": <ExperimentFeedback>,
                },
                "record": {
                    "trace": <Trace>,
                },
            },
        }
    """
    data: dict = defaultdict(lambda: defaultdict(dict))
    data["settings"] = {}
    data["scenario"] = None

    for msg in FileStorage(log_path).iter_msg():
        if not msg.tag:
            continue

        li, fn = extract_loopid_func_name(msg.tag)
        if li is not None:
            li = int(li)

        # Global messages – FHE_SETTINGS / scenario can appear without a loop prefix
        if "FHE_SETTINGS" in msg.tag and isinstance(msg.content, dict):
            data["settings"]["FHE_SETTINGS"] = msg.content
            if li is None:
                continue  # skip per-loop processing
        if "scenario" in msg.tag and li is None:
            data["scenario"] = msg.content
            continue

        if li is None:
            continue  # skip unrecognised global messages

        # Per-loop messages: store by last tag segment
        tag_parts = msg.tag.split(".")
        last_tag = tag_parts[-1] if tag_parts else msg.tag
        data[li][fn][last_tag] = msg.content

    return _convert_defaultdict(data)


def get_loop_ids(data: dict) -> list[int]:
    return sorted(k for k in data if isinstance(k, int))


def get_latest_code(data: dict) -> tuple[dict | None, int | None]:
    """
    Return (file_dict, loop_id) of the most recently generated code.

    Searches loop IDs in reverse order; prefers running workspace over
    coding workspace.  Returns (None, None) if no code was generated.
    """
    for li in reversed(get_loop_ids(data)):
        loop = data[li]
        for fn, key in [("running", "run_experiment"), ("coding", "coded_experiment")]:
            exp = loop.get(fn, {}).get(key)
            if isinstance(exp, FHEExperiment) and exp.experiment_workspace:
                fd = exp.experiment_workspace.file_dict
                if fd:
                    return fd, li
    return None, None


def _challenge_info(data: dict) -> tuple[str, str]:
    """Return (challenge_name, challenge_type) from logged data."""
    scen = data.get("scenario")
    if scen is not None and hasattr(scen, "challenge_name"):
        return scen.challenge_name, scen.challenge_type

    settings = data.get("settings", {}).get("FHE_SETTINGS", {})
    name = Path(settings.get("challenge_dir", "")).name or "Unknown"
    ctype = settings.get("challenge_type", "unknown")
    return name, ctype


# ---------------------------------------------------------------------------
# UI helper – C++ eval() extraction and code display
# ---------------------------------------------------------------------------

import re


def _extract_eval_body(cpp_code: str) -> str | None:
    """
    Extract the body of ``void ClassName::eval() { ... }`` from a C++ source
    string using the same brace-matching logic as FHECoder.

    Returns the body text (without the outer braces), or None if not found.
    """
    match = re.search(r"void\s+\w+::eval\s*\(\s*\)\s*\{", cpp_code)
    if not match:
        return None
    start = match.end()  # position just after the opening '{'
    depth = 1
    pos = start
    while pos < len(cpp_code) and depth > 0:
        if cpp_code[pos] == "{":
            depth += 1
        elif cpp_code[pos] == "}":
            depth -= 1
        pos += 1
    body = cpp_code[start : pos - 1].strip()
    return body if body else None


def _show_file_dict(file_dict: dict):
    """
    Display generated workspace files.

    For ``yourSolution.cpp`` only the ``eval()`` body is shown (not the full
    file).  Other files (e.g. ``config.json``) are shown in full.
    """
    if not file_dict:
        st.info("No files in workspace.")
        return

    tabs = st.tabs(list(file_dict.keys()))
    for tab, fname in zip(tabs, file_dict.keys()):
        with tab:
            content = file_dict[fname]
            if fname.endswith((".cpp", ".h", ".hpp")):
                body = _extract_eval_body(content)
                if body is not None:
                    st.caption("Showing `eval()` body only")
                    st.code(body, language="cpp", wrap_lines=True, line_numbers=True)
                else:
                    # Fallback: show full file if eval() pattern not found
                    st.code(content, language="cpp", wrap_lines=True, line_numbers=True)
            else:
                st.code(content, language="json", wrap_lines=True, line_numbers=True)


# ---------------------------------------------------------------------------
# Main windows
# ---------------------------------------------------------------------------


def summary_win(data: dict):
    st.header("Summary", divider="rainbow")

    challenge_name, challenge_type = _challenge_info(data)
    c1, c2 = st.columns(2)
    c1.metric("Challenge", challenge_name)
    c2.metric("Type", challenge_type)

    loop_ids = get_loop_ids(data)
    if not loop_ids:
        st.warning("No loop data found in the selected log.")
        return

    # ----- Summary table -----
    rows = []
    for li in loop_ids:
        loop = data[li]
        row: dict = {"Loop": li}

        hyp = loop.get("direct_exp_gen", {}).get("hypothesis")
        if isinstance(hyp, FHEHypothesis):
            preview = hyp.algorithm[:120].replace("\n", " ")
            row["Algorithm (preview)"] = preview + ("…" if len(hyp.algorithm) > 120 else "")
        else:
            row["Algorithm (preview)"] = "N/A"

        run_exp = loop.get("running", {}).get("run_experiment")
        if isinstance(run_exp, FHEExperiment):
            row["Build"] = "✅" if run_exp.build_success else "❌"
            row["Run"] = "✅" if run_exp.run_success else "❌"
            row["Accuracy"] = round(run_exp.accuracy, 4) if run_exp.accuracy is not None else None
        else:
            row["Build"] = "—"
            row["Run"] = "—"
            row["Accuracy"] = None

        # Check if we at least got generated code
        code_exp = loop.get("coding", {}).get("coded_experiment")
        row["Code generated"] = "✅" if isinstance(code_exp, FHEExperiment) and code_exp.experiment_workspace and code_exp.experiment_workspace.file_dict else "❌"

        fb = loop.get("feedback", {}).get("feedback")
        if isinstance(fb, ExperimentFeedback):
            row["Decision"] = "✅" if fb.decision else "❌"
        else:
            row["Decision"] = "—"

        rows.append(row)

    df = pd.DataFrame(rows).set_index("Loop")
    st.dataframe(df, use_container_width=True)

    # ----- Accuracy chart -----
    acc_data = {f"L{li}": data[li].get("running", {}).get("run_experiment")
                for li in loop_ids}
    acc_values = {k: v.accuracy for k, v in acc_data.items()
                  if isinstance(v, FHEExperiment) and v.accuracy is not None}
    if acc_values:
        st.subheader("Accuracy by Loop")
        st.line_chart(pd.DataFrame({"Accuracy": acc_values}))
    else:
        st.info("No accuracy scores recorded yet.")

    # ----- Latest generated code -----
    st.subheader("Latest Generated Code", divider="gray")
    file_dict, from_loop = get_latest_code(data)
    if file_dict:
        st.caption(f"From Loop {from_loop}")
        _show_file_dict(file_dict)
    else:
        st.info("No generated code found in any loop.")


def loop_detail_win(loop_id: int, data: dict):
    """Detailed view for a single loop."""
    loop = data.get(loop_id, {})

    tab_alg, tab_code, tab_docker, tab_fb = st.tabs(
        ["Algorithm Plan", "Generated Code", "Docker Output", "Feedback"]
    )

    # --- Algorithm Plan ---
    with tab_alg:
        hyp = loop.get("direct_exp_gen", {}).get("hypothesis")
        if isinstance(hyp, FHEHypothesis):
            st.code(hyp.algorithm, language="markdown", wrap_lines=True, line_numbers=True)
        else:
            st.info("No hypothesis logged for this loop.")

    # --- Generated Code ---
    with tab_code:
        file_dict = None
        source_label = ""
        for fn, key, label in [
            ("running", "run_experiment", "running experiment"),
            ("coding", "coded_experiment", "coding experiment"),
        ]:
            exp = loop.get(fn, {}).get(key)
            if isinstance(exp, FHEExperiment) and exp.experiment_workspace:
                fd = exp.experiment_workspace.file_dict
                if fd:
                    file_dict = fd
                    source_label = label
                    break

        if file_dict:
            st.caption(f"Code from {source_label}")
            _show_file_dict(file_dict)
        else:
            st.info("No generated code found for this loop.")

    # --- Docker Output ---
    with tab_docker:
        run_exp = loop.get("running", {}).get("run_experiment")
        if isinstance(run_exp, FHEExperiment):
            mc1, mc2, mc3 = st.columns(3)
            mc1.metric("Build", "✅" if run_exp.build_success else "❌")
            mc2.metric("Run", "✅" if run_exp.run_success else "❌")
            mc3.metric(
                "Accuracy",
                f"{run_exp.accuracy:.4f}" if run_exp.accuracy is not None else "N/A",
            )

            if run_exp.error_message:
                with st.expander("Error Message", expanded=True):
                    st.code(run_exp.error_message, language="log", wrap_lines=True)

            if run_exp.docker_output:
                with st.expander("Docker Output", expanded=not run_exp.error_message):
                    st.code(run_exp.docker_output, language="log", wrap_lines=True)
        else:
            st.info("No Docker run results found for this loop.")

    # --- Feedback ---
    with tab_fb:
        fb = loop.get("feedback", {}).get("feedback")
        if isinstance(fb, ExperimentFeedback):
            icon = "✅" if fb.decision else "❌"
            st.subheader(f"Decision: {icon}")
            try:
                st.code(str(fb).replace("\n", "\n\n"), wrap_lines=True)
            except Exception:
                st.write(fb.__dict__)
            if getattr(fb, "exception", None) is not None:
                st.markdown(f"**:red[Exception]**: {fb.exception}")
        else:
            st.info("No feedback logged for this loop.")


# ---------------------------------------------------------------------------
# Sidebar
# ---------------------------------------------------------------------------


def get_sessions(log_folder: Path) -> list[str]:
    if not log_folder.exists():
        return []
    return sorted(
        f.name for f in log_folder.iterdir() if is_valid_session(f)
    )


with st.sidebar:
    st.subheader("Log Folder")
    folder_input = st.text_input("Path", value=str(state.fhe_log_folder))
    if folder_input.strip():
        state.fhe_log_folder = Path(folder_input.strip())

    sessions = get_sessions(state.fhe_log_folder)
    if not sessions:
        if state.fhe_log_folder.exists():
            st.warning("No valid sessions found in this folder.")
        else:
            st.warning(f"Folder not found: {state.fhe_log_folder}")
        st.stop()

    state.fhe_log_path = st.selectbox(
        f"Session ({len(sessions)} found)",
        sessions,
        index=0,
    )

    if st.button("Load / Refresh"):
        full_path = state.fhe_log_folder / state.fhe_log_path
        with st.spinner("Loading log data…"):
            state.fhe_data = load_fhe_data(full_path)
        st.rerun()

    st.markdown("---")
    st.markdown(
        """
**Sections**
- [Summary](#summary)
- [Loop Detail](#loop-detail)
"""
    )


# ---------------------------------------------------------------------------
# Main page
# ---------------------------------------------------------------------------

data = state.fhe_data

if not data:
    st.info("Select a log session in the sidebar and click **Load / Refresh**.")
    st.stop()

challenge_name, challenge_type = _challenge_info(data)
st.title(f"FHE Trace: {challenge_name} ({challenge_type})")

summary_win(data)

# Loop detail selector
loop_ids = get_loop_ids(data)
if not loop_ids:
    st.stop()

st.header("Loop Detail", divider="blue", anchor="loop-detail")

if len(loop_ids) > 1:
    loop_id = st.slider("Select Loop", min_value=min(loop_ids), max_value=max(loop_ids), value=max(loop_ids))
else:
    loop_id = loop_ids[0]
    st.markdown(f"**Loop {loop_id}**")

loop_detail_win(loop_id, data)

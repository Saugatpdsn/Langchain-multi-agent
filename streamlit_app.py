"""Streamlit frontend for the LangGraph multi-agent research assistant.

Runs the Supervisor -> Researcher -> Writer -> Validate -> Reviewer graph
(agents/graph.py) directly in-process -- there is no separate backend
server. Uses Google Gemini (free tier) as the LLM and DuckDuckGo (no API
key) for web search.

The Gemini API key is read from the environment / .env / Streamlit secrets
first, so nothing sensitive is displayed by default. A manual override is
available but tucked away behind an expander, never shown as a first-class
field.

While the graph runs, a live pipeline tracker + rotating status line +
activity feed update in real time (via st.empty() placeholders refreshed
inside the streaming loop) so the user can see which agent is working and
what it's doing, instead of staring at a blank spinner.
"""

from __future__ import annotations

import html as html_lib
import os
import uuid
from datetime import datetime

import streamlit as st
from dotenv import load_dotenv
from langchain_core.messages import HumanMessage
from langgraph.errors import GraphRecursionError
from langgraph.types import Command

from agents.config import DEFAULT_MODEL, FREE_MODELS
from agents.graph import build_graph

load_dotenv()

st.set_page_config(
    page_title="Fieldnote — Research Assistant",
    page_icon="🖋️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# --------------------------------------------------------------------------
# Agent metadata + flavor text (drives the pipeline tracker & status line)
# --------------------------------------------------------------------------

NODE_META = {
    "supervisor": {"icon": "◆", "label": "Supervisor", "color": "#6B5B95"},
    "researcher": {"icon": "●", "label": "Researcher", "color": "#3B6EA5"},
    "writer": {"icon": "✎", "label": "Writer", "color": "#2E7D5B"},
    "validate": {"icon": "▲", "label": "Grounding check", "color": "#B5842A"},
    "reviewer": {"icon": "■", "label": "Reviewer", "color": "#B5533C"},
    "human_review": {"icon": "◐", "label": "You", "color": "#A33E75"},
}

# The canonical order used to draw the pipeline. The real graph can loop
# (researcher <-> supervisor, or back to writer after a revision) -- this is
# a vibe indicator of where things stand, not a strict progress bar.
STAGE_ORDER = ["supervisor", "researcher", "writer", "validate", "reviewer"]

STATUS_MESSAGES = {
    "supervisor": [
        "◆ Supervisor is deciding who goes next…",
        "◆ Supervisor is checking in on the team's progress…",
    ],
    "researcher": [
        "● Researcher is out searching the web…",
        "● Researcher is chasing down another lead…",
        "● Researcher is cross-checking sources…",
    ],
    "writer": [
        "✎ Writer is drafting the report…",
        "✎ Writer is turning notes into prose…",
        "✎ Writer is reworking the draft…",
    ],
    "validate": [
        "▲ Running a grounding check — every claim needs a source…",
    ],
    "reviewer": [
        "■ Reviewer is reading it over with a red pen…",
        "■ Reviewer is weighing accept vs. revise…",
    ],
    "human_review": [
        "◐ Waiting on your call…",
    ],
}

EXAMPLE_QUERIES = [
    "What are the latest developments in AI agents?",
    "How does retrieval-augmented generation reduce hallucination?",
    "What is the current state of solid-state battery research?",
]

# --------------------------------------------------------------------------
# Visual identity — "research desk / field notebook"
# --------------------------------------------------------------------------

st.markdown(
    """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Lora:ital,wght@0,500;0,600;1,500&family=Inter:wght@400;500;600&family=JetBrains+Mono:wght@400;500&display=swap');

    html, body, [class*="css"] { font-family: 'Inter', sans-serif; }
    .stApp { background: #F3F1EB; }

    h1, h2, h3 { font-family: 'Lora', serif !important; letter-spacing: -0.01em; }

    section[data-testid="stSidebar"] {
        background: #1E2430;
        border-right: 1px solid #2C3342;
    }
    section[data-testid="stSidebar"] * { color: #D9DCE3 !important; }
    section[data-testid="stSidebar"] h1 {
        font-family: 'Lora', serif !important;
        color: #F3F1EB !important;
        font-size: 1.35rem;
    }
    section[data-testid="stSidebar"] hr { border-color: #2C3342; }

    .fn-banner {
        border-left: 3px solid #B5533C;
        padding: 0.15rem 0 0.15rem 0.9rem;
        margin-bottom: 1.6rem;
    }
    .fn-banner h1 {
        margin: 0; font-size: 2.1rem; color: #1C2230;
    }
    .fn-banner p {
        margin: 0.25rem 0 0 0; color: #5B5F6B; font-size: 0.98rem;
    }

    .fn-pill {
        display: inline-flex; align-items: center; gap: 0.4rem;
        padding: 0.3rem 0.7rem; border-radius: 3px;
        font-size: 0.82rem; font-weight: 500;
        border: 1px solid;
    }
    .fn-pill-ok { color: #2E7D5B; border-color: #2E7D5B33; background: #2E7D5B14; }
    .fn-pill-warn { color: #B5533C; border-color: #B5533C33; background: #B5533C14; }

    /* ---- Live pipeline tracker ------------------------------------- */
    .fn-pipeline {
        display: flex; align-items: center;
        margin: 0.9rem 0 0.3rem 0; overflow-x: auto; padding-bottom: 0.35rem;
    }
    .fn-step {
        display: flex; flex-direction: column; align-items: center; gap: 0.35rem;
        min-width: 68px;
    }
    .fn-step-dot {
        width: 34px; height: 34px; border-radius: 50%;
        display: flex; align-items: center; justify-content: center;
        font-size: 0.95rem; border: 2px solid var(--step-color);
        color: var(--step-color); background: #FFFFFF;
        transition: all 0.3s ease;
    }
    .fn-step-done .fn-step-dot { background: var(--step-color); color: #fff; }
    .fn-step-active .fn-step-dot {
        background: var(--step-color); color: #fff;
        box-shadow: 0 0 0 4px rgba(181,83,60,0.18);
        animation: fn-pulse 1.4s ease-in-out infinite;
    }
    .fn-step-pending .fn-step-dot { opacity: 0.4; }
    .fn-step-label { font-size: 0.72rem; color: #5B5F6B; font-weight: 500; white-space: nowrap; }
    .fn-step-active .fn-step-label { color: #1C2230; font-weight: 600; }
    .fn-step-pending .fn-step-label { opacity: 0.5; }
    .fn-connector { flex: 1; height: 2px; background: #DCD8CC; min-width: 14px; margin-bottom: 1.15rem; }
    .fn-connector-done { flex: 1; height: 2px; background: #B5533C; min-width: 14px; margin-bottom: 1.15rem; }

    @keyframes fn-pulse {
        0%   { box-shadow: 0 0 0 0 rgba(181,83,60,0.35); }
        70%  { box-shadow: 0 0 0 9px rgba(181,83,60,0); }
        100% { box-shadow: 0 0 0 0 rgba(181,83,60,0); }
    }

    /* ---- Live status line ------------------------------------------ */
    .fn-status {
        display: flex; align-items: center; gap: 0.55rem;
        font-size: 0.98rem; font-weight: 500; color: #1C2230;
        padding: 0.35rem 0 0.75rem 0;
    }
    .fn-live-dot {
        width: 9px; height: 9px; border-radius: 50%; background: #B5533C;
        animation: fn-blink 1.1s ease-in-out infinite; flex-shrink: 0;
    }
    @keyframes fn-blink { 0%, 100% { opacity: 1; } 50% { opacity: 0.25; } }
    .fn-status-done { color: #2E7D5B; }
    .fn-status-wait { color: #A33E75; }
    .fn-status-warn { color: #B5533C; }
    .fn-substat { color: #8A8E99; font-weight: 400; font-size: 0.85rem; }

    /* ---- Activity feed ---------------------------------------------- */
    .fn-trace-row {
        border-left: 2px solid var(--node-color, #999);
        padding: 0.35rem 0 0.35rem 0.7rem;
        margin-bottom: 0.55rem;
    }
    .fn-trace-label {
        font-family: 'JetBrains Mono', monospace;
        font-size: 0.78rem;
        color: var(--node-color, #333);
        font-weight: 500;
    }
    .fn-trace-text {
        font-size: 0.88rem; color: #3A3E48; margin-top: 0.15rem;
        white-space: pre-wrap;
    }

    .stButton>button[kind="primary"], .stFormSubmitButton>button[kind="primary"] {
        background: #B5533C; border-color: #B5533C;
    }
    .stButton>button[kind="primary"]:hover, .stFormSubmitButton>button[kind="primary"]:hover {
        background: #9c4632; border-color: #9c4632;
    }

    div[data-testid="stChatMessage"], .fn-example-btn button {
        font-family: 'Inter', sans-serif;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# --------------------------------------------------------------------------
# Session state
# --------------------------------------------------------------------------

_DEFAULTS = {
    "phase": "idle",  # idle | running | awaiting_human | done | error
    "log": [],  # list[(node_name, text)]
    "draft": "",
    "sources": [],
    "validation_error": "",
    "error_msg": "",
    "pending_interrupt": None,
    "graph": None,
    "thread_id": None,
    "hitl": False,
    "query": "",
    "query_box": "",
    "history": [],
    "manual_api_key": "",
    "revision_count": 0,
}
for key, value in _DEFAULTS.items():
    if key not in st.session_state:
        st.session_state[key] = value


def _resolve_api_key() -> tuple[str, str]:
    """Look for a Gemini key without ever printing it: secrets > env > manual."""
    try:
        if "GOOGLE_API_KEY" in st.secrets and st.secrets["GOOGLE_API_KEY"]:
            return st.secrets["GOOGLE_API_KEY"], "Streamlit secrets"
    except Exception:
        pass
    env_key = os.getenv("GOOGLE_API_KEY", "")
    if env_key:
        return env_key, ".env / environment"
    if st.session_state.manual_api_key:
        return st.session_state.manual_api_key, "entered this session"
    return "", ""


def _reset_run_state() -> None:
    st.session_state.log = []
    st.session_state.draft = ""
    st.session_state.sources = []
    st.session_state.validation_error = ""
    st.session_state.error_msg = ""
    st.session_state.pending_interrupt = None
    st.session_state.revision_count = 0


# --------------------------------------------------------------------------
# Live rendering: pipeline tracker + status line + activity feed
# --------------------------------------------------------------------------


def _render_progress(pipeline_ph, status_ph, trace_ph, hitl: bool) -> None:
    """Repaint the three live placeholders from current session state.

    Called after every graph step (and once on a plain rerun) so the UI
    always reflects the freshest state, whether or not a run is in flight.
    """
    log = st.session_state.log
    phase = st.session_state.phase
    stage_order = STAGE_ORDER + (["human_review"] if hitl else [])

    reached: set[str] = set()
    counts: dict[str, int] = {}
    current_node = None
    for node_name, _ in log:
        if node_name in stage_order:
            reached.add(node_name)
        counts[node_name] = counts.get(node_name, 0) + 1
        current_node = node_name

    if phase == "awaiting_human":
        current_node = "human_review"
        reached.add("reviewer")
    elif phase == "done":
        current_node = stage_order[-1]
        reached = set(stage_order)

    # ---- pipeline tracker -------------------------------------------
    parts: list[str] = []
    for i, node in enumerate(stage_order):
        meta = NODE_META[node]
        if phase == "done" or (node in reached and node != current_node):
            state_cls, mark = "fn-step-done", "✓"
        elif node == current_node and phase in ("running", "awaiting_human"):
            state_cls, mark = "fn-step-active", meta["icon"]
        else:
            state_cls, mark = "fn-step-pending", meta["icon"]
        parts.append(
            f'<div class="fn-step {state_cls}" style="--step-color:{meta["color"]}">'
            f'<div class="fn-step-dot">{mark}</div>'
            f'<div class="fn-step-label">{meta["label"]}</div></div>'
        )
        if i < len(stage_order) - 1:
            connector_cls = "fn-connector-done" if node in reached else "fn-connector"
            parts.append(f'<div class="{connector_cls}"></div>')
    pipeline_ph.markdown(f'<div class="fn-pipeline">{"".join(parts)}</div>', unsafe_allow_html=True)

    # ---- status line ---------------------------------------------
    if phase == "running" and current_node:
        msgs = STATUS_MESSAGES.get(current_node, ["Working…"])
        n = counts.get(current_node, 1)
        msg = msgs[(n - 1) % len(msgs)]
        extra = ""
        if current_node == "reviewer" and st.session_state.revision_count:
            extra = f' <span class="fn-substat">· revision {st.session_state.revision_count}</span>'
        status_ph.markdown(
            f'<div class="fn-status"><span class="fn-live-dot"></span>{msg}{extra}</div>',
            unsafe_allow_html=True,
        )
    elif phase == "awaiting_human":
        status_ph.markdown(
            '<div class="fn-status fn-status-wait">⏸ Waiting on your review — see below</div>',
            unsafe_allow_html=True,
        )
    elif phase == "done":
        status_ph.markdown(
            '<div class="fn-status fn-status-done">✓ Report ready</div>', unsafe_allow_html=True
        )
    elif phase == "error":
        status_ph.markdown(
            '<div class="fn-status fn-status-warn">✕ Something went wrong — see below</div>',
            unsafe_allow_html=True,
        )
    else:
        status_ph.empty()

    # ---- activity feed (newest first) --------------------------------
    if log:
        rows = []
        for node_name, content in reversed(log[-40:]):
            meta = NODE_META.get(node_name, {"icon": "•", "label": node_name, "color": "#999"})
            safe = html_lib.escape(content)
            preview = safe if len(safe) <= 500 else safe[:500] + "…"
            rows.append(
                f'<div class="fn-trace-row" style="--node-color:{meta["color"]}">'
                f'<div class="fn-trace-label">{meta["icon"]} {meta["label"]}</div>'
                f'<div class="fn-trace-text">{preview}</div></div>'
            )
        trace_ph.markdown("".join(rows), unsafe_allow_html=True)
    else:
        trace_ph.empty()


def _log_step(node_name: str, node_output: dict) -> None:
    if node_output.get("draft"):
        st.session_state.draft = node_output["draft"]
    if node_output.get("sources"):
        st.session_state.sources = node_output["sources"]
    if "validation_error" in node_output:
        st.session_state.validation_error = node_output["validation_error"]
    if "revision_count" in node_output:
        st.session_state.revision_count = node_output["revision_count"]

    for msg in node_output.get("messages", []):
        content = msg.content if hasattr(msg, "content") else str(msg)
        st.session_state.log.append((node_name, content))


def _advance(stream_input, placeholders=None, hitl: bool = False) -> None:
    """Drive the graph forward until it finishes, errors, or interrupts.

    If ``placeholders`` (pipeline_ph, status_ph, trace_ph) is given, the
    live UI is repainted after every single graph step -- this is what
    makes the tracker/status line/feed update in real time as the agents
    work, rather than jumping straight to a finished state.
    """
    graph = st.session_state.graph
    config = (
        {"configurable": {"thread_id": st.session_state.thread_id}, "recursion_limit": 100}
        if st.session_state.hitl
        else None
    )
    try:
        for step in graph.stream(stream_input, config, stream_mode="updates"):
            if "__interrupt__" in step:
                st.session_state.pending_interrupt = step["__interrupt__"][0].value
                st.session_state.phase = "awaiting_human"
                if placeholders:
                    _render_progress(*placeholders, hitl)
                return
            for node_name, node_output in step.items():
                _log_step(node_name, node_output)
                if placeholders:
                    _render_progress(*placeholders, hitl)
        _finish_run()
    except GraphRecursionError:
        st.session_state.phase = "error"
        st.session_state.error_msg = (
            "The agents did not converge within the step limit -- no answer produced."
        )
    except Exception as exc:  # noqa: BLE001 - surface any provider/tool error to the UI
        st.session_state.phase = "error"
        st.session_state.error_msg = str(exc)
    if placeholders:
        _render_progress(*placeholders, hitl)


def _finish_run() -> None:
    if st.session_state.validation_error:
        st.session_state.phase = "error"
        st.session_state.error_msg = (
            f"Insufficient grounding — no answer produced. "
            f"Reason: {st.session_state.validation_error}"
        )
        return
    st.session_state.phase = "done"
    st.session_state.history.append(
        {
            "query": st.session_state.query,
            "draft": st.session_state.draft,
            "sources": st.session_state.sources,
            "time": datetime.now().strftime("%H:%M:%S"),
        }
    )


def start_run(query: str, api_key: str, model: str, hitl: bool, placeholders=None) -> None:
    os.environ["GOOGLE_API_KEY"] = api_key
    os.environ["LLM_MODEL"] = model

    _reset_run_state()
    st.session_state.query = query
    st.session_state.hitl = hitl
    st.session_state.thread_id = str(uuid.uuid4())
    st.session_state.graph = build_graph(human_in_the_loop=hitl)
    st.session_state.phase = "running"

    _advance({"messages": [HumanMessage(content=query)]}, placeholders, hitl)


def resume_run(action: str, feedback: str = "", placeholders=None) -> None:
    st.session_state.phase = "running"
    st.session_state.pending_interrupt = None
    _advance(Command(resume={"action": action, "feedback": feedback}), placeholders, st.session_state.hitl)


api_key, key_source = _resolve_api_key()

# --------------------------------------------------------------------------
# Sidebar
# --------------------------------------------------------------------------

with st.sidebar:
    st.markdown("# 🖋️ Fieldnote")
    st.caption("A multi-agent research desk, built on LangGraph + Gemini.")
    st.divider()

    st.markdown("**Gemini access**")
    if api_key:
        st.markdown(
            f'<span class="fn-pill fn-pill-ok">● connected — {key_source}</span>',
            unsafe_allow_html=True,
        )
    else:
        st.markdown(
            '<span class="fn-pill fn-pill-warn">● no key found</span>',
            unsafe_allow_html=True,
        )
        st.caption(
            "Set `GOOGLE_API_KEY` in a `.env` file or `.streamlit/secrets.toml` "
            "so it never has to be typed here."
        )
        with st.expander("Enter a key just for this session"):
            manual = st.text_input(
                "GOOGLE_API_KEY",
                type="password",
                label_visibility="collapsed",
                placeholder="paste key, then press Enter",
            )
            st.caption("Kept only in this browser session — never written to disk.")
            if manual and manual != st.session_state.manual_api_key:
                st.session_state.manual_api_key = manual
                st.rerun()
        api_key, key_source = _resolve_api_key()

    st.caption("Get a free key → [aistudio.google.com](https://aistudio.google.com/app/apikey)")

    st.divider()
    model = st.selectbox("Model", FREE_MODELS, index=FREE_MODELS.index(DEFAULT_MODEL))
    hitl = st.toggle(
        "Human-in-the-loop review",
        value=False,
        help="Pause before finishing so you can approve or request a revision.",
    )

    if st.session_state.history:
        st.divider()
        st.markdown("**Past runs**")
        for item in reversed(st.session_state.history[-8:]):
            with st.expander(f"{item['time']} · {item['query'][:32]}"):
                st.caption(item["query"])

    st.divider()
    st.caption("Search: DuckDuckGo — no key required.")
    st.caption("LLM: Google Gemini free tier.")

# --------------------------------------------------------------------------
# Header
# --------------------------------------------------------------------------

st.markdown(
    """
    <div class="fn-banner">
      <h1>Fieldnote</h1>
      <p>Ask a question. A researcher, writer, and editor work it through together — and refuse to
      publish anything they can't point back to a source.</p>
    </div>
    """,
    unsafe_allow_html=True,
)

with st.form("query_form", clear_on_submit=False):
    query = st.text_area(
        "Research question",
        value=st.session_state.query_box,
        placeholder="e.g. What are the latest developments in AI agents?",
        height=90,
        label_visibility="collapsed",
    )
    col_a, col_b = st.columns([5, 1])
    with col_a:
        chip_cols = st.columns(len(EXAMPLE_QUERIES))
        for chip_col, example in zip(chip_cols, EXAMPLE_QUERIES):
            with chip_col:
                st.markdown('<div class="fn-example-btn">', unsafe_allow_html=True)
                if st.form_submit_button(example, use_container_width=True):
                    st.session_state.query_box = example
                    st.rerun()
                st.markdown("</div>", unsafe_allow_html=True)
    with col_b:
        submitted = st.form_submit_button("Run ▶", type="primary", use_container_width=True)

if submitted:
    st.session_state.query_box = query

# --------------------------------------------------------------------------
# Live progress: pipeline tracker + status line + activity feed
# --------------------------------------------------------------------------
# These placeholders are created once, here, then reused: start_run /
# resume_run below repaint them live on every single graph step, which is
# what lets the user watch each agent hand off to the next in real time.

show_progress = submitted or st.session_state.phase != "idle"
if show_progress:
    pipeline_ph = st.empty()
    status_ph = st.empty()
    with st.expander(
        "Full agent trace", expanded=st.session_state.phase in {"running", "awaiting_human"}
    ):
        trace_ph = st.empty()
    live_placeholders = (pipeline_ph, status_ph, trace_ph)
    if not submitted:
        _render_progress(*live_placeholders, st.session_state.hitl)
else:
    live_placeholders = None

if submitted:
    if not api_key:
        st.error("No Gemini API key found. Add one in the sidebar before running.")
        _render_progress(*live_placeholders, hitl)
    elif not query.strip():
        st.error("Enter a research question first.")
        _render_progress(*live_placeholders, hitl)
    else:
        # Seed the tracker immediately so there's no blank gap while the
        # first LLM call (Supervisor) is in flight.
        status_ph.markdown(
            '<div class="fn-status"><span class="fn-live-dot"></span>'
            "◆ Kicking off the crew…</div>",
            unsafe_allow_html=True,
        )
        start_run(query.strip(), api_key.strip(), model, hitl, live_placeholders)

# --------------------------------------------------------------------------
# Human-in-the-loop prompt
# --------------------------------------------------------------------------

if st.session_state.phase == "awaiting_human" and st.session_state.pending_interrupt:
    payload = st.session_state.pending_interrupt
    st.subheader("Your review needed")
    verdict = payload.get("reviewer_verdict", "?")
    pill_class = "fn-pill-ok" if verdict == "ACCEPT" else "fn-pill-warn"
    st.markdown(
        f'<span class="fn-pill {pill_class}">AI reviewer: {verdict}</span> '
        f'&nbsp; revision {payload.get("revision_count")}/{payload.get("max_revisions")}',
        unsafe_allow_html=True,
    )
    st.write("")
    if payload.get("reviewer_feedback"):
        with st.expander("Reviewer notes", expanded=True):
            st.write(payload["reviewer_feedback"])
    with st.expander("Current draft"):
        st.markdown(payload.get("draft") or "_(empty)_")

    col1, col2 = st.columns([1, 2])
    with col1:
        if st.button("✓ Approve", type="primary", use_container_width=True):
            resume_run("approve", placeholders=live_placeholders)
            st.rerun()
    with col2:
        revise_note = st.text_input(
            "Revision instructions (optional)", key="revise_note", label_visibility="collapsed",
            placeholder="Revision instructions (optional)",
        )
        if st.button("↺ Request revision", use_container_width=True):
            resume_run("revise", revise_note, placeholders=live_placeholders)
            st.rerun()

# --------------------------------------------------------------------------
# Result
# --------------------------------------------------------------------------

if st.session_state.phase == "error":
    st.error(st.session_state.error_msg)

if st.session_state.phase == "done" and st.session_state.draft:
    tab_report, tab_sources = st.tabs(["Report", f"Sources ({len(st.session_state.sources)})"])

    with tab_report:
        with st.container(border=True):
            st.markdown(st.session_state.draft)

    with tab_sources:
        if st.session_state.sources:
            for i, s in enumerate(st.session_state.sources, 1):
                st.markdown(f"**[{i}] {s.get('title', 'Untitled')}**")
                st.caption(s.get("url", ""))
        else:
            st.caption("No sources were recorded for this run.")

    report_md = st.session_state.draft
    if st.session_state.sources:
        report_md += "\n\n## Sources\n" + "\n".join(
            f"[{i}] {s.get('title', 'Untitled')} — {s.get('url', '')}"
            for i, s in enumerate(st.session_state.sources, 1)
        )
    st.download_button(
        "Download report (.md)",
        data=report_md,
        file_name="research_report.md",
        mime="text/markdown",
    )

# 🧠 Multi-Agent Research Assistant — Streamlit

A **multi-agent AI system** that takes a research question, searches the web, writes a cited report, and reviews itself — with a Streamlit UI. Built with **LangGraph**, running on **Google Gemini's free tier**, using **DuckDuckGo** for search (no search API key needed).

This is a frontend-only project: `streamlit_app.py` calls the LangGraph agent graph directly in-process. There is no separate backend server to run or deploy.

---

## ✨ Features

* Streamlit UI: enter a question, watch the agents work, read the report
* Multi-agent workflow: Supervisor → Researcher → Writer → Validate → Reviewer
* Live agent trace as the graph streams
* Deterministic grounding gate — refuses to show a report with unsupported or fabricated citations
* Optional human-in-the-loop: approve or request a revision before the run finishes
* Sidebar model picker for Gemini's free-tier models
* Download the final report as Markdown

---

## 🏗️ How it works

```text
User Question
      ↓
  Supervisor
      ↓
  Researcher → Web Search (DuckDuckGo)
      ↓
    Writer
      ↓
   Validate (deterministic grounding check)
      ↓
   Reviewer
   ↙     ↘
Revise   Accept
  ↓        ↓
Writer   Final Report
```

If human-in-the-loop is enabled, the graph pauses after the Reviewer so you can approve the draft or send it back for another revision — right from the UI.

---

## 🚀 Getting started (local, no Docker)

### 1. Install dependencies

```bash
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Get a free Gemini API key

Create one at <https://aistudio.google.com/app/apikey> (free tier).

### 3. Provide your key (without typing it into the UI)

The app never shows your key as a plain field by default — it looks for it in this order:

1. `.streamlit/secrets.toml` — copy `.streamlit/secrets.toml.example` and fill it in
2. `.env` — copy `.env.example` and fill it in
3. A "just for this session" field tucked behind a sidebar expander, only shown if neither of the above is set

### 4. Run the app

```bash
streamlit run streamlit_app.py
```

The sidebar shows a green "connected" pill once a key is found, and never prints the key itself.

---

## 📁 Project structure

```text
.
├── streamlit_app.py       # Frontend — the only entry point
├── agents/
│   ├── config.py          # Gemini LLM setup (free-tier models)
│   ├── graph.py           # LangGraph state graph (supervisor/researcher/writer/reviewer)
│   └── tools.py           # DuckDuckGo web search + summarise tool
├── requirements.txt
├── .env.example
├── .streamlit/secrets.toml.example
└── README.md
```

**What was removed from the original project**, per request:
* `main.py` (the CLI entry point) — the Streamlit app is now the only frontend
* `Dockerfile` — you're building/deploying your own image
* Groq / OpenAI / Anthropic provider code in `agents/config.py` — Gemini only
* `pyproject.toml` / `uv.lock` — replaced with a plain `requirements.txt`
* `tests/` — they exercised the CLI (`main.py`) and multi-provider config that no longer exist

The core agent logic (`agents/graph.py`, `agents/tools.py`) is unchanged from the original.

---

## 🐳 Deploying with your own Docker image

No `Dockerfile` is included since you're handling that yourself. A minimal one for this app would look like:

```dockerfile
FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
EXPOSE 8501
ENTRYPOINT ["streamlit", "run", "streamlit_app.py", "--server.port=8501", "--server.address=0.0.0.0"]
```

Pass `GOOGLE_API_KEY` in at runtime (`-e GOOGLE_API_KEY=...` or `--env-file .env`) so it's picked up automatically — the sidebar's manual-entry expander is only a fallback for when no key is configured.

---

## 🛠️ Tech stack

| Technology | Purpose |
| --- | --- |
| Streamlit | Frontend UI |
| LangGraph | Agent workflow / state machine |
| LangChain | LLM + tool integration |
| Google Gemini (free tier) | LLM |
| DuckDuckGo | Web search (no API key) |
| Pydantic | State validation |

---

## 👤 Author

**Saugat Pudasaini**
IT Undergraduate | AI/ML & Generative AI Enthusiast

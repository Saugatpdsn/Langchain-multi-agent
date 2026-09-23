
# 🧠 Multi-Agent Research Assistant

An AI-powered research assistant that transforms research questions into structured, evidence-based reports. Built with **LangGraph, Google Gemini, and Streamlit**, it uses a multi-agent workflow to research topics, generate cited reports, and review its own output.

The application integrates DuckDuckGo for web search and Gemini's free-tier API to make AI-powered research accessible.

## ✨ Features

- **Multi-Agent Architecture:** Specialized agents collaborate to research, write, validate, and review reports.
- **Real-Time Agent Tracing:** Follow agent progress as the research runs.
- **Web-Based Research:** Retrieve relevant information using DuckDuckGo.
- **Cited Research Reports:** Generate structured reports supported by retrieved sources.
- **Grounding Validation:** Validate citations against collected research sources.
- **Self-Review & Revision:** The Reviewer evaluates drafts and can request revisions.
- **Human-in-the-Loop:** Approve reports or request changes before completion.
- **Interactive Streamlit UI:** Submit research questions and view results.
- **Downloadable Reports:** Export the final report as a Markdown file.
- **Gemini Model Selection:** Choose from supported Gemini models.

## 🏗️ System Architecture

The application uses LangGraph to coordinate multiple agents through a structured research workflow.

```text
             User Question
                   |
                   v
              Supervisor
                   |
                   v
              Researcher
                   |
                   v
          DuckDuckGo Search
                   |
                   v
                Writer
                   |
                   v
         Grounding Validation
                   |
                   v
                Reviewer
                   |
             +-----+-----+
             |           |
             v           v
           Revise      Accept
             |           |
             v           v
           Writer    Final Report
```

### Agent Responsibilities

| Component | Responsibility |
|---|---|
| Supervisor | Coordinates the research workflow |
| Researcher | Searches the web and collects relevant information |
| Writer | Creates a structured report using research findings |
| Validator | Checks citations against collected sources |
| Reviewer | Evaluates the report and requests revisions |

When Human-in-the-Loop is enabled, the workflow can pause after the Reviewer, allowing the user to approve the draft or request another revision.

## 🛠️ Tech Stack

| Technology | Purpose |
|---|---|
| Python | Core application logic |
| Streamlit | Interactive user interface |
| LangGraph | Multi-agent orchestration |
| LangChain | LLM and tool integration |
| Google Gemini | Research, writing, and review |
| DuckDuckGo Search | Web research and information retrieval |
| Pydantic | Data validation and structured state |

## 📁 Project Structure

```text
Multi-Agent-Research-Assistant/
│
├── streamlit_app.py
│
├── agents/
│   ├── config.py
│   ├── graph.py
│   └── tools.py
│
├── .streamlit/
│   └── secrets.toml.example
│
├── .env.example
├── requirements.txt
└── README.md
```

### Key Files

- `streamlit_app.py` — Streamlit interface and application entry point.
- `agents/config.py` — Gemini model configuration.
- `agents/graph.py` — LangGraph workflow, agent nodes, and transitions.
- `agents/tools.py` — DuckDuckGo search and research utilities.
- `requirements.txt` — Python project dependencies.
- `.env.example` — Example environment variable configuration.

## 🚀 Getting Started

Follow these steps to run the project locally.

### 1. Clone the Repository

```bash
git clone https://github.com/YOUR_USERNAME/Multi-Agent-Research-Assistant.git

cd Multi-Agent-Research-Assistant
```

### 2. Create a Virtual Environment

```bash
python -m venv .venv
```

Activate the environment.

**Windows (PowerShell):**

```powershell
.venv\Scripts\Activate.ps1
```

**Linux / macOS:**

```bash
source .venv/bin/activate
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure Google Gemini API Key

Get a Gemini API key from [Google AI Studio](https://aistudio.google.com/app/apikey).

Create a `.env` file in the project root:

```env
GOOGLE_API_KEY=your_gemini_api_key
```

Alternatively, configure the key using Streamlit secrets.

Create `.streamlit/secrets.toml`:

```toml
GOOGLE_API_KEY = "your_gemini_api_key"
```

Keep your API key private. Do not commit `.env` or `secrets.toml` to GitHub.

### 5. Run the Application

```bash
streamlit run streamlit_app.py
```

The application will open in your browser, usually at:

```text
http://localhost:8501
```

Enter a research question and let the agents generate your report.

## 🔍 Example Research Questions

- What are the recent developments in Generative AI?
- How is AI being used in healthcare?
- What are the applications of multi-agent systems?
- Compare RAG and fine-tuning for large language models.
- What are the challenges of AI adoption in Nepal?

## 🧠 Key Learning Outcomes

- Building multi-agent AI systems using LangGraph.
- Designing stateful workflows with conditional transitions.
- Integrating LLMs with external search tools.
- Implementing iterative review and revision loops.
- Applying source-grounding checks to LLM-generated reports.
- Building interactive AI applications with Streamlit.
- Managing API keys and environment-based configuration.

## ⚠️ Limitations

- Research quality depends on the availability and relevance of web search results.
- Gemini usage is subject to API rate limits and free-tier availability.
- Citation validation checks source grounding but does not guarantee factual correctness.
- AI-generated reports may contain inaccuracies and should be verified before academic or professional use.

## 👨‍💻 Author

**Saugat Pudasaini**  
IT Undergraduate | AI/ML & Generative AI Enthusiast

Interested in building practical AI applications using LLMs, RAG, LangChain, and LangGraph.

---

⭐ If you find this project interesting, feel free to explore the repository and build upon it.
# ERP Assistant

An AI-powered ERP assistant that manages core entities — **Users**, **Customers**, and **Offices** — via natural language, and generates interactive organizational charts from unstructured text. Built with Streamlit, FastAPI, LangGraph, and LLMs (Claude 3.5 Sonnet + Gemini 2.0 Flash).

## Features

- **Conversational CRUD** — Add or delete Users/Customers/Offices by chatting in plain English. Intent detection and entity routing are handled by an LLM-backed LangGraph workflow.
- **Multi-format file ingestion** — Upload `CSV`, `XLSX`, `PDF`, `TXT`, or `JSON` files; the agent extracts, normalizes, and maps records to the target schema in chunked LLM calls.
- **General ERP guidance** — Answers questions about schemas, file formats, and usage, and steers off-topic queries back to supported tasks.
- **Data browser** — Tabular view of all Users, Customers, and Offices stored in the JSON database (`src/show.py:17`).
- **Org-chart generation** — Give it a free-text transcription of reporting relationships and it extracts a structured hierarchy (Pydantic `EmployeeList`) and renders an interactive chart with NetworkX + Plotly (`src/org_chart.py:31`).

## Architecture

```
Streamlit Frontend (app.py)
  ├── src/chatbot.py        — Chat UI, file upload → input_bucket/, proxies to FastAPI
  ├── src/show.py           — Data viewer for database/*.json
  └── src/org_chart.py     — Transcription → structured org + Plotly chart

FastAPI Backend (src/backend.py)
  └── LangGraph StateGraph (GraphState)
        START → detect_intent → router ─┬─ read_file → interpret → add → END  (intent=add)
                                        ├─ delete → END                         (intent=delete)
                                        └─ general_chat → END                  (intent=general)

LLM Layer
  ├── src/functions_models.py  — IntentEntityPath classification + general_chat (Claude 3.5 Sonnet)
  ├── src/addition_workflow.py — read_file (pandas/PDFPlumber) + interpret/add (Claude 3.5 Sonnet)
  ├── src/deletion_workflow.py — delete by unique key (id)
  └── src/org_chart.py        — extract_structure (Gemini 2.0 Flash, structured output)
```

### Workflow Details

| Node | File | Description |
|------|------|-------------|
| `detect_intent` | `src/functions_models.py:53` | Classifies `intent` (`add`/`delete`/`general`), `entity` (`user`/`customer`/`office`), and delete params via structured LLM output. |
| `router` | `src/functions_models.py:66` | Conditional edge: `add` → `read_file`, `delete` → `delete`, `general` → `general_chat`. |
| `read_file` | `src/addition_workflow.py:21` | Reads `input_bucket/<file>` based on extension (CSV/XLSX via pandas, PDF via PDFPlumber, JSON/TXT natively). |
| `interpret` | `src/addition_workflow.py:69` | Chunks records (5 per chunk), maps each chunk to `User`/`Customer`/`Office` via LLM structured output. |
| `add` | `src/addition_workflow.py:149` | Deduplicates on `id`, appends new entities to `database/*.json`, reports added vs. skipped IDs. |
| `delete` | `src/deletion_workflow.py:4` | Deletes by `id` only; filters `users.json`/`customers.json`/`offices.json` and reports deleted count. |
| `general_chat` | `src/functions_models.py:74` | System-prompted assistant that explains schemas, file formats, and guides toward add/delete actions. |
| `extract_structure` | `src/org_chart.py:31` | Parses a transcription into `EmployeeList` via Gemini 2.0 Flash structured output. |
| `create_org_chart` | `src/org_chart.py:54` | Builds a `DiGraph`, computes hierarchical layers, and renders with `multipartite_layout` + Plotly. |

### Data Models

Defined in `src/functions_models.py:19` and `src/org_chart.py:19`:

- **User** — `id`, `username`, `email`, `designation`, `department`, `phone`
- **Customer** — `id`, `name`, `address` (`address1`, `address2`, `city`, `state`, `zip`, `country`, `county`)
- **Office** — `id`, `location`, `size`
- **Employee** — `id`, `name`, `age`, `position`, `reportees[]`

Persistence is JSON-file based (`database/users.json`, `database/customers.json`, `database/offices.json`).

## Project Structure

```
ERP-Assistant/
├── app.py                    # Streamlit entry point — multi-page navigation
├── requirements.txt
├── .env                      # GOOGLE_API_KEY, ANTHROPIC_API_KEY (not committed ideally)
├── org_structure.json        # Example org hierarchy (10 employees)
├── org_chart                 # Example Graphviz DOT export of org_structure.json
├── transcription.txt         # Example natural-language org description
├── database/
│   ├── users.json
│   ├── customers.json
│   └── offices.json
├── input_bucket/             # Uploaded files land here at runtime
├── src/
│   ├── backend.py            # FastAPI + LangGraph workflow definition
│   ├── chatbot.py            # Chatbot Streamlit page
│   ├── show.py               # Data viewer Streamlit page
│   ├── org_chart.py          # Org-chart Streamlit page + extraction/rendering
│   ├── functions_models.py   # Pydantic schemas, intent detection, general chat
│   ├── addition_workflow.py  # File reading, LLM interpretation, DB insertion
│   └── deletion_workflow.py  # Deletion by unique key
└── testing_files/
    ├── users/                # user_data.{csv,json,xlsx,pdf,txt}
    ├── customers/            # customer_data.{csv,json,pdf,...} + flattened variants
    └── offices/              # office_data.{csv,json,xlsx,pdf,txt}
```

## Prerequisites

- Python 3.10+
- API keys:
  - `GOOGLE_API_KEY` — for Gemini 2.0 Flash (org-chart extraction)
  - `ANTHROPIC_API_KEY` — for Claude 3.5 Sonnet (intent + addition workflow + general chat)

## Installation

```bash
git clone https://github.com/mowne67/ERP-Assistant.git
cd ERP-Assistant

python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate

pip install -r requirements.txt
```

Create a `.env` file in the project root:

```env
GOOGLE_API_KEY=your_google_api_key
ANTHROPIC_API_KEY=your_anthropic_api_key
```

> The committed `.env` contains example keys — replace them with your own and ensure `.env` is in `.gitignore` before pushing.

## Usage

The app requires **two processes**: the FastAPI backend and the Streamlit frontend.

### 1. Start the backend

```bash
uvicorn src.backend:app --reload --port 8000
```

The chat endpoint is exposed at `POST http://127.0.0.1:8000/chat/` with body:

```json
{
  "input_text": "Add a new user from the file.",
  "file_path": "input_bucket/user_data.csv"
}
```

Logs are written to `chat_output.log`.

### 2. Start the frontend

In a second terminal:

```bash
streamlit run app.py
```

This opens three pages via the sidebar navigation (`app.py:3`):

| Page | Description |
|------|-------------|
| **Chatbot** | Chat input + file uploader (CSV/XLSX/PDF/TXT/JSON). Type messages like `Add a new user from the file` or `Delete user with id 3`. |
| **Show Users, Customers, and Offices** | Expandable tables sourced from `database/*.json`. |
| **Organizational Chart creation** | Upload a `.txt` transcription → view extracted JSON + interactive Plotly org chart. See `transcription.txt` for an example. |

### Example Prompts

- `Add a new user from the file.` (upload a file first via the sidebar)
- `Add customers from the uploaded JSON.`
- `Delete user with id 3` / `Delete office with id 7`
- `What file formats do you support?`
- `Show me the user schema`

### Org-Chart Example

Upload `transcription.txt`:

> John Doe (id - 1) is the CEO... Jane Smith (id - 2), the CTO; Michael Green (id - 3), the CFO...

The LLM extracts an `EmployeeList` and the app renders a hierarchical NetworkX/Plotly graph. The same structure is available as `org_structure.json`.

## Supported File Formats for Addition

| Format | Reader | Notes |
|--------|--------|-------|
| CSV | `pandas.read_csv` | Header row required; must include `id`. |
| XLSX | `pandas.read_excel` | Requires `openpyxl`. |
| JSON | `json.load` | Single object or array; wrapped to list if needed. |
| PDF | `PDFPlumberLoader` | Text extraction; LLM interprets unstructured content. |
| TXT | Plain read | Raw text passed to LLM for structured mapping. |

Duplicate handling: records whose `id` already exists in the target JSON file are skipped (`src/addition_workflow.py:182`). Deletion is only allowed by `id` (`src/deletion_workflow.py:32`).

## API Reference

### `POST /chat/`

Defined in `src/backend.py:61`.

- **Request** — `ChatInput { input_text: str, file_path?: str }`
- **Response** — `str` (content of the final `AIMessage`)
- **State** — `MemorySaver` checkpointer with `thread_id: "1"` (single-threaded demo; extend for multi-user sessions).

## Testing

Sample data for manual testing is in `testing_files/`:

- `testing_files/users/user_data.{csv,json,xlsx,pdf,txt}`
- `testing_files/customers/flattened_customer_data.{csv,json,xlsx,pdf,txt}`
- `testing_files/offices/office_data.{csv,json,xlsx,pdf,txt}`

Upload any of these through the Chatbot page's file uploader and issue an add prompt.

## Logging

Workflow outputs are logged to `chat_output.log` at `INFO` level (`src/backend.py:13`).

## Tech Stack

- **UI** — Streamlit
- **API** — FastAPI + Uvicorn
- **Orchestration** — LangGraph (`StateGraph`, `MemorySaver`)
- **LLMs** — Anthropic Claude 3.5 Sonnet (`langchain-anthropic`), Google Gemini 2.0 Flash (`langchain-google-genai`)
- **Data** — pandas, PDFPlumber, Pydantic
- **Visualization** — Plotly, NetworkX

## Notes & Limitations

- Deletion only supports filtering by `id` (the unique key). Other attributes are rejected with a guidance message.
- The LangGraph checkpointer uses an in-memory `MemorySaver` with a hardcoded `thread_id` — not suitable for concurrent multi-user deployments without modification.
- The database is file-based JSON; consider migrating to a proper DB for production use.
- API keys should not be committed. Add `.env` to `.gitignore`.

## License

No license file is currently included. Add one if you intend to open-source this project.

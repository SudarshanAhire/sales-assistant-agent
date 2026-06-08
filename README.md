# Persistent Sales Assistant Agent

A hosted conversational API where a B2B SaaS sales assistant remembers user context across sessions, uses real tools to answer from a product catalog, and returns a structured self-evaluation score on every response.

**Live Demo:** [Railway Deployment URL will be added after deployment]

## Table of Contents

- [Overview](#overview)
- [Architecture](#architecture)
- [Tech Stack](#tech-stack)
- [Setup & Installation](#setup--installation)
- [Design Decisions](#design-decisions)
- [API Endpoints](#api-endpoints)
- [Demo: Cross-Session Memory](#demo-cross-session-memory)
- [Deployment](#deployment)
- [Bonus Features](#bonus-features)

---

## Overview

This project demonstrates **production-ready AI agent architecture** with three critical components:

1. **Persistent Cross-Session Memory** — Conversations stored in SQLite with semantic recall
2. **Tool Use, Not Hallucination** — Real function calls to search catalog and retrieve user context
3. **Structured Self-Evaluation** — Every response includes groundedness, relevance, and confidence scores

## Architecture

### Message Flow Diagram

```text
┌─────────────┐
│   Client    │ (Frontend / curl)
└──────┬──────┘
       │ POST /chat/{user_id}
       v
┌─────────────────────────────────────────────────────────┐
│                   FastAPI Router                         │
│  ├─ POST   /chat/{user_id}                              │
│  ├─ GET    /chat/{user_id}/history                      │
│  ├─ GET    /chat/{user_id}/evals                        │
│  ├─ DELETE /chat/{user_id}/memory                       │
│  ├─ GET    /catalog                                     │
│  └─ GET    /health                                      │
└──────┬──────────────────────────────────────────────────┘
       │
       v
┌─────────────────────────────────────────────────────────┐
│                 Chat Service Handler                     │
│  ├─ Generate session_id (UUID)                          │
│  ├─ Save user message to DB                             │
│  ├─ Call Sales Agent                                    │
│  ├─ Save assistant response + eval to DB                │
│  └─ Return JSON response with eval block                │
└──────┬──────────────────────────────────────────────────┘
       │
       v
┌─────────────────────────────────────────────────────────┐
│                   Sales Agent Loop                       │
│  ├─ Tool 1: get_user_memory(user_id)                    │
│  │           → Query SQLite for past facts/interests    │
│  ├─ Tool 2: search_catalog(query)                       │
│  │           → Keyword search over catalog.json         │
│  ├─ Optional: flag_for_human(user_id, reason)           │
│  │            → Log warning if confidence too low       │
│  └─ Construct LLM prompt with context                   │
└──────┬──────────────────────────────────────────────────┘
       │
       v
┌─────────────────────────────────────────────────────────┐
│              LLM Service (Groq/OpenAI)                   │
│  ├─ Model: llama-3.1-8b-instant (or OpenAI compatible)  │
│  ├─ System prompt: "Answer only from catalog context"   │
│  ├─ Context injection: catalog_results + user_memory    │
│  └─ Return: agent_response                              │
└──────┬──────────────────────────────────────────────────┘
       │
       v
┌─────────────────────────────────────────────────────────┐
│                 Eval Service (Self-Score)               │
│  ├─ Prompt LLM: "Evaluate your own response"            │
│  ├─ Extract JSON: groundedness, relevance, confidence   │
│  ├─ Flag if confidence < threshold (0.55)               │
│  └─ Return: eval_block with reasoning                   │
└──────┬──────────────────────────────────────────────────┘
       │
       v
┌─────────────────────────────────────────────────────────┐
│                    SQLite Database                       │
│  ├─ users table          (user_id, created_at)          │
│  ├─ messages table       (user, session, role, content) │
│  ├─ memories table       (facts extracted from queries) │
│  └─ eval_logs table      (scores + reasoning per msg)   │
└─────────────────────────────────────────────────────────┘
       │
       v
┌─────────────────────────────────────────────────────────┐
│               JSON Response to Client                    │
│  {                                                       │
│    "response": "The Enterprise plan is $499/mo...",      │
│    "eval": {                                             │
│      "groundedness": 0.91,                               │
│      "relevance": 0.88,                                  │
│      "confidence": 0.85,                                 │
│      "flagged": false,                                   │
│      "reasoning": "Response sourced from catalog..."     │
│    },                                                    │
│    "tools_called": ["get_user_memory", "search_catalog"],│
│    "session_id": "uuid-here"                             │
│  }                                                       │
└─────────────────────────────────────────────────────────┘
```

## Tech Stack

| Component       | Technology                                  |
| --------------- | ------------------------------------------- |
| **Framework**   | FastAPI 0.115                               |
| **Web Server**  | Uvicorn (ASGI)                              |
| **Database**    | SQLite + SQLAlchemy ORM                     |
| **Schemas**     | Pydantic 2.10                               |
| **LLM API**     | Groq/OpenAI-compatible                      |
| **HTTP Client** | httpx (async)                               |
| **Python**      | 3.11.9                                      |
| **Hosting**     | Railway                                     |

## Setup & Installation

### Prerequisites

- Python 3.11+
- A [Groq API key](https://console.groq.com) (free tier available)

### Local Development

#### 1. Clone and Install

```bash
cd sales-assistant-agent
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

#### 2. Configure Environment

Copy `.env.example` to `.env` and add your Groq API key:

```bash
cp .env.example .env
# Edit .env and add LLM_API_KEY=your_groq_api_key
```

#### 3. Run the Server

```bash
uvicorn app.main:app --reload
```

Server will start at `http://localhost:8000`

#### 4. Verify Health

```bash
curl http://localhost:8000/health
```

---

## Design Decisions

### 1. **Memory Layer Abstraction** (Why SQLite + Abstracted Interface)

**Decision:** Implement `MemoryStore` as an ABC with a SQLite backend (`SQLiteMemoryStore`).

**Rationale:**

- **Swappability:** Swapping SQLite → PostgreSQL → Mem0 requires changing only `memory/sqlite_store.py`, not ten files. The abstraction lives in `memory/base.py`.
- **Scalability Trade-off:** SQLite works for prototype/single-server deployments. At scale (1000s of concurrent users), we'd switch to PostgreSQL or a managed vector DB like Mem0.
- **Implementation:** All memory ops go through the `memory_store` singleton instance, which is a `SQLiteMemoryStore()`. To swap backends, only change the factory in `memory/sqlite_store.py`.

**Example Refactor to PostgreSQL:**

```python
# memory/postgres_store.py
class PostgresMemoryStore(MemoryStore):
    def get_memory(self, db: Session, user_id: str, limit: int = 10):
        # Different implementation, same interface
        pass

# In memory/sqlite_store.py, change the last line:
# memory_store = PostgresMemoryStore()  # Swap with one line!
```

### 2. **Eval Service Design** (Fallback Scoring + LLM Self-Eval)

**Decision:** Eval block includes fallback scoring (hardcoded rules) + LLM self-evaluation.

**Rationale:**

- **Always-On Evals:** Every response includes `eval` block, even if LLM evaluator is unavailable.
- **Confidence Threshold:** If LLM eval fails, fallback to simple heuristics:
  - `groundedness = 0.9` if catalog context present, else `0.55`
  - `confidence < 0.55` → auto-flag for human review
- **Quality Metrics:** Structured output allows aggregation (see `GET /chat/{user_id}/evals` for % high-confidence responses).

**Fallback Example:**

```python
fallback = {
    "groundedness": 0.9 if catalog_context else 0.55,
    "relevance": 0.88,
    "confidence": 0.86 if catalog_context else 0.55,
    "flagged": False if catalog_context else True,
    "reasoning": "Fallback scoring used if LLM unavailable."
}
```

**Production Upgrades:**

- **Separate Eval Model:** Use `gpt-3.5-turbo` for eval, `llama-3.1` for chat (different endpoints).
- **Learned Eval:** Fine-tune a smaller model (`distilbert`) on labeled QA pairs with eval ground truth.
- **Human Feedback Loop:** Track which auto-evals matched human review; retrain eval model on mismatches.

### 3. **Tool Use: Real Functions, Not String Injection**

**Decision:** Tools are actual Python functions with real DB queries, not string prompts.

**Rationale:**

- **No Hallucination:** LLM doesn't invent tool outputs; we control them.
- **Semantic Recall:** `get_user_memory()` retrieves facts from `memories` table, not user message history. These are extracted facts like "asked about Enterprise SSO".
- **Search Quality:** `search_catalog()` uses keyword matching (upgradeable to embeddings). It always returns ranked results, never imagined products.

**Tool Definitions:**

| Tool                 | Function                  | Real Work                                  |
| -------------------- | ------------------------- | ------------------------------------------ |
| `get_user_memory`    | `tools/memory_tools.py`   | Queries `memories` table for past facts    |
| `search_catalog`     | `tools/catalog_tools.py`  | Keyword search over `catalog.json`         |
| `flag_for_human`     | `tools/human_tools.py`    | Logs warning; aggregated in audit trail    |

### 4. **Cross-Session Memory Storage**

**Decision:** Store facts in `memories` table, not raw messages. Extract interests from user questions.

**How It Works:**

1. User asks: *"Do you have SSO?"*
2. Agent calls `save_user_interest()` → extracts keywords `["sso"]` → stores fact: `"User interested in SSO"`
3. Next session, user asks: *"What's the price of that plan with SSO?"*
4. Agent calls `get_user_memory()` → retrieves `"User interested in SSO"` → injects into context
5. Agent context now includes prior interest → avoids re-explaining SSO

**Trade-off:** Requires explicit extraction logic. At scale, use embeddings-based semantic memory instead.

---

## API Endpoints

### 1. **POST /chat/{user_id}**

Send a message, get a response with eval block.

**Request:**

```json
{
  "message": "What's your Enterprise plan pricing?",
  "session_id": "uuid-optional"
}
```

**Response:**

```json
{
  "response": "The Enterprise plan is $499/mo and includes unlimited users, SSO, audit logs, and SLA.",
  "eval": {
    "groundedness": 0.91,
    "relevance": 0.88,
    "confidence": 0.85,
    "flagged": false,
    "reasoning": "Response sourced directly from catalog with user context applied."
  },
  "tools_called": ["get_user_memory", "search_catalog"],
  "session_id": "550e8400-e29b-41d4-a716-446655440000"
}
```

---

### 2. **GET /chat/{user_id}/history**

Retrieve all past messages (user + assistant) across sessions.

**Response:**

```json
{
  "user_id": "sales-team-member-123",
  "history": [
    {
      "role": "user",
      "content": "What's your Enterprise plan pricing?",
      "session_id": "session-1",
      "created_at": "2026-06-08T10:30:00Z"
    },
    {
      "role": "assistant",
      "content": "The Enterprise plan is $499/mo...",
      "session_id": "session-1",
      "created_at": "2026-06-08T10:30:05Z"
    }
  ]
}
```

---

### 3. **GET /chat/{user_id}/evals**

Aggregated eval metrics across all sessions (bonus feature).

**Response:**

```json
{
  "user_id": "sales-team-member-123",
  "total_responses": 15,
  "average_groundedness": 0.89,
  "average_relevance": 0.87,
  "average_confidence": 0.82,
  "high_confidence_percentage": 73.3,
  "flagged_count": 2
}
```

---

### 4. **DELETE /chat/{user_id}/memory**

Wipe a user's memory (GDPR compliance).

**Response:**

```json
{
  "user_id": "sales-team-member-123",
  "deleted": true,
  "message": "User memory wiped successfully. Conversation history and eval logs are retained for audit."
}
```

---

### 5. **GET /catalog**

Get the product catalog.

**Response:**

```json
{
  "plans": [
    {
      "name": "Starter",
      "price": "$49/mo",
      "features": ["5 users", "API access", "email support"],
      "best_for": "Small teams starting with sales automation"
    },
    {
      "name": "Growth",
      "price": "$199/mo",
      "features": ["25 users", "webhooks", "priority support"],
      "best_for": "Growing teams needing integrations and faster support"
    },
    {
      "name": "Enterprise",
      "price": "$499/mo",
      "features": ["unlimited users", "SSO", "audit logs", "SLA"],
      "best_for": "Large organizations with security and compliance needs"
    }
  ]
}
```

---

### 6. **GET /health**

Service health check.

**Response:**

```json
{
  "status": "ok"
}
```

---

## Demo: Cross-Session Memory

This demonstrates that the agent **remembers context across separate API calls without re-sending it in the request body**.

### Setup

Start the server:

```bash
uvicorn app.main:app --reload
```

### Test Case: Two-Session Conversation

**Session 1 — User Asks About Enterprise Plan**

```bash
curl -X POST http://localhost:8000/chat/user-alice \
  -H "Content-Type: application/json" \
  -d '{
    "message": "Tell me about your Enterprise plan. Does it have SSO?"
  }' | jq .response
```

**Expected Response:**

```
"The Enterprise plan is $499/mo and includes unlimited users, SSO, audit logs, and SLA."
```

**Session 2 — User References Prior Context (No Re-send)**

Now, in a **new session**, ask a follow-up that depends on what was discussed in Session 1. The agent should remember the prior interest in Enterprise SSO:

```bash
curl -X POST http://localhost:8000/chat/user-alice \
  -H "Content-Type: application/json" \
  -d '{
    "message": "Does that plan also include audit logs?"
  }' | jq .response
```

**Expected Response:**

```
"Yes, the Enterprise plan includes audit logs along with SSO and SLA. All of these are included in the $499/mo price."
```

**Key Proof of Memory:**

- ✅ No `session_id` sent in Session 2 request → new session generated
- ✅ Agent referenced prior Enterprise interest → retrieved from `memories` table
- ✅ No context re-sent in request body → proof that memory is persisted in DB

### Verify History

```bash
curl http://localhost:8000/chat/user-alice/history | jq '.history | length'
```

Should return `4` (two user messages + two assistant responses).

### View Eval Metrics

```bash
curl http://localhost:8000/chat/user-alice/evals | jq .
```

Shows aggregated eval scores across all responses.

### Test Health & Catalog

```bash
# Health check
curl http://localhost:8000/health | jq .

# Get catalog
curl http://localhost:8000/catalog | jq .
```

---

## Curl Commands for Railway Deployment

After deploying to Railway, replace `http://localhost:8000` with your live URL:

```bash
LIVE_URL="https://your-railway-app.up.railway.app"

# Test health
curl $LIVE_URL/health

# Session 1: Ask about Enterprise pricing
curl -X POST "$LIVE_URL/chat/user-alice" \
  -H "Content-Type: application/json" \
  -d '{"message": "Tell me about your Enterprise plan. Does it have SSO?"}'

# Session 2: Reference prior context (memory test)
curl -X POST "$LIVE_URL/chat/user-alice" \
  -H "Content-Type: application/json" \
  -d '{"message": "Does that plan also include audit logs?"}'

# Get conversation history
curl "$LIVE_URL/chat/user-alice/history"

# Get eval metrics
curl "$LIVE_URL/chat/user-alice/evals"

# Get product catalog
curl "$LIVE_URL/catalog"
```

---

## Deployment

### Deploy to Railway

Railway auto-detects the `Procfile` and uses it to start the service. Here's how to deploy:

#### Step 1: Create Railway Account

Go to [railway.app](https://railway.app) and create a free account.

#### Step 2: Connect Your GitHub Repository

1. Push this project to a public GitHub repository
2. On Railway dashboard, click **"New Project"** → **"Deploy from GitHub Repo"**
3. Authorize Railway to access your GitHub account
4. Select this repository

#### Step 3: Configure Environment Variables

In the Railway dashboard for your project:

1. Click on the **"Variables"** tab (or **"Settings"** → **"Variables"**)
2. Add these environment variables:

```
LLM_API_KEY=your_groq_api_key_here
LLM_BASE_URL=https://api.groq.com/openai/v1
LLM_MODEL=llama-3.1-8b-instant
DATABASE_URL=sqlite:///./sales_agent.db
EVAL_CONFIDENCE_THRESHOLD=0.55
```

**Note:** To get a free Groq API key:
1. Visit [console.groq.com](https://console.groq.com)
2. Sign up with your GitHub or email
3. Create an API key in the dashboard
4. Paste it into the `LLM_API_KEY` variable above

#### Step 4: Deploy

Railway will automatically:

1. Detect the `Procfile` with the uvicorn command
2. Detect `runtime.txt` (Python 3.11.9)
3. Install dependencies from `requirements.txt`
4. Start the uvicorn server on port `$PORT`

Click **"Deploy"** and wait for the build to complete (typically 1-2 minutes).

#### Step 5: Get Your Live URL

Once deployed, Railway displays your service URL in the dashboard, something like:

```
https://sales-assistant-agent-production.up.railway.app
```

#### Step 6: Test the Live Deployment

```bash
# Test health
curl https://your-railway-app.up.railway.app/health

# Test chat with memory persistence
curl -X POST https://your-railway-app.up.railway.app/chat/demo-user \
  -H "Content-Type: application/json" \
  -d '{"message":"What is your Enterprise plan pricing?"}'
```

---

## Bonus Features Implemented

### ✅ GET /chat/{user_id}/evals

Returns aggregated eval scores:

```bash
curl http://localhost:8000/chat/user-alice/evals | jq .
```

Shows:

- `total_responses`: 15
- `average_groundedness`: 0.89
- `average_confidence`: 0.82
- `high_confidence_percentage`: 73.3%
- `flagged_count`: 2

Useful for monitoring agent quality over time.

### ✅ Fallback Eval Scoring

If LLM evaluator is unavailable, hardcoded fallback ensures every response includes structured eval:

```python
fallback = {
    "groundedness": 0.9 if catalog_context else 0.55,
    "confidence": 0.86 if catalog_context else 0.55,
    "flagged": False if catalog_context else True,
}
```

### ✅ Automatic Human Flagging

Responses with `confidence < 0.55` are automatically flagged:

```python
data["flagged"] = data["confidence"] < settings.eval_confidence_threshold
flag_for_human(user_id, reasoning)  # Logs warning
```

---

## Folder Structure

```
sales-assistant-agent/
├── app/
│   ├── __init__.py
│   ├── main.py                 # FastAPI app, startup hook
│   ├── config.py               # Settings (pydantic-settings)
│   ├── api/
│   │   ├── __init__.py
│   │   └── routes.py           # All endpoint handlers
│   ├── agents/
│   │   ├── __init__.py
│   │   └── sales_agent.py      # Agent loop, tool orchestration, eval
│   ├── db/
│   │   ├── __init__.py
│   │   ├── session.py          # SQLAlchemy session, engine
│   │   ├── models.py           # ORM models (User, Message, Memory, EvalLog)
│   │   └── init_db.py          # Create tables on startup
│   ├── memory/
│   │   ├── __init__.py
│   │   ├── base.py             # Abstract MemoryStore interface
│   │   └── sqlite_store.py     # SQLite implementation
│   ├── models/
│   │   ├── __init__.py
│   │   └── schemas.py          # Pydantic request/response schemas
│   ├── services/
│   │   ├── __init__.py
│   │   ├── chat_service.py     # Handle chat requests (saves messages, calls agent)
│   │   ├── llm_service.py      # Call Groq/OpenAI API with fallback
│   │   └── eval_service.py     # Self-eval logic with fallback scoring
│   └── tools/
│       ├── __init__.py
│       ├── catalog_tools.py    # search_catalog() implementation
│       ├── memory_tools.py     # get_user_memory(), save_user_interest()
│       └── human_tools.py      # flag_for_human() implementation
├── catalog.json                # Product catalog (Starter, Growth, Enterprise)
├── .env.example                # Template for environment variables
├── requirements.txt            # Python dependencies
├── runtime.txt                 # Python version (3.11.9)
├── Procfile                    # Heroku/Railway deployment config
└── README.md                   # This file
```

---

## Key Architecture Insights

### 1. **Memory is Stored, Not Computed**

Unlike stateless chat APIs, every user message triggers a DB write. Facts are extracted and stored, not re-derived on each call.

### 2. **Tools are Callable, Not Prompted**

LLM doesn't "imagine" tool outputs. Every tool is a real function with deterministic behavior (DB query or catalog search).

### 3. **Evals Are Always Structured**

Even if LLM evaluator fails, responses include `eval` block with fallback scores. This enables aggregation and monitoring.

### 4. **Memory Layer is Abstracted**

Swapping SQLite → PostgreSQL → Mem0 is a one-line change in the factory. The rest of the codebase is backend-agnostic.

---

## Troubleshooting

### LLM API Key Not Set

If you don't have a Groq API key, the service uses fallback responses (hardcoded). To get one:

1. Visit [console.groq.com](https://console.groq.com)
2. Sign up (free tier available)
3. Generate an API key
4. Add to `.env`: `LLM_API_KEY=...`

### Database Locked (SQLite)

If running multiple processes, SQLite may show "database is locked". Solutions:

- Use a single process in development
- Switch to PostgreSQL for production (change `DATABASE_URL` in `.env`)

### Catalog Not Found

Ensure `catalog.json` is in the project root (`sales-assistant-agent/catalog.json`). The path is resolved from `app/tools/catalog_tools.py`:

```python
CATALOG_PATH = Path(__file__).resolve().parents[2] / "catalog.json"
```

---

## Future Improvements

1. **Vector Embeddings for Memory:** Replace keyword extraction with sentence embeddings + semantic search
2. **Separate Eval Model:** Use a dedicated eval model (not the chat model) for unbiased scoring
3. **Human Review Dashboard:** Web UI to review flagged responses and retrain the agent
4. **Memory Summarization:** Auto-compress old facts into summaries after N messages
5. **Audit Trail:** Immutable log of all agent decisions (for compliance)
6. **Multi-Tool Planning:** Use an agentic loop to decide *which* tools to call, rather than always calling all tools

---

## License

MIT

---

**Questions?** Open an issue on GitHub or check the architecture diagram above.

      |
      v
SQLite Logs
      |
      v
JSON Response
```

## API Endpoints

| Method | Endpoint | Purpose |
|---|---|---|
| POST | `/chat/{user_id}` | Send a message and receive assistant response + eval |
| GET | `/chat/{user_id}/history` | Full conversation history across sessions |
| DELETE | `/chat/{user_id}/memory` | GDPR-style memory wipe |
| GET | `/catalog` | Product/pricing catalog |
| GET | `/health` | Health check |
| GET | `/chat/{user_id}/evals` | Bonus: aggregated eval scores |

## Memory Design Decision

Memory is stored in SQLite using SQLAlchemy models. The application does not rely on an in-memory dictionary, so memory persists across separate API calls and server sessions as long as the database file is retained.

The `app/memory/` layer is abstracted through a `MemoryStore` base class. Currently, `SQLiteMemoryStore` implements the interface. To move to Postgres, Redis, Mem0, or a vector database, only the store implementation needs to change while API, agent, and service layers remain mostly unchanged.

At scale, I would use:

- Postgres for durable user/message/eval storage
- pgvector or Pinecone for semantic memory retrieval
- A memory summarization job for older conversations
- Separate audit logs for compliance and review workflows

## Eval Design

Every `/chat` response includes an `eval` block with:

- `groundedness`
- `relevance`
- `confidence`
- `flagged`
- `reasoning`

The eval service asks the LLM to return structured JSON. If no API key is available, the app falls back to deterministic scoring so the project remains testable.

Limitations:

- LLM self-evaluation can be biased.
- It is not a replacement for offline benchmark testing.
- Scores should be calibrated with real user feedback.

At scale, I would replace or enhance this with:

- Separate evaluator model
- RAG citation verification
- Human review queue
- Golden test set regression checks
- Automated hallucination detection

## Tools

### `search_catalog(query)`
Searches the product catalog JSON using keyword search. At production scale, this can be replaced by semantic search using embeddings.

### `get_user_memory(user_id)`
Queries the database for previous user facts and interests.

### `flag_for_human(user_id, reason)`
Logs flagged responses for human review when confidence is low.

## Product Catalog

```json
{
  "plans": [
    { "name": "Starter", "price": "$49/mo", "features": ["5 users", "API access", "email support"] },
    { "name": "Growth", "price": "$199/mo", "features": ["25 users", "webhooks", "priority support"] },
    { "name": "Enterprise", "price": "$499/mo", "features": ["unlimited users", "SSO", "audit logs", "SLA"] }
  ]
}
```

## Local Setup

```bash
git clone <your-repo-url>
cd sales-assistant-agent
python -m venv venv
source venv/bin/activate  # Windows: venv\\Scripts\\activate
pip install -r requirements.txt
cp .env.example .env
uvicorn app.main:app --reload
```

Open:

```text
http://127.0.0.1:8000/docs
```

## Environment Variables

```env
DATABASE_URL=sqlite:///./sales_agent.db
LLM_API_KEY=your_api_key_here
LLM_BASE_URL=https://api.groq.com/openai/v1
LLM_MODEL=llama-3.1-8b-instant
EVAL_CONFIDENCE_THRESHOLD=0.55
```

If `LLM_API_KEY` is empty, the app still works using a local fallback response generator for demo/testing.

## Curl Demo: Cross-Session Memory

### Call 1: Set context

```bash
curl -X POST "http://127.0.0.1:8000/chat/demo-user" \
  -H "Content-Type: application/json" \
  -d '{"message":"I am interested in Enterprise pricing."}'
```

### Call 2: Separate call using same user_id

```bash
curl -X POST "http://127.0.0.1:8000/chat/demo-user" \
  -H "Content-Type: application/json" \
  -d '{"message":"Does that include SSO?"}'
```

Expected behavior: the second response should understand that “that” refers to the previously discussed Enterprise plan and answer that Enterprise includes SSO.

## Railway Deployment

1. Push this project to GitHub.
2. Create a new Railway project.
3. Choose **Deploy from GitHub Repo**.
4. Add environment variables from `.env.example`.
5. Railway will use the `Procfile`:

```text
web: uvicorn app.main:app --host 0.0.0.0 --port $PORT
```

6. After deployment, replace local URLs in the curl commands with your Railway URL.

Example:

```bash
curl -X POST "https://your-app.up.railway.app/chat/demo-user" \
  -H "Content-Type: application/json" \
  -d '{"message":"I am interested in Enterprise pricing."}'
```

## Live Railway URL

Add after deployment:

```text
https://your-app.up.railway.app
```

## Demo Video

Record a short video showing:

1. `/health`
2. `/catalog`
3. First `/chat/demo-user` call
4. Second `/chat/demo-user` call proving memory
5. `/chat/demo-user/history`
6. `/chat/demo-user/evals`

## Project Structure

```text
app/
  api/          route handlers only
  agents/       agent loop and tool orchestration
  memory/       memory abstraction and SQLite implementation
  tools/        search_catalog, get_user_memory, flag_for_human
  services/     chat, eval, and LLM services
  models/       Pydantic schemas
  db/           SQLAlchemy models and database session
  main.py
catalog.json
requirements.txt
Procfile
runtime.txt
README.md
```

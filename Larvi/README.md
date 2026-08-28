# Larvi — Autonomous Email & Calendar AI Agent

Larvi understands natural-language requests, routes them to the right specialized
agent (Email or Calendar), executes real actions against Gmail / Google Calendar
through tool calling, and reports back only what actually happened.

```
User → Larvi Master Agent → Email Agent / Calendar Agent → Gmail / Calendar API → Result → Larvi → User
```

## 1. Architecture

```
larvi/
  app/
    main.py                 FastAPI app: /chat, OAuth routes, serves the frontend
    config.py                Loads all settings from environment variables
    master_agent.py          Master Agent: routing, multi-step orchestration,
                              confirmation flow, context injection
    llm/gemini_client.py     Generic Gemini tool-use loop (used by every agent)
    agents/
      email_agent.py         Email Agent: tool schemas + system prompt
      calendar_agent.py      Calendar Agent: tool schemas + system prompt
    tools/
      email_tools.py         Real Gmail API calls (+ mock mode fallback)
      calendar_tools.py      Real Google Calendar API calls (+ mock mode fallback)
    auth/google_auth.py      OAuth 2.0 flow, token cache + refresh
    state/context_manager.py Per-session conversation memory (sqlite)
    models/schemas.py        Request/response models
  frontend/index.html        Chat UI with a live "agent trace" panel
  tests/test_workflows.py    Tool tests + 3 end-to-end multi-step workflow tests
  requirements.txt
  .env.example
```

### Why it's structured this way

- **Master Agent (`master_agent.py`)** is the only place that talks to the user. It
  never touches Gmail/Calendar directly — it can only call two tools,
  `email_agent` and `calendar_agent`, each of which accepts one natural-language
  instruction. This mirrors the required `User → Master → Email/Calendar Agent →
  Tool → Result → Master → User` architecture and keeps routing logic (which
  agent, in what order, how many times) entirely inside the LLM's tool-use loop
  rather than hard-coded if/else intent matching.

- **Sub-agents (`agents/*.py`)** each own one domain's tool schema and system
  prompt. They run their *own* Gemini tool-use loop against the real
  `tools/email_tools.py` / `tools/calendar_tools.py` functions, so a single
  natural-language task like "find Ahmed's email about the meeting" can turn into
  several tool calls (search → read) before the sub-agent reports back a summary.

- **`llm/gemini_client.run_tool_loop`** is one generic function used by the Master
  Agent *and* both sub-agents: send messages + tool schemas → if Gemini wants a
  tool, run it locally and feed the result back → repeat until Gemini answers in
  plain text. This is the actual "tool calling" mechanism required by the brief.

- **Tools (`tools/*.py`)** are the only code that calls Google APIs. Every
  function returns `{"success": bool, ...}`. Agents (and therefore the Master
  Agent) are instructed to **never** claim an action succeeded unless
  `success == true` came back — this satisfies the "never report success unless
  confirmed" requirement directly in code, not just in the prompt.

- **`state/context_manager.py`** persists, per session: recent conversation
  history, the last-referenced email, the last-referenced event, and any pending
  confirmation. This is how "Move it to 5 PM" resolves to the meeting mentioned
  two turns ago — the snapshot is injected into every agent's system prompt.

- **Confirmation flow**: the Master Agent has a third tool, `request_confirmation`,
  which it's instructed to call instead of executing directly whenever the action
  is important/destructive (send, delete, cancel, reschedule) and the user hasn't
  already confirmed in the same message. Calling it stores a `pending_confirmation`
  in the session state and asks the user to confirm; the next message is checked
  first against that pending action before any LLM routing happens.

## 2. Setup

```bash
cd larvi
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

Edit `.env`:
- `GEMINI_API_KEY` — required, powers all three agents.
- `MOCK_MODE=true` (default) — Larvi runs fully end-to-end against a realistic
  in-memory mailbox/calendar, no Google credentials needed. Great for grading the
  agent architecture without OAuth setup.
- To use **real Gmail/Calendar**: create an OAuth 2.0 Client ID in
  [Google Cloud Console](https://console.cloud.google.com) (enable the Gmail API
  and Google Calendar API), set `GOOGLE_CLIENT_ID` / `GOOGLE_CLIENT_SECRET`, set
  `MOCK_MODE=false`, run the app, then visit `http://localhost:8000/auth/google/login`
  once to authorize. Tokens are cached to `TOKEN_STORE_PATH` and refreshed
  automatically after that.

Run it:
```bash
uvicorn app.main:app --reload
```
Open `http://localhost:8000` for the chat UI (it shows a live "agent trace" of
every tool call Larvi makes), or call the API directly:

```bash
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"session_id": "demo", "message": "What meetings do I have tomorrow?"}'
```

Run tests:
```bash
pytest tests/ -v
```
Tool-level and context-manager tests run with no API key. The three multi-step
workflow tests (`test_workflow_1/2/3`) call the real Gemini API and are
auto-skipped if `GEMINI_API_KEY` isn't set.

## 3. The three required multi-step workflows (demonstrated in `tests/test_workflows.py`)

1. **Email → Calendar**: "Find the email from Ahmed about the project meeting and
   add that meeting to my calendar." → Master Agent calls `email_agent` (search +
   read), extracts the meeting time, then calls `calendar_agent` (check
   availability + create event).
2. **Context follow-up + confirmation**: "What meetings do I have tomorrow?" then
   "Move the Team Standup to 5 PM." → resolves "the Team Standup" via session
   context, then — because rescheduling is an important action — asks
   "Move Team Standup to 5 PM tomorrow — confirm?" before executing on the next
   "yes".
3. **Conditional multi-agent workflow**: "Check whether I received an email from
   Ali about tomorrow's project meeting. If you find the meeting time, check
   whether I am free and add it to my calendar." → `email_agent` search/read,
   then conditionally `calendar_agent` check_availability + create_event only if
   a time was actually found.

## 4. How each required piece works

- **Intent understanding & tool selection**: the Master Agent's system prompt +
  its two delegation tools (`email_agent`, `calendar_agent`) let Gemini decide,
  per request, which agent(s) to call and in what order — including calling the
  same agent multiple times for multi-part requests.
- **Tool execution**: `llm/gemini_client.run_tool_loop` executes the exact
  Python function mapped to whatever tool name Gemini requests, then feeds the
  real return value back to Gemini so it can decide the next step or produce a
  final answer grounded in real data.
- **Gmail / Calendar connection & auth**: `auth/google_auth.py` implements the
  standard OAuth 2.0 authorization-code flow (`/auth/google/login` →
  Google consent → `/auth/google/callback`), caching and auto-refreshing tokens.
  No secrets are hard-coded; everything comes from environment variables.
- **Context maintenance**: `state/context_manager.py`, sqlite-backed, per
  `session_id`, storing last-referenced email/event and a bounded message history.
- **Error handling**: every tool function wraps its logic in `try/except` and
  returns `{"success": false, "error": "..."}` on failure (email/event not found,
  invalid recipient, missing date/time, API failure) instead of raising; agents
  are instructed to explain the error rather than pretend success; `main.py`
  wraps the whole `/chat` call in `try/except` as a last line of defense.

## 5. Known limitations / next steps

- `MOCK_MODE` mailbox/calendar are in-process Python lists — fine for a single
  server process/demo, not multi-worker-safe. Real Gmail/Calendar mode has no such
  limitation.
- Confirmation state is per-session, single-pending-action at a time — good
  enough for the required workflows, but a production system would want a queue.
- No multi-user auth/session boundary beyond `session_id` — add real user
  accounts before deploying this beyond a personal demo.

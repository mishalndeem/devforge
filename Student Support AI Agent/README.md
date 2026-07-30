# DEVFORGE Student Support AI Agent

An AI agent built with **FastAPI**, **LangGraph**, **LangChain**, and an **Ollama Cloud** model that answers student questions about DEVFORGE internships, AI Engineering, Web Development, Python, FastAPI, LangChain, LangGraph, GitHub, Render deployment, student tasks, certificates, and technical project guidance. Unrelated questions receive a polite redirect.

## Architecture

```text
Student sends a message
        |
FastAPI receives the request
        |
LangGraph checks the message category
        |
   +---------+----------+
   |                     |
Related              Unrelated
   |                     |
Ollama Cloud AI      Safe support
model                response
   |                     |
   +---------+----------+
        |
FastAPI returns JSON response
        |
Render hosts the API publicly
```

## Project structure

```text
devforge-student-support-agent/
├── main.py             # FastAPI app and routes
├── agent.py             # LangGraph workflow + Ollama Cloud integration
├── static/
│   └── index.html        # Chat frontend, served at /ui
├── requirements.txt
├── .env                 # local secrets (never committed)
├── .env.example          # safe template
├── .gitignore
├── render.yaml
└── README.md
```

## Frontend

A single-file chat UI lives at `static/index.html`, served by FastAPI at **`/ui`**. It talks to `POST /chat` and shows which LangGraph node handled each message (`classify → support_agent` or `classify → unrelated_response`) via the header's live pipeline indicator, using the `category` field the API returns.

By default it calls `/chat` on the same origin — fine if you're serving the frontend from the same FastAPI app. If you host the frontend elsewhere, open the gear icon in the header and set the API base URL (e.g. your Render URL); it's saved in the browser's local storage.

## Setup

1. Create and activate a virtual environment:

   ```bash
   python -m venv venv
   source venv/bin/activate     # macOS/Linux
   venv\Scripts\activate        # Windows CMD
   .\venv\Scripts\Activate.ps1  # Windows PowerShell
   ```

2. Install dependencies:

   ```bash
   pip install -r requirements.txt
   ```

3. Copy `.env.example` to `.env` and fill in your real Ollama Cloud API key:

   ```bash
   cp .env.example .env
   ```

   ```env
   OLLAMA_API_KEY=your_real_ollama_cloud_api_key
   OLLAMA_MODEL=qwen3.5:cloud
   ```

   Get your API key from your Ollama account at https://ollama.com. You can substitute any other cloud model available in your account for `OLLAMA_MODEL`.

## Run locally

```bash
uvicorn main:app --reload
```

Then open:

- http://127.0.0.1:8000/ (API welcome JSON)
- http://127.0.0.1:8000/ui (chat frontend)
- http://127.0.0.1:8000/health
- http://127.0.0.1:8000/docs

Test `POST /chat` from the `/docs` Swagger UI with a body like:

```json
{ "message": "How can I deploy an AI agent using Python?" }
```

## Deploy on Render

1. Push this repo to GitHub (make sure `.env` is **not** committed — check with `git status` first).
2. On Render: **New +** → **Web Service** → connect the GitHub repo.
3. Settings:
   - Build Command: `pip install -r requirements.txt`
   - Start Command: `uvicorn main:app --host 0.0.0.0 --port $PORT`
4. Under **Environment Variables**, add `OLLAMA_API_KEY` and `OLLAMA_MODEL` with your real values.
5. Deploy. Render will give you a URL like `https://devforge-student-support-agent.onrender.com`.

Alternatively, Render can read `render.yaml` directly (Blueprint deploy) — it will prompt you for the two secret env vars since they're marked `sync: false`.

## Troubleshooting

| Symptom | Fix |
|---|---|
| `OLLAMA_API_KEY is missing` | Add `OLLAMA_API_KEY` in Render's Environment Variables. |
| `ModuleNotFoundError` | Add the missing package to `requirements.txt`, commit, and push — Render redeploys automatically. |
| App fails to start on Render | Confirm the start command uses `--port $PORT`, not a hardcoded port. |
| 401 / Unauthorized from Ollama | Double-check the API key and that the model name is available in your Ollama account. |
| First request is slow | Render free tier sleeps after inactivity; the first request can take 30–60s. This is expected. |
| Connection refused to `localhost:11434` | You're pointing at local Ollama. Deployed code must use `https://ollama.com` with the cloud API key, never localhost. |

## Bonus ideas

- Add conversation history to the LangGraph state.
- Add a fourth node to format/post-process responses.
- Add an FAQ tool for DEVFORGE internship info.
- Add `GET /agent-info`.
- Add rate limiting.
- Build a React/Next.js frontend, deploy on Vercel.
- Add RAG over DEVFORGE docs/PDFs/FAQs.

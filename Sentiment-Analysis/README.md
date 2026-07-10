# Sentiment Analysis Web App

An end-to-end AI app: a trained ML model classifies text as **Positive**, **Neutral**, or **Negative**, served by a FastAPI backend and read through a small web UI ("Pulse").

```
Dataset → Cleaning → Preprocessing → TF-IDF → Train → Evaluate → Save → API → UI
```

## Project structure

```
Sentiment-Analysis/
├── backend/
│   ├── main.py            # FastAPI app (/predict endpoint)
│   ├── utils.py            # shared text-cleaning helpers
│   ├── requirements.txt
│   ├── model.pkl            # created by the training notebook
│   └── vectorizer.pkl       # created by the training notebook
├── frontend/
│   ├── index.html
│   ├── style.css
│   └── script.js
├── dataset/
│   ├── README.md           # where to get a dataset
│   └── sentiment.csv        # you provide this (or the notebook generates a demo one)
├── training/
│   └── train_model.ipynb    # Phases 1–8: explore → clean → preprocess → train → evaluate → save
└── README.md
```

## 1. Train the model

Open `training/train_model.ipynb` in Google Colab or Jupyter and run every cell.

- Drop a labeled CSV (`text`, `label`) at `dataset/sentiment.csv` first for a real model.
- If you skip that, the notebook auto-generates a tiny synthetic dataset so you can see the whole pipeline run — swap in real data before you rely on the predictions.
- The last cell writes `model.pkl` and `vectorizer.pkl` into `backend/`.

## 2. Run the backend

```bash
cd backend
python -m venv venv && source venv/bin/activate      # optional but recommended
pip install -r requirements.txt
uvicorn main:app --reload --port 8000
```

Check it's alive: open `http://localhost:8000` — you should see `{"status": "ok", "model_loaded": true}`.

Try a prediction:

```bash
curl -X POST http://localhost:8000/predict \
  -H "Content-Type: application/json" \
  -d '{"text": "I love this internship!"}'
```

## 3. Run the frontend

The frontend is plain HTML/CSS/JS, no build step. Simplest option:

```bash
cd frontend
python -m http.server 5500
```

Then open `http://localhost:5500`. It calls the API at `http://localhost:8000` (edit `API_BASE` in `script.js` if your backend runs elsewhere).

## 4. Test it

Try each of these against the running app (Phase 12):

- A clearly positive sentence
- A clearly negative sentence
- A neutral/factual sentence
- Empty input (should show a friendly error, not crash)
- A long paragraph

## 5. Deploy (Phase 13)

- **Backend**: any host that runs a Python process (Render, Railway, Fly.io, an EC2 box, etc.). Point it at `backend/`, install `requirements.txt`, run `uvicorn main:app --host 0.0.0.0 --port $PORT`.
- **Frontend**: any static host (GitHub Pages, Netlify, Vercel). Update `API_BASE` in `script.js` to your deployed backend URL before publishing, and loosen/adjust the CORS `allow_origins` in `backend/main.py` to match your frontend's real domain.

## Tech stack

Python · Pandas · NumPy · Scikit-learn · NLTK · FastAPI · HTML/CSS/JS · Git & GitHub

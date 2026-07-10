"""
main.py
FastAPI backend for the Sentiment Analysis Web App (Phase 9).

Run locally:
    uvicorn main:app --reload --port 8000

Endpoints:
    GET  /            -> health check
    POST /predict      -> { "text": "..." } -> { "text", "prediction", "confidence" }
"""

import os
import joblib
import nltk
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from utils import preprocess_text

# ---------------------------------------------------------------------------
# Setup
# ---------------------------------------------------------------------------

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
MODEL_PATH = os.path.join(BASE_DIR, "model.pkl")
VECTORIZER_PATH = os.path.join(BASE_DIR, "vectorizer.pkl")

app = FastAPI(
    title="Sentiment Analysis API",
    description="Predicts whether a piece of text is Positive, Neutral, or Negative.",
    version="1.0.0",
)

# Allow the frontend (served from a different origin/port) to call the API.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],          # tighten this to your deployed frontend URL in production
    allow_methods=["*"],
    allow_headers=["*"],
)

# Lazily-initialised globals
model = None
vectorizer = None
stop_words = None
lemmatizer = None


@app.on_event("startup")
def load_artifacts():
    """Load the trained model + vectorizer once, at process startup."""
    global model, vectorizer, stop_words, lemmatizer

    if not (os.path.exists(MODEL_PATH) and os.path.exists(VECTORIZER_PATH)):
        # Don't crash the server if artifacts aren't there yet -- /predict
        # will return a clear error instead. This lets you boot the API
        # before you've finished Phase 6-8.
        print("⚠️  model.pkl / vectorizer.pkl not found. Train the model first (see training/train_model.ipynb).")
        return

    model = joblib.load(MODEL_PATH)
    vectorizer = joblib.load(VECTORIZER_PATH)

    try:
        nltk.data.find("corpora/stopwords")
    except LookupError:
        nltk.download("stopwords")
    try:
        nltk.data.find("corpora/wordnet")
    except LookupError:
        nltk.download("wordnet")

    from nltk.corpus import stopwords as nltk_stopwords
    from nltk.stem import WordNetLemmatizer

    stop_words = set(nltk_stopwords.words("english"))
    lemmatizer = WordNetLemmatizer()
    print("✅ Model and vectorizer loaded.")


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------

class PredictRequest(BaseModel):
    text: str = Field(..., min_length=1, max_length=2000, example="I love this internship!")


class PredictResponse(BaseModel):
    text: str
    prediction: str
    confidence: float | None = None


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@app.get("/")
def health_check():
    return {
        "status": "ok",
        "model_loaded": model is not None,
    }


@app.post("/predict", response_model=PredictResponse)
def predict(payload: PredictRequest):
    if model is None or vectorizer is None:
        raise HTTPException(
            status_code=503,
            detail="Model not loaded. Train it first and place model.pkl / vectorizer.pkl in backend/.",
        )

    text = payload.text.strip()
    if not text:
        raise HTTPException(status_code=400, detail="Text must not be empty.")

    processed = preprocess_text(text, stopwords=stop_words, lemmatizer=lemmatizer)
    vector = vectorizer.transform([processed])

    label = model.predict(vector)[0]

    confidence = None
    if hasattr(model, "predict_proba"):
        proba = model.predict_proba(vector)[0]
        confidence = float(max(proba))

    return PredictResponse(text=payload.text, prediction=str(label), confidence=confidence)

"""
utils.py
Shared text-cleaning helpers used by both the training notebook and the
FastAPI backend, so preprocessing is guaranteed to match at train and
inference time.
"""

import re
import string


def clean_text(text: str) -> str:
    """
    Lowercase, strip URLs/punctuation/numbers/extra whitespace.
    This mirrors Phase 3 (Data Cleaning) of the project workflow.
    """
    if not isinstance(text, str):
        return ""

    text = text.lower()
    text = re.sub(r"http\S+|www\.\S+", " ", text)          # URLs
    text = re.sub(r"[^a-z\s]", " ", text)                    # punctuation/numbers
    text = re.sub(r"\s+", " ", text).strip()                 # extra whitespace
    return text


def preprocess_text(text: str, stopwords: set | None = None, lemmatizer=None) -> str:
    """
    Tokenize + remove stopwords + lemmatize (Phase 4 - Text Preprocessing).
    stopwords / lemmatizer are injected so this file has no hard NLTK
    dependency at import time (keeps the API fast to boot).
    """
    cleaned = clean_text(text)
    tokens = cleaned.split()

    if stopwords:
        tokens = [t for t in tokens if t not in stopwords]

    if lemmatizer:
        tokens = [lemmatizer.lemmatize(t) for t in tokens]

    return " ".join(tokens)

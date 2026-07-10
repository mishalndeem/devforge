# Dataset

Place your labeled dataset here as `sentiment.csv` with two columns:

| column | description                                  |
|--------|-----------------------------------------------|
| text   | the raw sentence/review/tweet                 |
| label  | one of `Positive`, `Neutral`, `Negative`       |

Good free sources:
- **Kaggle: Twitter US Airline Sentiment** — already 3-class labeled.
- **Sentiment140** — 1.6M tweets, labeled 0/2/4 (map to Negative/Neutral/Positive).
- **IMDB Reviews** — binary (Positive/Negative) only, good if you drop the Neutral class.

If `sentiment.csv` is missing, `training/train_model.ipynb` will auto-generate a tiny
synthetic sample so the notebook still runs end-to-end — replace it before training
a model you actually deploy.

// script.js — connects the UI to the FastAPI /predict endpoint (Phase 11)

const API_BASE = "http://localhost:8000";

const textInput = document.getElementById("textInput");
const charCount = document.getElementById("charCount");
const analyzeBtn = document.getElementById("analyzeBtn");
const tracePath = document.getElementById("tracePath");
const result = document.getElementById("result");
const resultEmoji = document.getElementById("resultEmoji");
const resultLabel = document.getElementById("resultLabel");
const resultConfidence = document.getElementById("resultConfidence");
const errorBox = document.getElementById("errorBox");
const apiTarget = document.getElementById("apiTarget");

apiTarget.textContent = `${API_BASE}/predict`;

const EMOJI = { Positive: "😊", Neutral: "😐", Negative: "😞" };

textInput.addEventListener("input", () => {
  charCount.textContent = textInput.value.length;
});

textInput.addEventListener("keydown", (e) => {
  if (e.key === "Enter" && !e.shiftKey) {
    e.preventDefault();
    analyze();
  }
});

analyzeBtn.addEventListener("click", analyze);

async function analyze() {
  const text = textInput.value.trim();

  hideError();

  if (!text) {
    showError("Type something first — an empty sentence has no sentiment to read.");
    return;
  }

  setLoading(true);
  result.hidden = true;

  try {
    const response = await fetch(`${API_BASE}/predict`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ text }),
    });

    if (!response.ok) {
      const body = await response.json().catch(() => ({}));
      throw new Error(body.detail || `Request failed (${response.status})`);
    }

    const data = await response.json();
    renderResult(data);
  } catch (err) {
    showError(
      err.message.includes("fetch")
        ? "Can't reach the API. Is the FastAPI backend running on " + API_BASE + "?"
        : err.message
    );
  } finally {
    setLoading(false);
  }
}

function renderResult(data) {
  const label = normalizeLabel(data.prediction);

  resultEmoji.textContent = EMOJI[label] || "🤔";
  resultLabel.textContent = label;
  resultConfidence.textContent =
    typeof data.confidence === "number"
      ? `${(data.confidence * 100).toFixed(1)}% confidence`
      : "confidence n/a";

  drawTrace(label);
  result.hidden = false;
}

function normalizeLabel(raw) {
  const s = String(raw).toLowerCase();
  if (s.includes("pos")) return "Positive";
  if (s.includes("neg")) return "Negative";
  return "Neutral";
}

function drawTrace(label) {
  tracePath.classList.remove("positive", "negative", "neutral");

  let d;
  if (label === "Positive") {
    d = "M0,60 C120,60 140,15 220,15 C300,15 320,60 400,60 C480,60 500,10 580,10 C610,10 620,30 640,30";
    tracePath.classList.add("positive");
  } else if (label === "Negative") {
    d = "M0,60 C120,60 140,105 220,105 C300,105 320,60 400,60 C480,60 500,110 580,110 C610,110 620,90 640,90";
    tracePath.classList.add("negative");
  } else {
    d = "M0,60 C160,60 180,50 320,50 C460,50 480,70 640,60";
    tracePath.classList.add("neutral");
  }
  tracePath.setAttribute("d", d);
}

function setLoading(isLoading) {
  analyzeBtn.disabled = isLoading;
  analyzeBtn.classList.toggle("loading", isLoading);
}

function showError(message) {
  errorBox.textContent = message;
  errorBox.hidden = false;
}

function hideError() {
  errorBox.hidden = true;
}

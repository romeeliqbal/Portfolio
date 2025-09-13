import re
from typing import Tuple

try:
    from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
except Exception as import_error:
    raise SystemExit(
        "vaderSentiment is not installed. Run: pip install vaderSentiment"
    ) from import_error


_DEFAULT_ANALYZER: SentimentIntensityAnalyzer | None = None


def get_analyzer() -> SentimentIntensityAnalyzer:
    global _DEFAULT_ANALYZER
    if _DEFAULT_ANALYZER is None:
        _DEFAULT_ANALYZER = SentimentIntensityAnalyzer()
    return _DEFAULT_ANALYZER


def normalize_text(user_text: str | None) -> str:
    if user_text is None:
        return ""
    lowered = user_text.lower()
    collapsed = re.sub(r"\s+", " ", lowered).strip()
    return collapsed


def classify_sentiment(clean_text: str, analyzer: SentimentIntensityAnalyzer | None = None) -> Tuple[str, float]:
    if analyzer is None:
        analyzer = get_analyzer()
    scores = analyzer.polarity_scores(clean_text)
    compound = float(scores.get("compound", 0.0))
    if compound >= 0.05:
        label = "Positive"
    elif compound <= -0.05:
        label = "Negative"
    else:
        label = "Neutral"
    return label, compound


def describe_sentiment(label: str, score: float) -> str:
    magnitude = abs(score)
    if magnitude >= 0.75:
        intensity = "very strong"
    elif magnitude >= 0.4:
        intensity = "moderate"
    elif magnitude >= 0.15:
        intensity = "mild"
    else:
        intensity = "very mild"

    if label == "Positive":
        return f"Detected {intensity} positive sentiment."
    if label == "Negative":
        return f"Detected {intensity} negative sentiment."
    return "Detected neutral sentiment."


def format_score(score: float) -> str:
    return f"{score:+.2f}"


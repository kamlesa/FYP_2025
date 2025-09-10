# ------------------------------------------------------------
# survey_pipeline.py
# End-to-end processor for survey written responses:
# - Cleans text
# - Sentiment via DeepSeek LLM (fallback stub if no API key)
# - Keyword extraction via KeyBERT
# - TF-IDF (global + per-question)
# - Maps keywords to ethical concern categories
# - Exports annotated rows + summaries
#
# Requires:
#   requirements.txt (pandas, scikit-learn, nltk, keybert, sentence-transformers,
#                     tqdm, requests, python-dotenv, torch)
#   .env with:
#       DEEPSEEK_API_KEY=REDACTED
#       DEEPSEEK_ENDPOINT=https://api.deepseek.com/chat/completions
#       DEEPSEEK_MODEL=deepseek-chat
# ------------------------------------------------------------

import os
import re
import time
import json
import requests
import pandas as pd

from tqdm import tqdm
from dotenv import load_dotenv

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.feature_extraction import text as sk_text

from keybert import KeyBERT
from sentence_transformers import SentenceTransformer

import nltk
from nltk.corpus import stopwords


# ---------------------------
# ENV / SETUP
# ---------------------------
load_dotenv()

# Ensure NLTK data exists (first run will download)
try:
    _ = stopwords.words("english")
except LookupError:
    nltk.download("stopwords")
    nltk.download("punkt")


# ---------------------------
# CONFIG — EDIT THESE TO MATCH YOUR SURVEY
# ---------------------------

# CSV exported from your survey tool
INPUT_CSV = "survey_export.csv"         # <- change to your filename if needed
OUTPUT_PREFIX = "out"                   # files will be out_*.csv

# List ALL open-ended (written) question columns EXACTLY as they appear in the CSV
# For the minimal mock CSV we built earlier:
OPEN_ENDED_COLS = ["Q9_Open", "Q10_Open", "Q11_Open"]

# Optional: keep these structured fields (if they exist) for dashboards/analysis
# You can leave this list empty; the script will only keep columns that actually exist.
PRESERVE_COLS = [
    # Examples (uncomment or add if present in your CSV):
    # "Age_Band", "Gender", "Platform_Main",
    # "Overall_Sentiment_Scale", "Trust_Scale", "Seen_Discussion_Freq",
    # "Timestamp"
]

# DeepSeek (LLM) options
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY")
DEEPSEEK_ENDPOINT = os.getenv("DEEPSEEK_ENDPOINT", "https://api.deepseek.com/chat/completions")
DEEPSEEK_MODEL = os.getenv("DEEPSEEK_MODEL", "deepseek-chat")
DEEPSEEK_TEMPERATURE = 0.0

# Throttle LLM calls (avoid rate limits)
SLEEP_BETWEEN_CALLS = 1.0     # seconds
MAX_RETRIES = 3
TIMEOUT = 30

# Ethical concern taxonomy (expand as needed)
CONCERN_LEXICON = {
    "privacy":        ["privacy", "surveillance", "tracking", "mass surveillance", "data collection"],
    "bias":           ["bias", "discrimination", "fairness", "racial profiling", "inequity", "unfair"],
    "transparency":   ["transparency", "transparent", "explainable", "explainability", "opaque", "black box", "explanation"],
    "accountability": ["accountability", "oversight", "appeal", "redress", "governance", "audit"],
    "data_misuse":    ["misuse", "data breach", "leak", "unauthorised access", "security", "hacked"],
    "accessibility":  ["accessibility", "accessible", "usable", "usability", "readable", "inclusive", "screen reader"]
}

# TF-IDF sizes
TOP_K_TFIDF_GLOBAL = 40
TOP_K_TFIDF_PER_Q = 20
TOP_K_KEYBERT = 6


# ---------------------------
# TEXT UTILS
# ---------------------------
EN_STOP = set(stopwords.words("english")) | sk_text.ENGLISH_STOP_WORDS

def clean_text(s: str) -> str:
    """Basic normalization for short survey answers."""
    if not isinstance(s, str):
        return ""
    s = s.strip()
    s = re.sub(r"http\S+|www\.\S+", " ", s)
    s = re.sub(r"[@#]\w+", " ", s)             # remove @handles / #hashtags
    s = re.sub(r"[^A-Za-z0-9\s']", " ", s)     # keep letters, numbers, apostrophes
    s = re.sub(r"\s+", " ", s)
    return s.lower().strip()


# ---------------------------
# LLM: DEEPSEEK SENTIMENT
# ---------------------------
SENTIMENT_SYS = (
    "You are a precise sentiment classifier. "
    "Classify the user's short text about AI in law enforcement as one of: NEGATIVE, NEUTRAL, or POSITIVE. "
    "Return strict JSON with keys: label (NEGATIVE/NEUTRAL/POSITIVE) and confidence (0-1). No explanations."
)

def deepseek_sentiment(text: str):
    """Calls DeepSeek chat API to classify sentiment; returns (label, confidence)."""
    if not text or not text.strip():
        return "NEUTRAL", 0.0

    headers = {
        "Authorization": f"Bearer {DEEPSEEK_API_KEY}",
        "Content-Type": "application/json"
    }
    payload = {
        "model": DEEPSEEK_MODEL,
        "messages": [
            {"role": "system", "content": SENTIMENT_SYS},
            {"role": "user", "content": text}
        ],
        "temperature": DEEPSEEK_TEMPERATURE
    }

    for _ in range(MAX_RETRIES):
        try:
            r = requests.post(DEEPSEEK_ENDPOINT, headers=headers, json=payload, timeout=TIMEOUT)
            r.raise_for_status()
            msg = r.json()["choices"][0]["message"]["content"]
            data = json.loads(msg)
            label = str(data.get("label", "NEUTRAL")).upper()
            conf = float(data.get("confidence", 0.0))
            if label not in {"NEGATIVE", "NEUTRAL", "POSITIVE"}:
                label = "NEUTRAL"
            return label, conf
        except Exception:
            time.sleep(SLEEP_BETWEEN_CALLS)
    return "NEUTRAL", 0.0


# ---------------------------
# TF-IDF
# ---------------------------
def tfidf_top(texts, k=20):
    if not texts:
        return []
    vect = TfidfVectorizer(stop_words=EN_STOP, max_features=5000, ngram_range=(1,2))
    X = vect.fit_transform(texts)
    terms = vect.get_feature_names_out()
    scores = X.max(axis=0).A1
    top_idx = scores.argsort()[::-1][:k]
    return [(terms[i], float(scores[i])) for i in top_idx]


# ---------------------------
# KEYBERT
# ---------------------------
_kw_model = None
def kw_model():
    global _kw_model
    if _kw_model is None:
        sbert = SentenceTransformer("all-MiniLM-L6-v2")  # small & fast; swap to 'all-mpnet-base-v2' for higher quality
        _kw_model = KeyBERT(model=sbert)
    return _kw_model

def keybert_extract(text, top_n=TOP_K_KEYBERT):
    if not text.strip():
        return []
    model = kw_model()
    kws = model.extract_keywords(
        text,
        keyphrase_ngram_range=(1,2),
        stop_words=EN_STOP,
        use_mmr=True,
        diversity=0.6,
        top_n=top_n
    )
    return [(k, float(s)) for k, s in kws]


# ---------------------------
# MAP KEYWORDS -> CONCERNS
# ---------------------------
def map_concerns_from_keywords(keywords):
    """keywords can be list[str] or list[(kw,score)] -> returns dict concern->count"""
    if keywords and isinstance(keywords[0], tuple):
        words = [k for k, _ in keywords]
    else:
        words = keywords or []
    hay = " " + " ".join(words).lower() + " "
    hits = {c:0 for c in CONCERN_LEXICON}
    for concern, lex in CONCERN_LEXICON.items():
        for term in lex:
            if f" {term.lower()} " in hay:
                hits[concern] += 1
    return {k:v for k,v in hits.items() if v>0}


# ---------------------------
# MAIN
# ---------------------------
def main():
    # 1) Load
    df = pd.read_csv(INPUT_CSV)
    raw_cols = df.columns.tolist()

    # 2) Validate open-ended columns exist
    missing = [c for c in OPEN_ENDED_COLS if c not in df.columns]
    if missing:
        raise ValueError(
            f"These OPEN_ENDED_COLS are missing in the CSV: {missing}\n"
            f"Found columns: {raw_cols}\n"
            f"Edit OPEN_ENDED_COLS in the script to match your survey export."
        )

    # 3) Clean open-ended text, create combined 'text_all'
    for c in OPEN_ENDED_COLS:
        df[c + "_clean"] = df[c].fillna("").astype(str).apply(clean_text)
    df["text_all"] = df[[c + "_clean" for c in OPEN_ENDED_COLS]].agg(" ".join, axis=1).str.strip()

    # 4) Preserve chosen structured fields if present
    keep_cols = [c for c in PRESERVE_COLS if c in df.columns]

    # 5) Sentiment per question + combined (fallback if no API key)
    if not DEEPSEEK_API_KEY:
        print("WARNING: DEEPSEEK_API_KEY not set. Using simple placeholder labels (still end-to-end testable).")
    for c in OPEN_ENDED_COLS + ["text_all"]:
        labels, confs = [], []
        iterator = tqdm(df[c + "_clean"], desc=f"Sentiment: {c}")
        for txt in iterator:
            if DEEPSEEK_API_KEY:
                lab, con = deepseek_sentiment(txt)
                time.sleep(SLEEP_BETWEEN_CALLS)
            else:
                # very simple stub so you can test pipeline w/o an API key
                lab = "NEGATIVE" if any(k in txt for k in ["privacy","bias","surveillance","unfair","accountability"]) else "NEUTRAL"
                con = 0.55
            labels.append(lab); confs.append(con)
        df[c + "_sentiment"] = labels
        df[c + "_sent_conf"] = confs

    # 6) KeyBERT per question + combined + concern mapping
    for c in OPEN_ENDED_COLS + ["text_all"]:
        kwords = []
        chits = []
        iterator = tqdm(df[c + "_clean"], desc=f"KeyBERT: {c}")
        for txt in iterator:
            kws = keybert_extract(txt, top_n=TOP_K_KEYBERT)
            kwords.append(kws)
            chits.append(map_concerns_from_keywords(kws))
        df[c + "_keybert"] = kwords
        df[c + "_concerns"] = chits

    # 7) TF-IDF: global + per question
    tfidf_global = tfidf_top(df["text_all"].tolist(), k=TOP_K_TFIDF_GLOBAL)
    pd.DataFrame(tfidf_global, columns=["term","tfidf_score"]).to_csv(f"{OUTPUT_PREFIX}_tfidf_global.csv", index=False)

    perq_frames = []
    for c in OPEN_ENDED_COLS:
        tlist = df[c + "_clean"].tolist()
        tops = tfidf_top(tlist, k=TOP_K_TFIDF_PER_Q)
        tdf = pd.DataFrame(tops, columns=["term","tfidf_score"])
        tdf.insert(0, "question", c)
        perq_frames.append(tdf)
    if perq_frames:
        pd.concat(perq_frames, ignore_index=True).to_csv(f"{OUTPUT_PREFIX}_tfidf_per_question.csv", index=False)

    # 8) Aggregate concern frequencies (combined)
    agg_counts = {}
    for d in df["text_all_concerns"]:
        for k, v in d.items():
            agg_counts[k] = agg_counts.get(k, 0) + v
    pd.DataFrame(
        sorted(agg_counts.items(), key=lambda x: x[1], reverse=True),
        columns=["concern","hits"]
    ).to_csv(f"{OUTPUT_PREFIX}_concerns_frequency.csv", index=False)

    # 9) Save annotated rows (dashboard-ready)
    out_cols = keep_cols + \
               [col for col in df.columns if col.endswith("_clean") or col.endswith("_sentiment") or
                col.endswith("_sent_conf") or col.endswith("_keybert") or col.endswith("_concerns")] + \
               ["text_all"]
    # de-dupe while preserving order
    out_cols = list(dict.fromkeys(out_cols))
    df[out_cols].to_csv(f"{OUTPUT_PREFIX}_annotated_rows.csv", index=False)

    print(f"\nSaved files:"
          f"\n- {OUTPUT_PREFIX}_annotated_rows.csv"
          f"\n- {OUTPUT_PREFIX}_tfidf_global.csv"
          f"\n- {OUTPUT_PREFIX}_tfidf_per_question.csv"
          f"\n- {OUTPUT_PREFIX}_concerns_frequency.csv")


if __name__ == "__main__":
    main()

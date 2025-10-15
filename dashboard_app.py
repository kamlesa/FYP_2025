#dashboard_app.py
#Written by Marcus Wei

#importing necessary libraries 
import json
import re
from pathlib import Path

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

st.set_page_config("AI in Law Enforcement – Survey Dashboard", layout="wide")

# ---------- Helpers ----------
DATA_DIR = Path(".")  # change if your files live elsewhere

def safe_read_csv(name: str) -> pd.DataFrame | None:
    p = (DATA_DIR / name)
    if p.exists():
        try:
            return pd.read_csv(p)
        except Exception as e:
            st.warning(f"Could not read {name}: {e}")
    return None

def safe_read_json(name: str) -> dict | None:
    p = (DATA_DIR / name)
    if p.exists():
        try:
            with open(p, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            st.warning(f"Could not read {name}: {e}")
    return None

def extract_keywords_cell(cell):
    """Return list of keywords from a cell that may contain a list/JSON-string of (kw, score)."""
    if isinstance(cell, list):
        pairs = cell
    else:
        s = str(cell)
        try:
            pairs = json.loads(s.replace("'", '"'))
        except Exception:
            pairs = []
    out = []
    for item in pairs:
        if isinstance(item, (list, tuple)) and item:
            out.append(str(item[0]))
        elif isinstance(item, str):
            out.append(item)
    return out

def find_cols(df: pd.DataFrame, suffix: str):
    return [c for c in df.columns if c.endswith(suffix)]

# ---------- Load data ----------
df_rows = safe_read_csv("out_annotated_rows.csv")
df_tfidf_global = safe_read_csv("out_tfidf_global.csv")
df_tfidf_perq = safe_read_csv("out_tfidf_per_question.csv")
df_concerns_freq = safe_read_csv("out_concerns_frequency.csv")

spider = safe_read_json("spiderchart.json") or {}
key_data = safe_read_json("key_data.json") or {}

# ---------- Sidebar ----------
st.sidebar.header("Data Sources")
st.sidebar.caption("Files are expected in this folder:")
st.sidebar.code(str(DATA_DIR.resolve()))

ok_files = {
    "out_annotated_rows.csv": df_rows is not None,
    "out_tfidf_global.csv": df_tfidf_global is not None,
    "out_tfidf_per_question.csv": df_tfidf_perq is not None,
    "out_concerns_frequency.csv": df_concerns_freq is not None,
    "spiderchart.json": bool(spider),
    "key_data.json": bool(key_data),
}
for k, v in ok_files.items():
    st.sidebar.write(("✅" if v else "❌"), k)

st.sidebar.divider()
download_ready = df_rows is not None

# ---------- Title ----------
st.title("Public Sentiment & Ethics in AI for Law Enforcement – Survey Dashboard")
st.caption("Interactive view of sentiment, ethical concerns, keywords and TF-IDF summaries from your pipeline.")

# ---------- Tabs ----------
tab_overview, tab_concerns, tab_tfidf, tab_responses = st.tabs(
    ["Overview", "Concerns", "TF-IDF", "Responses"]
)

# ---------- Overview ----------
with tab_overview:
    c1, c2 = st.columns([1.1, 1])
    with c1:
        st.subheader("Ethical Concerns – Radar")
        if spider:
            labels = list(spider.keys())
            values = [spider[k] for k in labels]
            # close the loop for radar
            labels_closed = labels + [labels[0]]
            values_closed = values + [values[0]]

            fig = go.Figure(
                data=go.Scatterpolar(r=values_closed, theta=labels_closed, fill="toself", name="Concerns")
            )
            fig.update_layout(polar=dict(radialaxis=dict(visible=True)), showlegend=False, height=450)
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("spiderchart.json not found. Run build_json_outputs.py to generate it.")

    with c2:
        st.subheader("Concern Frequency")
        if df_concerns_freq is not None and not df_concerns_freq.empty:
            df_plot = df_concerns_freq.sort_values("hits", ascending=False)
            st.bar_chart(df_plot.set_index("concern")["hits"])
        else:
            st.info("out_concerns_frequency.csv not found.")

    st.subheader("Sentiment Distribution")
    if df_rows is not None and "text_all_sentiment" in df_rows.columns:
        counts = df_rows["text_all_sentiment"].value_counts(dropna=False).rename_axis("sentiment").reset_index(name="count")
        fig = px.pie(counts, names="sentiment", values="count", hole=0.45)
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("Sentiment column not found in out_annotated_rows.csv.")

# ---------- Concerns ----------
with tab_concerns:
    st.subheader("Explore a Concern")
    all_concerns = sorted(set(list(spider.keys()) + list(key_data.keys())))
    if not all_concerns:
        st.info("No concerns available. Ensure spiderchart.json and key_data.json are present.")
    else:
        sel = st.selectbox("Concern", all_concerns, index=0)
        c1, c2 = st.columns([1, 1])
        with c1:
            val = spider.get(sel, None)
            if val is not None:
                st.metric("Radar Score", f"{val:.2f}" if isinstance(val, float) else int(val))
        with c2:
            if df_concerns_freq is not None and not df_concerns_freq.empty:
                row = df_concerns_freq[df_concerns_freq["concern"] == sel]
                if not row.empty:
                    st.metric("Frequency (hits)", int(row["hits"].iloc[0]))

        st.markdown("**Representative responses**")
        examples = key_data.get(sel, [])[:200]
        if not examples:
            st.info("No responses recorded for this concern.")
        else:
            for i, ex in enumerate(examples[:50], 1):
                st.write(f"{i}. {ex}")

# ---------- TF-IDF ----------
with tab_tfidf:
    c1, c2 = st.columns(2)
    with c1:
        st.subheader("Global Top Terms")
        if df_tfidf_global is not None and not df_tfidf_global.empty:
            top_n = st.slider("Show top N terms", 5, min(50, len(df_tfidf_global)), 20)
            df_plot = df_tfidf_global.head(top_n)
            fig = px.bar(df_plot, x="term", y="tfidf_score")
            fig.update_layout(height=400)
            st.plotly_chart(fig, use_container_width=True)
            st.dataframe(df_tfidf_global, use_container_width=True, height=280)
        else:
            st.info("out_tfidf_global.csv not found.")

    with c2:
        st.subheader("Top Terms by Question")
        if df_tfidf_perq is not None and not df_tfidf_perq.empty:
            questions = df_tfidf_perq["question"].dropna().unique().tolist()
            q = st.selectbox("Question", questions, index=0)
            top_n_q = st.slider("Show top N per question", 5, 50, 20, key="tfidf_q_slider")
            subset = df_tfidf_perq[df_tfidf_perq["question"] == q].head(top_n_q)
            fig2 = px.bar(subset, x="term", y="tfidf_score")
            fig2.update_layout(height=400)
            st.plotly_chart(fig2, use_container_width=True)
            st.dataframe(df_tfidf_perq[df_tfidf_perq["question"] == q], use_container_width=True, height=280)
        else:
            st.info("out_tfidf_per_question.csv not found.")

# ---------- Responses (row-level) ----------
with tab_responses:
    st.subheader("Filter & Inspect Responses")

    if df_rows is None or df_rows.empty:
        st.info("out_annotated_rows.csv not found.")
    else:
        # basic filters
        sentiments = ["(any)"] + sorted([c for c in df_rows.get("text_all_sentiment", pd.Series()).dropna().unique().tolist()])
        sentiment_sel = st.selectbox("Sentiment", sentiments, index=0)

        # extract all concern keys present in *_concerns
        concern_candidates = set()
        concern_cols = find_cols(df_rows, "_concerns")
        for col in concern_cols:
            for _, cell in df_rows[col].items():
                try:
                    d = json.loads(str(cell).replace("'", '"'))
                    if isinstance(d, dict):
                        concern_candidates.update(d.keys())
                except Exception:
                    pass
        concerns = ["(any)"] + sorted(list(concern_candidates))
        concern_sel = st.selectbox("Concern", concerns, index=0)

        keyword_query = st.text_input("Search in cleaned text (contains)")

        # build mask
        mask = pd.Series([True] * len(df_rows))
        if sentiment_sel != "(any)" and "text_all_sentiment" in df_rows.columns:
            mask &= df_rows["text_all_sentiment"].astype(str) == sentiment_sel

        if concern_sel != "(any)" and concern_cols:
            def has_concern(cell):
                try:
                    d = json.loads(str(cell).replace("'", '"'))
                    return d.get(concern_sel, 0) > 0
                except Exception:
                    return False
            any_concern = pd.Series([False] * len(df_rows))
            for col in concern_cols:
                any_concern |= df_rows[col].apply(has_concern)
            mask &= any_concern

        if keyword_query:
            clean_cols = find_cols(df_rows, "_clean")
            if clean_cols:
                any_hit = pd.Series([False] * len(df_rows))
                for col in clean_cols:
                    any_hit |= df_rows[col].astype(str).str.contains(re.escape(keyword_query), case=False, na=False)
                mask &= any_hit

        sub = df_rows[mask].copy()

        st.write(f"**{len(sub)}** responses match filters.")
        display_cols = ["text_all"] + [c for c in df_rows.columns if c.endswith("_sentiment") or c.endswith("_concerns")]
        display_cols = [c for c in dict.fromkeys([c for c in display_cols if c in sub.columns])]  # de-dup keep order
        st.dataframe(sub[display_cols], use_container_width=True, height=420)

        # quick aggregate of extracted keywords from text_all_keybert if present
        if "text_all_keybert" in sub.columns:
            st.markdown("**Top Extracted Keywords (filtered set)**")
            all_kws = []
            for cell in sub["text_all_keybert"]:
                all_kws.extend(extract_keywords_cell(cell))
            if all_kws:
                top = pd.Series(all_kws).value_counts().head(25).reset_index()
                top.columns = ["keyword", "count"]
                st.bar_chart(top.set_index("keyword")["count"])

        st.download_button(
            "Download filtered rows (CSV)",
            data=sub.to_csv(index=False).encode("utf-8"),
            file_name="filtered_responses.csv",
            mime="text/csv",
        )

# ---------- Footer ----------
st.caption("Dashboard generated from survey_pipeline.py outputs. Use build_json_outputs.py to refresh spider/key data.")

import argparse, json, re
from collections import Counter, defaultdict
import pandas as pd

# ---- weights for optional sentiment-weighted spider chart
NEG_W, NEU_W, POS_W = 1.0, 0.6, 0.3

def _coerce_dict(x):
    """Safely parse a dict-ish cell from CSV into a Python dict[str,int]."""
    if isinstance(x, dict): return x
    if pd.isna(x) or x is None: return {}
    s = str(x).strip()
    if not s: return {}
    try:
        # handle python-literal style dicts from CSV by normalizing quotes
        return json.loads(s.replace("'", '"'))
    except Exception:
        # super defensive: parse key: int pairs
        out = {}
        for k, v in re.findall(r"'?([A-Za-z0-9_]+)'?\s*:\s*([0-9]+)", s):
            out[k] = int(v)
        return out

def _find_first(df, suffix):
    cols = [c for c in df.columns if c.endswith(suffix)]
    return cols[0] if cols else None

def _sentiment_weight(lbl):
    u = str(lbl).upper()
    if u == "NEGATIVE": return NEG_W
    if u == "POSITIVE": return POS_W
    return NEU_W

def main():
    ap = argparse.ArgumentParser(description="Emit spider-chart JSON and key→responses JSON from annotated CSV.")
    ap.add_argument("--input", required=True, help="Path to out_annotated_rows.csv")
    ap.add_argument("--spider-out", default="spiderchart.json", help="Filename for spider chart JSON")
    ap.add_argument("--keydata-out", default="key_data.json", help="Filename for key→responses JSON")
    ap.add_argument("--mode", choices=["mentions", "weighted"], default="mentions",
                    help="Spider values: raw concern mentions or sentiment-weighted scores")
    ap.add_argument("--limit-per-key", type=int, default=200,
                    help="Max number of responses to keep per key in key_data.json (default 200)")
    args = ap.parse_args()

    df = pd.read_csv(args.input)

    # --- choose concerns column(s)
    text_all_concerns_col = _find_first(df, "text_all_concerns")
    if text_all_concerns_col:
        concerns_series = df[text_all_concerns_col].apply(_coerce_dict)
    else:
        # merge any *_concerns columns row-wise
        ccols = [c for c in df.columns if c.endswith("_concerns")]
        if not ccols:
            raise SystemExit("No *_concerns columns found. Did you run the pipeline?")
        merged = []
        for _, row in df[ccols].iterrows():
            agg = Counter()
            for c in ccols:
                agg.update(_coerce_dict(row[c]))
            merged.append(dict(agg))
        concerns_series = pd.Series(merged, index=df.index)

    # --- sentiment weights (for weighted mode)
    sent_all = _find_first(df, "text_all_sentiment")
    if sent_all:
        weights = df[sent_all].apply(_sentiment_weight)
    else:
        scols = [c for c in df.columns if c.endswith("_sentiment")]
        if scols:
            weights = df[scols].apply(lambda r: sum(_sentiment_weight(v) for v in r) / max(1, len(scols)), axis=1)
        else:
            weights = pd.Series([NEU_W] * len(df))

    # --- pick a text column for "actual responses"
    text_col = _find_first(df, "text_all_clean") or _find_first(df, "text_all")
    if not text_col:
        # fall back to the first *_clean column
        clean_cols = [c for c in df.columns if c.endswith("_clean")]
        text_col = clean_cols[0] if clean_cols else None

    # --- build aggregates
    spider = Counter()
    key_to_responses = defaultdict(list)

    for i, row_concerns in concerns_series.items():
        if not isinstance(row_concerns, dict): continue
        w = weights.iloc[i]
        for key, hits in row_concerns.items():
            if hits <= 0: continue
            if args.mode == "weighted":
                spider[key] += hits * w
            else:
                spider[key] += hits
            # collect the actual response text for the key
            if text_col and len(key_to_responses[key]) < args.limit_per_key:
                txt = str(df.at[i, text_col]).strip()
                if txt:
                    key_to_responses[key].append(txt)

    # --- serialize
    # spiderchart: simple key→value mapping (floats safe for weighted)
    spider_dict = {k: (float(v) if args.mode == "weighted" else int(v))
                   for k, v in sorted(spider.items(), key=lambda kv: (-kv[1], kv[0]))}

    with open(args.spider_out, "w", encoding="utf-8") as f:
        json.dump(spider_dict, f, ensure_ascii=False, indent=2)

    # key_data: key→list of responses
    with open(args.keydata_out, "w", encoding="utf-8") as f:
        json.dump(key_to_responses, f, ensure_ascii=False, indent=2)

    print("Saved:")
    print(f"- {args.spider_out}")
    print(f"- {args.keydata_out}")

if __name__ == "__main__":
    main()
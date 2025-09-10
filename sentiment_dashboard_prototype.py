"""
YouTube data processor

Requires: selenium, vaderSentiment, requests, tqdm (pip install selenium vaderSentiment requests tqdm)

Requires: ChromeDriver + YCS extension paths to be configured

Usage: python sentiment_dashboard_prototype.py <URL 1> [<URL 2> ... etc]

If no arguments are given, a small demo set inside the script is used.
"""
from __future__ import annotations
import os, re, json, sys, concurrent.futures, requests, textwrap
from pathlib import Path
from typing import Optional
from urllib.parse import urlparse, parse_qs
from typing import Literal, NamedTuple

# Username data scraping toggle
# Set to False by default
usernameToggle: bool = False

# Path Configuration

BASE_DIR            = Path(__file__).resolve().parent
CHROMEDRIVER_PATH   = BASE_DIR / "chromedriver-win64" / "chromedriver.exe"
YCS_EXTENSION_PATH  = BASE_DIR / "chrome-extension-files"
TIMEOUT_REACHABLE   = 10        # seconds
POOL_WORKERS        = os.cpu_count() or 4

# Fixing URL information before it is processed

def normalize_url(url: str) -> str | None:
    url = url.strip()
    if not url:
        return None
    p = urlparse(url)
    host = p.netloc.lower()
    path = p.path.lstrip("/")
    vid = ""
    if host == "youtu.be":
        vid = path.split("?")[0]
    elif "youtube.com" in host:
        if path.startswith("watch"):
            vid = parse_qs(p.query).get("v", [""])[0]
        elif path.startswith("shorts/"):
            vid = path.split("/")[1]
        else:
            return None
    if re.fullmatch(r"[A-Za-z0-9_-]{11}", vid):
        return f"https://www.youtube.com/watch?v={vid}"
    return None


def is_url_reachable(url: str) -> bool:
    try:
        return requests.get(url, timeout=TIMEOUT_REACHABLE).status_code == 200
    except requests.RequestException:
        return False


# Using Selenium to scrape and parse data accordingly

from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver import ActionChains

def make_driver() -> webdriver.Chrome:
    opt = webdriver.ChromeOptions()
    opt.add_argument("--start-maximized")
    for arg in ("--disable-gpu", "--no-sandbox", "--disable-dev-shm-usage"):
        opt.add_argument(arg)
    opt.add_experimental_option("excludeSwitches", ["enable-logging"])
    opt.add_argument(f"--load-extension={YCS_EXTENSION_PATH}")
    return webdriver.Chrome(service=Service(str(CHROMEDRIVER_PATH)), options=opt)


# Parse and categorize extension text data into top-level comment and their replies

def _parse_head(arr: list[str], idx: int) -> tuple[dict, int]:
    """Parse the raw data before processing them into parent comments and replies."""
    d = {
        "username":    arr[idx + 1] if usernameToggle else "",
        "profile_url": arr[idx + 2],
        "comment_url": arr[idx + 3],   # unique comment ID for every comment
        "posted":      "",
        "edited":      False,
        "likes":       0,
        "replies":     0,              # filled for top-level comments only
    }
    meta = arr[idx + 4]
    if "(edited)" in meta:
        d["edited"] = True
        meta = meta.replace("(edited)", "").strip()
    for part in (p.strip() for p in meta.split("|")):
        if part.startswith("like:"):
            d["likes"] = int(part.split(":", 1)[1])
        elif part.startswith("reply:"):
            d["replies"] = int(part.split(":", 1)[1])
        else:              # first token gives us the relative date
            d["posted"] = part
    return d, idx + 5          # iterates to the next unread line


def parse_comment_block(block: str) -> Optional[tuple[dict, list[dict]]]:
    """Return (parent_dict, [reply_dict, ...]) or None if not a comment block."""
    lines = [ln.rstrip() for ln in block.splitlines() if ln.strip()]
    if not lines or "[COMMENT]" not in lines[0]:
        return None

    # Parent comment categorization
    parent, i = _parse_head(lines, 0)

    body: list[str] = []
    while i < len(lines) and lines[i] != "Replies:":
        body.append(lines[i]);  i += 1
    parent["comment"] = "\n".join(body)

    # Reply (child) comment categorization
    replies: list[dict] = []
    if i < len(lines) and lines[i] == "Replies:":
        i += 1                        # skip literal marker
        while i < len(lines):
            if lines[i] != "[REPLY]": # ignore [REPLY] text
                i += 1;  continue

            rep, j = _parse_head(lines, i)
            text: list[str] = []
            while j < len(lines) and lines[j] != "[REPLY]":
                text.append(lines[j]);  j += 1
            rep["comment"]  = "\n".join(text)
            rep["parent_id"] = parent["comment_url"]
            replies.append(rep)
            i = j

    return parent, replies


def get_comments(driver: webdriver.Chrome, url: str, timeout: int = 90) -> tuple[str, str, list[dict]]:
    """Returns video_id, video_title, list[comment-dict] (raw, no sentiment yet)."""
    wait = WebDriverWait(driver, timeout)
    driver.get(url)

    # video title
    wait.until(EC.presence_of_element_located((By.TAG_NAME, "h1")))
    full_title = driver.title.rsplit(" - YouTube", 1)[0].strip()

    # wait for YCS UI + green tick
    wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "div.ycs-app-main")))
    wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "#ycs_status_cmnt svg linearGradient")))

    # hook blob capture
    driver.execute_script("""
        window.__ycs = [];
        const orig = URL.createObjectURL;
        URL.createObjectURL = blob => {
            blob.text().then(t => window.__ycs.push(t));
            return orig(blob);
        };
    """)
    # click "Save all comments" on the webpage
    btn = wait.until(EC.element_to_be_clickable((By.ID, "ycs_save_all_comments")))
    driver.execute_script("window.scrollTo(0,0); arguments[0].scrollIntoView({block:'center'});", btn)
    ActionChains(driver).move_to_element(btn).click().perform()

    wait.until(lambda d: d.execute_script("return window.__ycs.length > 0"))
    raw_dump = driver.execute_script("return window.__ycs.pop()")

    # Every block in the extension JSON file starts with "#####" on its own newline
    blocks = [b.strip() for b in raw_dump.split("#####") if b.strip()]
    tops, children = [], []
    for blk in blocks:
        res = parse_comment_block(blk)
        if res:
            p, rs = res
            tops.append(p);  children.extend(rs)
    parsed = tops + children

    vid = parse_qs(urlparse(url).query).get("v", [""])[0]
    return vid, full_title, parsed


# Sentiment analysis using VADER

from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer

# Create Global VADER object for repeated Sentiment Analysis
_VADER = SentimentIntensityAnalyzer()

class Row(NamedTuple):
    video_id   : str
    video      : str
    comment_id : str
    parent_id  : Optional[str] # No parent id required for parent comments
    is_reply   : bool
    username   : str
    comment    : str
    likes      : int
    replies    : int
    polarity   : float
    label      : Literal["positive", "negative", "neutral"]

def _score(txt: str) -> float:
    """Return VADER 'compound' score within the range of -1 to +1."""
    return _VADER.polarity_scores(txt)["compound"]

def score_comments(video_id: str, video_title: str, comments: list[dict]) -> list[Row]:
    texts = [c["comment"] for c in comments]
    with concurrent.futures.ThreadPoolExecutor(max_workers=POOL_WORKERS) as pool:
        polarities = list(pool.map(_score, texts))

    rows: list[Row] = []
    for c, p in zip(comments, polarities):
        label = "positive" if p >= 0.05 else "negative" if p <= -0.05 else "neutral"
        rows.append(Row(
            video_id      = video_id,
            video         = video_title,
            comment_id    = c["comment_url"],
            parent_id     = c.get("parent_id"),
            is_reply      = bool(c.get("parent_id")),
            username      = c["username"] if usernameToggle else "",
            comment       = c["comment"],
            likes         = c["likes"],
            replies       = c["replies"],
            polarity      = round(p, 4),
            label         = label
        ))
    return rows

# Creating a Vega-Lite Dashboard from scratch based on the data scrapped

def make_dashboard(rows: list[Row], out_html: Path) -> None:
    import html, json as _json

    # unique videos for dropdown
    video_opts = sorted({r.video for r in rows})
    video_opts_display = ['All videos'] + video_opts

    data = [r._asdict() for r in rows]

    vl_spec = {
        "$schema": "https://vega.github.io/schema/vega-lite/v5.json",
        "datasets": {"comments": data},
        "params": [
            {
                "name": "video_pick",
                "value": "All videos",
                "bind": {"input": "select", "options": video_opts_display, "name": "Video: "}
            }
        ],
        "vconcat": [
            {
                "title": "Sentiment polarity distribution",
                "width": 600, "height": 120,
                "data": {"name": "comments"},
                "transform": [
                    {"filter":
                     "datum.video == video_pick || video_pick == 'All videos'"}
                ],
                "selection": {
                    "brush": {"type": "interval", "encodings": ["x"]},
                    "labelfilter": {"type": "multi", "fields": ["label"]}
                },
                "mark": "bar",
                "encoding": {
                    "x": {"field": "polarity", "type": "quantitative",
                          "bin": {"maxbins": 40}},
                    "y": {"aggregate": "count"},
                    "color": {
                        "condition": {
                            "selection": "labelfilter",
                            "field": "label", "type": "nominal",
                            "legend": {"title": "Sentiment"}
                        },
                        "value": "lightgray"
                    },
                    "tooltip": [{"aggregate": "count", "title": "Comments"}]
                }
            },
            {
                "hconcat": [
                    {
                        "title": "Likes vs polarity",
                        "width": 600, "height": 320,
                        "data": {"name": "comments"},
                        "transform": [
                            {"filter": "datum.video == video_pick || video_pick == 'All videos'"},
                            {"filter": {"selection": "brush"}}
                        ],
                        "selection": {
                            "labelfilter": {"type": "multi", "fields": ["label"]}
                        },
                        "mark": {"type": "point",  "filled": True, "opacity": 0.8, "size": 80},
                        "encoding": {
                            "x": {"field": "polarity", "type": "quantitative"},
                            "y": {"field": "likes", "type": "quantitative"},
                            "color": {
                                "field": "label",
                                "type": "nominal",
                                "legend": None
                            },
                            "tooltip": [
                                *([{"field":"username","type":"nominal"}] if usernameToggle else []),
                                {"field": "replies",   "type": "quantitative", "title": "Replies"},
                                {"field": "parent_id", "type": "nominal",      "title": "Reply to"},
                                {"field": "polarity", "type": "quantitative"},
                                {"field": "likes", "type": "quantitative"},
                                {"field": "comment", "type": "nominal"}
                            ],
                            "opacity": {
                                "condition": {"selection": "labelfilter", "value": 1},
                                "value": 0.1
                            },
                            "shape": {
                                "field": "is_reply",
                                "type" : "nominal",
                                "legend": {"title": "Reply?"},
                                "scale": {
                                    "domain": [False, True], # for top‑level comments and their replies
                                    "range" : ["circle", "triangle-up"]
                                }
                            }
                        }
                    },
                    {
                        "title": "Comment count by sentiment",
                        "width": 220, "height": 320,
                        "data": {"name": "comments"},
                        "transform": [
                            {"filter": "datum.video == video_pick || video_pick == 'All videos'"}
                        ],
                        "selection": {
                            "labelfilter": {"type": "multi", "fields": ["label"]}
                        },
                        "mark": "bar",
                        "encoding": {
                            "x": {"field": "label", "type": "nominal"},
                            "y": {"aggregate": "count"},
                            "color": {"field": "label", "type": "nominal", "legend": None},
                            "tooltip": [{"aggregate": "count", "title": "Comments"}],
                            "opacity": {
                                "condition": {"selection": "labelfilter", "value": 1},
                                "value": 0.3
                            }
                        }
                    }
                ]
            }
        ]
    }

    html_tpl = f"""<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
  <title>Processed Sentiment Analysis Dashboard</title>
  <script src="https://cdn.jsdelivr.net/npm/vega@5"></script>
  <script src="https://cdn.jsdelivr.net/npm/vega-lite@5"></script>
  <script src="https://cdn.jsdelivr.net/npm/vega-embed@6"></script>
  <style>
    body {{font-family: Arial, sans-serif; margin: 0; padding: 1rem;}}
    h2 {{text-align:center; margin-top:0;}}
  </style>
</head>
<body>
  <h2>Processed Sentiment Analysis Dashboard</h2>
  <div id="vis"></div>
  <script>
    const spec = {_json.dumps(vl_spec)};
    vegaEmbed("#vis", spec, {{actions:false}}).catch(console.error);
  </script>
</body>
</html>"""
    out_html.write_text(html_tpl, encoding="utf-8")
    print(f"\nDashboard written to: {out_html.resolve()}")


# Main process caller function

def process_videos(urls: list[str]) -> None:
    print("Normalising URLs.")
    seen, duplicates, malformed = set(), [], []
    canon: list[str] = []
    for u in urls:
        n = normalize_url(u)
        if not n:
            malformed.append(u)
        elif n in seen:
            duplicates.append(n)
        else:
            seen.add(n)
            canon.append(n)

    if malformed:
        print("\nIgnored malformed:", malformed)
    if duplicates:
        print("\nDuplicates removed:", duplicates)

    print("\nChecking reachability.")
    reachable = [u for u in canon if is_url_reachable(u)]
    unreachable = set(canon) - set(reachable)
    if unreachable:
        print("\nInaccessible:", unreachable)
    if not reachable:
        print("Nothing to do.")
        return

    print(f"\nScraping {len(reachable)} video(s).")

    driver = make_driver()
    all_rows: list[Row] = []

    try:
        for u in reachable:
            print("->", u)
            vid, title, comments = get_comments(driver, u)
            print(f"   {len(comments)} raw comments")
            all_rows.extend(score_comments(vid, title, comments))
    finally:
        driver.quit()

    print(f"\nTotal comments processed: {len(all_rows)}")
    out = Path("sentiment_dashboard.html")
    make_dashboard(all_rows, out)


if __name__ == "__main__":
    input_urls = sys.argv[1:] or [
        "https://www.youtube.com/watch?v=cpcfdwnf4M8",  # demo fallback
    ]
    process_videos(input_urls)

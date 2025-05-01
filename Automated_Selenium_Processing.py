#!/usr/bin/env python3
"""
YouTube Comment Extractor & Parser

1. Normalize input URLs (watch, shorts, youtu.be) to standard YouTube links (https://www.youtube.com/watch?v=<video_id>)
2. Remove duplicates, malformed and/or unreachable URLs mentioning each instance where it happened.
3. Use Chrome using headful scraping methods while using the unpacked YCS extension in order to capture comments in-memory avoiding text output entirely.
4. Parses raw text comments into JSON objects.
5. Save processed videos as anonymized files for example: video_1.json, video_2.json, etc in OUTPUT_DIR (./processed-json-comment-files/)
6. Once finished processing everything, print a summary for each processed video clearly stating their full video title, file name and number of comments in the file.
"""

import os
import re
import json
import requests
from urllib.parse import urlparse, parse_qs

from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver import ActionChains

# Absolute Configuration Paths
BASE_DIR            = os.path.dirname(__file__)
CHROMEDRIVER_PATH   = os.path.join(BASE_DIR, "chromedriver-win64", "chromedriver.exe")
YCS_EXTENSION_PATH  = os.path.join(BASE_DIR, "chrome-extension-files", "YCS-cont")
OUTPUT_DIR          = os.path.join(BASE_DIR, "processed-json-comment-files")

# Generic helper functions to process comment data 

def normalize_url(url: str) -> str | None:
    url = url.strip()
    if not url:
        return None
    parsed = urlparse(url)
    host = parsed.netloc.lower()
    path = parsed.path.lstrip("/")
    video_id = ""
    if host == "youtu.be":
        video_id = path.split("?")[0]
    elif "youtube.com" in host:
        if path.startswith("watch"):
            video_id = parse_qs(parsed.query).get("v", [""])[0]
        elif path.startswith("shorts/"):
            video_id = path.split("/")[1]
        else:
            return None
    else:
        return None
    if re.fullmatch(r"[A-Za-z0-9_-]{11}", video_id):
        return f"https://www.youtube.com/watch?v={video_id}"
    return None

def is_url_reachable(url: str, timeout: int = 10) -> bool:
    try:
        return requests.get(url, timeout=timeout).status_code == 200
    except requests.RequestException:
        return False

def make_driver() -> webdriver.Chrome:
    opts = webdriver.ChromeOptions()
    opts.add_argument("--start-maximized")
    for arg in ("--disable-gpu","--disable-software-rasterizer","--no-sandbox","--disable-dev-shm-usage"):
        opts.add_argument(arg)
    opts.add_experimental_option("excludeSwitches", ["enable-logging"])
    opts.add_argument(f"--load-extension={YCS_EXTENSION_PATH}")
    return webdriver.Chrome(service=Service(CHROMEDRIVER_PATH), options=opts)

def get_comments(driver: webdriver.Chrome, url: str, timeout: int = 90) -> tuple[str, str, str]:
    driver.get(url)
    wait = WebDriverWait(driver, timeout)
    # grab the raw full page title as "Video Title - YouTube"
    wait.until(EC.presence_of_element_located((By.TAG_NAME, "h1")))
    raw_title = driver.title
    title = raw_title.rsplit(" - YouTube", 1)[0].strip()

    # wait for YCS panel + green tick
    wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "div.ycs-app-main")))
    wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "#ycs_status_cmnt svg linearGradient")))

    btn = wait.until(EC.element_to_be_clickable((By.ID, "ycs_save_all_comments")))
    # intercept blob for in-memory text capture
    driver.execute_script("""
        window.__ycs = [];
        const orig = URL.createObjectURL;
        URL.createObjectURL = blob => {
            blob.text().then(t => window.__ycs.push(t));
            return orig(blob);
        };
    """)

    # reset scroll, center & click when complete
    driver.execute_script("window.scrollTo(0,0); arguments[0].scrollIntoView({block:'center'});", btn)
    ActionChains(driver).move_to_element(btn).click().perform()

    wait.until(lambda d: d.execute_script("return window.__ycs.length > 0"))
    raw = driver.execute_script("return window.__ycs.pop()")
    vid = parse_qs(urlparse(url).query).get("v", [""])[0]
    return vid, title, raw

def parse_comment_block(block: str) -> dict | None:
    lines = [l.strip() for l in block.splitlines() if l.strip()]
    if not lines or "[COMMENT]" not in lines[0]:
        return None
    d = {
        "username":    lines[1],
        "profile_url": lines[2],
        "comment_url": lines[3],
        "posted":      "",
        "edited":      False,
        "likes":       0,
        "replies":     0,
        "comment":     ""
    }
    meta = lines[4]
    if "(edited)" in meta:
        d["edited"] = True
        meta = meta.replace("(edited)", "").strip()
    parts = [p.strip() for p in meta.split("|")]
    d["posted"] = parts[0]
    for p in parts[1:]:
        if p.startswith("like:"):
            d["likes"] = int(p.split(":",1)[1])
        elif p.startswith("reply:"):
            d["replies"] = int(p.split(":",1)[1])
    d["comment"] = "\n".join(lines[5:])
    return d

# Main function to normalize and standardize comment processing from URLs directly

def main(urls: list[str]) -> None:
    # Normalize & dedupe
    seen, cleaned, malformed, duplicates = set(), [], [], []
    for u in urls:
        norm = normalize_url(u)
        if not norm:
            malformed.append(u)
        elif norm in seen:
            duplicates.append(norm)
        else:
            seen.add(norm)
            cleaned.append(norm)

    # Reachability
    reachable, broken = [], []
    for u in cleaned:
        (reachable if is_url_reachable(u) else broken).append(u)

    # Report
    if malformed:
        print("Malformed URLs:", malformed)
    if duplicates:
        print("Duplicates removed:", duplicates)
    if broken:
        print("Unreachable skipped:", broken)
    if not reachable:
        print("No valid videos to process.")
        return

    # Prepare
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    driver = make_driver()
    summary = []

    # Process
    for idx, url in enumerate(reachable, start=1):
        vid, title, raw = get_comments(driver, url)
        blocks = re.findall(r'#####(.*?)#####', raw, re.DOTALL)
        parsed = [c for b in blocks if (c := parse_comment_block(b))]
        fname = f"video_{idx}.json"
        out_path = os.path.join(OUTPUT_DIR, fname)
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(parsed, f, ensure_ascii=False, indent=2)
        summary.append((fname, title, len(parsed)))

    driver.quit()

    # Final summary
    print("\nVideos processed so far:")
    for fname, title, count in summary:
        print(f"{fname}: '{title}' - {count} comments")

if __name__ == "__main__":
    # YouTube test array of URLs to be later processed directly based on Front end data
    youtube_urls = [
        "https://youtu.be/cpcfdwnf4M8?si=XYZ",
        "https://www.youtube.com/shorts/cpcfdwnf4M8",
        "https://www.youtube.com/watch?v=cpcfdwnf4M8",
    ]
    main(youtube_urls)
#!/usr/bin/env python3
import requests
from bs4 import BeautifulSoup
import csv
import time
import argparse
import os
import pandas as pd

# ---- CLI Args ----
parser = argparse.ArgumentParser(description="Generate blog CSV + Markdown with summaries from base CSV.")
parser.add_argument("--alternate", action="store_true", help="Alternate columns in markdown table.")
parser.add_argument("--max-summary", type=int, default=200, help="Max summary length (default: 200 chars).")
parser.add_argument("--force", action="store_true", help="Force re-fetch all summaries and thumbnails.")
parser.add_argument("--force-summaries", action="store_true", help="Force re-fetch only summaries.")
parser.add_argument("--force-thumbnails", action="store_true", help="Force re-fetch only thumbnails.")
args = parser.parse_args()

# ---- Config ----
INPUT_FILE = "blog_posts.csv"  # Provided CSV with Title, Date, URL, Thumbnail
CSV_OUTPUT = "blog_summaries.csv"
MD_OUTPUT = "blog_summaries_with_summaries.md"
THUMB_DIR = "thumbnails"

headers = {
    "User-Agent": "Mozilla/5.0"
}

# ---- Load base CSV ----
df_base = pd.read_csv(INPUT_FILE)

# ---- Load existing summaries if present ----
existing_summaries = {}
if not args.force and not args.force_summaries and os.path.exists(CSV_OUTPUT):
    df_existing = pd.read_csv(CSV_OUTPUT)
    for _, row in df_existing.iterrows():
        if isinstance(row.get("Summary"), str) and row["Summary"].strip():
            existing_summaries[row["URL"]] = row["Summary"]

results = []

for idx, row in df_base.iterrows():
    url = row["URL"]
    title = (row["Title"] or "").replace("|", "-")
    date = row["Date"]
    thumb_url = row["Thumbnail"]

    # --- SUMMARY ---
    summary = existing_summaries.get(url) if not (args.force or args.force_summaries) else None
    if not summary:
        print(f"[{idx+1}/{len(df_base)}] Fetching summary: {url}")
        try:
            resp = requests.get(url, headers=headers, timeout=15)
            resp.raise_for_status()
            soup = BeautifulSoup(resp.text, "html.parser")
        except Exception as e:
            print(f"Error fetching {url}: {e}")
            soup = None

        if soup:
            meta_desc = soup.find("meta", attrs={"name": "description"})
            if meta_desc and meta_desc.get("content"):
                summary = meta_desc["content"].strip()
            else:
                p_tag = soup.find("p")
                summary = p_tag.get_text(strip=True) if p_tag else None

        if summary:
            summary = summary.replace("|", "-")
            if len(summary) > args.max_summary:
                summary = summary[:args.max_summary].rstrip() + "…"

        time.sleep(1)  # polite delay
    else:
        print(f"[{idx+1}/{len(df_base)}] Using existing summary for: {url}")

    # --- THUMBNAIL ---
    local_thumb = None
    if thumb_url and isinstance(thumb_url, str):
        # Fix relative thumbnail URLs
        if thumb_url.startswith("/"):
            if "snyk.io" in url:
                print(f"  Fixing relative Snyk thumbnail: {thumb_url}")
                thumb_url = f"https://snyk.io{thumb_url}"
            elif "elastic.co" in url:
                print(f"  Fixing relative Elastic thumbnail: {thumb_url}")
                thumb_url = f"https://www.elastic.co{thumb_url}"

        ext = os.path.splitext(thumb_url.split("?")[0])[1] or ".jpg"
        safe_name = "".join(c for c in title if c.isalnum() or c in "-_")[:50]
        local_thumb = f"{THUMB_DIR}/{safe_name}{ext}"
        os.makedirs(THUMB_DIR, exist_ok=True)

        if not os.path.exists(local_thumb) or args.force or args.force_thumbnails:
            print(f"  Downloading thumbnail: {thumb_url}")
            try:
                img_data = requests.get(thumb_url, headers=headers, timeout=15).content
                with open(local_thumb, "wb") as img_f:
                    img_f.write(img_data)
            except Exception as e:
                print(f"Failed to download {thumb_url}: {e}")
                local_thumb = None
        else:
            print(f"  Using existing thumbnail: {local_thumb}")

    results.append({
        "Title": title,
        "Date": date,
        "URL": url,
        "Thumbnail": local_thumb,
        "Summary": summary
    })

# ---- Write updated CSV ----
with open(CSV_OUTPUT, "w", newline="", encoding="utf-8") as f:
    writer = csv.DictWriter(f, fieldnames=["Title", "Date", "URL", "Thumbnail", "Summary"])
    writer.writeheader()
    writer.writerows(results)

# ---- Write Markdown ----
with open(MD_OUTPUT, "w", encoding="utf-8") as f:
    f.write("| Thumbnail | Details |\n|---|---|\n")
    for i, r in enumerate(results):
        thumb_md = f"[![Thumbnail]({r['Thumbnail']})]({r['URL']})" if r['Thumbnail'] else f"[Link]({r['URL']})"
        details_md = f"[{r['Title']}]({r['URL']})<br>{r['Date'] or ''}<br>{r['Summary'] or ''}"

        if args.alternate and i % 2 == 1:
            f.write(f"| {details_md} | {thumb_md} |\n")
        else:
            f.write(f"| {thumb_md} | {details_md} |\n")

print(f"Done! Saved {len(results)} rows to {CSV_OUTPUT} and {MD_OUTPUT}")


"""
debug_fighter_page.py
Run this to see the structure of a Tapology fighter page.
"""

import requests
from bs4 import BeautifulSoup

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "en-US,en;q=0.9",
}

# Paste Islam Makhachev's URL from your previous run
URL = "https://www.tapology.com/fightcenter/fighters/40148-islam-makhachev"

resp = requests.get(URL, headers=HEADERS, timeout=10)
print(f"Status: {resp.status_code}")
print(f"Length: {len(resp.text)} chars\n")

soup = BeautifulSoup(resp.text, "html.parser")

print("=" * 60)
print("ALL <ul> TAGS:")
print("=" * 60)
for ul in soup.find_all("ul"):
    print(f"  class={ul.get('class')}  id={ul.get('id')}")

print("\n" + "=" * 60)
print("ALL <li> TAGS (first 20):")
print("=" * 60)
for li in soup.find_all("li")[:20]:
    print(f"  class={li.get('class')}  text={li.get_text(strip=True)[:80]}")

print("\n" + "=" * 60)
print("ANYTHING CONTAINING 'win' or 'loss' (first 20 elements):")
print("=" * 60)
count = 0
for tag in soup.find_all(True):
    text = tag.get_text(strip=True).lower()
    if ("win" in text or "loss" in text) and len(text) < 200:
        print(f"  <{tag.name}> class={tag.get('class')}  text={text[:100]}")
        count += 1
        if count >= 20:
            break

print("\n" + "=" * 60)
print("RAW HTML MIDDLE SECTION (chars 5000-10000):")
print("=" * 60)
print(resp.text[5000:10000])

# append or replace the bottom of debug_fighter_page.py with this block

import json
from pathlib import Path

OUT_DIR = Path("tapology_debug")
OUT_DIR.mkdir(exist_ok=True)

# 1) Dump __NEXT_DATA__ if present
next_el = soup.find("script", id="__NEXT_DATA__", type="application/json")
if next_el and next_el.string:
    try:
        nd = json.loads(next_el.string)
        nd_path = OUT_DIR / "next_data.json"
        nd_path.write_text(json.dumps(nd, indent=2, ensure_ascii=False), encoding="utf-8")
        print("\n" + "="*60)
        print("Found __NEXT_DATA__ — saved to", nd_path)
        # Try to find any obvious 'fights' list inside the JSON and print a short sample
        def find_fights(obj):
            if isinstance(obj, dict):
                for k, v in obj.items():
                    if isinstance(v, list) and k.lower().startswith("fight"):
                        return k, v
                    res = find_fights(v)
                    if res:
                        return res
            elif isinstance(obj, list):
                for item in obj:
                    res = find_fights(item)
                    if res:
                        return res
            return None
        ff = find_fights(nd)
        if ff:
            key, fights = ff
            print(f"Sample JSON key for fights: '{key}' (showing up to 6 items)")
            print(json.dumps(fights[:6], indent=2, ensure_ascii=False)[:4000])
            sample_json_path = OUT_DIR / "next_data_fights_sample.json"
            sample_json_path.write_text(json.dumps(fights[:20], indent=2, ensure_ascii=False), encoding="utf-8")
            print("Saved sample fights to", sample_json_path)
        else:
            print("No obvious 'fights' list found inside __NEXT_DATA__ (but full JSON saved).")
    except Exception as e:
        print("Failed to parse __NEXT_DATA__ JSON:", e)
else:
    print("\n__NEXT_DATA__ not found on page.")

# 2) Find and save the first fight-history row (try several selectors)
candidates = []
selectors = [
    "table.fight-history tr",
    "table.record-table tr",
    ".fight-list .fight-row",
    ".fight-history .fight-row",
    ".fight-history li",
    ".record-list li",
    ".fight-row",
    ".record-row",
]

for sel in selectors:
    els = soup.select(sel)
    if els:
        print(f"\nSelector '{sel}' matched {len(els)} elements; saving first match.")
        first = els[0]
        html_path = OUT_DIR / f"sample_row_{sel.replace(' ', '_').replace('.', '').replace('/', '_')}.html"
        html_path.write_text(str(first), encoding="utf-8")
        print("Saved sample row HTML to", html_path)
        print("Sample text (first 400 chars):")
        print(first.get_text(" ", strip=True)[:400])
        candidates.append((sel, first))
        break

if not candidates:
    # fallback: find any <tr> or <li> that looks like a fight row by containing 'promotion' or 'method' keywords
    for tag in soup.find_all(["tr", "li"]):
        txt = tag.get_text(" ", strip=True).lower()
        if ("promotion" in txt or "method" in txt or "ko" in txt or "submission" in txt) and len(txt) < 2000:
            html_path = OUT_DIR / "sample_row_fallback.html"
            html_path.write_text(str(tag), encoding="utf-8")
            print("\nFallback: saved a candidate fight row to", html_path)
            print("Sample text (first 400 chars):")
            print(txt[:400])
            candidates.append(("fallback", tag))
            break

if not candidates:
    print("\nNo likely fight rows found with the tried selectors. You can paste a small HTML snippet of the fight-history section if needed.")

print("\nDebug files written to:", OUT_DIR.resolve())

print("NEW SCRIPT\n\n\n\n\n")
# Append this to the end of debug_fighter_page.py (after existing debug code)

import re
from pathlib import Path

OUT_DIR = Path("tapology_debug")
OUT_DIR.mkdir(exist_ok=True)

print("\n" + "="*60)
print("Saving up to 10 candidate fight rows (tr or li) with likely fight info")
print("="*60)

# Collect candidate rows by scanning for rows that contain 'ufc', 'win', 'loss', 'method', 'submission', or 'ko'
candidates = []
for tag in soup.find_all(["tr", "li", "div"]):
    txt = tag.get_text(" ", strip=True).lower()
    if any(k in txt for k in ("ufc", "win", "loss", "ko", "tko", "submission", "method", "decision")) and len(txt) < 4000:
        candidates.append(tag)
    if len(candidates) >= 10:
        break

if not candidates:
    print("No candidate rows found with the simple keyword scan. Will try looser scan for 'event' or 'promotion'.")
    for tag in soup.find_all(["tr", "li", "div"]):
        txt = tag.get_text(" ", strip=True).lower()
        if any(k in txt for k in ("event", "promotion", "opponent")) and len(txt) < 4000:
            candidates.append(tag)
        if len(candidates) >= 10:
            break

for idx, tag in enumerate(candidates, start=1):
    fname = OUT_DIR / f"sample_row_{idx}.html"
    fname.write_text(str(tag), encoding="utf-8")
    summary = tag.get_text(" ", strip=True)[:400].replace("\n", " ")
    print(f"Saved {fname}  summary: {summary}")

print("\n" + "="*60)
print("Searching for inline JSON blobs in <script> tags")
print("="*60)

script_blobs = []
for script in soup.find_all("script"):
    if not script.string:
        continue
    s = script.string.strip()
    # look for JSON-like starts or known variable names
    if s.startswith("{") or s.startswith("[") or re.search(r"(__NEXT_DATA__|__INITIAL_STATE__|window\.__INITIAL_STATE__|window\.__DATA__|initialState|window\.__APP_STATE__)", s, re.IGNORECASE):
        # limit size to avoid huge dumps
        snippet = s[:2000]
        script_blobs.append((script, snippet))

if script_blobs:
    for i, (script, snippet) in enumerate(script_blobs, start=1):
        fname = OUT_DIR / f"inline_script_blob_{i}.txt"
        # save full content but be cautious about size
        try:
            fname.write_text(script.string, encoding="utf-8")
            print(f"Saved inline script blob to {fname} (first 2000 chars shown):")
            print(snippet)
        except Exception as e:
            print(f"Failed to save script blob {i}: {e}")
else:
    print("No obvious inline JSON blobs found in <script> tags.")

print("\nFiles written to:", OUT_DIR.resolve())
print("Please paste the contents of one of the saved sample_row_*.html files (or attach it).")

# --- paste this at the end of debug_fighter_page.py and run ---
from pathlib import Path
import glob

OUT_DIR = Path("tapology_debug")

# Print the first sample_row_*.html file (full contents)
rows = sorted(OUT_DIR.glob("sample_row_*.html"))
if rows:
    print("\n" + "="*60)
    print("FULL CONTENTS OF", rows[0].name)
    print("="*60)
    print(rows[0].read_text(encoding="utf-8"))
else:
    print("No sample_row_*.html files found in", OUT_DIR)

# Print any inline script blobs (first 1200 chars each)
blobs = sorted(OUT_DIR.glob("inline_script_blob_*.txt"))
if blobs:
    for b in blobs:
        print("\n" + "="*60)
        print("INLINE SCRIPT BLOB:", b.name)
        print("="*60)
        txt = b.read_text(encoding="utf-8")
        print(txt[:1200])
else:
    print("No inline_script_blob_*.txt files found in", OUT_DIR)

# Also print a short summary of the first 3 sample rows (one-line each)
print("\n" + "="*60)
print("ONE-LINE SUMMARIES (first 3 sample_row_*.html)")
print("="*60)
for r in rows[:3]:
    txt = r.read_text(encoding="utf-8")
    one_line = " ".join(txt.split())[:400]
    print(f"{r.name}: {one_line}\n")



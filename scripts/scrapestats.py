"""
scrape_ufc_stats.py

Scrapes UFCStats.com to auto-populate ufc-wins, ufc-losses, ufc-ko-tko-wins, ufc-sub-wins
for every fighter in fighters.json.

Run from project root:
    python scripts/scrape_ufc_stats.py

Requirements:
    pip install requests beautifulsoup4
"""

import json
import time
import unicodedata
import requests
from bs4 import BeautifulSoup
from pathlib import Path

# ── Config ────────────────────────────────────────────────────────────────────

FIGHTERS_PATH   = Path(__file__).resolve().parent.parent / "data" / "fighters.json"
UFCSTATS_SEARCH = "http://ufcstats.com/statistics/fighters?char={}&action=fighter_search"
HEADERS         = {"User-Agent": "Mozilla/5.0"}
DELAY           = 0

# ── Helpers ───────────────────────────────────────────────────────────────────

def strip_accents(text: str) -> str:
    """Remove all accents/diacritics from a string."""
    return "".join(
        c for c in unicodedata.normalize("NFD", text)
        if unicodedata.category(c) != "Mn"
    )

def normalise(text: str) -> str:
    """Lowercase, strip accents, remove punctuation."""
    text = strip_accents(text).lower()
    text = "".join(c for c in text if c.isalnum() or c == " ")
    return " ".join(text.split())


def search_fighter(name: str):
    """
    Strategy:
      1. Browse UFCStats by first letter of the DB last name
      2. For each row, strip accents from the UFC name
      3. Match: first name must match AND first 2 letters of last name must match
    Returns fighter page URL or None.
    """
    parts      = name.strip().split()
    if len(parts) < 2:
        # Single name — try first letter of that name
        first_name = normalise(parts[0])
        last_name  = ""
        last_2     = ""
        search_char = first_name[0] if first_name else "a"
    else:
        first_name  = normalise(parts[0])
        last_name   = normalise(" ".join(parts[1:]))
        last_2      = last_name[:2]
        search_char = last_name[0] if last_name else first_name[0]

    if not search_char.isalpha():
        return None

    url  = UFCSTATS_SEARCH.format(search_char)
    resp = requests.get(url, headers=HEADERS, timeout=10)
    if resp.status_code != 200:
        return None

    soup = BeautifulSoup(resp.text, "html.parser")
    rows = soup.select("table.b-statistics__table tbody tr")

    for row in rows:
        cells = row.find_all("td")
        if len(cells) < 2:
            continue
        first_a = cells[0].find("a")
        last_a  = cells[1].find("a")
        if not first_a or not last_a:
            continue

        # Strip accents from UFC site names before comparing
        ufc_first = normalise(first_a.text.strip())
        ufc_last  = normalise(last_a.text.strip())

        # First name must match exactly
        if ufc_first != first_name:
            continue

        # Last name first 2 letters must match (handles Jr., compound names etc.)
        if last_2 and not ufc_last.startswith(last_2):
            continue

        href = first_a.get("href") or last_a.get("href")
        return href

    return None


def scrape_fighter_page(url: str):
    """
    Scrape a fighter's UFC stats page.
    Returns dict with ufc-wins, ufc-losses, ufc-ko-tko-wins, ufc-sub-wins.
    """
    resp = requests.get(url, headers=HEADERS, timeout=10)
    if resp.status_code != 200:
        return None

    soup = BeautifulSoup(resp.text, "html.parser")
    rows = soup.select("table.b-fight-details__table tbody tr")

    ufc_wins     = 0
    ufc_losses   = 0
    ufc_ko_wins  = 0
    ufc_sub_wins = 0

    for row in rows:
        cells = row.find_all("td")
        if len(cells) < 8:
            continue

        result_cell = cells[0].get_text(strip=True).upper()
        method_cell = cells[7].get_text(separator=" ", strip=True).upper()

        if result_cell == "WIN":
            ufc_wins += 1
            if "KO" in method_cell or "TKO" in method_cell:
                ufc_ko_wins += 1
            elif "SUB" in method_cell:
                ufc_sub_wins += 1

        elif result_cell == "LOSS":
            ufc_losses += 1

    return {
        "ufc-wins":        ufc_wins,
        "ufc-losses":      ufc_losses,
        "ufc-ko-tko-wins": ufc_ko_wins,
        "ufc-sub-wins":    ufc_sub_wins,
    }


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    with open(FIGHTERS_PATH, "r", encoding="utf-8") as f:
        fighters = json.load(f)

    total   = len(fighters)
    updated = 0
    failed  = []

    for i, fighter in enumerate(fighters):
        name   = fighter.get("personal-info", {}).get("name", "Unknown")
        career = fighter.get("career", {})

        print(f"[{i+1}/{total}] {name} ... ", end="", flush=True)

        # Skip if already populated with non-zero values
        if career.get("ufc-wins") not in (None, 0) or career.get("ufc-losses") not in (None, 0):
            print("already has UFC stats, skipping")
            continue

        try:
            page_url = search_fighter(name)
            time.sleep(DELAY)

            if not page_url:
                print("NOT FOUND")
                failed.append(name)
                career["ufc-wins"]        = 0
                career["ufc-losses"]      = 0
                career["ufc-ko-tko-wins"] = 0
                career["ufc-sub-wins"]    = 0
                continue

            stats = scrape_fighter_page(page_url)
            time.sleep(DELAY)

            if not stats:
                print(f"page fetch failed ({page_url})")
                failed.append(name)
                career["ufc-wins"]        = 0
                career["ufc-losses"]      = 0
                career["ufc-ko-tko-wins"] = 0
                career["ufc-sub-wins"]    = 0
                continue

            career["ufc-wins"]        = stats["ufc-wins"]
            career["ufc-losses"]      = stats["ufc-losses"]
            career["ufc-ko-tko-wins"] = stats["ufc-ko-tko-wins"]
            career["ufc-sub-wins"]    = stats["ufc-sub-wins"]

            print(
                f"wins={stats['ufc-wins']}  "
                f"losses={stats['ufc-losses']}  "
                f"ko={stats['ufc-ko-tko-wins']}  "
                f"sub={stats['ufc-sub-wins']}"
            )
            updated += 1

        except Exception as e:
            print(f"ERROR — {e}")
            failed.append(name)
            career["ufc-wins"]        = 0
            career["ufc-losses"]      = 0
            career["ufc-ko-tko-wins"] = 0
            career["ufc-sub-wins"]    = 0

    # Save back
    with open(FIGHTERS_PATH, "w", encoding="utf-8") as f:
        json.dump(fighters, f, indent=4, ensure_ascii=False)

    print(f"\nDone. Updated: {updated}/{total}")
    if failed:
        print(f"\nFailed / not found ({len(failed)}):")
        for n in failed:
            print(f"  - {n}")
    print(f"\nfighters.json saved to {FIGHTERS_PATH}")


if __name__ == "__main__":
    main()
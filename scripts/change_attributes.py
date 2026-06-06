import json
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parent.parent
fighters_path = DATA_DIR / "data" / "fighters.json"

with open(fighters_path, "r", encoding="utf-8") as f:
    fighters = json.load(f)

updated = 0
for fighter in fighters:
    info = fighter.get("personal-info", {})
    if info.get("gender") == "Female" and info.get("weight-class") == "Bantamweight":
        info["weight-class"] = "Women's Bantamweight"
        updated += 1

with open(fighters_path, "w", encoding="utf-8") as f:
    json.dump(fighters, f, indent=4, ensure_ascii=False)

print(f"Done. Updated {updated} fighter(s).")
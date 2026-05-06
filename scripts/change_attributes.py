import json
import shutil
from pathlib import Path
from datetime import datetime

DATA_DIR      = Path(__file__).resolve().parent.parent / "data"
fighters_path = DATA_DIR / "fighters.json"
backups_dir   = DATA_DIR / "backups"

backups_dir.mkdir(exist_ok=True)

UFC_STATS = ["ufc-wins", "ufc-losses", "ufc-ko-tko-wins", "ufc-sub-wins"]

def main():
    backups_dir.mkdir(exist_ok=True)
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    backup_path = backups_dir / f"fighters_backup_{timestamp}.json"
    shutil.copy2(fighters_path, backup_path)
    print(f"Backup saved → {backup_path}")

    with open(fighters_path, "r", encoding="utf-8") as f:
        fighters = json.load(f)

    updated_grappling = 0
    updated_career    = 0
    zeroes_replaced   = 0

    for fighter in fighters:

        # ── Grappling: add ground-and-pound if missing ────────────────────────
        grappling = fighter.get("skillset", {}).get("grappling", {})
        if "ground-and-pound" not in grappling:
            new_grappling = {}
            for key, val in grappling.items():
                new_grappling[key] = val
                if key == "ground-control":
                    new_grappling["ground-and-pound"] = val
            grappling.clear()
            grappling.update(new_grappling)
            updated_grappling += 1

        # ── Career: add UFC stats fields if missing, replace 0s with -1 ──────
        career = fighter.get("career", {})
        career_changed = False

        for field in UFC_STATS:
            if field not in career:
                career[field] = -1
                career_changed = True
            elif career[field] == 0:
                career[field] = -1
                career_changed = True
                zeroes_replaced += 1

        if career_changed:
            updated_career += 1

    with open(fighters_path, "w", encoding="utf-8") as f:
        json.dump(fighters, f, indent=4, ensure_ascii=False)

    print(f"Done.")
    print(f"  Grappling updated : {updated_grappling} fighters (added 'ground-and-pound')")
    print(f"  Career updated    : {updated_career} fighters (added/fixed ufc stats fields)")
    print(f"  Zeroes replaced   : {zeroes_replaced} values set to -1")


if __name__ == "__main__":
    main()
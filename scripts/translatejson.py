import json
from pathlib import Path
from datetime import datetime
import shutil

DATA_DIR = Path(__file__).resolve().parent.parent / "data"

fighters_path = DATA_DIR / "fighters.json"
rankings_path = DATA_DIR / "rankings.json"

def escape_json_in_place(path: Path):
    path = Path(path)
    if not path.exists():
        print(f"File not found: {path}")
        return

    # Backup original file
    timestamp = datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")
    backup_path = path.with_suffix(path.suffix + f".bak.{timestamp}")
    shutil.copy2(path, backup_path)

    # Read raw bytes so Windows cp1252 doesn't choke
    with open(path, "rb") as f:
        raw = f.read()

    # Decode as UTF-8 with fallback so it never crashes
    text = raw.decode("utf-8", errors="replace")

    # Load JSON normally
    data = json.loads(text)

    # Write back with all non-ASCII escaped (in-place)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=True, indent=4)

    print(f"Cleaned and escaped JSON saved back to {path} (backup: {backup_path})")


def main():
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    # Process fighters.json
    try:
        escape_json_in_place(fighters_path)
    except Exception as e:
        print(f"Error processing {fighters_path}: {e}")

    # Process rankings.json
    try:
        escape_json_in_place(rankings_path)
    except Exception as e:
        print(f"Error processing {rankings_path}: {e}")


if __name__ == "__main__":
    main()

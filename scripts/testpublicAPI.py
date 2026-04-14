"""
Safe end-to-end checks for api.public_server using TestClient.
Writes a snapshot file next to this script: scripts/testpublicAPI_snapshot.json
"""

from pathlib import Path
import urllib.parse
import json
from pprint import pprint
import importlib
import logging

# Import the FastAPI app module (but do NOT create TestClient at import time)
try:
    mod = importlib.import_module("api.public_server")
    app = getattr(mod, "app")
except Exception as e:
    raise SystemExit(f"Failed to import api.public_server.app: {e}")

logger = logging.getLogger(__name__)


def safe_get(client, path: str, params: dict | None = None):
    """Helper: perform GET using the provided TestClient and return (status_code, json_or_text)."""
    r = client.get(path, params=params)
    try:
        body = r.json()
    except Exception:
        body = r.text
    return r.status_code, body


def choose_sample_name(fighters):
    if not isinstance(fighters, list) or not fighters:
        return None
    first = fighters[0]
    if isinstance(first, dict):
        # try several common keys
        return (
            first.get("personal-info", {}).get("name")
            or next((v for v in first.values() if isinstance(v, str)), None)
        )
    return str(first)


def main():
    # Module diagnostics (if module exposes DATA_DIR or dbs)
    info = {
        "module": mod.__name__,
        "has_DATA_DIR": hasattr(mod, "DATA_DIR"),
        "DATA_DIR": str(getattr(mod, "DATA_DIR", None)),
        "fighters_db_exists": hasattr(mod, "fighters_db"),
        "rankings_db_exists": hasattr(mod, "rankings_db"),
    }
    print("=== Module inspection ===")
    pprint(info)

    # Create TestClient as a context manager so FastAPI runs lifespan startup/shutdown
    from fastapi.testclient import TestClient

    with TestClient(app) as client:
        # 1) List fighters
        status, fighters = safe_get(client, "/fighters")
        print("\nGET /fighters ->", status)
        if isinstance(fighters, list):
            print("Total fighters:", len(fighters))
            pprint(fighters[:5])
        else:
            print("Unexpected response for /fighters:")
            pprint(fighters)

        # 2) Choose a sample name only if fighters exist
        sample_name = choose_sample_name(fighters)
        if not sample_name:
            print("\nNo fighters available; skipping exact-name lookup.")
            sample_lookup = {"status": None, "data": None}
        else:
            encoded = urllib.parse.quote(sample_name, safe="")
            status, fighter_data = safe_get(client, f"/fighters/{encoded}")
            print(f"\nGET /fighters/{sample_name} ->", status)
            pprint(fighter_data)
            sample_lookup = {"status": status, "data": fighter_data}

        # 3) Filter example
        params = {"gender": "male", "division": "Heavyweight"}
        status, filtered = safe_get(client, "/fighters", params=params)
        print("\nGET /fighters with filters ->", status)
        if isinstance(filtered, list):
            print("Filtered count:", len(filtered))
            pprint(filtered[:5])
        else:
            pprint(filtered)

        # 4) Rankings endpoint
        status, rankings = safe_get(client, "/rankings")
        print("\nGET /rankings ->", status)
        pprint(rankings.keys())

        # Division rankings
        status, div = safe_get(client, "/rankings/men's/lightweight")
        print("\n\nGET /rankings/men's/lightweight ->", status)
        if isinstance(div, list):
            pprint(div[:5])
        else:
            pprint(div)

        # Division champions
        params = {"gender" : "women's"}
        status, champs = safe_get(client, "/rankings/champions", params=params)
        print("\n\nGET /rankings/champions?gender=women's ->", status)
        pprint(champs)


        # Search for fighter's rank
        status, fighter = safe_get(client, "/rankings/search/Joe Pyfer")
        print("\n\nGET /rankings/search/Joe Pyfer ->", status)
        pprint(fighter)

        # Find divisions
        params = {"gender": "men's"}
        status, divs = safe_get(client, "/rankings/divisions", params=params)
        print("\n\nGET /rankings/divisions ->", status)
        pprint(divs)



        # 5) Prepare snapshot and write next to this script
        script_dir = Path(__file__).resolve().parent
        snapshot_path = script_dir / "testpublicAPI_snapshot.json"
        results = {
            "module_info": info,
            "all_fighters": fighters[:5],
            "sample_fighter_name": sample_name,
            "sample_fighter_lookup": sample_lookup,
            "filtered_fighters": filtered,
            "rankings": rankings,
            "division": div,
            "Champions": champs,
            "rank_of_fighter_lookup": fighter,
            "Divisions": divs
        }


        # Ensure directory exists and write snapshot
        script_dir.mkdir(parents=True, exist_ok=True)
        with open(snapshot_path, "w", encoding="utf-8") as fh:
            json.dump(results, fh, ensure_ascii=False, indent=2)
        print(f"\nSaved snapshot to {snapshot_path}")


if __name__ == "__main__":
    main()

from pathlib import Path
import json

DATA_DIR = Path(__file__).resolve().parent.parent / "data"

fighters_path = DATA_DIR / "fighters.json"
rankings_path = DATA_DIR / "rankings.json"


from core.fighter import Fighter


def get_rank(name):
    index = next((index for index, variable in enumerate(rankings_db) if name in variable), None)
    return index

def float_specs(flat_data: dict) -> dict:
    if "specs_height" in flat_data:
        try:
            flat_data["specs_height"] = float(flat_data["specs_height"])
        except Exception:
            flat_data["specs_height"] = 0.0
    if "specs_reach" in flat_data:
        try:
            flat_data["specs_reach"] = float(flat_data["specs_reach"])
        except Exception:
            flat_data["specs_reach"] = 0.0
    return flat_data

def load_data():
    global fighter_db, rankings_db
    fighter_db = load_fighters()
    rankings_db = load_rankings()
    return


def flat_dict(nested_dict):
    flat_results = {}

    def check(current_item, prefix=""):
        if isinstance(current_item, dict):
            for key, value in current_item.items():
                new_prefix = f"{prefix}_{key}" if prefix else key
                check(value, new_prefix)
        else:
            flat_results[prefix] = current_item

    check(nested_dict, "")
    return flat_results


def load_fighters():
    db = {}
    try:
        with open(fighters_path, 'r') as f:
            data = json.load(f)
            for item in data:
                flat_data = flat_dict(item)
                flat_data = float_specs(flat_data)
                fighter = Fighter(**flat_data)
                name_key = flat_data.get("personal-info_name", "Error: TYPO").lower()
                db[name_key] = fighter
    except FileNotFoundError:
        print("Error: MISSING FILE")
    except json.JSONDecodeError:
        print("Error: WRONG FORMAT")
    return db


def load_rankings():
    db = {}
    try:
        with open(rankings_path, 'r') as f:
            data = json.load(f)
            db = flat_dict(data)
    except FileNotFoundError:
        print("Error: MISSING FILE")
    except json.JSONDecodeError:
        print("Error: WRONG FORMAT")
    return db


empty_db = {
    "personal-info": {
        "name": "",
        "nickname": "",
        "birth-date": "",
        "nationality": "",
        "fighting-out-of": "",
        "country-code": "",
        "weight-class": "",
        "gym": "",
        "status": "",
        "gender": ""
    },
    "specs": {
        "height": 0,
        "reach": 0,
        "stance": ""
    },
    "skillset": {
        "striking": {
            "punches": {
                "jab": 0,
                "cross": 0,
                "haymaker": 0
            },
            "kicks": {
                "low": 0,
                "body": 0,
                "head": 0
            },
            "overview": {
                "power": 0,
                "accuracy": 0,
                "volume": 0,
                "defence": 0
            },
            "proportion": 0.0,
            "style": ""
        },
        "grappling": {
            "takedown": 0,
            "defence": 0,
            "submissions": 0,
            "ground-control": 0,
            "scrambles": 0,
            "style": ""
        },
        "clinch": {
            "clinch-control": 0,
            "clinch-striking": 0
        },
        "intangibles": {
            "stamina": 0,
            "chin": 0,
            "recovery": 0,
            "fight-iq": 0
        },
        "ratio": 0.0
    },
    "career": {
        "api-id": 0,
        "wins": 0,
        "losses": 0,
        "draws": 0,
        "no-contests": 0,
        "ko-tko-wins": 0,
        "sub-wins": 0,
        "win-streak": 0,
        "last-five": [0, 0, 0, 0, 0],
        "fight-history": []
    },
    "description": ""
}

rankings_index = {
    "Flyweight": 0,
    "Bantamweight": 1,
    "Featherweight": 2,
    "Lightweight": 3,
    "Welterweight": 4,
    "Middleweight": 5,
    "Light Heavyweight": 6,
    "Heavyweight": 7
}

load_data()
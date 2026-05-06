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
        with open(fighters_path, "r", encoding="utf-8") as f:
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


empty_db =     {
        "personal-info": {
            "name": "Youssef Zalal",
            "nickname": "The Moroccan Devil",
            "birth-date": "1996-09-04",
            "nationality": "Moroccan",
            "fighting-out-of": "Englewood, Colorado",
            "country-code": "MA",
            "weight-class": "Featherweight",
            "gym": "Factor X Muay Thai",
            "status": "Active",
            "gender": "Male"
        },
        "specs": {
            "height": 178.0,
            "reach": 72.0,
            "stance": "Switch"
        },
        "skillset": {
            "striking": {
                "punches": {
                    "jab": 9,
                    "cross": 8,
                    "haymaker": 7
                },
                "kicks": {
                    "low": 8,
                    "body": 7,
                    "head": 9
                },
                "overview": {
                    "power": 8,
                    "accuracy": 9,
                    "volume": 8,
                    "defence": 8,
                    "footwork": 10
                },
                "proportion": 0.45,
                "style": "Outside Sniper"
            },
            "grappling": {
                "takedown": 8,
                "takedown-defence": 8,
                "submissions": 10,
                "ground-control": 9,
                "ground-and-pound": 9,
                "scrambles": 9,
                "style": "Submission Specialist",
                "bottom-game": 7
            },
            "clinch": {
                "clinch-control": 9,
                "clinch-striking": 7
            },
            "intangibles": {
                "stamina": 7,
                "chin": 8,
                "durability": 9,
                "fight-iq": 8
            },
            "ratio": 0.55
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
    "Strawweight": -1,
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
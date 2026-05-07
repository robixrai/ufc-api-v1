import json
import re
from contextlib import asynccontextmanager
from copy import deepcopy
from pathlib import Path
from typing import Optional

import unicodedata
from fastapi import FastAPI, HTTPException

from core import predictor

DATA_DIR = Path(__file__).resolve().parent.parent
fighters_path = DATA_DIR / "data/fighters.json"
rankings_path = DATA_DIR / "data/rankings.json"
fights_path = DATA_DIR / "ufc_events.json"

rankings_db = []
fighters_db = {}
events_db = {}


@asynccontextmanager
async def lifespan(app: FastAPI):
    global rankings_db, fighters_db, events_db

    # load rankings
    try:
        with open(rankings_path, "r", encoding="utf-8") as f:
            rankings_db = deepcopy(json.load(f))
    except FileNotFoundError:
        raise RuntimeError("rankings.json missing")
    for gender in rankings_db.keys():
        for division in rankings_db[gender].keys():
            for index, fighter in enumerate(rankings_db[gender][division]):
                rankings_db[gender][division][index] = normalise_name(fighter)

    # load fighters list
    try:
        with open(fighters_path, "r", encoding="utf-8") as f:
            fighters_list = deepcopy(json.load(f))
    except FileNotFoundError:
        raise RuntimeError("fighters.json missing")

    # Build the fighters_db: key = normalised name, value = full fighter dict
    fighters_db = {}  # reset/ensure dict
    for item in fighters_list:
        personal = item.get("personal-info", {}) or {}
        raw_name = personal.get("name") or item.get("name")
        if not raw_name:
            continue
        key = normalise_name(raw_name)
        stored = deepcopy(item)
        stored.setdefault("personal-info", {}).setdefault("name", raw_name)
        fighters_db[key] = stored

    # optional quick log so you can verify at startup
    import logging
    logging.getLogger(__name__).info("Loaded fighters_db entries=%d sample_key=%s",
                                     len(fighters_db), next(iter(fighters_db), None))
    try:
        with open(fights_path, "r", encoding="utf-8") as f:
            events_db = json.load(f)
    except FileNotFoundError:
        events_db = {}

    yield


app = FastAPI(lifespan=lifespan)


def extract_champions():
    if rankings_db is None:
        raise HTTPException(status_code=500, detail="Rankings not loaded")

    champions = {}
    for gender_key, divisions in rankings_db.items():
        champions[gender_key] = {}
        for division, fighters in divisions.items():
            if division == "pound-for-pound":
                continue  # skip pound-for-pound
            if fighters:  # make sure list isn't empty
                champions[gender_key][division] = fighters[0]
    return champions


def normalise_name(user_input: Optional[str]) -> str:
    """
    Normalise only user-provided name/query strings for matching against your
    already-normalised fighters DB keys.
    Steps:
      - Return empty string for None/empty input
      - Trim and lowercase
      - Unicode NFKD normalise and strip combining marks (remove accents)
      - Remove any non-alphanumeric characters except spaces
      - Collapse multiple spaces to a single space
    """
    if not user_input:
        return ""
    s = user_input.strip().lower()
    s = unicodedata.normalize("NFKD", s)
    s = "".join(ch for ch in s if not unicodedata.combining(ch))
    s = re.sub(r"[^a-z\s]", "", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s


def copy_without_skillset(fighter_obj: dict) -> dict:
    """Return a shallow copy of fighter_obj with 'skillset' removed."""
    result = deepcopy(fighter_obj)
    result.pop("skillset", None)
    return result


@app.get("/rankings")
def get_rankings():
    return rankings_db


@app.get("/rankings/champions")
def get_champions(gender: Optional[str] = None, division: Optional[str] = None):
    if rankings_db is None:
        raise HTTPException(status_code=500, detail="Rankings not loaded")

    champions = extract_champions()

    # Normalise inputs
    gender_key = gender.lower() if gender else None
    division_key = division.lower() if division else None

    # Case 1: both gender and division provided
    if gender_key and division_key:
        if gender_key not in champions:
            raise HTTPException(status_code=404, detail=f"Gender '{gender}' not found")
        if division_key not in champions[gender_key]:
            raise HTTPException(
                status_code=404,
                detail=f"Division '{division}' not found under gender '{gender}'"
            )
        return {gender_key: {division_key: champions[gender_key][division_key]}}

    # Case 2: only gender provided
    if gender_key:
        if gender_key not in champions:
            raise HTTPException(status_code=404, detail=f"Gender '{gender}' not found")
        return {gender_key: champions[gender_key]}

    # Case 3: only division provided
    if division_key:
        filtered = {}
        for gk, divs in champions.items():
            if division_key in divs:
                filtered[gk] = {division_key: divs[division_key]}
        if not filtered:
            raise HTTPException(status_code=404, detail=f"Division '{division}' not found in any gender")
        return filtered

    # Case 4: no filters → return all champions
    return champions


@app.get("/rankings/search/{fighter}")
def search_fighter(fighter: str):
    """
    Search for a fighter across all genders and divisions.
    Returns a list of matches with name, gender ("Male" or "Female"), division and rank.
    Rank is "Champion" when index == 0, otherwise the numeric index.
    If no matches are found, returns {"result": "Unranked"}.
    """
    if rankings_db is None:
        raise HTTPException(status_code=500, detail="Rankings not loaded")

    query = normalise_name(fighter)
    matches = []

    for gender_key, divisions in rankings_db.items():
        for division, roster in divisions.items():
            for idx, person in enumerate(roster):
                if query in person.lower():
                    # Map stored gender key to "Male" or "Female"
                    display_gender = "Male" if gender_key.lower().startswith("men") else "Female"
                    rank = "Champion" if idx == 0 else idx
                    matches.append({
                        "name": person,
                        "gender": display_gender,
                        "division": division,
                        "rank": rank
                    })

    if not matches:
        return {query: "Unranked / Not Found"}

    return matches


@app.get("/rankings/divisions")
def list_divisions(gender: Optional[str] = None):
    if rankings_db is None:
        raise HTTPException(status_code=500, detail="Rankings not loaded")

    # If gender is provided → return divisions for that gender
    if gender:
        gender_key = gender.lower()
        if gender_key not in rankings_db:
            raise HTTPException(status_code=404, detail=f"Gender '{gender}' not found")
        return list(rankings_db[gender_key].keys())

    # Otherwise → return all divisions grouped by gender
    divisions = {}
    for gender_key, divs in rankings_db.items():
        divisions[gender_key] = list(divs.keys())
    return divisions


@app.get("/rankings/{gender}")
def get_gender_rankings(gender: str):
    if rankings_db is None:
        raise HTTPException(status_code=500, detail="Rankings not loaded")

    gender_key = gender.lower()
    if gender_key not in rankings_db:
        raise HTTPException(status_code=404, detail=f"Gender '{gender}' not found")

    # Return all divisions under this gender
    return rankings_db[gender_key]


@app.get("/rankings/{gender}/{division}")
def get_division_rankings(gender: str, division: str, rank: Optional[int] = None):
    if rankings_db is None:
        raise HTTPException(status_code=500, detail="Rankings not loaded")

    gender_key = gender.lower()
    division_key = division.lower()

    if gender_key not in rankings_db:
        raise HTTPException(status_code=404, detail=f"Gender '{gender}' not found")
    if division_key not in rankings_db[gender_key]:
        raise HTTPException(status_code=404, detail=f"Division '{division}' not found under gender '{gender}'")

    fighters = rankings_db[gender_key][division_key]

    # If rank is provided, return just that fighter
    if rank is not None:
        if rank < 0 or rank > 16:
            raise HTTPException(status_code=400, detail=f"Invalid rank '{rank}'. Must be between 0 and 16")
        return fighters[rank]

    # Otherwise return the full division list
    return fighters


@app.get("/fighters/{name}")
def get_fighter(name: str, block: Optional[str] = None):
    """
    Search for a fighter by name.
    - Exact match first
    - If not found, partial search across fighters_db keys
    - Returns fighter dict without 'skillset'
    - If block is provided, return only that section (personal-info, specs, career)
    - If no match at all, returns "Fighter not found / Not in database"
    """
    if fighters_db is None:
        raise HTTPException(status_code=500, detail="Fighters are not loaded")

    norm_query = normalise_name(name)
    if not norm_query:
        raise HTTPException(status_code=404, detail=f"Fighter {name} not found / Not in database")

    # Exact lookup
    fighter = fighters_db.get(norm_query)
    if not fighter:
        # Partial search
        for key in fighters_db.keys():
            if norm_query in key:
                fighter = fighters_db[key]
                break

    if not fighter:
        raise HTTPException(status_code=404, detail=f"Fighter {name} not found / Not in database")

    fighter_copy = copy_without_skillset(fighter)

    # If block is specified, return only that section
    if block in {"personal-info", "specs", "career"}:
        return fighter_copy.get(block, {})

    return fighter_copy


@app.get("/fighters")
def list_fighters(gender: Optional[str] = None, division: Optional[str] = None):
    """
    Return a list of fighter names.
    - If no parameters are given, return all names.
    - If gender and/or division are provided, filter accordingly.
    - Filtering is based on fighter["personal-info"]["gender"] and fighter["personal-info"]["weight-class"].
    - Parameters are normalised before comparison.
    """
    if fighters_db is None:
        raise HTTPException(status_code=500, detail="Fighters are not loaded")

    # Normalise parameters if present
    norm_gender = normalise_name(gender) if gender else None
    norm_division = normalise_name(division) if division else None

    results = []
    for name, fighter in fighters_db.items():
        info = fighter["personal-info"]
        f_gender = normalise_name(info["gender"])
        f_division = normalise_name(info["weight-class"])

        # Apply filters
        if norm_gender and norm_division:
            if f_gender == norm_gender and f_division == norm_division:
                results.append(name)
        elif norm_gender:
            if f_gender == norm_gender:
                results.append(name)
        elif norm_division:
            if f_division == norm_division:
                results.append(name)
        else:
            # No filters, include all
            results.append(name)

    return results


@app.get("/predict/{f1}/{f2}")
def predict_matchup(f1: str, f2: str):
    if not fighters_db:
        raise HTTPException(status_code=500, detail="Database not initialized")

    # 1. Normalise names and fetch Fighter objects
    n1 = normalise_name(f1.replace("_", " "))
    n2 = normalise_name(f2.replace("_", " "))
    fighter1_obj = fighters_db.get(n1)
    fighter2_obj = fighters_db.get(n2)

    if not fighter1_obj or not fighter2_obj:
        missing = []
        if not fighter1_obj: missing.append(f1)
        if not fighter2_obj: missing.append(f2)
        raise HTTPException(status_code=404, detail=f"Fighter(s) not found: {missing}")

    # 2. Determine rounds from ufc_events.json
    rounds = 3
    for event in events_db.values():
        all_bouts = event.get("main_card", []) + event.get("prelims", [])
        for bout in all_bouts:
            b1_norm = normalise_name(bout.get("fighter1", ""))
            b2_norm = normalise_name(bout.get("fighter2", ""))
            if (n1 == b1_norm and n2 == b2_norm) or (n1 == b2_norm and n2 == b1_norm):
                try:
                    rounds = int(bout.get("rounds", 3))
                except (ValueError, TypeError):
                    rounds = 3
                break

    # 3. Run prediction
    try:
        _, _, result = predictor.predict_fight(fighter1_obj, fighter2_obj, rounds=rounds, json=1)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Model Error: {str(e)}")


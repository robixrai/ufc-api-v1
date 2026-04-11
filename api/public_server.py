from typing import Optional
from fastapi import FastAPI, HTTPException
from contextlib import asynccontextmanager
import json
from pathlib import Path
import re
import unicodedata




DATA_DIR = Path(__file__).resolve().parent.parent / "data"
fighters_path = DATA_DIR / "fighters.json"
rankings_path = DATA_DIR / "rankings.json"

rankings_db = None
fighters_db = {}


@asynccontextmanager
async def lifespan(app: FastAPI):
    global rankings_db, fighters_db
    try:
        with open(rankings_path, "r", encoding="utf-8") as f:
            rankings_db = json.load(f)
    except FileNotFoundError:
        raise RuntimeError("File missing")

    try:
        with open(fighters_path, "r", encoding="utf-8") as f:
            fighters_list = json.load(f)
    except FileNotFoundError:
        raise RuntimeError("fighters.json missing")

        # Build the fighters_db: key = personal-info.name, value = full fighter dict
    for item in fighters_list:
        # defensive extraction of the nested name
        personal = item.get("personal-info", {})
        name = personal.get("name")
        if not name:
            # skip entries without a name (or you could raise/log depending on preference)
            continue
        # store the full object under the canonical name
        fighters_db[name] = item
    # Yield control back to FastAPI (startup complete)
    yield
    # Optional cleanup code goes here (runs on shutdown)

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

def normalize_name(user_input: Optional[str]) -> str:
    """
    Normalize only user-provided name/query strings for matching against your
    already-normalized fighters DB keys.
    Steps:
      - Return empty string for None/empty input
      - Trim and lowercase
      - Unicode NFKD normalize and strip combining marks (remove accents)
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


@app.get("/rankings")
def get_rankings():
    return rankings_db

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

@app.get("/rankings/champions")
def get_champions(gender: Optional[str] = None, division: Optional[str] = None):
    if rankings_db is None:
        raise HTTPException(status_code=500, detail="Rankings not loaded")

    champions = extract_champions()

    # Normalize inputs
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

    query = fighter.lower()
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
        return {query : "Unranked / Not Found"}

    return matches






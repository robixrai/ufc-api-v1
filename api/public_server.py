from typing import Optional
from fastapi import FastAPI, HTTPException
from contextlib import asynccontextmanager
import json
from pathlib import Path



DATA_DIR = Path(__file__).resolve().parent.parent / "data"
fighters_path = DATA_DIR / "fighters.json"
rankings_path = DATA_DIR / "rankings.json"

rankings_db = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    global rankings_db
    try:
        with open(rankings_path, "r", encoding="utf-8") as f:
            rankings_db = json.load(f)
    except FileNotFoundError:
        raise RuntimeError("Rankings file missing")
    # Yield control back to FastAPI (startup complete)
    yield
    # Optional cleanup code goes here (runs on shutdown)

app = FastAPI(lifespan=lifespan)

def extract_champions(gender_key: str):
    champions = {}
    for division, fighters in rankings_db[gender_key].items():
        if division == "pound-for-pound":
            continue
        if fighters:
            champions[division] = fighters[0]
    return champions

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
            raise HTTPException(status_code=400, detail=f"Invalid rank '{rank}'. Must be between 0 and {len(fighters)-1}")
        return fighters[rank]

    # Otherwise return the full division list
    return fighters


@app.get("/rankings/champions")
def get_champions(gender: Optional[str] = None, division: Optional[str] = None):
    if rankings_db is None:
        raise HTTPException(status_code=500, detail="Rankings not loaded")

    champions = {}

    # If gender is provided
    if gender:
        gender_key = gender.lower()
        if gender_key not in rankings_db:
            raise HTTPException(status_code=404, detail=f"Gender '{gender}' not found")

        # If division is also provided
        if division:
            division_key = division.lower()
            if division_key not in rankings_db[gender_key]:
                raise HTTPException(
                    status_code=404,
                    detail=f"Division '{division}' not found under gender '{gender}'"
                )
            if division_key == "pound-for-pound":
                raise HTTPException(status_code=400, detail="No champion for pound-for-pound divisions")
            fighters = rankings_db[gender_key][division_key]
            if not fighters:
                raise HTTPException(status_code=404, detail=f"No fighters found in {gender} {division}")
            return {f"{gender_key}_{division_key}": fighters[0]}

        # Gender only → all divisions for that gender
        for div, fighters in rankings_db[gender_key].items():
            if div == "pound-for-pound":
                continue
            if fighters:
                champions[f"{gender_key}_{div}"] = fighters[0]
        return champions

    # No gender provided → all genders
    for gender_key, divisions in rankings_db.items():
        for div, fighters in divisions.items():
            if div == "pound-for-pound":
                continue
            if fighters:
                champions[f"{gender_key}_{div}"] = fighters[0]

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






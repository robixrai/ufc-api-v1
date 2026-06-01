import json
import os
import sys
from datetime import datetime
from pathlib import Path

# ─── Paths ────────────────────────────────────────────────────────────────────
BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
PREDICTIONS_FILE = Path(__file__).resolve().parent / "predictions_log.json"
EVENTS_FILE = DATA_DIR / "ufc_events.json"
FIGHTERS_FILE = DATA_DIR / "fighters.json"

# ─── Import predictor ─────────────────────────────────────────────────────────
sys.path.insert(0, str(BASE_DIR))
from core.predictor import Predict

predictor = Predict()

# ─── Storage ──────────────────────────────────────────────────────────────────
def _input(prompt=""):
    """input() wrapper that strips all surrounding whitespace including stray newlines."""
    return input(prompt).strip()

def load():
    if PREDICTIONS_FILE.exists():
        with open(PREDICTIONS_FILE, encoding="utf-8") as f:
            return json.load(f)
    return {}

def save(data):
    with open(PREDICTIONS_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)

def load_events():
    with open(EVENTS_FILE, encoding="utf-8") as f:
        return json.load(f)

def load_fighters():
    with open(FIGHTERS_FILE, encoding="utf-8") as f:
        return json.load(f)

def save_fighters(fighters):
    with open(FIGHTERS_FILE, "w", encoding="utf-8") as f:
        json.dump(fighters, f, indent=4, ensure_ascii=False)

# ─── Fighter DB lookup ────────────────────────────────────────────────────────
def find_fighter(fighters, name):
    """Find a fighter by name (case-insensitive, exact then partial)."""
    name_lower = name.lower().strip()
    for fighter in fighters:
        if fighter.get("personal-info", {}).get("name", "").lower() == name_lower:
            return fighter
    for fighter in fighters:
        if name_lower in fighter.get("personal-info", {}).get("name", "").lower():
            return fighter
    return None

# ─── Event fight lookup ───────────────────────────────────────────────────────
def get_fight_rounds(event_name, f1, f2):
    """Return the scheduled rounds for a fight from ufc_events.json."""
    try:
        events = load_events()
        event = events.get(event_name, {})
        all_fights = event.get("main_card", []) + event.get("prelims", [])
        f1_l, f2_l = f1.lower(), f2.lower()
        for fight in all_fights:
            a = fight.get("fighter1", "").lower()
            b = fight.get("fighter2", "").lower()
            if (a == f1_l and b == f2_l) or (a == f2_l and b == f1_l):
                return fight.get("rounds", 3)
    except Exception:
        pass
    return 3  # fallback

# ─── Method helpers ───────────────────────────────────────────────────────────

# KO/TKO finish types
KO_TYPES = [
    "Punches", "Punch", "Elbows", "Elbow", "Head Kick", "Body Kick",
    "Knee", "Knees", "Stomp", "Flying Knee", "Spinning Back Fist",
    "Head Kick and Punches", "Punches and Elbows", "Other (KO/TKO)",
]

# Submission types
SUB_TYPES = [
    "Rear Naked Choke", "Guillotine", "Arm Triangle", "Armbar",
    "Triangle Choke", "D'Arce Choke", "Anaconda Choke", "Heel Hook",
    "Rear Naked Choke (Body Triangle)", "North-South Choke",
    "Ezekiel Choke", "Von Flue Choke", "Kimura", "Rear Naked Choke",
    "Other (Sub)",
]

DECISION_TYPES = ["U-Dec", "S-Dec", "M-Dec"]
SPECIAL_TYPES  = ["Draw", "No Contest"]

def prompt_finish_category():
    print("\n  Finish category:")
    print("    1. KO/TKO")
    print("    2. Submission")
    print("    3. Decision")
    print("    4. Draw")
    print("    5. No Contest")
    return _input("  > ")

def prompt_ko_type():
    print("\n  KO/TKO type:")
    for i, t in enumerate(KO_TYPES, 1):
        print(f"    {i:>2}. {t}")
    choice = _input("  > ").strip()
    try:
        return KO_TYPES[int(choice) - 1]
    except (ValueError, IndexError):
        return _input("  Enter manually: ")

def prompt_sub_type():
    print("\n  Submission type:")
    for i, t in enumerate(SUB_TYPES, 1):
        print(f"    {i:>2}. {t}")
    choice = _input("  > ").strip()
    try:
        return SUB_TYPES[int(choice) - 1]
    except (ValueError, IndexError):
        return _input("  Enter manually: ")

def prompt_decision_type():
    print("\n  Decision type:")
    for i, t in enumerate(DECISION_TYPES, 1):
        print(f"    {i}. {t}")
    choice = _input("  > ").strip()
    try:
        return DECISION_TYPES[int(choice) - 1]
    except (ValueError, IndexError):
        return "U-Dec"

def prompt_method_full(event_name, f1, f2):
    """
    Prompt for finish category then sub-type.
    Returns (method_str, bucket, round_num, time_str, actual_winner_needed).
    For decisions, round/time are calculated automatically.
    """
    cat = prompt_finish_category()

    if cat == "1":
        sub = prompt_ko_type()
        method = f"KO/TKO - {sub}"
        bucket = "KO"
        round_num = _input("\n  Round: ").strip()
        time_str  = _input("  Time (e.g. 3:45): ").strip()
        return method, bucket, round_num, time_str, True

    elif cat == "2":
        sub = prompt_sub_type()
        method = f"Sub - {sub}"
        bucket = "Sub"
        round_num = _input("\n  Round: ").strip()
        time_str  = _input("  Time (e.g. 3:45): ").strip()
        return method, bucket, round_num, time_str, True

    elif cat == "3":
        method = prompt_decision_type()
        bucket = "Dec"
        # auto-calculate from scheduled rounds
        rounds = get_fight_rounds(event_name, f1, f2)
        round_num = str(rounds)
        time_str  = "5:00"
        print(f"\n  → Decision: R{round_num} 5:00 (auto)")
        return method, bucket, round_num, time_str, True

    elif cat == "4":
        rounds = get_fight_rounds(event_name, f1, f2)
        round_num = str(rounds)
        time_str  = "5:00"
        print(f"\n  → Draw: R{round_num} 5:00 (auto)")
        return "Draw", "Draw", round_num, time_str, False

    elif cat == "5":
        round_num = _input("\n  Round NC occurred: ").strip()
        time_str  = _input("  Time (e.g. 2:11): ").strip()
        return "No Contest", "NC", round_num, time_str, False

    else:
        print("  Invalid category.")
        return None, None, None, None, None

def method_to_bucket(method):
    """Map granular method string to KO/Sub/Dec bucket for predictor scoring."""
    if method is None:
        return None
    m = method.upper()
    if m.startswith("KO") or "KO/TKO" in m:
        return "KO"
    if m.startswith("SUB"):
        return "Sub"
    if "DEC" in m:
        return "Dec"
    return method  # Draw / No Contest pass through

def is_ufc_fight(event_name):
    """Treat all events as UFC — adjust here if non-UFC events are added."""
    return True

# ─── DB update ────────────────────────────────────────────────────────────────
def update_fighter_db(fighters, fighter_name, opponent_name, result, method,
                      round_num, time_str, event_name, is_ufc):
    """
    Update a fighter's career block in-place.
    result : "W" | "L" | "D" | "NC"
    """
    fighter = find_fighter(fighters, fighter_name)
    if not fighter:
        print(f"  ⚠ Could not find '{fighter_name}' in fighters DB — skipping.")
        return False

    career = fighter.setdefault("career", {})
    bucket = method_to_bucket(method)

    # ── wins / losses / draws / no-contests ───────────────────────────────────
    if result == "W":
        career["wins"] = career.get("wins", 0) + 1
        if bucket == "KO":
            career["ko-tko-wins"] = career.get("ko-tko-wins", 0) + 1
        elif bucket == "Sub":
            career["sub-wins"] = career.get("sub-wins", 0) + 1
        if is_ufc:
            career["ufc-wins"] = career.get("ufc-wins", 0) + 1
            if bucket == "KO":
                career["ufc-ko-tko-wins"] = career.get("ufc-ko-tko-wins", 0) + 1
            elif bucket == "Sub":
                career["ufc-sub-wins"] = career.get("ufc-sub-wins", 0) + 1

    elif result == "L":
        career["losses"] = career.get("losses", 0) + 1
        if is_ufc:
            career["ufc-losses"] = career.get("ufc-losses", 0) + 1

    elif result == "D":
        career["draws"] = career.get("draws", 0) + 1

    elif result == "NC":
        career["no-contests"] = career.get("no-contests", 0) + 1

    # ── win-streak ────────────────────────────────────────────────────────────
    if result == "W":
        career["win-streak"] = career.get("win-streak", 0) + 1
    elif result in ("L", "D", "NC"):
        career["win-streak"] = 0

    # ── last-five (newest at front, max 5) ────────────────────────────────────
    last_five_map = {"W": 1, "L": 0, "D": 2, "NC": 3}
    lf = career.get("last-five", [])
    lf = [last_five_map.get(result, 0)] + lf
    career["last-five"] = lf[:5]

    # ── fight-history (newest at front) ───────────────────────────────────────
    # e.g. "W vs Jon Jones (KO/TKO - Head Kick) R2 3:45 - UFC 300"
    history_entry = (
        f"{result} vs {opponent_name} ({method}) "
        f"R{round_num} {time_str} - {event_name}"
    )
    fh = career.get("fight-history", [])
    fh.insert(0, history_entry)
    career["fight-history"] = fh

    print(f"  ✓ DB updated: {fighter_name} → {history_entry}")
    return True

# ─── Lock predictions for an event ────────────────────────────────────────────
def lock_event(data):
    from core.tools import fighter_db

    events = load_events()
    event_names = list(events.keys())

    print("\n  Available events:")
    for i, name in enumerate(event_names, 1):
        locked = "LOCKED" if name in data else ""
        print(f"    {i}. {name} {locked}")

    choice = _input("\n  Select event number: ").strip()
    try:
        event_name = event_names[int(choice) - 1]
    except (ValueError, IndexError):
        print("  Invalid choice.")
        return

    if event_name in data:
        redo = _input(f"  Predictions already locked for {event_name}. Redo? (y/n): ").strip().lower()
        if redo != "y":
            return
        del data[event_name]

    event = events[event_name]
    all_fights = event.get("main_card", []) + event.get("prelims", [])

    data[event_name] = {"locked_at": datetime.now().isoformat(), "fights": {}}

    print(f"\n  Running predictor for {event_name}...\n")

    for fight in all_fights:
        f1 = fight["fighter1"]
        f2 = fight["fighter2"]
        rounds = fight["rounds"]
        key = f"{f1} vs {f2}"

        try:
            f1_obj = fighter_db.get(f1.lower())
            f2_obj = fighter_db.get(f2.lower())

            if not f1_obj:
                print(f"  ✗ SKIPPED {key}: {f1} not found in fighters_db")
                continue
            if not f2_obj:
                print(f"  ✗ SKIPPED {key}: {f2} not found in fighters_db")
                continue

            win_prob, lose_prob, logs = predictor.predict_fight(f1_obj, f2_obj, rounds, json=0)

            if win_prob >= 0.5:
                winner = f1
                prob = round(win_prob * 100, 1)
            else:
                winner = f2
                prob = round(lose_prob * 100, 1)

            fight_method = "Dec"
            for line in logs.splitlines():
                if "Most likely method" in line:
                    if "KO/TKO" in line:
                        fight_method = "KO"
                    elif "Submission" in line:
                        fight_method = "Sub"
                    else:
                        fight_method = "Dec"
                    break

            winner_method = "Dec"
            winner_section = False
            for line in logs.splitlines():
                if f"METHOD PROFILE : {winner}" in line:
                    winner_section = True
                if winner_section and "Final profile" in line:
                    ko_val  = float(line.split("KO:")[1].split()[0])
                    sub_val = float(line.split("Sub:")[1].split()[0])
                    dec_val = float(line.split("Dec:")[1].split()[0])
                    best = max(ko_val, sub_val, dec_val)
                    if best == ko_val:
                        winner_method = "KO"
                    elif best == sub_val:
                        winner_method = "Sub"
                    else:
                        winner_method = "Dec"
                    break

            data[event_name]["fights"][key] = {
                "predicted_winner": winner,
                "predicted_winner_method": winner_method,
                "predicted_fight_method": fight_method,
                "win_probability": prob,
                "actual_winner": None,
                "actual_winner_method": None,
                "actual_fight_method": None,
                "winner_correct": None,
                "winner_method_correct": None,
                "fight_method_correct": None,
            }
            print(f"  ✓ {key}")
            print(f"    → {winner} by {winner_method} (winner method) / {fight_method} (fight method) ({prob}%)")

        except Exception as e:
            print(f"  ✗ SKIPPED {key}: {e}")

    save(data)
    print(f"\n  Predictions locked for {event_name}.")

# ─── Log result ───────────────────────────────────────────────────────────────
def log_result(data):
    event_names = list(data.keys())
    if not event_names:
        print("  No locked predictions found.")
        return

    print("\n  Locked events:")
    for i, name in enumerate(event_names, 1):
        print(f"    {i}. {name}")

    choice = _input("\n  Select event number: ").strip()
    try:
        event_name = event_names[int(choice) - 1]
    except (ValueError, IndexError):
        print("  Invalid choice.")
        return

    fights = data[event_name]["fights"]
    fight_keys = list(fights.keys())

    print("\n  Fights:")
    for i, key in enumerate(fight_keys, 1):
        fight = fights[key]
        if fight["actual_winner"] is not None:
            status = "✓" if fight["winner_correct"] else "✗"
        else:
            status = "—"
        print(f"    {i}. [{status}] {key}")

    choice = _input("\n  Select fight number: ").strip()
    try:
        key = fight_keys[int(choice) - 1]
    except (ValueError, IndexError):
        print("  Invalid choice.")
        return

    fight = fights[key]
    f1, f2 = [s.strip() for s in key.split(" vs ", 1)]

    # ── who won? ──────────────────────────────────────────────────────────────
    print(f"\n  Result:")
    print(f"    1. {f1} won")
    print(f"    2. {f2} won")
    print(f"    3. Draw")
    print(f"    4. No Contest")
    result_choice = _input("  > ").strip()

    if result_choice == "1":
        actual_winner = f1
        result_f1, result_f2 = "W", "L"
    elif result_choice == "2":
        actual_winner = f2
        result_f1, result_f2 = "L", "W"
    elif result_choice == "3":
        actual_winner = None
        result_f1 = result_f2 = "D"
    elif result_choice == "4":
        actual_winner = None
        result_f1 = result_f2 = "NC"
    else:
        print("  Invalid choice.")
        return

    # ── gather finish details ─────────────────────────────────────────────────
    method, bucket, round_num, time_str, _ = prompt_method_full(event_name, f1, f2)
    if method is None:
        return

    # ── update predictions log ────────────────────────────────────────────────
    fight["actual_winner"]        = actual_winner if actual_winner else result_f1
    fight["actual_winner_method"] = method
    fight["actual_fight_method"]  = method
    fight["winner_correct"] = (
        fight["predicted_winner"] == actual_winner if actual_winner else None
    )
    fight["winner_method_correct"] = (
        method_to_bucket(fight["predicted_winner_method"]) == bucket
        if actual_winner else None
    )
    fight["fight_method_correct"] = (
        method_to_bucket(fight["predicted_fight_method"]) == bucket
        if actual_winner else None
    )
    save(data)

    # ── update fighters DB ────────────────────────────────────────────────────
    ufc      = is_ufc_fight(event_name)
    fighters = load_fighters()
    update_fighter_db(fighters, f1, f2, result_f1, method, round_num, time_str, event_name, ufc)
    update_fighter_db(fighters, f2, f1, result_f2, method, round_num, time_str, event_name, ufc)
    save_fighters(fighters)

    # ── summary ───────────────────────────────────────────────────────────────
    print()
    if actual_winner:
        w_icon  = "✓" if fight["winner_correct"]        else "✗"
        wm_icon = "✓" if fight["winner_method_correct"] else "✗"
        fm_icon = "✓" if fight["fight_method_correct"]  else "✗"
        print(f"  Winner {w_icon}  Winner Method {wm_icon}  Fight Method {fm_icon}")
    else:
        print(f"  Result: {result_f1} — no winner recorded.")

# ─── View predictions ─────────────────────────────────────────────────────────
def view_predictions(data):
    event_names = list(data.keys())
    if not event_names:
        print("  No locked predictions found.")
        return

    print("\n  Locked events:")
    for i, name in enumerate(event_names, 1):
        print(f"    {i}. {name}")

    choice = _input("\n  Select event number: ").strip()
    try:
        event_name = event_names[int(choice) - 1]
    except (ValueError, IndexError):
        print("  Invalid choice.")
        return

    print(f"\n  {event_name}")
    print("  " + "─" * 50)
    for key, fight in data[event_name]["fights"].items():
        w  = fight.get("winner_correct")
        wm = fight.get("winner_method_correct")
        fm = fight.get("fight_method_correct")
        w_icon  = "✓" if w  else ("✗" if w  is False else "—")
        wm_icon = "✓" if wm else ("✗" if wm is False else "—")
        fm_icon = "✓" if fm else ("✗" if fm is False else "—")
        print(f"\n  {key}")
        print(f"    Predicted : {fight['predicted_winner']} by {fight['predicted_winner_method']} (winner method) / {fight['predicted_fight_method']} (fight method) ({fight['win_probability']}%)")
        if fight.get("actual_winner"):
            print(f"    Actual    : {fight['actual_winner']} — winner method: {fight.get('actual_winner_method')} / fight method: {fight.get('actual_fight_method')}")
        print(f"    Result    : Winner {w_icon}  Winner Method {wm_icon}  Fight Method {fm_icon}")

# ─── Accuracy ─────────────────────────────────────────────────────────────────
def print_accuracy(data):
    total = win_c = winner_method_c = fight_method_c = resolved = 0
    for event in data.values():
        for fight in event["fights"].values():
            total += 1
            if fight.get("actual_winner") is not None:
                resolved += 1
                win_c           += int(bool(fight.get("winner_correct")))
                winner_method_c += int(bool(fight.get("winner_method_correct")))
                fight_method_c  += int(bool(fight.get("fight_method_correct")))

    print(f"\n  OVERALL               {total} fights ({resolved} resolved)")
    if resolved:
        print(f"  Win accuracy          {win_c}/{resolved}  ({win_c/resolved:.1%})")
        print(f"  Winner method acc.    {winner_method_c}/{resolved}  ({winner_method_c/resolved:.1%})")
        print(f"  Fight method acc.     {fight_method_c}/{resolved}  ({fight_method_c/resolved:.1%})")
    else:
        print("  No results logged yet.")

# ─── Main ─────────────────────────────────────────────────────────────────────
def main():
    while True:
        data = load()
        print("\n─── FIGHT ORACLE ───────────────────────")
        print("  1. Lock predictions for event")
        print("  2. Log result")
        print("  3. View event predictions")
        print("  4. Overall accuracy")
        print("  5. Exit")
        print("────────────────────────────────────────")
        choice = _input("  > ").strip()

        if choice == "1":
            lock_event(data)
        elif choice == "2":
            log_result(data)
        elif choice == "3":
            view_predictions(data)
        elif choice == "4":
            print_accuracy(data)
        elif choice == "5":
            break
        else:
            print("  Invalid choice.")

if __name__ == "__main__":
    main()
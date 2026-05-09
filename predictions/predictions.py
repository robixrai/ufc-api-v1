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

# ─── Import predictor ─────────────────────────────────────────────────────────
sys.path.insert(0, str(BASE_DIR))
from core.predictor import Predict

predictor = Predict()

# ─── Storage ──────────────────────────────────────────────────────────────────
def load():
    if PREDICTIONS_FILE.exists():
        with open(PREDICTIONS_FILE) as f:
            return json.load(f)
    return {}

def save(data):
    with open(PREDICTIONS_FILE, "w") as f:
        json.dump(data, f, indent=4)

def load_events():
    with open(EVENTS_FILE) as f:
        return json.load(f)

# ─── Lock predictions for an event ────────────────────────────────────────────
def lock_event(data):
    from core.tools import fighter_db

    events = load_events()
    event_names = list(events.keys())

    print("\n  Available events:")
    for i, name in enumerate(event_names, 1):
        locked = "LOCKED" if name in data else ""
        print(f"    {i}. {name} {locked}")

    choice = input("\n  Select event number: ").strip()
    try:
        event_name = event_names[int(choice) - 1]
    except (ValueError, IndexError):
        print("  Invalid choice.")
        return

    if event_name in data:
        if event_name in data:
            redo = input(f"  Predictions already locked for {event_name}. Redo? (y/n): ").strip().lower()
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

            win_prob, lose_prob, logs = predictor.predict_fight(f1_obj, f2_obj, rounds,json=0)

            # determine winner
            if win_prob >= 0.5:
                winner = f1
                prob = round(win_prob * 100, 1)
            else:
                winner = f2
                prob = round(lose_prob * 100, 1)

            # parse combined fight method
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

            # parse winner's individual method from their "Final profile" line
            # logs have two METHOD PROFILE blocks — winner is f1 if win_prob >= 0.5, else f2
            # we find the Final profile line for the winner's block
            winner_method = "Dec"
            winner_section = False
            for line in logs.splitlines():
                if f"METHOD PROFILE : {winner}" in line:
                    winner_section = True
                if winner_section and "Final profile" in line:
                    # line looks like: Final profile  →  KO: 0.352   Sub: 0.622   Dec: 0.026
                    parts = line.split("KO:")[1].split("Sub:")[1].split("Dec:")
                    ko_val = float(line.split("KO:")[1].split()[0])
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
                "actual_method": None,
                "winner_correct": None,
                "method_correct": None,
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

    choice = input("\n  Select event number: ").strip()
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
        if fight["actual_winner"]:
            status = "✓" if fight["winner_correct"] else "✗"
        else:
            status = "—"
        print(f"    {i}. [{status}] {key}")

    choice = input("\n  Select fight number: ").strip()
    try:
        key = fight_keys[int(choice) - 1]
    except (ValueError, IndexError):
        print("  Invalid choice.")
        return

    actual_winner = input("  Actual winner: ").strip()
    print("  Method: 1. KO  2. Sub  3. Dec")
    method_choice = input("  > ").strip()
    method_map = {"1": "KO", "2": "Sub", "3": "Dec"}
    actual_method = method_map.get(method_choice)
    if not actual_method:
        print("  Invalid method.")
        return

    fight = fights[key]
    fight["actual_winner"] = actual_winner
    fight["actual_method"] = actual_method
    fight["winner_correct"] = fight["predicted_winner"] == actual_winner
    fight["method_correct"] = fight["predicted_method"] == actual_method
    save(data)
    print(f"\n  Winner: {'✓' if fight['winner_correct'] else '✗'}  Method: {'✓' if fight['method_correct'] else '✗'}")

# ─── View predictions ─────────────────────────────────────────────────────────
def view_predictions(data):
    event_names = list(data.keys())
    if not event_names:
        print("  No locked predictions found.")
        return

    print("\n  Locked events:")
    for i, name in enumerate(event_names, 1):
        print(f"    {i}. {name}")

    choice = input("\n  Select event number: ").strip()
    try:
        event_name = event_names[int(choice) - 1]
    except (ValueError, IndexError):
        print("  Invalid choice.")
        return

    print(f"\n  {event_name}")
    print("  " + "─" * 50)
    for key, fight in data[event_name]["fights"].items():
        w = fight["winner_correct"]
        m = fight["method_correct"]
        w_icon = "✓" if w else ("✗" if w is False else "—")
        m_icon = "✓" if m else ("✗" if m is False else "—")
        print(f"\n  {key}")
        print(f"    Predicted : {fight['predicted_winner']} by {fight['predicted_winner_method']} (winner) / {fight['predicted_fight_method']} (fight) ({fight['win_probability']}%)")
        if fight["actual_winner"]:
            print(f"    Actual    : {fight['actual_winner']} by {fight['actual_method']}")
        print(f"    Result    : Winner {w_icon}  Method {m_icon}")

# ─── Accuracy ─────────────────────────────────────────────────────────────────
def print_accuracy(data):
    total = win_c = method_c = resolved = 0
    for event in data.values():
        for fight in event["fights"].values():
            total += 1
            if fight["actual_winner"] is not None:
                resolved += 1
                win_c += int(fight["winner_correct"])
                method_c += int(fight["method_correct"])

    print(f"\n  OVERALL          {total} fights ({resolved} resolved)")
    if resolved:
        print(f"  Win accuracy     {win_c}/{resolved}  ({win_c/resolved:.1%})")
        print(f"  Method accuracy  {method_c}/{resolved}  ({method_c/resolved:.1%})")
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
        choice = input("  > ").strip()

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
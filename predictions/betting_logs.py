"""
betting.py

UFC Betting Tracker — Menu-driven interface.
Tracks bets, compares bookmaker odds to your predictor model,
calculates EV, and manages a fake bankroll.

Run from project root:
    python betting.py
"""

import json
import os
from pathlib import Path
from datetime import datetime

# ── Project imports ────────────────────────────────────────────────────────────
from core.tools import fighter_db
from core.predictor import Predict

predictor = Predict()

# ── Config ─────────────────────────────────────────────────────────────────────

BETS_PATH = Path(__file__).resolve().parent / "bets.json"

DEFAULT_BANKROLL  = 500.0
DEFAULT_UNIT_SIZE = 10.0   # fixed unit size in $

# ── Data helpers ───────────────────────────────────────────────────────────────

def load_data() -> dict:
    if BETS_PATH.exists():
        with open(BETS_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
        data.setdefault("bankroll", DEFAULT_BANKROLL)
        data.setdefault("unit_size", DEFAULT_UNIT_SIZE)
        data.setdefault("bets", [])
        for b in data["bets"]:
            if "type" not in b:
                b["type"] = "single"
        return data
    return {
        "bankroll":  DEFAULT_BANKROLL,
        "unit_size": DEFAULT_UNIT_SIZE,
        "next-id":   0,
        "bets":      []
    }

def save_data(data: dict):
    with open(BETS_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)

# ── Fighter search ─────────────────────────────────────────────────────────────

def search_fighters(query: str) -> list:
    query = query.lower().strip()
    results = []
    for f in fighter_db.values():
        name = getattr(f, "_personal-info_name", "")
        if query in name.lower():
            results.append(f)
    return results

def pick_fighter(prompt: str):
    while True:
        query = input(prompt).strip()
        if not query:
            print("  Please enter a name.")
            continue

        matches = search_fighters(query)

        if not matches:
            print(f"  ✗ No fighters found matching '{query}'. Try again.")
            continue

        if len(matches) == 1:
            fighter = matches[0]
            name    = getattr(fighter, "_personal-info_name")
            confirm = input(f"  Found: {name} — is this correct? (y/n): ").strip().lower()
            if confirm == "y":
                return fighter
            continue

        print(f"\n  Found {len(matches)} matches:")
        for i, f in enumerate(matches, 1):
            print(f"    {i}. {getattr(f, '_personal-info_name')}")
        print(f"    0. Search again")

        while True:
            try:
                choice = int(input("  Pick a number: ").strip())
                if choice == 0:
                    break
                if 1 <= choice <= len(matches):
                    return matches[choice - 1]
                print(f"  Please enter a number between 0 and {len(matches)}.")
            except ValueError:
                print("  Please enter a number.")

def select_fighter_for_bet(prompt: str):
    while True:
        query = input(prompt).strip()
        if not query:
            print("  Please enter a name.")
            continue

        matches = search_fighters(query)

        if matches:
            if len(matches) == 1:
                fighter = matches[0]
                name = getattr(fighter, "_personal-info_name", "")
                confirm = input(f"  Found: {name} — use this fighter? (y/n): ").strip().lower()
                if confirm == "y":
                    return fighter
                continue

            print(f"\n  Found {len(matches)} matches:")
            for i, f in enumerate(matches, 1):
                print(f"    {i}. {getattr(f, '_personal-info_name')}")
            print("    0. Search again")

            while True:
                try:
                    choice = int(input("  Pick a number: ").strip())
                    if choice == 0:
                        break
                    if 1 <= choice <= len(matches):
                        return matches[choice - 1]
                    print(f"  Please enter a number between 0 and {len(matches)}.")
                except ValueError:
                    print("  Please enter a number.")
            continue

        print(f"  ✗ No fighters found matching '{query}'.")
        print("    Options: (r)etry search  (c)ontinue with this name  (x) cancel")
        choice = input("    Choice (r/c/x): ").strip().lower()
        if choice == "r":
            continue
        if choice == "c":
            return query
        return None

# ── Odds helpers ───────────────────────────────────────────────────────────────

def american_to_decimal(odds: int) -> float:
    if odds > 0:
        return (odds / 100) + 1
    else:
        return (100 / abs(odds)) + 1

def american_to_implied_prob(odds: int) -> float:
    if odds > 0:
        return 100 / (odds + 100)
    else:
        return abs(odds) / (abs(odds) + 100)

def normalise_probs(odds_f1: int, odds_f2: int) -> tuple[float, float]:
    raw_f1 = american_to_implied_prob(odds_f1)
    raw_f2 = american_to_implied_prob(odds_f2)
    total  = raw_f1 + raw_f2
    return raw_f1 / total, raw_f2 / total

def calculate_ev(model_prob: float, odds: int) -> float:
    decimal = american_to_decimal(odds)
    profit  = decimal - 1
    return (model_prob * profit) - ((1 - model_prob) * 1)

def decimal_to_american(decimal: float) -> int:
    if decimal >= 2.0:
        return int(round((decimal - 1) * 100))
    else:
        return int(round(-100 / (decimal - 1)))

def format_odds(odds: int) -> str:
    return f"+{odds}" if odds > 0 else str(odds)

def format_currency(amount: float) -> str:
    return f"${amount:.2f}"

def format_ev(ev: float) -> str:
    sign = "+" if ev >= 0 else ""
    tag  = "✓ +EV" if ev >= 0 else "✗ -EV"
    return f"{sign}{ev:.4f} ({tag})"

# ── Display helpers ────────────────────────────────────────────────────────────

def print_header(title: str):
    print("\n" + "=" * 60)
    print(title.center(60))
    print("=" * 60)

def print_divider():
    print("-" * 60)

def pause():
    input("\nPress Enter to continue...")

# ── Quick odds -> probabilities tool ──────────────────────────────────────────

def odds_to_probs():
    while True:
        try:
            a = int(input("Enter American odds for side A (e.g. -150 or +130): ").strip())
            b = int(input("Enter American odds for side B (e.g. +120 or -110): ").strip())
            break
        except ValueError:
            print("Please enter valid integer odds.")

    raw_a = american_to_implied_prob(a)
    raw_b = american_to_implied_prob(b)
    total = raw_a + raw_b
    norm_a = raw_a / total
    norm_b = raw_b / total

    print("\nResults")
    print("-------")
    print(f"Side A odds: {a}  |  Decimal: {american_to_decimal(a):.3f}")
    print(f"  Implied probability (raw): {raw_a*100:.2f}%")
    print(f"  Normalised probability:    {norm_a*100:.2f}%")
    print()
    print(f"Side B odds: {b}  |  Decimal: {american_to_decimal(b):.3f}")
    print(f"  Implied probability (raw): {raw_b*100:.2f}%")
    print(f"  Normalised probability:    {norm_b*100:.2f}%")
    print(f"\nSum check normalised: {(norm_a+norm_b)*100:.2f}%")
    input("\nPress Enter to continue...")

# ── Core features ──────────────────────────────────────────────────────────────

def add_bet(data: dict):
    print_header("ADD NEW BET")

    print()
    f1_sel = select_fighter_for_bet("  Fighter 1 — search name: ")
    if f1_sel is None:
        print("  Cancelled adding bet.")
        pause()
        return

    if isinstance(f1_sel, str):
        f1_display = f1_sel
    else:
        f1_display = getattr(f1_sel, "_personal-info_name")

    print(f"  ✓ Fighter 1: {f1_display}")

    print()
    f2_sel = select_fighter_for_bet("  Fighter 2 — search name: ")
    if f2_sel is None:
        print("  Cancelled adding bet.")
        pause()
        return

    if isinstance(f2_sel, str):
        f2_display = f2_sel
    else:
        f2_display = getattr(f2_sel, "_personal-info_name")

    print(f"  ✓ Fighter 2: {f2_display}")

    while True:
        try:
            rounds = int(input("  Rounds (3 or 5): ").strip())
            if rounds in (3, 5):
                break
            print("  Please enter 3 or 5.")
        except ValueError:
            print("  Please enter a number.")

    print("\n  Running predictor model...")
    try:
        f1_for_model = f1_sel
        f2_for_model = f2_sel
        win_prob, lose_prob, msg = predictor.predict_fight(f1_for_model, f2_for_model, rounds)
        if win_prob == 0 and lose_prob == 0:
            predictor_msg = msg
            f1_model_prob = None
            f2_model_prob = None
            print(f"  Predictor: {predictor_msg}")
        else:
            predictor_msg = msg
            f1_model_prob = round(win_prob, 4)
            f2_model_prob = round(lose_prob, 4)
            print(f"  Predictor results: {f1_display}: {f1_model_prob*100:.1f}%, {f2_display}: {f2_model_prob*100:.1f}%")
    except Exception as e:
        predictor_msg = f"Predictor error: {e}"
        f1_model_prob = None
        f2_model_prob = None
        print(f"  ✗ Predictor error: {e}")

    print("\n  Enter bookmaker American odds (e.g. -150 or +130):")
    while True:
        try:
            odds_f1 = int(input(f"    {f1_display} odds: ").strip())
            break
        except ValueError:
            print("    Please enter a valid integer.")

    while True:
        try:
            odds_f2 = int(input(f"    {f2_display} odds: ").strip())
            break
        except ValueError:
            print("    Please enter a valid integer.")

    print(f"\n  Who are you betting on?")
    print(f"    1. {f1_display} ({format_odds(odds_f1)})")
    print(f"    2. {f2_display} ({format_odds(odds_f2)})")

    while True:
        choice = input("  Choice (1 or 2): ").strip()
        if choice == "1":
            bet_fighter = f1_display
            bet_odds    = odds_f1
            opponent    = f2_display
            chosen_model_prob = f1_model_prob
            break
        elif choice == "2":
            bet_fighter = f2_display
            bet_odds    = odds_f2
            opponent    = f1_display
            chosen_model_prob = f2_model_prob
            break
        print("  Please enter 1 or 2.")

    unit_size = data["unit_size"]
    bankroll  = data["bankroll"]
    max_units = bankroll / unit_size

    print(f"\n  Bankroll          : {format_currency(bankroll)}")
    print(f"  Unit size         : {format_currency(unit_size)}")
    print(f"  Max units available: {max_units:.1f}")

    while True:
        try:
            units = float(input("  How many units to bet? ").strip())
            stake = units * unit_size
            if stake > bankroll:
                print(f"  ✗ Not enough bankroll. Max units: {max_units:.1f}")
                continue
            if units <= 0:
                print("  ✗ Must bet more than 0 units.")
                continue
            break
        except ValueError:
            print("  Please enter a number.")

    stake            = round(units * unit_size, 2)
    decimal_odds     = american_to_decimal(bet_odds)
    potential_win    = round(stake * (decimal_odds - 1), 2)
    potential_return = round(stake * decimal_odds, 2)

    impl_f1, impl_f2 = normalise_probs(odds_f1, odds_f2)
    chosen_implied = impl_f1 if bet_fighter == f1_display else impl_f2

    if chosen_model_prob is not None:
        ev_for_bet = calculate_ev(chosen_model_prob, bet_odds)
    else:
        ev_for_bet = None

    print_divider()
    print("  BET SUMMARY")
    print_divider()
    print(f"  Fighter  : {bet_fighter}")
    print(f"  Opponent : {opponent}")
    print(f"  Odds     : {format_odds(bet_odds)}")
    print(f"  Units    : {units}")
    print(f"  Stake    : {format_currency(stake)}")
    print(f"  To win   : {format_currency(potential_win)}")
    print(f"  Potential: {format_currency(potential_return)}")
    if chosen_model_prob is not None:
        print(f"  Model prob: {chosen_model_prob*100:.1f}%")
    else:
        print(f"  Model prob: None")
    print(f"  Implied prob (vig removed): {chosen_implied*100:.1f}%")
    if ev_for_bet is not None:
        print(f"  EV (per $1 staked): {format_ev(ev_for_bet)}")
    else:
        print(f"  EV (per $1 staked): None")
    print_divider()

    confirm = input("  Confirm bet? (y/n): ").strip().lower()
    if confirm != "y":
        print("  Bet cancelled.")
        pause()
        return

    data["bankroll"] = round(bankroll - stake, 2)

    bet = {
        "id":            data["next-id"] + 1,
        "type":          "single",
        "date":          datetime.now().strftime("%Y-%m-%d %H:%M"),
        "fighter":       bet_fighter,
        "opponent":      opponent,
        "odds":          bet_odds,
        "model_prob_f1": f1_model_prob,
        "model_prob_f2": f2_model_prob,
        "predictor_msg": predictor_msg,
        "implied_prob":  chosen_implied,
        "ev":            ev_for_bet,
        "units":         units,
        "stake":         stake,
        "potential_win": potential_win,
        "status":        "pending",
        "pnl":           0.0
    }

    data["bets"].append(bet)
    data["next-id"] += 1
    save_data(data)

    print(f"\n  ✓ Bet #{bet['id']} added. New bankroll: {format_currency(data['bankroll'])}")
    pause()


def add_parlay(data: dict):
    """
    Add a multi-leg parlay. Each leg stores full fighter/model/odds info
    matching the single bet structure. The parlay itself stores combined
    odds, stake, potential win, implied probability of the whole parlay,
    and overall pnl.
    """
    print_header("ADD PARLAY")

    while True:
        try:
            legs_count = int(input("  How many legs in the parlay? (min 2): ").strip())
            if legs_count >= 2:
                break
            print("  Please enter a number >= 2.")
        except ValueError:
            print("  Please enter a valid number.")

    legs = []
    for i in range(1, legs_count + 1):
        print(f"\n  ── Leg {i} of {legs_count} ──")

        # Fighter being bet on
        f_sel = select_fighter_for_bet("    Fighter (betting on) — search name: ")
        if f_sel is None:
            print("  Cancelled adding parlay.")
            pause()
            return
        if isinstance(f_sel, str):
            fighter_display = f_sel
        else:
            fighter_display = getattr(f_sel, "_personal-info_name")
        print(f"    ✓ Fighter: {fighter_display}")

        # Opponent
        opp_sel = select_fighter_for_bet("    Opponent — search name: ")
        if opp_sel is None:
            print("  Cancelled adding parlay.")
            pause()
            return
        if isinstance(opp_sel, str):
            opponent_display = opp_sel
        else:
            opponent_display = getattr(opp_sel, "_personal-info_name")
        print(f"    ✓ Opponent: {opponent_display}")

        # Rounds
        while True:
            try:
                rounds = int(input("    Rounds (3 or 5): ").strip())
                if rounds in (3, 5):
                    break
                print("    Please enter 3 or 5.")
            except ValueError:
                print("    Please enter a number.")

        # Run predictor for this leg
        print(f"\n    Running predictor model for leg {i}...")
        try:
            win_prob, lose_prob, pred_msg = predictor.predict_fight(f_sel, opp_sel, rounds)
            if win_prob == 0 and lose_prob == 0:
                f1_model_prob = None
                f2_model_prob = None
                predictor_msg = pred_msg
                print(f"    Predictor: {predictor_msg}")
            else:
                f1_model_prob = round(win_prob, 4)
                f2_model_prob = round(lose_prob, 4)
                predictor_msg = pred_msg
                print(f"    Predictor: {fighter_display}: {f1_model_prob*100:.1f}%  |  {opponent_display}: {f2_model_prob*100:.1f}%")
        except Exception as e:
            predictor_msg = f"Predictor error: {e}"
            f1_model_prob = None
            f2_model_prob = None
            print(f"    ✗ Predictor error: {e}")

        # Bookmaker odds for both fighters in this leg
        print(f"\n    Enter bookmaker American odds for leg {i}:")
        while True:
            try:
                odds_fighter = int(input(f"      {fighter_display} odds: ").strip())
                break
            except ValueError:
                print("      Please enter a valid integer.")

        while True:
            try:
                odds_opponent = int(input(f"      {opponent_display} odds: ").strip())
                break
            except ValueError:
                print("      Please enter a valid integer.")

        # Normalised implied prob for chosen fighter in this leg
        impl_fighter, impl_opponent = normalise_probs(odds_fighter, odds_opponent)

        # EV for this leg
        if f1_model_prob is not None:
            leg_ev = calculate_ev(f1_model_prob, odds_fighter)
        else:
            leg_ev = None

        legs.append({
            "fighter":       fighter_display,
            "opponent":      opponent_display,
            "odds":          odds_fighter,          # odds for the chosen fighter
            "odds_opponent": odds_opponent,          # opponent odds (for reference / normalisation)
            "model_prob_f1": f1_model_prob,          # model prob for chosen fighter
            "model_prob_f2": f2_model_prob,          # model prob for opponent
            "predictor_msg": predictor_msg,
            "implied_prob":  round(impl_fighter, 4), # vig-removed implied prob for chosen fighter
            "ev":            round(leg_ev, 4) if leg_ev is not None else None,
            "status":        "pending",              # each leg can be tracked individually
            "pnl":           0.0
        })

        print(f"    ✓ Leg {i} added: {fighter_display} ({format_odds(odds_fighter)})")

    # Combined parlay odds
    combined_decimal = 1.0
    for leg in legs:
        combined_decimal *= american_to_decimal(leg["odds"])
    combined_decimal  = round(combined_decimal, 4)
    combined_american = decimal_to_american(combined_decimal)

    # Combined implied probability of the parlay hitting (product of each leg's implied prob)
    combined_implied_prob = 1.0
    for leg in legs:
        combined_implied_prob *= leg["implied_prob"]
    combined_implied_prob = round(combined_implied_prob, 4)

    # Units & stake
    unit_size = data["unit_size"]
    bankroll  = data["bankroll"]
    max_units = bankroll / unit_size

    print(f"\n  Combined parlay odds : {format_odds(combined_american)}  (decimal: {combined_decimal:.4f})")
    print(f"  Implied hit chance   : {combined_implied_prob*100:.2f}%")
    print(f"\n  Bankroll             : {format_currency(bankroll)}")
    print(f"  Unit size            : {format_currency(unit_size)}")
    print(f"  Max units available  : {max_units:.1f}")

    while True:
        try:
            units = float(input("  How many units to bet on the parlay? ").strip())
            stake = units * unit_size
            if stake > bankroll:
                print(f"  ✗ Not enough bankroll. Max units: {max_units:.1f}")
                continue
            if units <= 0:
                print("  ✗ Must bet more than 0 units.")
                continue
            break
        except ValueError:
            print("  Please enter a number.")

    stake         = round(units * unit_size, 2)
    potential_win = round(stake * (combined_decimal - 1), 2)

    # Summary
    print_divider()
    print("  PARLAY SUMMARY")
    print_divider()
    for idx, leg in enumerate(legs, 1):
        ev_tag = f"  EV: {format_ev(leg['ev'])}" if leg["ev"] is not None else "  EV: N/A"
        model_tag = f"  Model: {leg['model_prob_f1']*100:.1f}%" if leg["model_prob_f1"] is not None else "  Model: N/A"
        print(f"  Leg {idx}: {leg['fighter']:<28} {format_odds(leg['odds']):<8}{model_tag}{ev_tag}")
    print_divider()
    print(f"  Combined odds  : {format_odds(combined_american)}  (decimal: {combined_decimal:.4f})")
    print(f"  Implied chance : {combined_implied_prob*100:.2f}%")
    print(f"  Units          : {units}")
    print(f"  Stake          : {format_currency(stake)}")
    print(f"  To win         : {format_currency(potential_win)}")
    print_divider()

    confirm = input("  Confirm parlay? (y/n): ").strip().lower()
    if confirm != "y":
        print("  Parlay cancelled.")
        pause()
        return

    data["bankroll"] = round(bankroll - stake, 2)

    bet = {
        "id":                   data["next-id"] + 1,
        "type":                 "parlay",
        "date":                 datetime.now().strftime("%Y-%m-%d %H:%M"),
        "legs":                 legs,
        "combined_decimal":     combined_decimal,
        "combined_american":    combined_american,
        "combined_implied_prob": combined_implied_prob,
        "units":                units,
        "stake":                stake,
        "potential_win":        potential_win,
        "status":               "pending",
        "pnl":                  0.0
    }

    data["bets"].append(bet)
    data["next-id"] += 1
    save_data(data)

    print(f"\n  ✓ Parlay #{bet['id']} added. New bankroll: {format_currency(data['bankroll'])}")
    pause()


def analyse_matchup(data: dict):
    print_header("ANALYSE MATCHUP")

    print()
    f1 = pick_fighter("  Fighter 1 — search name: ")
    if f1 is None:
        pause()
        return
    f1_display = getattr(f1, "_personal-info_name")
    print(f"  ✓ Selected: {f1_display}")

    f2 = pick_fighter("  Fighter 2 — search name: ")
    if f2 is None:
        pause()
        return
    f2_display = getattr(f2, "_personal-info_name")
    print(f"  ✓ Selected: {f2_display}")

    while True:
        try:
            rounds = int(input("  Rounds (3 or 5): ").strip())
            if rounds in (3, 5):
                break
            print("  Please enter 3 or 5.")
        except ValueError:
            print("  Please enter a number.")

    print("\n  Running predictor model...")
    try:
        win_prob, lose_prob, _ = predictor.predict_fight(f1, f2, rounds)
        f1_model_prob = round(win_prob, 4)
        f2_model_prob = round(lose_prob, 4)
    except Exception as e:
        print(f"  ✗ Predictor error: {e}")
        pause()
        return

    print("\n  Enter bookmaker American odds (e.g. -150 or +130):")
    while True:
        try:
            odds_f1 = int(input(f"    {f1_display} odds: ").strip())
            break
        except ValueError:
            print("    Please enter a valid integer.")

    while True:
        try:
            odds_f2 = int(input(f"    {f2_display} odds: ").strip())
            break
        except ValueError:
            print("    Please enter a valid integer.")

    impl_f1, impl_f2 = normalise_probs(odds_f1, odds_f2)

    ev_f1 = calculate_ev(f1_model_prob, odds_f1)
    ev_f2 = calculate_ev(f2_model_prob, odds_f2)

    edge_f1 = f1_model_prob - impl_f1
    edge_f2 = f2_model_prob - impl_f2

    print_divider()
    print("  MATCHUP ANALYSIS".center(60))
    print_divider()
    print(f"  {'':30} {f1_display:<20} {f2_display:<20}")
    print_divider()
    print(f"  {'Odds':<30} {format_odds(odds_f1):<20} {format_odds(odds_f2):<20}")
    print(f"  {'Implied prob (raw)':<30} {round(american_to_implied_prob(odds_f1)*100,1):<19}% {round(american_to_implied_prob(odds_f2)*100,1):<19}%")
    print(f"  {'Implied prob (vig removed)':<30} {round(impl_f1*100,1):<19}% {round(impl_f2*100,1):<19}%")
    print(f"  {'Model probability':<30} {round(f1_model_prob*100,1):<19}% {round(f2_model_prob*100,1):<19}%")
    print(f"  {'Edge (model - implied)':<30} {('+' if edge_f1 >= 0 else '')}{round(edge_f1*100,1):<18}% {('+' if edge_f2 >= 0 else '')}{round(edge_f2*100,1):<18}%")
    print(f"  {'EV (per $1 staked)':<30} {format_ev(ev_f1):<20} {format_ev(ev_f2):<20}")
    print_divider()

    if ev_f1 > 0 and ev_f1 > ev_f2:
        rec      = f1_display
        rec_ev   = ev_f1
        rec_edge = edge_f1
        rec_prob = f1_model_prob
        rec_odds = odds_f1
    elif ev_f2 > 0:
        rec      = f2_display
        rec_ev   = ev_f2
        rec_edge = edge_f2
        rec_prob = f2_model_prob
        rec_odds = odds_f2
    else:
        rec = None

    if rec:
        print(f"\n  ✓ RECOMMENDATION: Bet {rec}")
        print(f"    Edge  : {('+' if rec_edge >= 0 else '')}{round(rec_edge*100,1)}%")
        print(f"    EV    : {format_ev(rec_ev)}")

        dec           = american_to_decimal(rec_odds)
        kelly         = (rec_prob * (dec - 1) - (1 - rec_prob)) / (dec - 1)
        quarter_kelly = max(0, kelly / 4)
        suggested_units = round(quarter_kelly * (data["bankroll"] / data["unit_size"]), 2)
        print(f"    Kelly : {suggested_units}u suggested (quarter Kelly)")
    else:
        print(f"\n  ✗ NO RECOMMENDATION — both sides are -EV at these odds.")

    print_divider()
    pause()


def view_bets(data: dict):
    print_header("ALL BETS")

    bets = data["bets"]
    if not bets:
        print("\n  No bets recorded yet.")
        pause()
        return

    singles_pending = [b for b in bets if b.get("type", "single") == "single" and b["status"] == "pending"]
    singles_settled = [b for b in bets if b.get("type", "single") == "single" and b["status"] != "pending"]
    parlays_pending = [b for b in bets if b.get("type") == "parlay" and b["status"] == "pending"]
    parlays_settled = [b for b in bets if b.get("type") == "parlay" and b["status"] != "pending"]

    # ── UPCOMING ──────────────────────────────────────────────────────────────
    print(f"\n  ┌─ UPCOMING BETS ─────────────────────────────────────────┐")

    if singles_pending:
        print(f"\n  SINGLES ({len(singles_pending)})")
        print_divider()
        for b in singles_pending:
            ev      = b.get("ev")
            ev_tag  = f"[{'+EV' if ev is not None and ev >= 0 else ('-EV' if ev is not None else 'no EV')}]"
            print(f"  #{b['id']:<3} {b['date']}  |  {b['fighter']:<22}  {format_odds(b['odds']):<7}  "
                  f"{b['units']}u  {format_currency(b['stake'])}  {ev_tag}")
    else:
        print("\n  SINGLES — none pending")

    if parlays_pending:
        print(f"\n  PARLAYS ({len(parlays_pending)})")
        print_divider()
        for b in parlays_pending:
            print(f"  #{b['id']:<3} {b['date']}  |  {len(b['legs'])} legs  "
                  f"Combined: {format_odds(b['combined_american'])}  |  "
                  f"Hit chance: {b['combined_implied_prob']*100:.1f}%  |  "
                  f"{b['units']}u  {format_currency(b['stake'])}  To win: {format_currency(b['potential_win'])}")
            for idx, leg in enumerate(b["legs"], 1):
                model_str = f"{leg['model_prob_f1']*100:.1f}%" if leg["model_prob_f1"] is not None else "N/A"
                ev_str    = format_ev(leg["ev"]) if leg["ev"] is not None else "N/A"
                impl_str  = f"{leg['implied_prob']*100:.1f}%"
                print(f"       Leg {idx}: {leg['fighter']:<26} {format_odds(leg['odds']):<8} "
                      f"Model: {model_str:<8} Implied: {impl_str:<8} EV: {ev_str}")
    else:
        print("\n  PARLAYS — none pending")

    # ── COMPLETED ─────────────────────────────────────────────────────────────
    print(f"\n  ├─ COMPLETED BETS ────────────────────────────────────────┤")

    if singles_settled:
        print(f"\n  SINGLES ({len(singles_settled)})")
        print_divider()
        for b in singles_settled:
            result_icon = "✓" if b["status"] == "won" else "✗"
            pnl_str     = f"+{format_currency(b['pnl'])}" if b["pnl"] >= 0 else format_currency(b["pnl"])
            print(f"  {result_icon} #{b['id']:<3} {b['date']}  |  {b['fighter']:<22}  {format_odds(b['odds']):<7}  "
                  f"{b['units']}u  {format_currency(b['stake'])}  {pnl_str}")
    else:
        print("\n  SINGLES — none settled")

    if parlays_settled:
        print(f"\n  PARLAYS ({len(parlays_settled)})")
        print_divider()
        for b in parlays_settled:
            result_icon = "✓" if b["status"] == "won" else "✗"
            pnl_str     = f"+{format_currency(b['pnl'])}" if b["pnl"] >= 0 else format_currency(b["pnl"])
            print(f"  {result_icon} #{b['id']:<3} {b['date']}  |  {len(b['legs'])} legs  "
                  f"Combined: {format_odds(b['combined_american'])}  |  "
                  f"{b['units']}u  {format_currency(b['stake'])}  {pnl_str}")
            for idx, leg in enumerate(b["legs"], 1):
                leg_icon  = "✓" if leg["status"] == "won" else ("✗" if leg["status"] == "lost" else "·")
                model_str = f"{leg['model_prob_f1']*100:.1f}%" if leg["model_prob_f1"] is not None else "N/A"
                ev_str    = format_ev(leg["ev"]) if leg["ev"] is not None else "N/A"
                impl_str  = f"{leg['implied_prob']*100:.1f}%"
                print(f"       {leg_icon} Leg {idx}: {leg['fighter']:<24} {format_odds(leg['odds']):<8} "
                      f"Model: {model_str:<8} Implied: {impl_str:<8} EV: {ev_str}")
    else:
        print("\n  PARLAYS — none settled")

    print(f"\n  └─────────────────────────────────────────────────────────┘")

    # Optional removal
    print("\n  Enter a bet ID to remove it, or press Enter to go back.")
    raw = input("  > ").strip()

    if raw:
        try:
            remove_id = int(raw)
            bet       = next((b for b in data["bets"] if b["id"] == remove_id), None)
            if not bet:
                print("  ✗ Bet ID not found.")
            else:
                if bet.get("type") == "parlay":
                    desc = f"PARLAY ({len(bet['legs'])} legs)"
                    disp_odds = bet.get("combined_american")
                else:
                    desc = f"{bet['fighter']} vs {bet['opponent']}"
                    disp_odds = bet.get("odds")
                print(f"\n  Remove bet #{remove_id}: {desc} "
                      f"({format_odds(disp_odds)}, {format_currency(bet['stake'])})?")
                confirm = input("  Confirm removal (y/n): ").strip().lower()
                if confirm == "y":
                    if bet["status"] == "pending":
                        data["bankroll"] = round(data["bankroll"] + bet["stake"], 2)
                        print(f"  ✓ Bet removed. Stake refunded. New bankroll: {format_currency(data['bankroll'])}")
                    else:
                        print("  ✓ Bet removed from history.")
                    data["bets"] = [b for b in data["bets"] if b["id"] != remove_id]
                    save_data(data)
                else:
                    print("  Removal cancelled.")
        except ValueError:
            pass


def settle_bet(data: dict):
    print_header("SETTLE BET")

    pending = [b for b in data["bets"] if b["status"] == "pending"]
    if not pending:
        print("\n  No pending bets to settle.")
        pause()
        return

    print("\n  Pending bets:")
    print_divider()
    for b in pending:
        if b.get("type") == "parlay":
            print(f"  #{b['id']:<3} PARLAY ({len(b['legs'])} legs)  |  {format_odds(b.get('combined_american'))}  {b['units']}u  {format_currency(b['stake'])}")
            for idx, leg in enumerate(b["legs"], 1):
                print(f"       Leg {idx}: {leg['fighter']:<28} {format_odds(leg['odds'])}")
        else:
            print(f"  #{b['id']:<3} {b['fighter']:<24} vs {b['opponent']:<24} "
                  f"{format_odds(b['odds'])}  {b['units']}u  {format_currency(b['stake'])}")

    while True:
        try:
            bet_id = int(input("\n  Enter bet ID to settle: ").strip())
            bet    = next((b for b in pending if b["id"] == bet_id), None)
            if bet:
                break
            print("  ✗ Bet ID not found in pending bets.")
        except ValueError:
            print("  Please enter a valid number.")

    if bet.get("type") == "parlay":
        print(f"\n  Settling: PARLAY #{bet['id']} ({len(bet['legs'])} legs)  {format_odds(bet.get('combined_american'))}  —  {format_currency(bet['stake'])} staked")
    else:
        print(f"\n  Settling: {bet['fighter']} ({format_odds(bet['odds'])})  —  {format_currency(bet['stake'])} staked")
    print("  1. Won")
    print("  2. Lost")

    while True:
        result = input("  Result (1 or 2): ").strip()
        if result in ("1", "2"):
            break
        print("  Please enter 1 or 2.")

    if result == "1":
        pnl = bet["potential_win"]
        bet["status"]    = "won"
        bet["pnl"]       = pnl
        data["bankroll"] = round(data["bankroll"] + bet["stake"] + pnl, 2)
        # Mark all legs as won if parlay won
        if bet.get("type") == "parlay":
            for leg in bet["legs"]:
                leg["status"] = "won"
        print(f"\n  ✓ Won! +{format_currency(pnl)}")
    else:
        pnl           = -bet["stake"]
        bet["status"] = "lost"
        bet["pnl"]    = pnl
        if bet.get("type") == "parlay":
            for leg in bet["legs"]:
                leg["status"] = "lost"
        print(f"\n  ✗ Lost. -{format_currency(bet['stake'])}")

    print(f"  New bankroll: {format_currency(data['bankroll'])}")
    save_data(data)
    pause()


def view_stats(data: dict):
    print_header("STATS & PERFORMANCE")

    bets     = data["bets"]
    singles  = [b for b in bets if b.get("type", "single") == "single"]
    settled  = [b for b in singles if b["status"] != "pending"]
    won      = [b for b in settled if b["status"] == "won"]
    lost     = [b for b in settled if b["status"] == "lost"]
    pending  = [b for b in singles if b["status"] == "pending"]

    total_staked       = sum(b["stake"] for b in settled)
    total_pnl          = sum(b["pnl"]   for b in settled)
    total_units_staked = sum(b["units"] for b in settled)
    total_units_pnl    = sum(b["pnl"] / data["unit_size"] for b in settled)

    plus_ev_bets  = [b for b in settled if b.get("ev") is not None and b["ev"] >= 0]
    minus_ev_bets = [b for b in settled if b.get("ev") is not None and b["ev"] <  0]

    roi = (total_pnl / total_staked * 100) if total_staked > 0 else 0.0

    favs      = [b for b in settled if b["odds"] < 0]
    underdogs = [b for b in settled if b["odds"] >= 0]
    favs_won      = [b for b in favs      if b["status"] == "won"]
    underdogs_won = [b for b in underdogs if b["status"] == "won"]
    favs_pnl      = sum(b["pnl"] for b in favs)
    underdogs_pnl = sum(b["pnl"] for b in underdogs)

    print(f"\n  {'Bankroll':<28}: {format_currency(data['bankroll'])}")
    print(f"  {'Unit size':<28}: {format_currency(data['unit_size'])}")
    print(f"  {'Starting bankroll':<28}: {format_currency(DEFAULT_BANKROLL)}")
    print(f"  {'Overall P&L':<28}: {('+' if total_pnl >= 0 else '')}{format_currency(total_pnl)}")
    print(f"  {'ROI':<28}: {('+' if roi >= 0 else '')}{roi:.2f}%")

    print_divider()
    print(f"  {'Total bets (all types)':<28}: {len(bets)}")
    print(f"  {'Pending (singles only)':<28}: {len(pending)}")
    print(f"  {'Settled (singles only)':<28}: {len(settled)}")
    print(f"  {'Won (singles only)':<28}: {len(won)}")
    print(f"  {'Lost (singles only)':<28}: {len(lost)}")

    if settled:
        win_rate = len(won) / len(settled) * 100
        print(f"  {'Win rate':<28}: {win_rate:.1f}%")
        print(f"  {'Correct pick rate':<28}: {len(won)}/{len(settled)} ({win_rate:.1f}%)")

    print_divider()
    print(f"  {'Units staked':<28}: {total_units_staked:.1f}u")
    print(f"  {'Units P&L':<28}: {('+' if total_units_pnl >= 0 else '')}{total_units_pnl:.2f}u")

    if plus_ev_bets or minus_ev_bets:
        ev_bets_all = [b for b in settled if b.get("ev") is not None]
        avg_ev = sum(b["ev"] for b in ev_bets_all) / len(ev_bets_all) if ev_bets_all else None
        print(f"  {'+EV bets placed':<28}: {len(plus_ev_bets)}")
        print(f"  {'-EV bets placed':<28}: {len(minus_ev_bets)}")
        if avg_ev is not None:
            print(f"  {'Avg EV per bet':<28}: {('+' if avg_ev >= 0 else '')}{avg_ev:.4f}")
        if plus_ev_bets:
            plus_ev_won = [b for b in plus_ev_bets if b["status"] == "won"]
            print(f"  {'+EV win rate':<28}: {len(plus_ev_won)}/{len(plus_ev_bets)} ({len(plus_ev_won)/len(plus_ev_bets)*100:.1f}%)")

    if won:
        avg_odds_won = sum(b["odds"] for b in won) / len(won)
        print(f"\n  {'Avg odds (winners)':<28}: {avg_odds_won:+.0f}")
    if lost:
        avg_odds_lost = sum(b["odds"] for b in lost) / len(lost)
        print(f"  {'Avg odds (losers)':<28}: {avg_odds_lost:+.0f}")

    print_divider()
    print(f"  FAVOURITES (negative odds)")
    if favs:
        fav_pick_rate = len(favs_won) / len(favs) * 100
        print(f"  {'  Bets':<28}: {len(favs)}")
        print(f"  {'  Pick rate':<28}: {len(favs_won)}/{len(favs)} ({fav_pick_rate:.1f}%)")
        print(f"  {'  P&L':<28}: {('+' if favs_pnl >= 0 else '')}{format_currency(favs_pnl)}")
    else:
        print(f"  {'  No settled favourite bets':<28}")

    print(f"  UNDERDOGS (+100 or higher)")
    if underdogs:
        dog_pick_rate = len(underdogs_won) / len(underdogs) * 100
        print(f"  {'  Bets':<28}: {len(underdogs)}")
        print(f"  {'  Pick rate':<28}: {len(underdogs_won)}/{len(underdogs)} ({dog_pick_rate:.1f}%)")
        print(f"  {'  P&L':<28}: {('+' if underdogs_pnl >= 0 else '')}{format_currency(underdogs_pnl)}")
    else:
        print(f"  {'  No settled underdog bets':<28}")

    # ── PARLAY STATS ──────────────────────────────────────────────────────────
    parlays_all     = [b for b in bets if b.get("type") == "parlay"]
    parlays_pending = [b for b in parlays_all if b["status"] == "pending"]
    parlays_settled = [b for b in parlays_all if b["status"] != "pending"]
    parlays_won     = [b for b in parlays_settled if b["status"] == "won"]
    parlays_lost    = [b for b in parlays_settled if b["status"] == "lost"]

    print_divider()
    print("  PARLAYS")
    print_divider()
    print(f"  {'Total parlays':<28}: {len(parlays_all)}")
    print(f"  {'Pending':<28}: {len(parlays_pending)}")
    print(f"  {'Settled':<28}: {len(parlays_settled)}")
    print(f"  {'Won':<28}: {len(parlays_won)}")
    print(f"  {'Lost':<28}: {len(parlays_lost)}")

    if parlays_settled:
        parlay_units_staked = sum(p["units"] for p in parlays_settled)
        parlay_units_pnl    = sum(p["pnl"] / data["unit_size"] for p in parlays_settled)
        parlay_win_rate     = len(parlays_won) / len(parlays_settled) * 100
        avg_legs_per_parlay = sum(len(p["legs"]) for p in parlays_all) / len(parlays_all) if parlays_all else 0.0
        biggest_win         = max((p["pnl"] for p in parlays_settled), default=0.0)
        print(f"  {'Units staked':<28}: {parlay_units_staked:.1f}u")
        print(f"  {'Units P&L':<28}: {('+' if parlay_units_pnl >= 0 else '')}{parlay_units_pnl:.2f}u")
        print(f"  {'Win rate':<28}: {parlay_win_rate:.1f}%")
        print(f"  {'Avg legs per parlay':<28}: {avg_legs_per_parlay:.2f}")
        print(f"  {'Biggest win':<28}: {('+' if biggest_win >= 0 else '')}{format_currency(biggest_win)}")
    else:
        print(f"  {'No settled parlays yet':<28}")

    print_divider()
    pause()


# ── Main menu ──────────────────────────────────────────────────────────────────

def main():
    data = load_data()

    MENU = """
UFC Betting Tracker
-------------------
1. Add Bet
2. Analyse Matchup
3. View Bets
4. Settle Bet
5. Stats & Performance
6. Add Parlay
7. Quick odds -> probabilities
0. Exit
"""

    while True:
        print(MENU)
        choice = input("Choose an option: ").strip()
        if choice == "1":
            add_bet(data)
        elif choice == "2":
            analyse_matchup(data)
        elif choice == "3":
            view_bets(data)
        elif choice == "4":
            settle_bet(data)
        elif choice == "5":
            view_stats(data)
        elif choice == "6":
            add_parlay(data)
        elif choice == "7":
            odds_to_probs()
        elif choice == "0":
            print("Goodbye.")
            break
        else:
            print("Please enter a valid option (0-7).")


if __name__ == "__main__":
    main()
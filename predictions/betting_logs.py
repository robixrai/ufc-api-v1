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
DEFAULT_UNIT_SIZE = 10.0

# ── Bet market definitions ─────────────────────────────────────────────────────

BET_MARKETS = {
    "1":  "ML",
    "2":  "KO/TKO",
    "3":  "Sub",
    "4":  "Dec",
    "5":  "KO/TKO or Sub",
    "6":  "Sub or Dec",
    "7":  "ITD",
    "8":  "OOTD",
    "9":  "O/U Rounds",
    "10": "Sig Strikes",
    "11": "Takedowns",
}

# Markets where the model can derive a probability automatically
MODEL_DERIVED_MARKETS = {"ML", "KO/TKO", "Sub", "Dec", "KO/TKO or Sub", "Sub or Dec", "ITD", "OOTD"}

# Markets where the user must supply their own probability estimate
MANUAL_PROB_MARKETS = {"O/U Rounds", "Sig Strikes", "Takedowns"}

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

# ── Market selection ───────────────────────────────────────────────────────────

def select_market() -> str:
    """Prompt user to pick a bet market. Returns the market string."""
    print("\n  Bet market:")
    for key, name in BET_MARKETS.items():
        print(f"    {key:>2}. {name}")
    while True:
        choice = input("  Select market: ").strip()
        if choice in BET_MARKETS:
            return BET_MARKETS[choice]
        print("  Please enter a valid number.")

def select_market_for_parlay_leg() -> str:
    """Same as select_market but with leg-indented formatting."""
    print("\n    Bet market:")
    for key, name in BET_MARKETS.items():
        print(f"      {key:>2}. {name}")
    while True:
        choice = input("    Select market: ").strip()
        if choice in BET_MARKETS:
            return BET_MARKETS[choice]
        print("    Please enter a valid number.")

# ── Market label builder ───────────────────────────────────────────────────────

def market_label(market: str, extra: dict) -> str:
    """Build a human-readable label for a bet, e.g. 'O/U Rounds — Over 2.5'."""
    if market == "O/U Rounds":
        return f"O/U Rounds — {extra.get('ou_pick','?')} {extra.get('ou_line','?')}"
    if market in ("Sig Strikes", "Takedowns"):
        return f"{market} — {extra.get('ou_pick','?')} {extra.get('ou_line','?')}"
    if market == "ML":
        return f"ML — {extra.get('bet_fighter','?')}"
    if market in ("KO/TKO", "Sub", "Dec"):
        return f"{market} — {extra.get('bet_fighter','?')}"
    if market in ("KO/TKO or Sub", "Sub or Dec"):
        return market
    if market in ("ITD", "OOTD"):
        return market
    return market

# ── Predictor helpers ──────────────────────────────────────────────────────────

def run_predictor(f1_sel, f2_sel, f1_display: str, f2_display: str, rounds: int) -> dict:
    """
    Run the predictor and return a structured result dict with all probs.
    Returns None values if predictor fails or fighters can't be found.
    """
    result = {
        "f1_win_prob":    None,
        "f2_win_prob":    None,
        "fight_ko_prob":  None,
        "fight_sub_prob": None,
        "fight_dec_prob": None,
        "f1_ko_prob":     None,
        "f1_sub_prob":    None,
        "f1_dec_prob":    None,
        "f2_ko_prob":     None,
        "f2_sub_prob":    None,
        "f2_dec_prob":    None,
        "predictor_msg":  None,
    }

    if isinstance(f1_sel, str) or isinstance(f2_sel, str):
        result["predictor_msg"] = "Predictor skipped: fighter(s) not in DB"
        return result

    try:
        win_prob, lose_prob, logs = predictor.predict_fight(f1_sel, f2_sel, rounds, json=0)

        if win_prob == 0 and lose_prob == 0:
            result["predictor_msg"] = logs
            return result

        result["f1_win_prob"]   = round(win_prob,  4)
        result["f2_win_prob"]   = round(lose_prob, 4)
        result["predictor_msg"] = logs

        # ── Parse fight-level method probs ────────────────────────────────────
        in_fight_section = False
        for line in logs.splitlines():
            if "FIGHT METHOD PROFILE" in line or "Most likely method" in line:
                in_fight_section = True
            if in_fight_section and "Final profile" in line:
                try:
                    result["fight_ko_prob"]  = float(line.split("KO:")[1].split()[0])
                    result["fight_sub_prob"] = float(line.split("Sub:")[1].split()[0])
                    result["fight_dec_prob"] = float(line.split("Dec:")[1].split()[0])
                except Exception:
                    pass
                break

        # ── Parse per-fighter method probs ────────────────────────────────────
        for fighter_name, prefix in [(f1_display, "f1"), (f2_display, "f2")]:
            in_section = False
            for line in logs.splitlines():
                if f"METHOD PROFILE : {fighter_name}" in line:
                    in_section = True
                if in_section and "Final profile" in line:
                    try:
                        result[f"{prefix}_ko_prob"]  = float(line.split("KO:")[1].split()[0])
                        result[f"{prefix}_sub_prob"] = float(line.split("Sub:")[1].split()[0])
                        result[f"{prefix}_dec_prob"] = float(line.split("Dec:")[1].split()[0])
                    except Exception:
                        pass
                    break

    except Exception as e:
        result["predictor_msg"] = f"Predictor error: {e}"

    return result


def derive_model_prob(market: str, bet_fighter: str, f1_display: str, preds: dict) -> float | None:
    """
    Derive the model probability for a given market from predictor output.
    Returns None if not derivable.
    """
    is_f1 = (bet_fighter == f1_display)

    if market == "ML":
        return preds["f1_win_prob"] if is_f1 else preds["f2_win_prob"]

    if market == "KO/TKO":
        base_win = preds["f1_win_prob"] if is_f1 else preds["f2_win_prob"]
        ko_prob  = preds["f1_ko_prob"]  if is_f1 else preds["f2_ko_prob"]
        if base_win is not None and ko_prob is not None:
            return round(base_win * ko_prob, 4)
        return None

    if market == "Sub":
        base_win = preds["f1_win_prob"] if is_f1 else preds["f2_win_prob"]
        sub_prob = preds["f1_sub_prob"] if is_f1 else preds["f2_sub_prob"]
        if base_win is not None and sub_prob is not None:
            return round(base_win * sub_prob, 4)
        return None

    if market == "Dec":
        base_win = preds["f1_win_prob"] if is_f1 else preds["f2_win_prob"]
        dec_prob = preds["f1_dec_prob"] if is_f1 else preds["f2_dec_prob"]
        if base_win is not None and dec_prob is not None:
            return round(base_win * dec_prob, 4)
        return None

    if market == "KO/TKO or Sub":
        # Fight ends inside the distance (either fighter)
        ko  = preds["fight_ko_prob"]
        sub = preds["fight_sub_prob"]
        if ko is not None and sub is not None:
            return round(ko + sub, 4)
        return None

    if market == "Sub or Dec":
        base_win = preds["f1_win_prob"] if is_f1 else preds["f2_win_prob"]
        sub_prob = preds["f1_sub_prob"] if is_f1 else preds["f2_sub_prob"]
        dec_prob = preds["f1_dec_prob"] if is_f1 else preds["f2_dec_prob"]
        if base_win is not None and sub_prob is not None and dec_prob is not None:
            return round(base_win * (sub_prob + dec_prob), 4)
        return None

    if market == "ITD":
        ko  = preds["fight_ko_prob"]
        sub = preds["fight_sub_prob"]
        if ko is not None and sub is not None:
            return round(ko + sub, 4)
        return None

    if market == "OOTD":
        dec = preds["fight_dec_prob"]
        return round(dec, 4) if dec is not None else None

    return None


def get_manual_prob(market: str, extra_label: str = "") -> float | None:
    """Ask the user to enter their estimated probability for a prop market."""
    prompt = f"  Your estimated probability for {market}{extra_label} (0-100, or leave blank to skip EV): "
    while True:
        raw = input(prompt).strip()
        if raw == "":
            return None
        try:
            val = float(raw)
            if 0 <= val <= 100:
                return round(val / 100, 4)
            print("  Please enter a value between 0 and 100.")
        except ValueError:
            print("  Please enter a number.")


def get_ou_details(market: str, indent: str = "  ") -> dict:
    """Prompt for O/U line and pick. Returns dict with ou_line and ou_pick."""
    while True:
        try:
            line = float(input(f"{indent}Line (e.g. 2.5): ").strip())
            break
        except ValueError:
            print(f"{indent}Please enter a valid number.")

    while True:
        pick = input(f"{indent}Pick — (o)ver or (u)nder: ").strip().lower()
        if pick in ("o", "over"):
            pick = "Over"
            break
        elif pick in ("u", "under"):
            pick = "Under"
            break
        print(f"{indent}Please enter 'o' or 'u'.")

    return {"ou_line": line, "ou_pick": pick}

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

# ── Add single bet ─────────────────────────────────────────────────────────────

def add_bet(data: dict):
    print_header("ADD NEW BET")

    # ── Fighter selection ──────────────────────────────────────────────────────
    print()
    f1_sel = select_fighter_for_bet("  Fighter 1 — search name: ")
    if f1_sel is None:
        print("  Cancelled.")
        pause()
        return
    f1_display = f1_sel if isinstance(f1_sel, str) else getattr(f1_sel, "_personal-info_name")
    print(f"  ✓ Fighter 1: {f1_display}")

    print()
    f2_sel = select_fighter_for_bet("  Fighter 2 — search name: ")
    if f2_sel is None:
        print("  Cancelled.")
        pause()
        return
    f2_display = f2_sel if isinstance(f2_sel, str) else getattr(f2_sel, "_personal-info_name")
    print(f"  ✓ Fighter 2: {f2_display}")

    while True:
        try:
            rounds = int(input("  Rounds (3 or 5): ").strip())
            if rounds in (3, 5):
                break
            print("  Please enter 3 or 5.")
        except ValueError:
            print("  Please enter a number.")

    # ── Market selection ───────────────────────────────────────────────────────
    market = select_market()

    # ── Fighter selection for directional markets ──────────────────────────────
    extra = {}
    bet_fighter = None
    opponent    = None

    needs_fighter = market in ("ML", "KO/TKO", "Sub", "Dec", "Sub or Dec")
    if needs_fighter:
        print(f"\n  Betting on which fighter?")
        print(f"    1. {f1_display}")
        print(f"    2. {f2_display}")
        while True:
            ch = input("  Choice (1 or 2): ").strip()
            if ch == "1":
                bet_fighter = f1_display
                opponent    = f2_display
                break
            elif ch == "2":
                bet_fighter = f2_display
                opponent    = f1_display
                break
            print("  Please enter 1 or 2.")
        extra["bet_fighter"] = bet_fighter
        extra["opponent"]    = opponent
    else:
        # For non-directional markets store both names for context
        bet_fighter = f"{f1_display} vs {f2_display}"
        opponent    = ""

    # ── O/U line details ───────────────────────────────────────────────────────
    if market in ("O/U Rounds", "Sig Strikes", "Takedowns"):
        print(f"\n  Enter line details for {market}:")
        ou = get_ou_details(market)
        extra.update(ou)

    # ── Run predictor ──────────────────────────────────────────────────────────
    print("\n  Running predictor model...")
    preds = run_predictor(f1_sel, f2_sel, f1_display, f2_display, rounds)

    if preds["f1_win_prob"] is not None:
        print(f"  Model: {f1_display}: {preds['f1_win_prob']*100:.1f}%  |  {f2_display}: {preds['f2_win_prob']*100:.1f}%")
        if preds["fight_ko_prob"] is not None:
            print(f"  Fight method — KO: {preds['fight_ko_prob']*100:.1f}%  Sub: {preds['fight_sub_prob']*100:.1f}%  Dec: {preds['fight_dec_prob']*100:.1f}%")
    else:
        print(f"  Model: {preds['predictor_msg']}")

    # ── Derive or request model prob ───────────────────────────────────────────
    chosen_fighter_for_prob = f1_display if (needs_fighter and bet_fighter == f1_display) else f2_display

    if market in MODEL_DERIVED_MARKETS:
        model_prob = derive_model_prob(market, bet_fighter if needs_fighter else f1_display, f1_display, preds)
        if model_prob is not None:
            print(f"  Model prob for [{market_label(market, extra)}]: {model_prob*100:.1f}%")
        else:
            print(f"  Model prob for [{market}]: could not derive — enter manually.")
            model_prob = get_manual_prob(market)
    else:
        label_suffix = f" ({extra.get('ou_pick','')} {extra.get('ou_line','')})" if "ou_line" in extra else ""
        model_prob = get_manual_prob(market, label_suffix)
        if model_prob is not None:
            print(f"  Using your estimate: {model_prob*100:.1f}%")

    # ── Bookmaker odds ─────────────────────────────────────────────────────────
    print(f"\n  Enter bookmaker American odds for [{market_label(market, extra)}]:")
    while True:
        try:
            bet_odds = int(input("    Odds: ").strip())
            break
        except ValueError:
            print("    Please enter a valid integer.")

    # Implied probability — for two-sided markets get both sides; for props just single side
    two_sided_markets = {"ML", "KO/TKO", "Sub", "Dec", "ITD", "OOTD"}
    if market in two_sided_markets and needs_fighter:
        print(f"  Enter odds for the other side ({opponent}) for vig removal:")
        while True:
            try:
                opp_odds = int(input("    Opponent odds: ").strip())
                break
            except ValueError:
                print("    Please enter a valid integer.")
        impl_bet, _ = normalise_probs(bet_odds, opp_odds)
    else:
        impl_bet = american_to_implied_prob(bet_odds)

    ev_for_bet = calculate_ev(model_prob, bet_odds) if model_prob is not None else None

    # ── Stake ──────────────────────────────────────────────────────────────────
    unit_size = data["unit_size"]
    bankroll  = data["bankroll"]
    max_units = bankroll / unit_size

    print(f"\n  Bankroll           : {format_currency(bankroll)}")
    print(f"  Unit size          : {format_currency(unit_size)}")
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

    # ── Summary ────────────────────────────────────────────────────────────────
    print_divider()
    print("  BET SUMMARY")
    print_divider()
    print(f"  Market   : {market_label(market, extra)}")
    print(f"  Fight    : {f1_display} vs {f2_display}")
    if needs_fighter:
        print(f"  Selection: {bet_fighter}")
    print(f"  Odds     : {format_odds(bet_odds)}")
    print(f"  Units    : {units}")
    print(f"  Stake    : {format_currency(stake)}")
    print(f"  To win   : {format_currency(potential_win)}")
    print(f"  Potential: {format_currency(potential_return)}")
    if model_prob is not None:
        print(f"  Model prob: {model_prob*100:.1f}%")
    else:
        print(f"  Model prob: N/A")
    print(f"  Implied prob (vig removed): {impl_bet*100:.1f}%")
    if ev_for_bet is not None:
        print(f"  EV (per $1 staked): {format_ev(ev_for_bet)}")
    else:
        print(f"  EV (per $1 staked): N/A")
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
        "market":        market,
        "extra":         extra,
        "date":          datetime.now().strftime("%Y-%m-%d %H:%M"),
        "fighter":       bet_fighter,
        "opponent":      opponent,
        "f1":            f1_display,
        "f2":            f2_display,
        "odds":          bet_odds,
        "model_prob":    model_prob,
        "model_prob_f1": preds["f1_win_prob"],
        "model_prob_f2": preds["f2_win_prob"],
        "fight_ko_prob": preds["fight_ko_prob"],
        "fight_sub_prob":preds["fight_sub_prob"],
        "fight_dec_prob":preds["fight_dec_prob"],
        "implied_prob":  round(impl_bet, 4),
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


# ── Add parlay ─────────────────────────────────────────────────────────────────

def add_parlay(data: dict):
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

        f_sel = select_fighter_for_bet("    Fighter 1 — search name: ")
        if f_sel is None:
            print("  Cancelled.")
            pause()
            return
        f1_display = f_sel if isinstance(f_sel, str) else getattr(f_sel, "_personal-info_name")
        print(f"    ✓ Fighter 1: {f1_display}")

        opp_sel = select_fighter_for_bet("    Fighter 2 — search name: ")
        if opp_sel is None:
            print("  Cancelled.")
            pause()
            return
        f2_display = opp_sel if isinstance(opp_sel, str) else getattr(opp_sel, "_personal-info_name")
        print(f"    ✓ Fighter 2: {f2_display}")

        while True:
            try:
                rounds = int(input("    Rounds (3 or 5): ").strip())
                if rounds in (3, 5):
                    break
                print("    Please enter 3 or 5.")
            except ValueError:
                print("    Please enter a number.")

        # Market
        market = select_market_for_parlay_leg()

        # Fighter selection for directional markets
        extra = {}
        bet_fighter = None
        needs_fighter = market in ("ML", "KO/TKO", "Sub", "Dec", "Sub or Dec")

        if needs_fighter:
            print(f"\n    Betting on which fighter?")
            print(f"      1. {f1_display}")
            print(f"      2. {f2_display}")
            while True:
                ch = input("    Choice (1 or 2): ").strip()
                if ch == "1":
                    bet_fighter = f1_display
                    break
                elif ch == "2":
                    bet_fighter = f2_display
                    break
                print("    Please enter 1 or 2.")
            extra["bet_fighter"] = bet_fighter
            extra["opponent"]    = f2_display if bet_fighter == f1_display else f1_display
        else:
            bet_fighter = f"{f1_display} vs {f2_display}"

        # O/U details
        if market in ("O/U Rounds", "Sig Strikes", "Takedowns"):
            print(f"\n    Enter line details for {market}:")
            ou = get_ou_details(market, indent="    ")
            extra.update(ou)

        # Run predictor
        print(f"\n    Running predictor for leg {i}...")
        preds = run_predictor(f_sel, opp_sel, f1_display, f2_display, rounds)

        if preds["f1_win_prob"] is not None:
            print(f"    Model: {f1_display}: {preds['f1_win_prob']*100:.1f}%  |  {f2_display}: {preds['f2_win_prob']*100:.1f}%")
            if preds["fight_ko_prob"] is not None:
                print(f"    Fight method — KO: {preds['fight_ko_prob']*100:.1f}%  Sub: {preds['fight_sub_prob']*100:.1f}%  Dec: {preds['fight_dec_prob']*100:.1f}%")
        else:
            print(f"    Model: {preds['predictor_msg']}")

        # Derive or request model prob
        if market in MODEL_DERIVED_MARKETS:
            model_prob = derive_model_prob(market, bet_fighter if needs_fighter else f1_display, f1_display, preds)
            if model_prob is not None:
                print(f"    Model prob for [{market_label(market, extra)}]: {model_prob*100:.1f}%")
            else:
                print(f"    Model prob for [{market}]: could not derive — enter manually.")
                model_prob = get_manual_prob(market)
        else:
            label_suffix = f" ({extra.get('ou_pick','')} {extra.get('ou_line','')})" if "ou_line" in extra else ""
            model_prob = get_manual_prob(market, label_suffix)

        # Odds
        print(f"\n    Odds for [{market_label(market, extra)}]:")
        while True:
            try:
                odds_leg = int(input(f"      Odds: ").strip())
                break
            except ValueError:
                print("      Please enter a valid integer.")

        # Implied prob
        two_sided = {"ML", "KO/TKO", "Sub", "Dec", "ITD", "OOTD"}
        if market in two_sided and needs_fighter:
            opp_name = extra.get("opponent", "opponent")
            print(f"      {opp_name} odds (for vig removal):")
            while True:
                try:
                    opp_odds_leg = int(input(f"      Odds: ").strip())
                    break
                except ValueError:
                    print("      Please enter a valid integer.")
            impl_leg, _ = normalise_probs(odds_leg, opp_odds_leg)
        else:
            impl_leg = american_to_implied_prob(odds_leg)

        leg_ev = calculate_ev(model_prob, odds_leg) if model_prob is not None else None

        legs.append({
            "fighter":       bet_fighter,
            "opponent":      extra.get("opponent", ""),
            "f1":            f1_display,
            "f2":            f2_display,
            "market":        market,
            "extra":         extra,
            "odds":          odds_leg,
            "model_prob":    model_prob,
            "model_prob_f1": preds["f1_win_prob"],
            "model_prob_f2": preds["f2_win_prob"],
            "fight_ko_prob": preds["fight_ko_prob"],
            "fight_sub_prob":preds["fight_sub_prob"],
            "fight_dec_prob":preds["fight_dec_prob"],
            "implied_prob":  round(impl_leg, 4),
            "ev":            round(leg_ev, 4) if leg_ev is not None else None,
            "status":        "pending",
            "pnl":           0.0
        })

        print(f"    ✓ Leg {i} added: [{market_label(market, extra)}] ({format_odds(odds_leg)})")

    # Combined parlay odds
    combined_decimal = 1.0
    for leg in legs:
        combined_decimal *= american_to_decimal(leg["odds"])
    combined_decimal  = round(combined_decimal, 4)
    combined_american = decimal_to_american(combined_decimal)

    combined_implied_prob = 1.0
    for leg in legs:
        combined_implied_prob *= leg["implied_prob"]
    combined_implied_prob = round(combined_implied_prob, 4)

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

    print_divider()
    print("  PARLAY SUMMARY")
    print_divider()
    for idx, leg in enumerate(legs, 1):
        ev_tag    = f"  EV: {format_ev(leg['ev'])}" if leg["ev"] is not None else "  EV: N/A"
        model_tag = f"  Model: {leg['model_prob']*100:.1f}%" if leg["model_prob"] is not None else "  Model: N/A"
        lbl       = market_label(leg["market"], leg["extra"])
        print(f"  Leg {idx}: [{lbl}]  {format_odds(leg['odds']):<8}{model_tag}{ev_tag}")
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
        "id":                    data["next-id"] + 1,
        "type":                  "parlay",
        "date":                  datetime.now().strftime("%Y-%m-%d %H:%M"),
        "legs":                  legs,
        "combined_decimal":      combined_decimal,
        "combined_american":     combined_american,
        "combined_implied_prob": combined_implied_prob,
        "units":                 units,
        "stake":                 stake,
        "potential_win":         potential_win,
        "status":                "pending",
        "pnl":                   0.0
    }

    data["bets"].append(bet)
    data["next-id"] += 1
    save_data(data)

    print(f"\n  ✓ Parlay #{bet['id']} added. New bankroll: {format_currency(data['bankroll'])}")
    pause()


# ── Analyse matchup ────────────────────────────────────────────────────────────

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
    preds = run_predictor(f1, f2, f1_display, f2_display, rounds)

    if preds["f1_win_prob"] is None:
        print(f"  ✗ Predictor error: {preds['predictor_msg']}")
        pause()
        return

    f1_model_prob = preds["f1_win_prob"]
    f2_model_prob = preds["f2_win_prob"]

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

    # Method breakdown if available
    if preds["fight_ko_prob"] is not None:
        print_divider()
        print(f"  FIGHT METHOD BREAKDOWN")
        ko  = preds["fight_ko_prob"]
        sub = preds["fight_sub_prob"]
        dec = preds["fight_dec_prob"]
        print(f"  {'KO/TKO':<30} {ko*100:.1f}%")
        print(f"  {'Submission':<30} {sub*100:.1f}%")
        print(f"  {'Decision':<30} {dec*100:.1f}%")
        print(f"  {'ITD (KO+Sub)':<30} {(ko+sub)*100:.1f}%")
        print(f"  {'OOTD (Dec)':<30} {dec*100:.1f}%")

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

        dec_odds      = american_to_decimal(rec_odds)
        kelly         = (rec_prob * (dec_odds - 1) - (1 - rec_prob)) / (dec_odds - 1)
        quarter_kelly = max(0, kelly / 4)
        suggested_units = round(quarter_kelly * (data["bankroll"] / data["unit_size"]), 2)
        print(f"    Kelly : {suggested_units}u suggested (quarter Kelly)")
    else:
        print(f"\n  ✗ NO RECOMMENDATION — both sides are -EV at these odds.")

    print_divider()
    pause()


# ── View bets ──────────────────────────────────────────────────────────────────

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

    def _single_line(b):
        ev         = b.get("ev")
        ev_str     = format_ev(ev) if ev is not None else "N/A"
        model_prob = b.get("model_prob")
        model_str  = f"{model_prob*100:.1f}%" if model_prob is not None else "N/A"
        implied    = b.get("implied_prob")
        impl_str   = f"{implied*100:.1f}%" if implied is not None else "N/A"
        decimal    = american_to_decimal(b["odds"])
        ret        = round(b["stake"] * decimal, 2)
        mkt        = market_label(b.get("market", "ML"), b.get("extra", {}))
        return (f"  #{b['id']:<3} {b['date']}  |  {b['fighter']:<22}  [{mkt}]  "
                f"{format_odds(b['odds']):<8} {b['units']}u  {format_currency(b['stake'])}  "
                f"To win: {format_currency(b['potential_win'])}  Return: {format_currency(ret)}  "
                f"Model: {model_str:<8} Implied: {impl_str:<8} EV: {ev_str}")

    # ── UPCOMING ──────────────────────────────────────────────────────────────
    print(f"\n  ┌─ UPCOMING BETS ─────────────────────────────────────────┐")

    if singles_pending:
        print(f"\n  SINGLES ({len(singles_pending)})")
        print_divider()
        for b in singles_pending:
            print(_single_line(b))
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
                model_str = f"{leg['model_prob']*100:.1f}%" if leg.get("model_prob") is not None else "N/A"
                ev_str    = format_ev(leg["ev"]) if leg.get("ev") is not None else "N/A"
                impl_str  = f"{leg['implied_prob']*100:.1f}%"
                lbl       = market_label(leg.get("market", "ML"), leg.get("extra", {}))
                print(f"       Leg {idx}: {leg['fighter']:<26} [{lbl}]  {format_odds(leg['odds']):<8} "
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
            mkt         = market_label(b.get("market", "ML"), b.get("extra", {}))
            print(f"  {result_icon} #{b['id']:<3} {b['date']}  |  {b['fighter']:<22}  [{mkt}]  "
                  f"{format_odds(b['odds']):<7}  {b['units']}u  {format_currency(b['stake'])}  {pnl_str}")
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
                model_str = f"{leg['model_prob']*100:.1f}%" if leg.get("model_prob") is not None else "N/A"
                ev_str    = format_ev(leg["ev"]) if leg.get("ev") is not None else "N/A"
                impl_str  = f"{leg['implied_prob']*100:.1f}%"
                lbl       = market_label(leg.get("market", "ML"), leg.get("extra", {}))
                print(f"       {leg_icon} Leg {idx}: {leg['fighter']:<24} [{lbl}]  {format_odds(leg['odds']):<8} "
                      f"Model: {model_str:<8} Implied: {impl_str:<8} EV: {ev_str}")
    else:
        print("\n  PARLAYS — none settled")

    print(f"\n  └─────────────────────────────────────────────────────────┘")

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
                    desc      = f"PARLAY ({len(bet['legs'])} legs)"
                    disp_odds = bet.get("combined_american")
                else:
                    mkt       = market_label(bet.get("market", "ML"), bet.get("extra", {}))
                    desc      = f"{bet['fighter']} [{mkt}]"
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


# ── Settle bet ─────────────────────────────────────────────────────────────────

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
                lbl = market_label(leg.get("market", "ML"), leg.get("extra", {}))
                print(f"       Leg {idx}: {leg['fighter']:<28} [{lbl}]  {format_odds(leg['odds'])}")
        else:
            mkt = market_label(b.get("market", "ML"), b.get("extra", {}))
            print(f"  #{b['id']:<3} {b['fighter']:<24} [{mkt}]  "
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
        print(f"\n  Settling: PARLAY #{bet['id']} ({len(bet['legs'])} legs)  —  {format_currency(bet['stake'])} staked")
    else:
        mkt = market_label(bet.get("market", "ML"), bet.get("extra", {}))
        print(f"\n  Settling: {bet['fighter']} [{mkt}] ({format_odds(bet['odds'])})  —  {format_currency(bet['stake'])} staked")

    print("  1. Won")
    print("  2. Lost")

    while True:
        result = input("  Result (1 or 2): ").strip()
        if result in ("1", "2"):
            break
        print("  Please enter 1 or 2.")

    if result == "1":
        pnl              = bet["potential_win"]
        bet["status"]    = "won"
        bet["pnl"]       = pnl
        data["bankroll"] = round(data["bankroll"] + bet["stake"] + pnl, 2)
        if bet.get("type") == "parlay":
            for leg in bet["legs"]:
                leg["status"] = "won"
        print(f"\n  ✓ Won! +{format_currency(pnl)}")
    else:
        pnl              = -bet["stake"]
        bet["status"]    = "lost"
        bet["pnl"]       = pnl
        if bet.get("type") == "parlay":
            for leg in bet["legs"]:
                leg["status"] = "lost"
        print(f"\n  ✗ Lost. -{format_currency(bet['stake'])}")

    print(f"  New bankroll: {format_currency(data['bankroll'])}")
    save_data(data)
    pause()


# ── View stats ─────────────────────────────────────────────────────────────────

def view_stats(data: dict):
    print_header("STATS & PERFORMANCE")

    bets    = data["bets"]

    # ── All settled bets (singles + parlays) for overall P&L / ROI ───────────
    all_settled       = [b for b in bets if b["status"] != "pending"]
    all_total_staked  = sum(b["stake"] for b in all_settled)
    all_total_pnl     = sum(b["pnl"]   for b in all_settled)
    all_units_staked  = sum(b["units"] for b in all_settled)
    all_units_pnl     = sum(b["pnl"] / data["unit_size"] for b in all_settled)
    overall_roi       = (all_total_pnl / all_total_staked * 100) if all_total_staked > 0 else 0.0

    # ── Singles breakdown ─────────────────────────────────────────────────────
    singles = [b for b in bets if b.get("type", "single") == "single"]
    settled = [b for b in singles if b["status"] != "pending"]
    won     = [b for b in settled if b["status"] == "won"]
    lost    = [b for b in settled if b["status"] == "lost"]
    pending = [b for b in singles if b["status"] == "pending"]

    singles_staked     = sum(b["stake"] for b in settled)
    singles_pnl        = sum(b["pnl"]   for b in settled)
    singles_units_pnl  = sum(b["pnl"] / data["unit_size"] for b in settled)
    singles_roi        = (singles_pnl / singles_staked * 100) if singles_staked > 0 else 0.0

    plus_ev_bets  = [b for b in settled if b.get("ev") is not None and b["ev"] >= 0]
    minus_ev_bets = [b for b in settled if b.get("ev") is not None and b["ev"] <  0]

    favs          = [b for b in settled if b["odds"] < 0]
    underdogs     = [b for b in settled if b["odds"] >= 0]
    favs_won      = [b for b in favs      if b["status"] == "won"]
    underdogs_won = [b for b in underdogs if b["status"] == "won"]
    favs_pnl      = sum(b["pnl"] for b in favs)
    underdogs_pnl = sum(b["pnl"] for b in underdogs)

    print(f"\n  {'Bankroll':<28}: {format_currency(data['bankroll'])}")
    print(f"  {'Starting bankroll':<28}: {format_currency(DEFAULT_BANKROLL)}")
    print(f"  {'Unit size':<28}: {format_currency(data['unit_size'])}")
    print_divider()
    print(f"  OVERALL (singles + parlays)")
    print(f"  {'Total staked':<28}: {format_currency(all_total_staked)}")
    print(f"  {'Total P&L':<28}: {('+' if all_total_pnl >= 0 else '')}{format_currency(all_total_pnl)}")
    print(f"  {'ROI':<28}: {('+' if overall_roi >= 0 else '')}{overall_roi:.2f}%")
    print(f"  {'Units staked':<28}: {all_units_staked:.1f}u")
    print(f"  {'Units P&L':<28}: {('+' if all_units_pnl >= 0 else '')}{all_units_pnl:.2f}u")

    print_divider()
    print(f"  {'Total bets (all types)':<28}: {len(bets)}")
    print(f"  {'Pending (singles)':<28}: {len(pending)}")
    print(f"  {'Settled (singles)':<28}: {len(settled)}")
    print(f"  {'Won (singles)':<28}: {len(won)}")
    print(f"  {'Lost (singles)':<28}: {len(lost)}")

    if settled:
        win_rate = len(won) / len(settled) * 100
        print(f"  {'Win rate':<28}: {win_rate:.1f}%  ({len(won)}/{len(settled)})")

    print_divider()
    print(f"  SINGLES DETAIL")
    print(f"  {'Staked':<28}: {format_currency(singles_staked)}")
    print(f"  {'P&L':<28}: {('+' if singles_pnl >= 0 else '')}{format_currency(singles_pnl)}")
    print(f"  {'ROI':<28}: {('+' if singles_roi >= 0 else '')}{singles_roi:.2f}%")
    print(f"  {'Units P&L':<28}: {('+' if singles_units_pnl >= 0 else '')}{singles_units_pnl:.2f}u")

    if plus_ev_bets or minus_ev_bets:
        ev_bets_all = [b for b in settled if b.get("ev") is not None]
        avg_ev      = sum(b["ev"] for b in ev_bets_all) / len(ev_bets_all) if ev_bets_all else None
        print(f"  {'+EV bets placed':<28}: {len(plus_ev_bets)}")
        print(f"  {'-EV bets placed':<28}: {len(minus_ev_bets)}")
        if avg_ev is not None:
            print(f"  {'Avg EV per bet':<28}: {('+' if avg_ev >= 0 else '')}{avg_ev:.4f}")
        if plus_ev_bets:
            plus_ev_won = [b for b in plus_ev_bets if b["status"] == "won"]
            print(f"  {'+EV win rate':<28}: {len(plus_ev_won)}/{len(plus_ev_bets)} ({len(plus_ev_won)/len(plus_ev_bets)*100:.1f}%)")

    # ── Breakdown by market ────────────────────────────────────────────────────
    print_divider()
    print(f"  BY MARKET")
    print_divider()
    market_names = list(dict.fromkeys(b.get("market", "ML") for b in settled))
    for mkt in market_names:
        mkt_bets = [b for b in settled if b.get("market", "ML") == mkt]
        mkt_won  = [b for b in mkt_bets if b["status"] == "won"]
        mkt_pnl  = sum(b["pnl"] for b in mkt_bets)
        wr        = len(mkt_won) / len(mkt_bets) * 100 if mkt_bets else 0
        pnl_str   = f"{'+' if mkt_pnl >= 0 else ''}{format_currency(mkt_pnl)}"
        print(f"  {mkt:<20} {len(mkt_won)}/{len(mkt_bets)} ({wr:.0f}%)  P&L: {pnl_str}")

    print_divider()
    print(f"  FAVOURITES (negative odds)")
    if favs:
        fav_pick_rate = len(favs_won) / len(favs) * 100
        print(f"  {'  Bets':<28}: {len(favs)}")
        print(f"  {'  Pick rate':<28}: {len(favs_won)}/{len(favs)} ({fav_pick_rate:.1f}%)")
        print(f"  {'  P&L':<28}: {('+' if favs_pnl >= 0 else '')}{format_currency(favs_pnl)}")
    else:
        print(f"  {'  No settled favourite bets'}")

    print(f"  UNDERDOGS (+100 or higher)")
    if underdogs:
        dog_pick_rate = len(underdogs_won) / len(underdogs) * 100
        print(f"  {'  Bets':<28}: {len(underdogs)}")
        print(f"  {'  Pick rate':<28}: {len(underdogs_won)}/{len(underdogs)} ({dog_pick_rate:.1f}%)")
        print(f"  {'  P&L':<28}: {('+' if underdogs_pnl >= 0 else '')}{format_currency(underdogs_pnl)}")
    else:
        print(f"  {'  No settled underdog bets'}")

    # ── Parlay stats ───────────────────────────────────────────────────────────
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
        avg_legs            = sum(len(p["legs"]) for p in parlays_all) / len(parlays_all) if parlays_all else 0.0
        biggest_win         = max((p["pnl"] for p in parlays_settled), default=0.0)
        print(f"  {'Units staked':<28}: {parlay_units_staked:.1f}u")
        print(f"  {'Units P&L':<28}: {('+' if parlay_units_pnl >= 0 else '')}{parlay_units_pnl:.2f}u")
        print(f"  {'Win rate':<28}: {parlay_win_rate:.1f}%")
        print(f"  {'Avg legs per parlay':<28}: {avg_legs:.2f}")
        print(f"  {'Biggest win':<28}: {('+' if biggest_win >= 0 else '')}{format_currency(biggest_win)}")
    else:
        print(f"  No settled parlays yet.")

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
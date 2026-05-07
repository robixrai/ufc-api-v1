from core.tools import fighter_db
from core.predictor import Predict

predictor = Predict()

# ── Helpers ──────────────────────────────────────────────────────────────────

def get_fighter(name: str):
    for f in fighter_db.values():
        if getattr(f, "_personal-info_name") == name:
            return f
    # fallback: case-insensitive
    for f in fighter_db.values():
        if getattr(f, "_personal-info_name", "").lower() == name.lower():
            return f
    return None


def tier(prob: float) -> str:
    if prob >= 0.80: return "LOCK"
    if prob >= 0.55: return "NORMAL"
    return "COIN FLIP"


# ── Fight List ────────────────────────────────────────────────────────────────
# Format: (Fighter1, Fighter2, rounds, actual_winner, actual_method)
# actual_method: "KO/TKO" | "Submission" | "Decision"

FIGHTS = [

    # ── UFC FIGHT NIGHT 275 — PERTH, May 2 2026 ──────────────────────────────────
    ("Carlos Prates",       "Jack Della Maddalena",    5, "Carlos Prates",       "KO/TKO"),    # UFC Perth, May 2026 — R3 TKO
    ("Quillan Salkilld",    "Beneil Dariush",           3, "Quillan Salkilld",    "KO/TKO"),    # UFC Perth, May 2026 — R1 TKO
    ("Steve Erceg",         "Tim Elliott",              3, "Steve Erceg",         "Decision"),  # UFC Perth, May 2026 — unanimous
    ("Marwan Rahiki",       "Ollie Schmid",             3, "Marwan Rahiki",       "KO/TKO"),    # UFC Perth, May 2026 — R1 KO
    ("Brando Pericic",      "Shamil Gaziev",            3, "Brando Pericic",      "KO/TKO"),    # UFC Perth, May 2026 — R2 KO
    ("Louie Sutherland",    "Tai Tuivasa",              3, "Louie Sutherland",    "Decision"),  # UFC Perth, May 2026 — unanimous 30-26

    # ── HEAVYWEIGHT ──────────────────────────────────────────────────────────
    ("Tom Aspinall",        "Curtis Blaydes",          5, "Tom Aspinall",        "KO/TKO"),    # UFC 304, Jul 2024
    ("Tom Aspinall",        "Sergei Pavlovich",         5, "Tom Aspinall",        "KO/TKO"),    # UFC 295, Nov 2023
    ("Ciryl Gane",          "Serghei Spivac",           3, "Ciryl Gane",          "KO/TKO"),    # UFC Paris, Sep 2023
    ("Jailton Almeida",     "Serghei Spivac",           3, "Jailton Almeida",     "KO/TKO"),    # UFC Fight Night, Jun 2024
    ("Jailton Almeida",     "Alexander Volkov",         3, "Alexander Volkov",    "Decision"),  # UFC 321, Oct 2025
    ("Waldo Cortes-Acosta", "Ante Delija",              3, "Waldo Cortes-Acosta", "KO/TKO"),    # UFC Fight Night, Nov 2025
    ("Waldo Cortes-Acosta", "Derrick Lewis",            3, "Waldo Cortes-Acosta", "KO/TKO"),    # UFC 316, Jun 2025
    ("Serghei Spivac",      "Marcin Tybura",            3, "Serghei Spivac",      "Submission"),# UFC on ESPN, Aug 2024

    # ── LIGHT HEAVYWEIGHT ─────────────────────────────────────────────────────
    ("Alex Pereira",        "Jamahal Hill",             5, "Alex Pereira",        "KO/TKO"),    # UFC 300, Apr 2024
    ("Alex Pereira",        "Jiri Prochazka",           5, "Alex Pereira",        "KO/TKO"),    # UFC 303, Jun 2024
    ("Alex Pereira",        "Khalil Rountree Jr.",      5, "Alex Pereira",        "KO/TKO"),    # UFC Fight Night, Jun 2025
    ("Magomed Ankalaev",    "Alex Pereira",             5, "Alex Pereira",    "KO/TKO"),  # UFC 320, Oct 2025
    ("Jiri Prochazka",      "Aleksandar Rakić",         3, "Jiri Prochazka",      "KO/TKO"),    # UFC 300, Apr 2024
    ("Carlos Ulberg",       "Jamahal Hill",             5, "Carlos Ulberg",       "KO/TKO"),    # UFC 327, Apr 2026
    ("Khalil Rountree Jr.", "Bogdan Guskov",            3, "Khalil Rountree Jr.", "KO/TKO"),    # UFC Fight Night, 2024
    ("Jiri Prochazka",      "Khalil Rountree Jr.",      3, "Jiri Prochazka",      "KO/TKO"),    # UFC 320, Oct 2025
    ("Magomed Ankalaev",    "Jamahal Hill",             5, "Magomed Ankalaev",    "Decision"),  # UFC Fight Night, 2024

    # ── MIDDLEWEIGHT ──────────────────────────────────────────────────────────
    ("Sean Strickland",     "Paulo Costa",              3, "Sean Strickland",     "Decision"),  # UFC Fight Night, Sep 2024
    ("Israel Adesanya",     "Robert Whittaker",         5, "Israel Adesanya",     "Decision"),  # UFC 271, Feb 2022
    ("Caio Borralho",       "Jared Cannonier",          5, "Caio Borralho",       "Decision"),  # UFC Fight Night, 2024
    ("Nassourdine Imavov",  "Sean Strickland",          5, "Sean Strickland",  "Decision"),  # UFC Fight Night, Feb 2025
    ("Joe Pyfer",           "Israel Adesanya",          5, "Joe Pyfer",           "KO/TKO"),    # UFC Fight Night Seattle, Mar 2026
    ("Robert Whittaker",    "Paulo Costa",              3, "Robert Whittaker",    "Decision"),  # UFC 298, Feb 2024
    ("Anthony Hernandez",   "Michel Pereira",           5, "Anthony Hernandez",   "KO/TKO"),    # UFC Fight Night, Oct 2024
    ("Anthony Hernandez",   "Roman Dolidze",            3, "Anthony Hernandez",   "Submission"),# UFC Fight Night, Aug 2025
    ("Caio Borralho",       "Reinier De Ridder",        3, "Caio Borralho",       "Decision"),  # UFC Fight Night, 2024

    # ── WELTERWEIGHT ──────────────────────────────────────────────────────────
    ("Belal Muhammad",      "Leon Edwards",             5, "Belal Muhammad",      "Decision"),  # UFC 304, Jul 2024
    ("Jack Della Maddalena","Belal Muhammad",           5, "Jack Della Maddalena","Decision"),  # UFC 315, May 2025
    ("Sean Brady",          "Michael Morales",          3, "Michael Morales","KO/TKO"),    # UFC Fight Night, 2024
    ("Carlos Prates",       "Gabriel Bonfim",           3, "Carlos Prates",       "KO/TKO"),    # UFC Fight Night, 2025
    ("Sean Brady",          "Gilbert Burns",            5, "Sean Brady",          "Decision"),  # UFC Fight Night, 2024
    ("Carlos Prates",     "Ian Machado Garry",        5, "Ian Machado Garry",     "Decision"),  # UFC 322, Nov 2025
    ("Kamaru Usman",        "Leon Edwards",             5, "Leon Edwards",        "Decision"),  # UFC 286, Mar 2023

    # ── LIGHTWEIGHT ───────────────────────────────────────────────────────────
    ("Islam Makhachev",     "Renato Moicano",           5, "Islam Makhachev",     "Submission"),# UFC 311, Jan 2025
    ("Arman Tsarukyan",     "Charles Oliveira",         3, "Arman Tsarukyan",     "Decision"),  # UFC 300, Apr 2024
    ("Renato Moicano",      "Beneil Dariush",           3, "Beneil Dariush",      "Decision"),# UFC Fight Night, 2024
    ("Benoît Saint Denis",  "Renato Moicano",           3, "Renato Moicano",      "KO/TKO"),    # UFC Paris, Sep 2024 — doctor stoppage TKO
    ("Rafael Fiziev",       "Justin Gaethje",           3, "Justin Gaethje",      "Decision"),  # UFC 286, Mar 2023
    ("Paddy Pimblett",      "Michael Chandler",           3, "Paddy Pimblett",      "KO/TKO"),  # UFC 304, Jul 2024
    ("Mauricio Ruffy",      "Rafael Fiziev",           3, "Mauricio Ruffy",      "KO/TKO"),    # UFC 313, Mar 2025
    ("Arman Tsarukyan",     "Dan Hooker",           3, "Arman Tsarukyan",     "KO/TKO"),  # UFC Fight Night, 2024

    # ── FEATHERWEIGHT ─────────────────────────────────────────────────────────
    ("Ilia Topuria",        "Alexander Volkanovski",    5, "Ilia Topuria",        "KO/TKO"),    # UFC 298, Feb 2024
    ("Ilia Topuria",        "Max Holloway",             5, "Ilia Topuria",        "KO/TKO"),    # UFC 308, Oct 2024
    ("Movsar Evloev",       "Arnold Allen",             3, "Movsar Evloev",       "Decision"),  # UFC Fight Night, 2024
    ("Diego Lopes",         "Brian Ortega",             3, "Diego Lopes",         "Decision"),  # UFC 306, Sep 2024
    ("Lerone Murphy",       "Josh Emmett",              5, "Lerone Murphy",       "Decision"),  # UFC Fight Night, 2024
    ("Jean Silva",          "Arnold Allen",             3, "Jean Silva",          "Decision"),    # UFC Fight Night, 2025
    ("Yair Rodriguez",      "Brian Ortega",             5, "Yair Rodriguez",      "Submission"),# UFC Fight Night, 2023
    ("Movsar Evloev",       "Lerone Murphy",            5, "Movsar Evloev",       "Decision"),  # UFC London, Mar 2026
    ("Diego Lopes",         "Jean Silva",               5, "Diego Lopes",         "KO/TKO"),  # UFC Fight Night, 2025
    ("Youssef Zalal",       "Aljamain Sterling",        5, "Aljamain Sterling",       "Decision"),  # UFC Fight Night, Apr 2026

    # ── BANTAMWEIGHT ──────────────────────────────────────────────────────────
    ("Merab Dvalishvili",   "Sean O'Malley",            5, "Merab Dvalishvili",   "Submission"),  # UFC 306, Sep 2024
    ("Umar Nurmagomedov",   "Merab Dvalishvili",        5, "Merab Dvalishvilli",   "Decision"),  # UFC 311, Jan 2025
    ("Cory Sandhagen",      "Song Yadong",              5, "Cory Sandhagen",      "KO/TKO"),  # UFC Fight Night, Aug 2024
    ("Petr Yan",            "Cory Sandhagen",          5, "Petr Yan",            "Decision"),  # UFC 299, Mar 2024
    ("Deiveson Figueiredo", "Marlon Vera",              3, "Deiveson Figueiredo", "Decision"),  # UFC Fight Night, Aug 2024
    ("Umar Nurmagomedov",   "Deiveson Figueiredo",           3, "Umar Nurmagomedov",   "Decision"),  # UFC Abu Dhabi, Aug 2024
    ("Sean O'Malley",       "Marlon Vera",              5, "Sean O'Malley",       "Decision"),  # UFC 299, Mar 2024

    # ── FLYWEIGHT ─────────────────────────────────────────────────────────────
    ("Alexandre Pantoja",   "Brandon Moreno",           5, "Alexandre Pantoja",   "Decision"),  # UFC 290, Jul 2023
    ("Alexandre Pantoja",   "Steve Erceg",              5, "Alexandre Pantoja",   "Decision"),  # UFC 301, May 2024
    ("Alexandre Pantoja",   "Brandon Royval",           5, "Alexandre Pantoja",   "Decision"),# UFC 296, Dec 2023
    ("Tatsuro Taira",       "Brandon Moreno",              3, "Tatsuro Taira",       "Submission"),# UFC Fight Night, 2024
    ("Brandon Royval",      "Tim Elliott",              3, "Brandon Royval",      "Submission"),    # UFC Fight Night, 2024
    ("Kyoji Horiguchi",     "Tagir Ulanbekov",          3, "Kyoji Horiguchi",     "Submission"),  # UFC Fight Night, 2024
    ("Tatsuro Taira",         "Brandon Royval",           5, "Brandon Royval",         "Decision"),  # UFC Fight Night, 2024

    # ── WOMEN'S STRAWWEIGHT ───────────────────────────────────────────────────
    ("Zhang Weili",         "Yan Xiaonan",              5, "Zhang Weili",         "Decision"),    # UFC 300, Apr 2024
    ("Zhang Weili",         "Tatiana Suarez",           5, "Zhang Weili",         "Decision"),  # UFC 312, Feb 2025
    ("Mackenzie Dern",      "Virna Jandiroba",          5, "Mackenzie Dern",      "Decision"),  # UFC Fight Night, 2025
    ("Amanda Lemos",        "Mackenzie Dern",           3, "Amanda Lemos",        "Decision"),  # UFC Fight Night, 2024
    ("Loopy Godinez",       "Tabatha Ricci",            3, "Loopy Godinez",       "Decision"),  # UFC Fight Night, 2024
    ("Jéssica Andrade",     "Marina Rodriguez",         3, "Jéssica Andrade",     "Decision"),    # UFC 300, Apr 2024
    ("Yan Xiaonan",         "Virna Jandiroba",          3, "Yan Xiaonan",         "Decision"),  # UFC Fight Night, 2025

    # ── WOMEN'S FLYWEIGHT ─────────────────────────────────────────────────────
    ("Valentina Shevchenko","Alexa Grasso",             5, "Valentina Shevchenko","Decision"),  # UFC 306, Sep 2024
    ("Erin Blanchfield",    "Manon Fiorot",             5, "Manon Fiorot",        "Decision"),  # UFC Fight Night, 2024
    ("Rose Namajunas","Tracy Cortez", 3, "Rose Namajunas","Decision"),
    ("Manon Fiorot",        "Rose Namajunas",           3, "Manon Fiorot",        "Decision"),  # UFC Fight Night, 2024
    ("Alexa Grasso","Maycee Barber", 3, "Alexa Grasso","KO/TKO"),
("Manon Fiorot","Jasmine Jasudavicius", 3, "Manon Fiorot","KO/TKO"),

    # ── WOMEN'S BANTAMWEIGHT ──────────────────────────────────────────────────
    ("Julianna Peña","Raquel Pennington", 5, "Julianna Peña","Decision"),  # UFC 307, Oct 2024
    ("Kayla Harrison",      "Julianna Peña",            5, "Kayla Harrison",      "Submission"),# UFC 316, Jun 2025
    ("Kayla Harrison",      "Ketlen Vieira",            3, "Kayla Harrison",      "Decision"),  # UFC 307, Oct 2024
    ("Macy Chiasson","Mayra Bueno Silva", 3, "Macy Chiasson","KO/TKO"),  # UFC Fight Night, 2024
    ("Irene Aldana",        "Karol Rosa",               3, "Irene Aldana",        "Decision"),    # UFC Fight Night, 2024
    ("Norma Dumont",        "Ketlen Vieira",            3, "Norma Dumont",        "Decision"),  # UFC Fight Night, Nov 2025
    ("Ketlen Vieira",       "Macy Chiasson",            3, "Ketlen Vieira",       "Decision"),  # UFC Fight Night, May 2025
    ("Raquel Pennington",   "Mayra Bueno Silva",        5, "Raquel Pennington",   "Decision"),  # UFC 297, Jan 2024
]
# ── Run Backtest ──────────────────────────────────────────────────────────────

def run_backtest():
    results = []

    skipped = []

    for f1_name, f2_name, rounds, actual_winner, actual_method in FIGHTS:
        # skip placeholder fights (same fighter vs themselves)
        if f1_name == f2_name:
            skipped.append(f"  SKIPPED (placeholder): {f1_name} vs {f2_name}")
            continue

        f1 = get_fighter(f1_name)
        f2 = get_fighter(f2_name)

        if f1 is None:
            skipped.append(f"  SKIPPED (not found): {f1_name}")
            continue
        if f2 is None:
            skipped.append(f"  SKIPPED (not found): {f2_name}")
            continue

        try:
            win_prob, lose_prob, logs = predictor.predict_fight(f1, f2, rounds, 0)
        except Exception as e:
            skipped.append(f"  SKIPPED (error): {f1_name} vs {f2_name} — {e}")
            continue

        # who did the model pick
        if win_prob >= 0.5:
            predicted_winner = f1_name
            confidence       = win_prob
        else:
            predicted_winner = f2_name
            confidence       = lose_prob

        # get method from logs — combine_method_profiles logs "Most likely method"
        predicted_method = "Decision"  # default
        for line in logs.splitlines():
            if "Most likely method" in line:
                if "KO/TKO"     in line: predicted_method = "KO/TKO"
                elif "Submission" in line: predicted_method = "Submission"
                else:                     predicted_method = "Decision"
                break

        fight_tier      = tier(confidence)
        winner_correct  = (predicted_winner == actual_winner)
        method_correct  = predicted_method == actual_method

        results.append({
            "f1":             f1_name,
            "f2":             f2_name,
            "predicted":      predicted_winner,
            "actual":         actual_winner,
            "pred_method":    predicted_method,
            "actual_method":  actual_method,
            "confidence":     confidence,
            "tier":           fight_tier,
            "winner_correct": winner_correct,
            "method_correct": method_correct,
        })

    # ── Print Results ─────────────────────────────────────────────────────────

    print("\n" + "=" * 90)
    print("BACKTEST RESULTS".center(90))
    print("=" * 90)

    tiers = ["LOCK", "NORMAL", "COIN FLIP"]
    tier_data = {t: {"total": 0, "winner": 0, "method": 0} for t in tiers}

    print(f"\n{'#':<4} {'MATCHUP':<42} {'CONF':>6}  {'TIER':<10} {'WIN':>4} {'METHOD':>7}")
    print("-" * 90)

    for i, r in enumerate(results, 1):
        matchup    = f"{r['f1']} vs {r['f2']}"[:41]
        win_mark   = "✓" if r["winner_correct"] else "✗"
        meth_mark  = "✓" if r["method_correct"] else "✗"
        conf_str   = f"{round(r['confidence'] * 100, 1)}%"

        print(f"{i:<4} {matchup:<42} {conf_str:>6}  {r['tier']:<10} {win_mark:>4} {meth_mark:>7}")

        td = tier_data[r["tier"]]
        td["total"]  += 1
        td["winner"] += int(r["winner_correct"])
        td["method"] += int(r["method_correct"])

    # ── Summary ───────────────────────────────────────────────────────────────

    total        = len(results)
    total_win    = sum(r["winner_correct"] for r in results)
    total_method = sum(r["method_correct"] for r in results)
    # method accuracy only on correct winner picks
    correct_wins = [r for r in results if r["winner_correct"]]
    method_on_correct = sum(r["method_correct"] for r in correct_wins)

    print("\n" + "=" * 90)
    print("SUMMARY".center(90))
    print("=" * 90)

    print(f"\n  {'TIER':<12} {'FIGHTS':>7} {'WIN CORRECT':>12} {'WIN %':>7} {'METHOD CORRECT':>15} {'METHOD %':>9}")
    print("  " + "-" * 70)
    for t in tiers:
        td = tier_data[t]
        if td["total"] == 0:
            continue
        win_pct  = round(td["winner"] / td["total"] * 100, 1)
        meth_pct = round(td["method"] / td["total"] * 100, 1)
        print(f"  {t:<12} {td['total']:>7} {td['winner']:>12} {win_pct:>6}% {td['method']:>15} {meth_pct:>8}%")

    print("  " + "-" * 70)
    overall_win_pct  = round(total_win  / total * 100, 1) if total else 0
    overall_meth_pct = round(total_method / total * 100, 1) if total else 0
    method_on_correct_pct = round(method_on_correct / len(correct_wins) * 100, 1) if correct_wins else 0

    print(f"\n  {'OVERALL':<20} {total} fights")
    print(f"  {'Win accuracy':<20} {total_win}/{total}  ({overall_win_pct}%)")
    print(f"  {'Method accuracy':<20} {total_method}/{total}  ({overall_meth_pct}%)")
    print(f"  {'Method (wins only)':<20} {method_on_correct}/{len(correct_wins)}  ({method_on_correct_pct}%)")

    if skipped:
        print("\n" + "=" * 90)
        print("SKIPPED FIGHTS".center(90))
        print("=" * 90)
        for s in skipped:
            print(s)

    print("\n" + "=" * 90 + "\n")


if __name__ == "__main__":
    run_backtest()
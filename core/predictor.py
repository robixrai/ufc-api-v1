from typing import Tuple
import math

from core.fighter import Fighter
from core.tools import rankings_index

def clamp(x: float, low: float = -1.0, high: float = 1.0) -> float:
    return max(low, min(high, x))

def clamp_prop(x: float, low: float = 0.0, high: float = 1.0) -> float:
    return max(low, min(high, x))


class Predict():
    def __init__(self) -> None:
        pass

    diff_small = 0.10
    scale = 10
    age_div = 10.0
    height_div = 10.0
    reach_div = 5.0

    age_weight = 0.25
    height_weight = 0.35
    reach_weight = 0.40

    def predict_fight(self, fighter1: Fighter, fighter2: Fighter) -> Tuple[float, float, str]:
        number1 = rankings_index[getattr(fighter1, "_personal-info_weight-class")]
        number2 = rankings_index[getattr(fighter2, "_personal-info_weight-class")]

        if number1 != number2 and (number1 + 1 != number2 and number1 - 1 != number2):
            return 0, 0, "Not possible. Different weight classes"
        if getattr(fighter1, "_personal-info_gender") != getattr(fighter2, "_personal-info_gender"):
            return 0, 0, "Not possible. Different genders"
        if getattr(fighter1, "_personal-info_status") == "Retired" or getattr(fighter2, "_personal-info_status") == "Retired":
            return 0.0, 0.0, "Not possible. One or both of the fighters is retired."

        gameplan1, gameplan2, logs = self.predict_gameplan(fighter1, fighter2)
        standing_prob, grappling_prob, logs = self.predict_location(fighter1, fighter2, gameplan1, gameplan2, logs)
        win_prob, lose_prob, logs = self.predict_outcome(standing_prob, grappling_prob, fighter1, fighter2, logs)

        logs += "\n\n"
        logs += "FINAL WIN PROBABILITY".center(80) + "\n"
        logs += "\n\n"
        logs += (
            f"{getattr(fighter1, '_personal-info_name')}: {round(win_prob * 100, 2)}%".center(40) +
            f"{getattr(fighter2, '_personal-info_name')}: {round(lose_prob * 100, 2)}%".center(40) +
            "\n\n\n"
        )
        logs += "_" * 80 + "\n"
        return win_prob, lose_prob, logs

    def skill_gap_multipliers(self, fighter1: Fighter, fighter2: Fighter, diff: float, logs: str) -> Tuple[float, str]:
        f1_str_score = getattr(fighter1, "striking_score")
        f2_str_score = getattr(fighter2, "striking_score")
        f1_str_def   = getattr(fighter1, "_skillset_striking_overview_defence")
        f2_str_def   = getattr(fighter2, "_skillset_striking_overview_defence")

        f1_str_adv = (f1_str_score - f2_str_def) / self.scale
        f2_str_adv = (f2_str_score - f1_str_def) / self.scale

        f1_grap_score = getattr(fighter1, "grappling_score")
        f2_grap_score = getattr(fighter2, "grappling_score")
        f1_grap_def   = getattr(fighter1, "_skillset_grappling_defence")
        f2_grap_def   = getattr(fighter2, "_skillset_grappling_defence")

        f1_grap_adv = (f1_grap_score - f2_grap_def) / self.scale
        f2_grap_adv = (f2_grap_score - f1_grap_def) / self.scale

        net_striking  = f1_str_adv  - f2_str_adv
        net_grappling = f1_grap_adv - f2_grap_adv

        logs += "\n\n" + "-" * 80 + "\n"
        logs += "SKILL GAP CALCULATIONS".center(80) + "\n"
        logs += "-" * 80 + "\n\n"
        logs += f"{'STRIKING':<20} | {getattr(fighter1, '_personal-info_name')}: {round(f1_str_adv, 3)} vs {getattr(fighter2, '_personal-info_name')}: {round(f2_str_adv, 3)}\n"
        logs += f"{'NET STRIKING':<20} | {round(net_striking, 3)}\n\n"
        logs += f"{'GRAPPLING':<20} | {getattr(fighter1, '_personal-info_name')}: {round(f1_grap_adv, 3)} vs {getattr(fighter2, '_personal-info_name')}: {round(f2_grap_adv, 3)}\n"
        logs += f"{'NET GRAPPLING':<20} | {round(net_grappling, 3)}\n"

        combined = (0.8 * net_striking) + (1.0 * net_grappling)
        delta = combined
        logs += f"\n{'COMBINED DELTA':<20} | (0.8 * {round(net_striking, 3)}) + (1.0 * {round(net_grappling, 3)}) = {round(delta, 4)}\n"
        return delta, logs

    def specs_adv(self, fighter1: Fighter, fighter2: Fighter) -> Tuple[float, str]:

        age_diff    = fighter2.age - fighter1.age
        height_diff = getattr(fighter1, "_specs_height") - getattr(fighter2, "_specs_height") ; height_diff /= 2
        reach_diff  = getattr(fighter1, "_specs_reach")  - getattr(fighter2, "_specs_reach")

        age_norm    = clamp(age_diff, -10, 10)
        height_norm = clamp(height_diff, -10, 10)
        reach_norm  = clamp(reach_diff, -10, 10)

        advantage  = (self.age_weight * age_norm) + (self.height_weight * height_norm) + (self.reach_weight * reach_norm) ; advantage /= 10
        advantage /= 2

        logs_add  = "\n\n" + "_" * 80 + "\n\n"
        logs_add += "PHYSICAL SPECS COMPARISON".center(80) + "\n"
        logs_add += "_" * 80 + "\n\n\n"
        logs_add += f"{'Age Diff':<10}: {round(age_diff, 2)} yrs | {'Height Diff':<10}: {round(height_diff, 2)}cm | {'Reach Diff':<10}: {round(reach_diff, 2)}in\n\n"
        logs_add += f"{'Specs Advantage for ' + getattr(fighter1, '_personal-info_name'):<30}: {round(advantage, 3)}\n"
        return advantage, logs_add

    def scale_for_diff(self, fighter1: Fighter, fighter2: Fighter, diff: float, logs: str) -> Tuple[float, str]:
        fighter1_adv, logs = self.skill_gap_multipliers(fighter1, fighter2, diff, logs)
        absd = abs(diff)
        average = getattr(fighter1, "_skillset_ratio") + getattr(fighter2, "_skillset_ratio")
        average /= 2

        small_thresh, med_thresh, high_thresh = 0.1, 0.2, 0.3

        logs += "\n\n" + "-" * 80 + "\n"
        logs += "SCALING ADJUSTMENTS".center(80) + "\n"
        logs += "-" * 80 + "\n\n"

        if absd <= self.diff_small:
            logs += "RESULT: MARGINAL RATIO DIFFERENCE. NO SCALING APPLIED.\n"
            return average, logs

        skill_diff = abs(fighter1_adv)
        ratio = 0.9
        if skill_diff < small_thresh:   ratio = 0.5
        elif skill_diff < med_thresh:   ratio = 0.67
        elif skill_diff < high_thresh:  ratio = 0.75

        logs += f"SKILL DIFFERENCE (F1 Advantage): {round(fighter1_adv, 3)}\n"
        logs += f"DETERMINED RATIO: {ratio} : {round(1.0 - ratio, 2)}\n"

        if fighter1_adv > 0.0:
            matchup = (ratio * getattr(fighter1, "_skillset_ratio")) + ((1 - ratio) * getattr(fighter2, "_skillset_ratio"))
            logs += f"MATCHUP CALC: ({ratio} * {getattr(fighter1, '_skillset_ratio')}) + ({round(1 - ratio, 2)} * {getattr(fighter2, '_skillset_ratio')}) = {round(matchup, 3)}\n"
            return matchup, logs

        matchup = (ratio * getattr(fighter2, "_skillset_ratio")) + ((1 - ratio) * getattr(fighter1, "_skillset_ratio"))
        logs += f"MATCHUP CALC: ({round(1 - ratio, 2)} * {getattr(fighter1, '_skillset_ratio')}) + ({ratio} * {getattr(fighter2, '_skillset_ratio')}) = {round(matchup, 3)}\n"
        return matchup, logs

    def predict_gameplan(self, fighter1: Fighter, fighter2: Fighter) -> Tuple[float, float, str]:
        gameplan1 = getattr(fighter1, "_skillset_ratio")
        gameplan2 = getattr(fighter2, "_skillset_ratio")

        logs  = "\n" + "=" * 80 + "\n"
        logs += "FIGHT PREDICTION ENGINE LOGS".center(80) + "\n"
        logs += "=" * 80 + "\n\n\n"
        logs += f"{getattr(fighter1, '_personal-info_name'):<40} Striking Ratio: {gameplan1}\n"
        logs += f"{getattr(fighter2, '_personal-info_name'):<40} Striking Ratio: {gameplan2}\n"
        return gameplan1, gameplan2, logs

    def predict_location(self, fighter1: Fighter, fighter2: Fighter, gameplan1: float, gameplan2: float, logs: str) -> Tuple[float, float, str]:
        striking_diff = gameplan1 - gameplan2

        logs += "\n\n" + "_" * 80 + "\n\n"
        logs += "LOCATION PROBABILITY ANALYSIS".center(80) + "\n"
        logs += "_" * 80 + "\n\n"
        logs += f"Initial Ratio Difference: {round(striking_diff, 2)}\n"

        S, logs        = self.scale_for_diff(fighter1, fighter2, striking_diff, logs)
        standing_prob  = clamp_prop(S)
        grappling_prob = 1.0 - standing_prob

        logs += "\n\n" + "LOCATION RESULTS".center(40).center(80, ".") + "\n\n\n"
        logs += f"{'Standing Probability':<30}: {round(standing_prob * 100, 2)}%\n"
        logs += f"{'Grappling Probability':<30}: {round(grappling_prob * 100, 2)}%\n"
        return standing_prob, grappling_prob, logs

    def build_base_features(self, fighter, style):
        striking_base = {
            "Accuracy":      getattr(fighter, "_skillset_striking_overview_accuracy", 0),
            "Power":         getattr(fighter, "_skillset_striking_overview_power", 0),
            "Volume":        getattr(fighter, "_skillset_striking_overview_volume", 0),
            "LegKicks":      getattr(fighter, "_skillset_striking_kicks_low", 0),
            "HeadKicks":     getattr(fighter, "_skillset_striking_kicks_head", 0),
            "ClinchStriking":getattr(fighter, "_skillset_clinch_clinch-striking", 0),
            "Defense":       getattr(fighter, "_skillset_striking_overview_defence", 0),
            "Stamina":       getattr(fighter, "_skillset_intangibles_stamina", 0),
            "FightIQ":       getattr(fighter, "_skillset_intangibles_fight-iq", 0),
        }
        grappling_base = {
            "TakedownOffense":   getattr(fighter, "_skillset_grappling_takedown", 0),
            "TakedownDefense":   getattr(fighter, "_skillset_grappling_defence", 0),
            "SubmissionThreat":  getattr(fighter, "_skillset_grappling_submissions", 0),
            "Scrambles":         getattr(fighter, "_skillset_grappling_scrambles", 0),
            "GroundControl":     getattr(fighter, "_skillset_grappling_ground-control", 0),
            "ClinchControl":     getattr(fighter, "_skillset_clinch_clinch-control", 0),
            "Stamina":           getattr(fighter, "_skillset_intangibles_stamina", 0),
            "Recovery":          getattr(fighter, "_skillset_intangibles_recovery", 0),
            "FightIQ":           getattr(fighter, "_skillset_intangibles_fight-iq", 0),
        }
        if style in ("s", "S"): return striking_base
        if style in ("g", "G"): return grappling_base
        raise ValueError("style must be 's' or 'g'")

    def calc_style_multiplier(self, fighter1: Fighter, fighter2: Fighter, logs: str) -> Tuple[
        float, float, float, float, str]:

        striking_style_weights = {
            "Counter Striker": {
                "Accuracy": 0.2, "Power": 0.15, "Volume": 0.1, "LegKicks": 0.10,
                "HeadKicks": 0.05, "ClinchStriking": 0.04, "Defense": 0.2,
                "Stamina": 0.06, "FightIQ": 0.1
            },
            "Pressure Striker": {
                "Accuracy": 0.13, "Power": 0.1, "Volume": 0.25, "LegKicks": 0.13,
                "HeadKicks": 0.03, "ClinchStriking": 0.14, "Defense": 0.06,
                "Stamina": 0.15, "FightIQ": 0.01
            },
            "Outside Sniper": {
                "Accuracy": 0.20, "Power": 0.09, "Volume": 0.20, "LegKicks": 0.09,
                "HeadKicks": 0.06, "ClinchStriking": 0.02, "Defense": 0.18,
                "Stamina": 0.05, "FightIQ": 0.11
            },
            "Technical Boxer": {
                "Accuracy": 0.25, "Power": 0.2, "Volume": 0.16, "LegKicks": 0.05,
                "HeadKicks": 0.04, "ClinchStriking": 0.07, "Defense": 0.10,
                "Stamina": 0.04, "FightIQ": 0.09
            },
            "Muay Thai / Kickboxer": {
                "Accuracy": 0.15, "Power": 0.17, "Volume": 0.12, "LegKicks": 0.27,
                "HeadKicks": 0.10, "ClinchStriking": 0.12, "Defense": 0.03,
                "Stamina": 0.03, "FightIQ": 0.01
            }
        }

        grappling_style_weights = {
            "Wrestler": {
                "TakedownOffense": 0.25, "TakedownDefense": 0.18, "SubmissionThreat": 0.04,
                "Scrambles": 0.1, "GroundControl": 0.18,
                "ClinchControl": 0.08, "Stamina": 0.1, "Recovery": 0.02, "FightIQ": 0.05
            },
            "Defensive Grappler": {
                "TakedownOffense": 0.06, "TakedownDefense": 0.34, "SubmissionThreat": 0.08,
                "Scrambles": 0.18, "GroundControl": 0.08,
                "ClinchControl": 0.08, "Stamina": 0.06, "Recovery": 0.08, "FightIQ": 0.04
            },
            "Submission Specialist": {
                "TakedownOffense": 0.12, "TakedownDefense": 0.08, "SubmissionThreat": 0.34,
                "Scrambles": 0.16, "GroundControl": 0.14,
                "ClinchControl": 0.04, "Stamina": 0.06, "Recovery": 0.04, "FightIQ": 0.02
            },
            "Ground and Pound": {
                "TakedownOffense": 0.25, "TakedownDefense": 0.10, "SubmissionThreat": 0.05,
                "Scrambles": 0.10, "GroundControl": 0.20,
                "ClinchControl": 0.15, "Stamina": 0.09, "Recovery": 0.05, "FightIQ": 0.01
            },
            "All-Round Grappler": {
                "TakedownOffense": 0.16, "TakedownDefense": 0.16, "SubmissionThreat": 0.12,
                "Scrambles": 0.14, "GroundControl": 0.14,
                "ClinchControl": 0.1, "Stamina": 0.1, "Recovery": 0.06, "FightIQ": 0.02
            }
        }

        STR_STYLE_ADVANTAGE = {
            "Counter Striker": ["Pressure Striker"],
            "Pressure Striker": ["Outside Sniper"],
            "Outside Sniper": ["Technical Boxer", "Muay Thai / Kickboxer"],
            "Technical Boxer": ["Pressure Striker"],
            "Muay Thai / Kickboxer": ["Technical Boxer"]
        }

        GRP_STYLE_ADVANTAGE = {
            "Wrestler": ["Submission Specialist", "Ground and Pound"],
            "Defensive Grappler": ["Wrestler", "Submission Specialist"],
            "Submission Specialist": ["Ground and Pound"],
            "Ground and Pound": ["Defensive Grappler", "All-Round Grappler"],
            "All-Round Grappler": ["Wrestler"]
        }

        STANCE_ATTRIBUTE_ADJUSTMENTS = {
            "Orthodox": {},
            "Southpaw": {
                "Power": +0.20,
                "Defense": +0.10,
                "Accuracy": +0.10,
                "LegKicks": -0.20,
                "HeadKicks": -0.10,
                "Volume": -0.10,
            },
            "Switch": {
                "Volume": +0.20,
                "FightIQ": +0.10,
                "Accuracy": +0.10,
                "Power": -0.20,
                "ClinchStriking": -0.10,
                "LegKicks": -0.10,
            }
        }

        STANCE_MATCHUP_BONUS = {
            ("Southpaw", "Orthodox"): +0.25,
            ("Orthodox", "Southpaw"): -0.25,
            ("Switch", "Orthodox"): +0.125,
            ("Switch", "Southpaw"): +0.125,
            ("Orthodox", "Switch"): -0.125,
            ("Southpaw", "Switch"): -0.125,
        }

        style_boost = 1.1

        f1_name = getattr(fighter1, "_personal-info_name")
        f2_name = getattr(fighter2, "_personal-info_name")
        f1_stance = getattr(fighter1, "_specs_stance", "Orthodox")
        f2_stance = getattr(fighter2, "_specs_stance", "Orthodox")

        # ------------------------------------------------------------------ #
        def apply_stance_adjustments(base: dict, stance: str) -> Tuple[dict, str]:
            adjustments = STANCE_ATTRIBUTE_ADJUSTMENTS.get(stance, {})
            adjusted = dict(base)
            s_log = ""

            if not adjustments:
                s_log += f"  Stance : {stance} (orthodox baseline — no attribute changes)\n"
                return adjusted, s_log

            s_log += f"  Stance : {stance}\n\n"
            s_log += f"  {'Attribute':<22} | {'Original':>8} | {'Adj':>6} | {'New Value':>10}\n"
            s_log += "  " + "-" * 53 + "\n"
            for attr, pct in adjustments.items():
                if attr in adjusted:
                    original = adjusted[attr]
                    adjusted[attr] = original * (1 + pct)
                    sign = "+" if pct >= 0 else ""
                    s_log += (
                        f"  {attr:<22} | {round(original, 2):>8} | "
                        f"{sign}{int(pct * 100):>5}% | "
                        f"{round(adjusted[attr], 4):>10}\n"
                    )
            s_log += "  " + "-" * 53 + "\n"
            return adjusted, s_log

        # ------------------------------------------------------------------ #
        def compute_style_strength(
                base: dict, weights: dict,
                fighter_name: str, label: str,
                stance: str, opp_stance: str,
                apply_stance: bool = True
        ) -> Tuple[float, str]:

            bd = "\n"
            bd += f"  Fighter  : {fighter_name}\n"
            bd += f"  Style    : {label}\n"
            bd += f"  Stance   : {stance}  vs  opponent stance: {opp_stance}\n\n"

            # Step 1 — stance attribute adjustments
            if apply_stance:
                adjusted, s_log = apply_stance_adjustments(base, stance)
                bd += s_log + "\n"
            else:
                adjusted = dict(base)
                bd += f"  Stance adjustments: N/A (grappling is stance-neutral)\n\n"

            # Step 2 — weighted dot product
            bd += f"  {'Attribute':<22} | {'Value':>8} | {'Weight':>8} | {'Contribution':>12}\n"
            bd += "  " + "-" * 57 + "\n"
            total = 0.0
            for key, w in weights.items():
                val = adjusted.get(key, 0)
                contribution = val * w
                total += contribution
                bd += (
                    f"  {key:<22} | {round(val, 2):>8} | "
                    f"{round(w, 3):>8} | {round(contribution, 4):>12}\n"
                )
            bd += "  " + "-" * 57 + "\n"
            bd += f"  {'Weighted Total':<22} | {'':>8} | {'':>8} | {round(total, 4):>12}\n"

            # Step 3 — stance matchup flat bonus
            if apply_stance:
                matchup_key = (stance, opp_stance)
                stance_bonus = STANCE_MATCHUP_BONUS.get(matchup_key, 0.0)
                final = total + stance_bonus
                bd += "\n"
                if stance_bonus != 0.0:
                    sign = "+" if stance_bonus > 0 else ""
                    bd += f"  Stance matchup  : {stance} vs {opp_stance} → {sign}{stance_bonus} flat bonus\n"
                    bd += f"  Strength after  : {round(total, 4)} {sign}{stance_bonus} = {round(final, 4)}\n"
                else:
                    bd += f"  Stance matchup  : {stance} vs {opp_stance} → no bonus (mirror stance)\n"
                    bd += f"  Final strength  : {round(final, 4)}\n"
            else:
                final = total
                bd += f"\n  Final strength  : {round(final, 4)}\n"

            return final, bd

        # ------------------------------------------------------------------ #

        f1_str_style = getattr(fighter1, "_skillset_striking_style", None)
        f2_str_style = getattr(fighter2, "_skillset_striking_style", None)
        f1_grp_style = getattr(fighter1, "_skillset_grappling_style", None)
        f2_grp_style = getattr(fighter2, "_skillset_grappling_style", None)

        f1_str_base = self.build_base_features(fighter1, "s")
        f2_str_base = self.build_base_features(fighter2, "s")
        f1_grp_base = self.build_base_features(fighter1, "g")
        f2_grp_base = self.build_base_features(fighter2, "g")

        logs += "\n\n" + "=" * 80 + "\n"
        logs += "STYLE MULTIPLIER CALCULATION".center(80) + "\n"
        logs += "=" * 80 + "\n\n"
        logs += f"  {f1_name:<18} Stance: {f1_stance}\n"
        logs += f"  {f2_name:<18} Stance: {f2_stance}\n"
        logs += f"  {f1_name:<18} Striking Style : {f1_str_style}\n"
        logs += f"  {f2_name:<18} Striking Style : {f2_str_style}\n"
        logs += f"  {f1_name:<18} Grappling Style: {f1_grp_style}\n"
        logs += f"  {f2_name:<18} Grappling Style: {f2_grp_style}\n"

        # --- Striking ---
        logs += "\n" + "  STRIKING BASE SCORES".ljust(80) + "\n"
        logs += "  " + "-" * 78 + "\n\n"

        if f1_str_style and f1_str_style in striking_style_weights:
            f1_str_strength, bd = compute_style_strength(
                f1_str_base, striking_style_weights[f1_str_style],
                f1_name, f1_str_style, f1_stance, f2_stance, apply_stance=True
            )
            logs += bd
        else:
            f1_str_strength = 0.0
            logs += f"\n  {f1_name}: striking style missing/unrecognised ({f1_str_style!r}) → score = 0\n"

        logs += "\n"

        if f2_str_style and f2_str_style in striking_style_weights:
            f2_str_strength, bd = compute_style_strength(
                f2_str_base, striking_style_weights[f2_str_style],
                f2_name, f2_str_style, f2_stance, f1_stance, apply_stance=True
            )
            logs += bd
        else:
            f2_str_strength = 0.0
            logs += f"\n  {f2_name}: striking style missing/unrecognised ({f2_str_style!r}) → score = 0\n"

        # --- Grappling ---
        logs += "\n\n" + "  GRAPPLING BASE SCORES".ljust(80) + "\n"
        logs += "  " + "-" * 78 + "\n\n"

        if f1_grp_style and f1_grp_style in grappling_style_weights:
            f1_grp_strength, bd = compute_style_strength(
                f1_grp_base, grappling_style_weights[f1_grp_style],
                f1_name, f1_grp_style, f1_stance, f2_stance, apply_stance=False
            )
            logs += bd
        else:
            f1_grp_strength = 0.0
            logs += f"\n  {f1_name}: grappling style missing/unrecognised ({f1_grp_style!r}) → score = 0\n"

        logs += "\n"

        if f2_grp_style and f2_grp_style in grappling_style_weights:
            f2_grp_strength, bd = compute_style_strength(
                f2_grp_base, grappling_style_weights[f2_grp_style],
                f2_name, f2_grp_style, f2_stance, f1_stance, apply_stance=False
            )
            logs += bd
        else:
            f2_grp_strength = 0.0
            logs += f"\n  {f2_name}: grappling style missing/unrecognised ({f2_grp_style!r}) → score = 0\n"

        # --- Raw summary ---
        logs += "\n\n" + "  RAW STYLE STRENGTH SUMMARY".ljust(80) + "\n"
        logs += "  " + "-" * 78 + "\n\n"
        logs += f"  {'Fighter':<28} | {'Striking':>10} | {'Grappling':>10}\n"
        logs += "  " + "-" * 54 + "\n"
        logs += f"  {f1_name:<28} | {round(f1_str_strength, 4):>10} | {round(f1_grp_strength, 4):>10}\n"
        logs += f"  {f2_name:<28} | {round(f2_str_strength, 4):>10} | {round(f2_grp_strength, 4):>10}\n"

        # --- Style matchup boosts ---
        f1_str_updated, f2_str_updated = f1_str_strength, f2_str_strength
        f1_grp_updated, f2_grp_updated = f1_grp_strength, f2_grp_strength

        logs += "\n\n" + "  STYLE MATCHUP BOOSTS".ljust(80) + "\n"
        logs += f"  Boost factor: x{style_boost} (winner)   x{round(2 - style_boost, 2)} (loser)\n\n"

        if f1_str_style and f2_str_style:
            if f2_str_style in STR_STYLE_ADVANTAGE.get(f1_str_style, []):
                f1_str_updated *= style_boost
                f2_str_updated *= (2 - style_boost)
                logs += f"  Striking  : {f1_str_style} counters {f2_str_style}\n"
                logs += f"              {f1_name}: {round(f1_str_strength, 4)} x{style_boost} = {round(f1_str_updated, 4)}\n"
                logs += f"              {f2_name}: {round(f2_str_strength, 4)} x{round(2 - style_boost, 2)} = {round(f2_str_updated, 4)}\n"
            elif f1_str_style in STR_STYLE_ADVANTAGE.get(f2_str_style, []):
                f2_str_updated *= style_boost
                f1_str_updated *= (2 - style_boost)
                logs += f"  Striking  : {f2_str_style} counters {f1_str_style}\n"
                logs += f"              {f2_name}: {round(f2_str_strength, 4)} x{style_boost} = {round(f2_str_updated, 4)}\n"
                logs += f"              {f1_name}: {round(f1_str_strength, 4)} x{round(2 - style_boost, 2)} = {round(f1_str_updated, 4)}\n"
            else:
                logs += f"  Striking  : No style advantage ({f1_str_style} vs {f2_str_style})\n"
                logs += f"              Scores unchanged — {f1_name}: {round(f1_str_updated, 4)}   {f2_name}: {round(f2_str_updated, 4)}\n"
        else:
            logs += f"  Striking  : Style missing for one or both fighters — no boost applied\n"

        logs += "\n"

        if f1_grp_style and f2_grp_style:
            if f2_grp_style in GRP_STYLE_ADVANTAGE.get(f1_grp_style, []):
                f1_grp_updated *= style_boost
                f2_grp_updated *= (2 - style_boost)
                logs += f"  Grappling : {f1_grp_style} counters {f2_grp_style}\n"
                logs += f"              {f1_name}: {round(f1_grp_strength, 4)} x{style_boost} = {round(f1_grp_updated, 4)}\n"
                logs += f"              {f2_name}: {round(f2_grp_strength, 4)} x{round(2 - style_boost, 2)} = {round(f2_grp_updated, 4)}\n"
            elif f1_grp_style in GRP_STYLE_ADVANTAGE.get(f2_grp_style, []):
                f2_grp_updated *= style_boost
                f1_grp_updated *= (2 - style_boost)
                logs += f"  Grappling : {f2_grp_style} counters {f1_grp_style}\n"
                logs += f"              {f2_name}: {round(f2_grp_strength, 4)} x{style_boost} = {round(f2_grp_updated, 4)}\n"
                logs += f"              {f1_name}: {round(f1_grp_strength, 4)} x{round(2 - style_boost, 2)} = {round(f1_grp_updated, 4)}\n"
            else:
                logs += f"  Grappling : No style advantage ({f1_grp_style} vs {f2_grp_style})\n"
                logs += f"              Scores unchanged — {f1_name}: {round(f1_grp_updated, 4)}   {f2_name}: {round(f2_grp_updated, 4)}\n"
        else:
            logs += f"  Grappling : Style missing for one or both fighters — no boost applied\n"

        # --- Updated summary ---
        logs += "\n\n" + "  UPDATED STYLE STRENGTHS (after boost)".ljust(80) + "\n"
        logs += "  " + "-" * 78 + "\n\n"
        logs += f"  {'Fighter':<28} | {'Striking':>10} | {'Grappling':>10}\n"
        logs += "  " + "-" * 54 + "\n"
        logs += f"  {f1_name:<28} | {round(f1_str_updated, 4):>10} | {round(f1_grp_updated, 4):>10}\n"
        logs += f"  {f2_name:<28} | {round(f2_str_updated, 4):>10} | {round(f2_grp_updated, 4):>10}\n"

        # --- tanh multiplier ---
        def to_multiplier(f1_score: float, f2_score: float) -> Tuple[float, float]:
            total = f1_score + f2_score
            if total == 0: return 1.0, 1.0
            norm_diff = (f1_score - f2_score) / total
            m1 = 1 + math.tanh(norm_diff)
            return m1, 2 - m1

        str_multiplier_f1, str_multiplier_f2 = to_multiplier(f1_str_updated, f2_str_updated)
        grp_multiplier_f1, grp_multiplier_f2 = to_multiplier(f1_grp_updated, f2_grp_updated)

        str_norm = (f1_str_updated - f2_str_updated) / (f1_str_updated + f2_str_updated) if (
                    f1_str_updated + f2_str_updated) else 0
        grp_norm = (f1_grp_updated - f2_grp_updated) / (f1_grp_updated + f2_grp_updated) if (
                    f1_grp_updated + f2_grp_updated) else 0

        logs += "\n\n" + "  FINAL STYLE MULTIPLIERS".ljust(80) + "\n"
        logs += "  " + "-" * 78 + "\n\n"
        logs += f"  Striking\n"
        logs += f"    norm_diff  = ({round(f1_str_updated, 4)} - {round(f2_str_updated, 4)}) / ({round(f1_str_updated, 4)} + {round(f2_str_updated, 4)}) = {round(str_norm, 4)}\n"
        logs += f"    tanh({round(str_norm, 4)}) = {round(math.tanh(str_norm), 4)}\n"
        logs += f"    {f1_name:<28}: 1 + {round(math.tanh(str_norm), 4)} = {round(str_multiplier_f1, 4)}\n"
        logs += f"    {f2_name:<28}: 2 - {round(str_multiplier_f1, 4)} = {round(str_multiplier_f2, 4)}\n"
        logs += "\n"
        logs += f"  Grappling\n"
        logs += f"    norm_diff  = ({round(f1_grp_updated, 4)} - {round(f2_grp_updated, 4)}) / ({round(f1_grp_updated, 4)} + {round(f2_grp_updated, 4)}) = {round(grp_norm, 4)}\n"
        logs += f"    tanh({round(grp_norm, 4)}) = {round(math.tanh(grp_norm), 4)}\n"
        logs += f"    {f1_name:<28}: 1 + {round(math.tanh(grp_norm), 4)} = {round(grp_multiplier_f1, 4)}\n"
        logs += f"    {f2_name:<28}: 2 - {round(grp_multiplier_f1, 4)} = {round(grp_multiplier_f2, 4)}\n"
        logs += "\n"
        logs += f"  {'FINAL MULTIPLIER SUMMARY':<28}\n\n"
        logs += f"  {'Fighter':<28} | {'Str Mult':>10} | {'Grp Mult':>10}\n"
        logs += "  " + "-" * 54 + "\n"
        logs += f"  {f1_name:<28} | {round(str_multiplier_f1, 4):>10} | {round(grp_multiplier_f1, 4):>10}\n"
        logs += f"  {f2_name:<28} | {round(str_multiplier_f2, 4):>10} | {round(grp_multiplier_f2, 4):>10}\n"
        logs += "\n" + "=" * 80 + "\n\n"

        return str_multiplier_f1, grp_multiplier_f1, str_multiplier_f2, grp_multiplier_f2, logs

    def predict_outcome(self, standing_prob: float, grappling_prob: float, fighter1: Fighter, fighter2: Fighter, logs: str) -> Tuple[float, float, str]:

        S1, S2 = fighter1.striking_score,    fighter2.striking_score
        C1, C2 = fighter1.clinch_score,      fighter2.clinch_score
        G1, G2 = fighter1.grappling_score,   fighter2.grappling_score
        I1, I2 = fighter1.intangibles_score, fighter2.intangibles_score

        specs_adv_1, logs_add = self.specs_adv(fighter1, fighter2)
        specs_adv_2 = -specs_adv_1

        str_adv_1, grp_adv_1, str_adv_2, grp_adv_2, logs = self.calc_style_multiplier(fighter1, fighter2, logs)

        S1 *= str_adv_1;  S2 *= str_adv_2
        G1 *= grp_adv_1;  G2 *= grp_adv_2

        strike_phase_1  = 0.80 * S1 + 0.2 * C1
        strike_phase_2  = 0.80 * S2 + 0.2 * C2
        grapple_phase_1 = G1
        grapple_phase_2 = G2

        skillset_1 = 0.8 * (standing_prob * strike_phase_1 + grappling_prob * grapple_phase_1)
        skillset_2 = 0.8 * (standing_prob * strike_phase_2 + grappling_prob * grapple_phase_2)

        intang_1, intang_2 = 0.2 * I1, 0.2 * I2
        specs_1,  specs_2  = specs_adv_1, specs_adv_2

        R1 = skillset_1 + intang_1 + specs_1
        R2 = skillset_2 + intang_2 + specs_2

        raw       = R1 - R2
        win_prob  = round(1 / (1 + math.exp(-raw)), 3)
        lose_prob = round(1 - win_prob, 3)

        f1_name = getattr(fighter1, "_personal-info_name")
        f2_name = getattr(fighter2, "_personal-info_name")

        logs += "\n\n" + "=" * 80 + "\n"
        logs += "FINAL TALLY & PREDICTION".center(80) + "\n"
        logs += "=" * 80 + "\n\n"
        logs += f"  {'CATEGORY':<20} | {f1_name:<25} | {f2_name:<25}\n"
        logs += "  " + "-" * 76 + "\n"
        logs += f"  {'Skillset (80%)':<20} | {round(skillset_1, 3):<25} | {round(skillset_2, 3):<25}\n"
        logs += f"  {'Intangibles (15%)':<20} | {round(intang_1, 3):<25} | {round(intang_2, 3):<25}\n"
        logs += f"  {'Specs (5%)':<20} | {round(specs_1, 3):<25} | {round(specs_2, 3):<25}\n"
        logs += "  " + "-" * 76 + "\n"
        logs += f"  {'TOTAL SCORE (R)':<20} | {round(R1, 3):<25} | {round(R2, 3):<25}\n\n"

        logs += logs_add

        logs += "\n\n" + "SIGMOID CALCULATION".center(80, "-") + "\n\n\n"
        logs += f"Score Delta (R1 - R2) = {round(raw, 4)}\n"
        logs += f"P(Win) = 1 / (1 + e^-{round(raw, 4)}) = {round(win_prob * 100, 2)}%\n"
        logs += f"P(Lose) = 100% - P(Win) = {round(lose_prob * 100, 2)}%\n\n\n"
        logs += "=" * 80 + "\n\n"

        return win_prob, lose_prob, logs
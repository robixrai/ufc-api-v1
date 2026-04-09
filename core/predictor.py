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

    def predict_fight(self, fighter1 : Fighter, fighter2 : Fighter) -> Tuple[float, float, str]:

        # VALIDITY CHECKS - WOULD THIS EVEN BE A POSSIBLE FIGHT?

        number1 = rankings_index[getattr(fighter1, "_personal-info_weight-class")]
        number2 = rankings_index[getattr(fighter2, "_personal-info_weight-class")]

        if number1 != number2 and number1 + 1 != number2 and number1 - 1 != number2:
            return 0, 0, "Not possible. Different weight classes"
        if getattr(fighter1, "_personal-info_gender") != getattr(fighter2, "_personal-info_gender"):
            return 0, 0, "Not possible. Different genders"
        if getattr(fighter1, "_personal-info_status") == "Retired" or getattr(fighter2, "_personal-info_status") == "Retired":
            return 0.0, 0.0, "Not possible. One or both of the fighters is retired."


        gameplan1, gameplan2, logs = self.predict_gameplan(fighter1, fighter2)
        standing_prob, grappling_prob, logs = self.predict_location(fighter1, fighter2, gameplan1, gameplan2, logs)
        win_prob, lose_prob, logs = self.predict_outcome(standing_prob, grappling_prob, fighter1, fighter2, logs)
        return win_prob, lose_prob, logs

    def skill_gap_multipliers(self, fighter1 : Fighter, fighter2 : Fighter, diff : float, logs : str) -> Tuple[float, str]:
        f1_str_score = getattr(fighter1, "striking_score")
        f2_str_score = getattr(fighter2, "striking_score")
        f1_str_def = getattr(fighter1, "_skillset_striking_overview_defence")
        f2_str_def = getattr(fighter2, "_skillset_striking_overview_defence")

        f1_str_adv = (f1_str_score - f2_str_def) / self.scale
        f2_str_adv = (f2_str_score - f1_str_def) / self.scale

        # Grappling advantage for each fighter (relative to the other's defence)
        f1_grap_score = getattr(fighter1, "grappling_score")
        f2_grap_score = getattr(fighter2, "grappling_score")
        f1_grap_def = getattr(fighter1, "_skillset_grappling_defence")
        f2_grap_def = getattr(fighter2, "_skillset_grappling_defence")

        f1_grap_adv = (f1_grap_score - f2_grap_def) / self.scale
        f2_grap_adv = (f2_grap_score - f1_grap_def) / self.scale

        # Net values: fighter1 advantage = fighter1_adv - fighter2_adv
        net_striking = f1_str_adv - f2_str_adv
        net_grappling = f1_grap_adv - f2_grap_adv

        logs += f"\n\nSkill Gap Calculations\n"
        logs += f"{getattr(fighter1, '_personal-info_name')} Striking advantage: {round(f1_str_adv, 3)}\n"
        logs += f"{getattr(fighter2, '_personal-info_name')} Striking advantage: {round(f2_str_adv, 3)}\n"
        logs += f"Net Striking Advantage (fighter1 - fighter2): {round(net_striking, 3)}\n\n"

        logs += f"{getattr(fighter1, '_personal-info_name')} Grappling advantage: {round(f1_grap_adv, 3)}\n"
        logs += f"{getattr(fighter2, '_personal-info_name')} Grappling advantage: {round(f2_grap_adv, 3)}\n"
        logs += f"Net Grappling Advantage (fighter1 - fighter2): {round(net_grappling, 3)}\n"

        # Combine nets into a single fighter1 advantage
        # Use your 0.8 strike weighting; adjust weights here if you want different emphasis
        combined = (0.8 * net_striking) + (1.0 * net_grappling)

        # Map to multiplicative delta centered at 1.0 and clamp
        delta = combined

        logs += f"\n\nDelta = (0.8 * net_striking + 1.0 * net_grappling) == {round(delta, 4)}\n"
        return delta, logs

    def specs_adv(self, fighter1 : Fighter, fighter2 : Fighter) -> Tuple[float, str]:

            age_diff = fighter2.age - fighter1.age
            height_diff = getattr(fighter1, "_specs_height") - getattr(fighter2, "_specs_height")
            reach_diff = getattr(fighter1, "_specs_reach") - getattr(fighter2, "_specs_reach")

            age_norm = age_diff / self.age_div
            height_norm = height_diff / self.height_div
            reach_norm = reach_diff / self.reach_div

            advantage = (self.age_weight * age_norm) + (self.height_weight * height_norm) + (self.reach_weight * reach_norm)
            advantage /= 3

            logs_add = f"Age difference - {round(age_diff, 2)} Years,   Height difference - {round(height_diff, 2)}cm,   Reach difference - {round(reach_diff, 2)} In\n"
            logs_add += f"Specs Advantage for {getattr(fighter1, "_personal-info_name")} - {round(advantage, 3)}\n\n"

            return advantage, logs_add

    def scale_for_diff(self, fighter1 : Fighter, fighter2 : Fighter, diff: float, logs : str) -> Tuple[float, str]:
        fighter1_adv, logs = self.skill_gap_multipliers(fighter1, fighter2, diff, logs)
        absd = abs(diff)

        small_thresh = 0.1
        med_thresh = 0.2
        high_thresh = 0.3
        small_boost = 0.05
        med_boost = 0.1
        large_boost = 0.2
        if absd <= self.diff_small:
            logs += "Scale_for_diff: MARGINAL RATIO DIFFERENCE. KEPT THE SAME"
            return diff, logs
        else:
            skill_diff = abs(fighter1_adv)
            ratio = 0.9
            if skill_diff < small_thresh:
                ratio = 0.5
            elif skill_diff < med_thresh:
                ratio = 0.67
            elif skill_diff < high_thresh:
                ratio = 0.75

            logs += f"\n\nSCALE_FOR_DIFF:\n\n" + f"SKILL DIFFERENCE (For Fighter 1) - {round(fighter1_adv, 3)}\n"
            logs += f"Ratio for fighter 1 : fighter 2 - {ratio}:{round(1.0 - ratio, 1)}\n"

            if fighter1_adv > 0.0:
                matchup = (ratio * getattr(fighter1, "_skillset_ratio")) + ((1 - ratio) * getattr(fighter2, "_skillset_ratio"))
                logs += f"matchup = ({ratio} * {getattr(fighter1, '_skillset_ratio')}) + ({round(1 - ratio, 1)} * {getattr(fighter2, '_skillset_ratio')})"
                return matchup, logs
            matchup = (ratio * getattr(fighter2, "_skillset_ratio")) + ((1 - ratio) * getattr(fighter1, "_skillset_ratio"))
            logs += f"matchup = ({round(1 - ratio, 1)} * {getattr(fighter1, '_skillset_ratio')}) + ({ratio} * {getattr(fighter2, '_skillset_ratio')})"
            return matchup, logs


    def predict_gameplan(self, fighter1 : Fighter, fighter2: Fighter) -> Tuple[float, float, str]:

        gameplan1 = getattr(fighter1, "_skillset_ratio") ; gameplan2 = getattr(fighter2, "_skillset_ratio")
        logs = "\n\n\n\nLOGS\n\n\n"
        logs += f"\n{getattr(fighter1, "_personal-info_name")} striking ratio : {gameplan1}\n"
        logs += f"{getattr(fighter2, "_personal-info_name")} striking ratio : {gameplan2}\n\n"
        return gameplan1, gameplan2, logs

    def predict_location(self, fighter1 : Fighter, fighter2: Fighter, gameplan1 : float, gameplan2 : float, logs : str) -> Tuple[float, float, str]:



        striking_diff = gameplan1 - gameplan2

        logs += f"Ratio difference: {round(striking_diff, 2)}\n"

        S, logs = self.scale_for_diff(fighter1, fighter2, striking_diff, logs)

        logs += f"\nFactor - {round(S, 3)}\n\n"

        standing_prob = clamp_prop(S)
        grappling_prob = 1.0 - standing_prob

        logs += f"\nStanding Probability - {round(standing_prob, 2)}\nGrappling Probability - {round(grappling_prob, 3)}\n\n"

        return standing_prob, grappling_prob, logs

    def predict_outcome(self, standing_prob : float, grappling_prob : float, fighter1 : Fighter, fighter2 : Fighter, logs : str) -> Tuple[float, float, str]:

        logs += f"\n\nFINAL CALCULATION:\n\n"

        S1 = fighter1.striking_score
        S2 = fighter2.striking_score

        C1 = fighter1.clinch_score
        C2 = fighter2.clinch_score

        G1 = fighter1.grappling_score
        G2 = fighter2.grappling_score

        I1 = fighter1.intangibles_score
        I2 = fighter2.intangibles_score


        specs_adv_1, logs_add = self.specs_adv(fighter1, fighter2)
        specs_adv_1 /= 2
        specs_adv_2 = -specs_adv_1   # for fighter 2

        strike_phase_1 = 0.8 * S1 + 0.2 * C1
        strike_phase_2 = 0.8 * S2 + 0.2 * C2

        grapple_phase_1 = G1
        grapple_phase_2 = G2

        skillset_1 = 0.8 * (
                standing_prob * strike_phase_1 +
                grappling_prob * grapple_phase_1
        )

        skillset_2 = 0.8 * (
                standing_prob * strike_phase_2 +
                grappling_prob * grapple_phase_2
        )

        intang_1 = 0.15 * I1
        intang_2 = 0.15 * I2

        specs_1 = 0.05 * specs_adv_1
        specs_2 = 0.05 * specs_adv_2

        R1 = skillset_1 + intang_1 + specs_1
        R2 = skillset_2 + intang_2 + specs_2

        if R1 == 0.0:
            return 0.0, 100.0
        elif R2 == 0.0:
            return 100.0, 0.0

        raw = R1 - R2

        mismatch = 1
        win_prob = round(1 / (1 + math.exp(-mismatch * raw)),3)
        lose_prob = round(1 - win_prob, 3)

        if win_prob + lose_prob != 1.0:
            lose_prob += 0.005

        logs += f"\n\n{getattr(fighter1, "_personal-info_name")} STATS\n\n"
        logs += f"Striking - {S1}\nGrappling - {G1}\nClinch - {C1}\nIntangibles - {I1}\n"
        logs += f"Total score - {round(R1, 3)}\n\n"

        logs += f"\n{getattr(fighter2, "_personal-info_name")} STATS\n\n"
        logs += f"Striking - {S2}\nGrappling - {G2}\nClinch - {C2}\nIntangibles - {I2}\n"
        logs += f"Total score - {round(R2, 3)}\n\n\n"

        logs += logs_add

        logs += "\nEquation\n\n"

        logs += f"Raw Score Difference - {round(raw, 2)}\n"
        logs += f"Win probability for {getattr(fighter1, "_personal-info_name")} - 1 / (1 + -{round(mismatch, 2)} * {round(raw, 2)}) == {round(win_prob, 2)}\n"
        logs += f"Win probability for {getattr(fighter2, "_personal-info_name")} - 1 / (1 + -{round(mismatch, 2)} * -{round(raw, 2)}) == {round(lose_prob, 2)}\n"


        return win_prob, lose_prob, logs
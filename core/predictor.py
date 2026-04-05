from typing import Tuple
import math

from core.fighter import Fighter

def clamp(x: float, low: float = -1.0, high: float = 1.0) -> float:
    return max(low, min(high, x))

def clamp_prop(x: float, low: float = 0.0, high: float = 1.0) -> float:
    return max(low, min(high, x))


class Predict():
    def __init__(self) -> None:
        pass

    diff_small = 0.10
    diff_large = 0.30
    alpha = 0.5
    power = 2.0

    scale = 10

    age_div = 10.0
    height_div = 10.0
    reach_div = 5.0

    age_weight = 0.25
    height_weight = 0.35
    reach_weight = 0.40

    def predict_fight(self, fighter1 : Fighter, fighter2 : Fighter) -> Tuple[float, float, str]:

        gameplan1, gameplan2, logs = self.predict_gameplan(fighter1, fighter2)
        standing_prob, grappling_prob, logs = self.predict_location(fighter1, fighter2, gameplan1, gameplan2, logs)
        win_prob, lose_prob, logs = self.predict_outcome(standing_prob, grappling_prob, fighter1, fighter2, logs)
        return win_prob, lose_prob, logs

    def skill_gap_multipliers(self, fighter1 : Fighter, fighter2 : Fighter, diff : float, logs : str) -> Tuple[float, float, str]:

        if diff > 0:
            striker, grappler = fighter1, fighter2
        else:
            striker, grappler = fighter2, fighter1

        str_score_striker = getattr(striker, "striking_score")
        str_def_grappler = getattr(grappler, "_skillset_striking_overview_defence")
        str_score_grappler = getattr(grappler, "striking_score")
        str_def_striker = getattr(striker, "_skillset_striking_overview_defence")

        striker_striking_adv = (str_score_striker - str_def_grappler) / self.scale
        grappler_striking_adv = (str_score_grappler - str_def_striker) / self.scale

        # Grappling advantage for each
        grap_score_striker = getattr(striker, "grappling_score")
        grap_def_grappler = getattr(grappler, "_skillset_grappling_defence")
        grap_score_grappler = getattr(grappler, "grappling_score")
        grap_def_striker = getattr(striker, "_skillset_grappling_defence")

        striker_grappling_adv = (grap_score_striker - grap_def_grappler) / self.scale
        grappler_grappling_adv = (grap_score_grappler - grap_def_striker) / self.scale

        # Net values
        net_striking = striker_striking_adv - grappler_striking_adv
        net_grappling = grappler_grappling_adv - striker_grappling_adv

        logs += f"\n\nSkill Gap Calculations\n"
        logs += f"{getattr(striker, '_personal-info_name')} Striking advantage: {round(striker_striking_adv, 3)}\n"
        logs += f"{getattr(grappler, '_personal-info_name')} Striking advantage: {round(grappler_striking_adv, 3)}\n"
        logs += f"Net Striking Advantage (for {getattr(striker, '_personal-info_name')}): {round(net_striking, 3)}\n\n"

        logs += f"{getattr(striker, '_personal-info_name')} Grappling advantage: {round(striker_grappling_adv, 3)}\n"
        logs += f"{getattr(grappler, '_personal-info_name')} Grappling advantage: {round(grappler_grappling_adv, 3)}\n"
        logs += f"Net Grappling Advantage (for {getattr(grappler, '_personal-info_name')}): {round(net_grappling, 3)}\n"

        if striker == fighter1:
            return (0.8 * net_striking), net_grappling, logs
        else:
            return net_grappling, (0.8 * net_striking), logs



    def specs_adv(self, fighter1 : Fighter, fighter2 : Fighter) -> Tuple[float, str]:

        age_diff = fighter2.age - fighter1.age
        height_diff = getattr(fighter1, "_specs_height") - getattr(fighter2, "_specs_height")
        reach_diff = getattr(fighter1, "_specs_reach") - getattr(fighter2, "_specs_reach")

        age_norm = age_diff / self.age_div
        height_norm = height_diff / self.height_div
        reach_norm = reach_diff / self.reach_div

        advantage = (self.age_weight * age_norm) + (self.height_weight * height_norm) + (self.reach_weight * reach_norm)

        logs_add = f"Age difference - {round(age_diff, 2)} Years,   Height difference - {round(height_diff, 2)}cm,   Reach difference - {round(reach_diff, 2)} In\n"
        logs_add += f"Specs Advantage for {getattr(fighter1, "_personal-info_name")} - {round(advantage, 3)}\n\n"

        return advantage, logs_add

    def scale_for_diff(self, fighter1 : Fighter, fighter2 : Fighter, diff: float, logs : str) -> Tuple[float, str]:
        num_mult, den_mult, logs = self.skill_gap_multipliers(fighter1, fighter2, diff, logs)
        absd = abs(diff)
        if absd <= self.diff_small:
            logs += "Scale_for_diff: MARGINAL RATIO DIFFERENCE. 0.0"
            return 0.0, logs
        if absd <= self.diff_large:
            S = (absd - self.diff_small) / (self.diff_large - self.diff_small)
        else:
            S = 1.0 + self.alpha * ((absd - self.diff_large) ** self.power)

        if num_mult < 0:
            num_mult = 1 + num_mult
        elif den_mult < 0:
            den_mult = 1 + den_mult

        SS = (S * num_mult) / den_mult

        logs += f"Scale_for_diff : ({round(S, 3)} * {round(num_mult, 3)}) / {round(den_mult, 3)} == {round(SS, 3)}\n\n"

        sign = 1.0 if diff >= 0.0 else -1.0
        SS = SS * sign

        return SS, logs

    def predict_gameplan(self, fighter1 : Fighter, fighter2: Fighter) -> Tuple[float, float, str]:

        gameplan1 = getattr(fighter1, "_skillset_ratio") ; gameplan2 = getattr(fighter2, "_skillset_ratio")
        logs = "\n\n\n\nLOGS\n\n\n"
        logs += f"\n{getattr(fighter1, "_personal-info_name")} striking ratio : {gameplan1}\n"
        logs += f"{getattr(fighter2, "_personal-info_name")} striking ratio : {gameplan2}\n\n"
        return gameplan1, gameplan2, logs

    def predict_location(self, fighter1 : Fighter, fighter2: Fighter, gameplan1 : float, gameplan2 : float, logs : str) -> Tuple[float, float, str]:

        intent = 0.67
        matchup = 0.33

        base = (gameplan1 + gameplan2) / 2.0
        striking_diff = gameplan1 - gameplan2

        logs += f"Base ratio: {round(base, 2)}\n"
        logs += f"Ratio difference: {round(striking_diff, 2)}\n"

        S, logs = self.scale_for_diff(fighter1, fighter2, striking_diff, logs)
        factor = 1.0 + S
        #factor = max(0.05, min(3.0, factor))

        logs += f"Factor - {round(factor, 3)}\n\n"

        standing_prob = clamp_prop((base * intent) + (matchup * factor))
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
        specs_adv_2 = -specs_adv_1   # for fighter 2

        strike_phase_1 = 0.8 * S1 + 0.2 * C1
        strike_phase_2 = 0.8 * S2 + 0.2 * C2

        grapple_phase_1 = G1
        grapple_phase_2 = G2

        skillset_1 = 0.75 * (
                standing_prob * strike_phase_1 +
                grappling_prob * grapple_phase_1
        )

        skillset_2 = 0.75 * (
                standing_prob * strike_phase_2 +
                grappling_prob * grapple_phase_2
        )

        intang_1 = 0.15 * I1
        intang_2 = 0.15 * I2

        specs_1 = 0.10 * specs_adv_1
        specs_2 = 0.10 * specs_adv_2

        R1 = skillset_1 + intang_1 + specs_1
        R2 = skillset_2 + intang_2 + specs_2

        if R1 == 0.0:
            return 0.0, 100.0
        elif R2 == 0.0:
            return 100.0, 0.0

        raw = R1 - R2

        mismatch = 2
        win_prob = round(1 / (1 + math.exp(-mismatch * raw)),3)
        lose_prob = round(1 - win_prob, 3)

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
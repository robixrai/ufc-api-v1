from typing import Tuple
import math
import json
from pathlib import Path
from core.fighter import Fighter
from core.tools import rankings_index

DATA_DIR = Path(__file__).resolve().parent.parent

fighters_path = DATA_DIR / "data" / "fighters.json"
rankings_path = DATA_DIR / "data" / "rankings.json"


def get_champion() -> set:
    """Return a set of all current champions (index 0 of each weight class)."""
    champions = set()
    with open(rankings_path, "r", encoding="utf-8") as f:
        rankings = json.load(f)
    for gender in rankings.values():
        for division, fighters in gender.items():
            if division == "pound-for-pound":
                continue
            if fighters:
                champions.add(fighters[0].lower())
    return champions


def is_title_fight(fighter1_name: str, fighter2_name: str) -> bool:
    champions = get_champion()
    return (fighter1_name.lower() in champions or
            fighter2_name.lower() in champions)


def clamp(x: float, low: float = -1.0, high: float = 1.0) -> float:
    return max(low, min(high, x))


def clamp_prop(x: float, low: float = 0.0, high: float = 1.0) -> float:
    return max(low, min(high, x))


def cardio_boost(fighter1: Fighter, fighter2: Fighter, rounds: int) -> Tuple[float, float, str]:
    name1 = getattr(fighter1, "_personal-info_name")
    name2 = getattr(fighter2, "_personal-info_name")

    s1 = float(getattr(fighter1, "_skillset_intangibles_stamina", 0) or 0)
    s2 = float(getattr(fighter2, "_skillset_intangibles_stamina", 0) or 0)

    diff = (s1 - s2)

    # 5-rounders punish poor cardio more
    round_scalar = 0.1 if rounds == 3 else 0.20

    boost1 = round(diff * round_scalar, 4)
    boost2 = -boost1

    logs = "\n\n" + "_" * 80 + "\n\n"
    logs += "CARDIO BOOST".center(80) + "\n"
    logs += "_" * 80 + "\n\n"
    logs += f"  {'Rounds':<22}: {rounds}\n"
    logs += f"  {'Round scalar':<22}: {round_scalar}\n\n"
    logs += f"  {name1:<28} Stamina: {s1}\n"
    logs += f"  {name2:<28} Stamina: {s2}\n\n"
    logs += f"  Stamina diff : ({s1} - {s2}) / 10 = {round(diff, 4)}\n"
    logs += f"  Boost formula: {round(diff, 4)} x {round_scalar} = {boost1}\n\n"
    logs += f"  {('Cardio Boost for ' + name1):<40}: {boost1}\n"
    logs += f"  {('Cardio Boost for ' + name2):<40}: {boost2}\n"

    return boost1, boost2, logs


def form_boost(fighter: Fighter) -> Tuple[float, str]:
    last_five = getattr(fighter, "_career_last-five", [])
    name = getattr(fighter, "_personal-info_name")
    weights_all = [0.35, 0.25, 0.20, 0.12, 0.08]

    RESULT_LABELS = {1: "Win", 0: "Loss", 3: "Draw", 4: "NC"}
    RESULT_VALUES = {1: +1.0, 0: -1.0, 3: 0.0, 4: 0.0}

    if not last_five:
        logs_add = f"  {name}: no fight history — form boost = 0.0\n"
        return 0.0, logs_add

    w = weights_all[:len(last_five)]
    total_w = sum(w)
    w = [x / total_w for x in w]

    raw_score = sum(w[i] * RESULT_VALUES.get(last_five[i], 0.0) for i in range(len(last_five)))
    boost = round(raw_score * 0.25, 4)

    logs_add = f"\n  {name} — Recent Form\n\n"
    logs_add += f"  {'Fight':<12} | {'Result':<6} | {'Weight':>8} | {'Contribution':>12}\n"
    logs_add += "  " + "-" * 45 + "\n"
    for i, result in enumerate(last_five):
        label = RESULT_LABELS.get(result, "?")
        val = RESULT_VALUES.get(result, 0.0)
        contribution = w[i] * val
        fight_label = "Most Recent" if i == 0 else f"Fight -{i}"
        logs_add += (
            f"  {fight_label:<12} | {label:<6} | "
            f"{round(w[i], 3):>8} | {round(contribution, 4):>12}\n"
        )
    logs_add += "  " + "-" * 45 + "\n"
    logs_add += f"  Raw score  : {round(raw_score, 4)}\n"
    logs_add += f"  Form boost : {round(raw_score, 4)} x 0.25 = {boost}\n"

    return boost, logs_add


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

    def predict_fight(self, fighter1: Fighter, fighter2: Fighter, rounds: int, json: int) -> Tuple[float, float, str]:

        if not fighter1 or not fighter2:
            return 0, 0, "Fighters are not in the database"

        number1 = rankings_index[getattr(fighter1, "_personal-info_weight-class")]
        number2 = rankings_index[getattr(fighter2, "_personal-info_weight-class")]

        if number1 != number2 and (number1 + 1 != number2 and number1 - 1 != number2):
            return 0, 0, "Not possible. Different weight classes"
        if getattr(fighter1, "_personal-info_gender") != getattr(fighter2, "_personal-info_gender"):
            return 0, 0, "Not possible. Different genders"
        if getattr(fighter1, "_personal-info_status") == "Retired" or getattr(fighter2,
                                                                              "_personal-info_status") == "Retired":
            return 0.0, 0.0, "Not possible. One or both of the fighters is retired."

        gameplan1, gameplan2, logs = self.predict_gameplan(fighter1, fighter2)
        standing_prob, grappling_prob, logs = self.predict_location(fighter1, fighter2, gameplan1, gameplan2, logs)
        win_prob, lose_prob, logs = self.predict_outcome(standing_prob, grappling_prob, fighter1, fighter2, logs,
                                                         rounds, json)
        if json == 1:
            return win_prob, lose_prob, logs
        logs += "\n\n"
        logs += "FINAL WIN PROBABILITY".center(80) + "\n\n\n"
        logs += (
                f"{getattr(fighter1, '_personal-info_name')}: {round(win_prob * 100, 2)}%".center(40) +
                f"{getattr(fighter2, '_personal-info_name')}: {round(lose_prob * 100, 2)}%".center(40) +
                "\n\n\n"
        )
        logs += "_" * 80 + "\n"
        return win_prob, lose_prob, logs

    def predict_individual_methods(
            self,
            fighter: Fighter,
            opponent: Fighter,
            standing_prob: float,
            grappling_prob: float
    ) -> Tuple[float, float, float, str]:

        eps = 1e-8
        name = getattr(fighter, "_personal-info_name", "Fighter")
        opp_name = getattr(opponent, "_personal-info_name", "Opponent")

        log = "\n" + "-" * 80 + "\n"
        log += f"  METHOD PROFILE : {name}  vs  {opp_name}\n"
        log += "-" * 80 + "\n\n"

        MALE_PRIORS = {
            "Heavyweight": [0.518, 0.143, 0.339],
            "Light Heavyweight": [0.440, 0.174, 0.386],
            "Middleweight": [0.374, 0.216, 0.410],
            "Welterweight": [0.333, 0.186, 0.481],
            "Lightweight": [0.295, 0.216, 0.489],
            "Featherweight": [0.289, 0.165, 0.546],
            "Bantamweight": [0.255, 0.192, 0.553],
            "Flyweight": [0.236, 0.215, 0.549]
        }

        FEMALE_PRIORS = {
            "Bantamweight": [0.231, 0.163, 0.606],
            "Flyweight": [0.167, 0.193, 0.640],
            "Strawweight": [0.133, 0.193, 0.674]
        }

        priors_dict = FEMALE_PRIORS if getattr(fighter, "_personal-info_gender") == "female" else MALE_PRIORS
        division = getattr(fighter, "_personal-info_division", "Lightweight")
        stats_prior = priors_dict.get(division, [0.32, 0.18, 0.50])

        # --- Career rates ---
        ko_wins = float(getattr(fighter, "_career_ko-tko-wins", 0) or 0)
        sub_wins = float(getattr(fighter, "_career_sub-wins", 0) or 0)
        wins = float(getattr(fighter, "_career_wins", 0) or 0)
        losses = float(getattr(fighter, "_career_losses", 0) or 0)
        draws = float(getattr(fighter, "_career_draws", 0) or 0)
        ncs = float(getattr(fighter, "_career_no-contests", 0) or 0)
        total_fights = max(1.0, wins + losses + draws + ncs)

        ufc_ko_wins = getattr(fighter, "_career_ufc-ko-tko-wins")
        ufc_sub_wins = getattr(fighter, "_career_ufc-sub-wins")
        ufc_wins = getattr(fighter, "_career_ufc-wins")
        ufc_losses = getattr(fighter, "_career_ufc-losses")
        ufc_fights = ufc_wins + ufc_losses
        ufc_dec_wins = ufc_wins - (ufc_ko_wins + ufc_sub_wins)

        m = 2
        ko_prior_num = stats_prior[0] * m
        sub_prior_num = stats_prior[1] * m
        dec_prior_num = stats_prior[2] * m

        denom = ufc_fights + m

        ufc_ko_rate = (ko_prior_num + ufc_ko_wins) / denom
        ufc_sub_rate = (sub_prior_num + ufc_sub_wins) / denom
        ufc_dec_rate = (ufc_dec_wins + dec_prior_num) / denom

        ko_rate = ko_wins / total_fights
        sub_rate = sub_wins / total_fights
        finish_rate = (ko_wins + sub_wins) / total_fights
        dec_rate = 1.0 - finish_rate

        # --- Blended rates (50% UFC, 50% whole-career MMA) ---
        blended_ko_rate = 0.5 * ufc_ko_rate + 0.5 * ko_rate
        blended_sub_rate = 0.5 * ufc_sub_rate + 0.5 * sub_rate
        blended_dec_rate = 0.5 * ufc_dec_rate + 0.5 * dec_rate

        log += f"  {'Total fights':<22}: {total_fights}\n"
        log += f"  {'KO/TKO wins':<22}: {ko_wins}  →  KO rate  = {round(ko_rate, 3)}\n"
        log += f"  {'Sub wins':<22}: {sub_wins}  →  Sub rate = {round(sub_rate, 3)}\n"
        log += f"  {'Finish rate':<22}: {round(finish_rate, 3)}\n\n"
        log += f"  {'Blended KO rate':<22}: UFC {round(ufc_ko_rate, 3)} | Career {round(ko_rate, 3)} → {round(blended_ko_rate, 3)}\n"
        log += f"  {'Blended Sub rate':<22}: UFC {round(ufc_sub_rate, 3)} | Career {round(sub_rate, 3)} → {round(blended_sub_rate, 3)}\n"
        log += f"  {'Blended Dec rate':<22}: UFC {round(ufc_dec_rate, 3)} | Career {round(dec_rate, 3)} → {round(blended_dec_rate, 3)}\n\n"

        # --- Fighter scores ---
        striking_score = float(getattr(fighter, "striking_score", 0.0) or 0.0)
        grappling_score = float(getattr(fighter, "grappling_score", 0.0) or 0.0)
        sub_rating = float(getattr(fighter, "_skillset_grappling_submissions", 0.0) or 0.0)

        # --- Opponent resistances ---
        opp_chin = max(0.1, float(getattr(opponent, "_skillset_intangibles_chin", 0.0) or 0.0))
        opp_durability = max(0.1, float(getattr(opponent, "_skillset_intangibles_durability", 0.0) or 0.0))
        opp_str_def = max(0.1, float(getattr(opponent, "_skillset_striking_overview_defence", 0.0) or 0.0))
        opp_footwork = max(0.1, float(getattr(opponent, "_skillset_striking_overview_footwork", 0.0) or 0.0))
        opp_grap_score = max(0.1, float(getattr(opponent, "grappling_score", 0.0) or 0.0))
        opp_tkd_def = max(0.1, float(getattr(opponent, "_skillset_grappling_takedown-defence", 0.0) or 0.0))
        opp_bottom_game = max(0.1, float(getattr(opponent, "_skillset_grappling_bottom-game", 0.0) or 0.0))

        log += f"  {'Striking score':<22}: {striking_score}\n"
        log += f"  {'Grappling score':<22}: {grappling_score}\n"
        log += f"  {'Submission rating':<22}: {sub_rating}\n\n"
        log += f"  Opponent resistances\n"
        log += f"  {'  Chin':<22}: {opp_chin}\n"
        log += f"  {'  Durability':<22}: {opp_durability}\n"
        log += f"  {'  Str Defence':<22}: {opp_str_def}\n"
        log += f"  {'  Footwork':<22}: {opp_footwork}\n"
        log += f"  {'  Grappling score':<22}: {opp_grap_score}\n"
        log += f"  {'  Takedown defence':<22}: {opp_tkd_def}\n"
        log += f"  {'  Bottom game':<22}: {opp_bottom_game}\n\n"

        # --- KO threat ---
        ko_resistance = (opp_chin * opp_durability * opp_str_def * opp_footwork) ** 0.25
        ko_threat = (striking_score * (blended_ko_rate + eps)) / (ko_resistance + eps)
        ko_threat *= (0.5 + 0.5 * standing_prob)  # soft modifier, ranges 0.5–1.0

        # --- Sub threat ---
        sub_rating_factor = 0.5 + 0.5 * (sub_rating / 10.0)  # dampened to ~0.5–1.0 range
        sub_resistance = (opp_grap_score * opp_tkd_def * opp_bottom_game) ** (1 / 3)
        sub_threat = (grappling_score * sub_rating_factor * (blended_sub_rate + eps)) / (sub_resistance + eps)
        sub_threat *= (0.5 + 0.5 * grappling_prob)  # soft modifier, ranges 0.5–1.0

        # --- Decision propensity ---
        location_balance = 1.0 - abs(standing_prob - grappling_prob)
        dec_threat = blended_dec_rate * (0.7 + 0.3 * location_balance)

        f1_name = getattr(fighter, "_personal-info_name")
        f2_name = getattr(opponent, "_personal-info_name")
        title_fight = is_title_fight(f1_name, f2_name)
        if title_fight:
            dec_threat *= 1.5

        log += f"  KO resistance (geom mean chin/dur/def/ftw) : {round(ko_resistance, 4)}\n"
        log += f"  Sub resistance (geom mean grp/tkd/btm)     : {round(sub_resistance, 4)}\n\n"
        log += f"  Raw KO threat   : {round(ko_threat, 4)}\n"
        log += f"  Raw Sub threat  : {round(sub_threat, 4)}\n"
        log += f"  Raw Dec threat  : {round(dec_threat, 4)}\n\n"

        # --- Apply uniform power law to all three, then normalise ---
        ko_threat = ko_threat ** 1.2
        sub_threat =  sub_threat ** 1.2
        dec_threat = dec_threat ** 1.3

        total_raw = ko_threat + sub_threat + dec_threat + eps
        ko_p = ko_threat / total_raw
        sub_p = sub_threat / total_raw
        dec_p = dec_threat / total_raw

        s = ko_p + sub_p + dec_p
        if s <= 0:
            ko_p = sub_p = dec_p = 1.0 / 3.0
        else:
            ko_p /= s
            sub_p /= s
            dec_p /= s

        log += f"  Final profile  →  KO: {round(ko_p, 3)}   Sub: {round(sub_p, 3)}   Dec: {round(dec_p, 3)}\n"

        return ko_p, sub_p, dec_p, log
    def combine_method_profiles(
            self,
            f1_profile: Tuple[float, float, float],
            f2_profile: Tuple[float, float, float],
            win_prob: float,
            lose_prob: float
    ) -> Tuple[float, float, float, str]:

        log = "\n" + "-" * 80 + "\n"
        log += "  COMBINED FIGHT METHOD PROBABILITIES\n"
        log += "-" * 80 + "\n\n"
        log += f"  F1 profile : KO={f1_profile[0]:.3f}  Sub={f1_profile[1]:.3f}  Dec={f1_profile[2]:.3f}  (win prob={win_prob:.3f})\n"
        log += f"  F2 profile : KO={f2_profile[0]:.3f}  Sub={f2_profile[1]:.3f}  Dec={f2_profile[2]:.3f}  (win prob={lose_prob:.3f})\n\n"

        fight_ko = f1_profile[0] * win_prob + f2_profile[0] * lose_prob
        fight_sub = f1_profile[1] * win_prob + f2_profile[1] * lose_prob
        fight_dec = f1_profile[2] * win_prob + f2_profile[2] * lose_prob

        total = fight_ko + fight_sub + fight_dec
        if total <= 0:
            fight_ko = fight_sub = fight_dec = 1.0 / 3.0
        else:
            fight_ko /= total;
            fight_sub /= total;
            fight_dec /= total

        log += f"  fight_ko  = (f1_ko  x {win_prob:.3f}) + (f2_ko  x {lose_prob:.3f}) = {round(fight_ko, 3)}\n"
        log += f"  fight_sub = (f1_sub x {win_prob:.3f}) + (f2_sub x {lose_prob:.3f}) = {round(fight_sub, 3)}\n"
        log += f"  fight_dec = (f1_dec x {win_prob:.3f}) + (f2_dec x {lose_prob:.3f}) = {round(fight_dec, 3)}\n\n"
        log += f"  Most likely method : "

        methods = {"KO/TKO": fight_ko, "Submission": fight_sub, "Decision": fight_dec}
        likely = max(methods, key=methods.get)
        log += f"{likely} ({round(methods[likely] * 100, 1)}%)\n\n"
        log += f"  {'KO/TKO':<12}: {round(fight_ko * 100, 1)}%\n"
        log += f"  {'Submission':<12}: {round(fight_sub * 100, 1)}%\n"
        log += f"  {'Decision':<12}: {round(fight_dec * 100, 1)}%\n"

        return fight_ko, fight_sub, fight_dec, log

    def skill_gap_multipliers(self, fighter1: Fighter, fighter2: Fighter, diff: float, logs: str) -> Tuple[float, str]:
        f1_str_score = getattr(fighter1, "striking_score")
        f2_str_score = getattr(fighter2, "striking_score")
        f1_str_def = getattr(fighter1, "_skillset_striking_overview_defence")
        f2_str_def = getattr(fighter2, "_skillset_striking_overview_defence")

        f1_str_adv = (f1_str_score - f2_str_def) / self.scale
        f2_str_adv = (f2_str_score - f1_str_def) / self.scale

        f1_grap_score = getattr(fighter1, "grappling_score")
        f2_grap_score = getattr(fighter2, "grappling_score")
        f1_grap_def = fighter1.__dict__.get("_skillset_grappling_takedown-defence", 0)
        f2_grap_def = fighter2.__dict__.get("_skillset_grappling_takedown-defence", 0)

        f1_grap_adv = (f1_grap_score - f2_grap_def) / self.scale
        f2_grap_adv = (f2_grap_score - f1_grap_def) / self.scale

        net_striking = f1_str_adv - f2_str_adv
        net_grappling = f1_grap_adv - f2_grap_adv

        f1_name = getattr(fighter1, "_personal-info_name")
        f2_name = getattr(fighter2, "_personal-info_name")

        logs += "\n\n" + "-" * 80 + "\n"
        logs += "SKILL GAP CALCULATIONS".center(80) + "\n"
        logs += "-" * 80 + "\n\n"
        logs += f"{'STRIKING':<20} | {f1_name}: {round(f1_str_adv, 3)}  vs  {f2_name}: {round(f2_str_adv, 3)}\n"
        logs += f"{'NET STRIKING':<20} | {round(net_striking, 3)}\n\n"
        logs += f"{'GRAPPLING':<20} | {f1_name}: {round(f1_grap_adv, 3)}  vs  {f2_name}: {round(f2_grap_adv, 3)}\n"
        logs += f"{'NET GRAPPLING':<20} | {round(net_grappling, 3)}\n"

        combined = (0.8 * net_striking) + (1.0 * net_grappling)
        delta = combined
        logs += f"\n{'COMBINED DELTA':<20} | (0.8 * {round(net_striking, 3)}) + (1.0 * {round(net_grappling, 3)}) = {round(delta, 4)}\n"
        return delta, logs

    def specs_adv(self, fighter1: Fighter, fighter2: Fighter) -> Tuple[float, str]:
        age_diff = fighter2.age - fighter1.age
        height_diff = (getattr(fighter1, "_specs_height") - getattr(fighter2, "_specs_height")) / 2
        reach_diff = getattr(fighter1, "_specs_reach") - getattr(fighter2, "_specs_reach")

        age_norm = clamp(age_diff, -10, 10)
        height_norm = clamp(height_diff, -10, 10)
        reach_norm = clamp(reach_diff, -10, 10)

        advantage = (self.age_weight * age_norm) + (self.height_weight * height_norm) + (self.reach_weight * reach_norm)
        advantage /= 10
        advantage /= 2

        logs_add = "\n\n" + "_" * 80 + "\n\n"
        logs_add += "PHYSICAL SPECS COMPARISON".center(80) + "\n"
        logs_add += "_" * 80 + "\n\n\n"
        logs_add += f"{'Age Diff':<10}: {round(age_diff, 2)} yrs | {'Height Diff':<10}: {round(height_diff, 2)}cm | {'Reach Diff':<10}: {round(reach_diff, 2)}in\n\n"
        logs_add += f"{'Specs Advantage for ' + getattr(fighter1, '_personal-info_name'):<40}: {round(advantage, 3)}\n"
        return advantage, logs_add

    def scale_for_diff(self, fighter1: Fighter, fighter2: Fighter, diff: float, logs: str) -> Tuple[float, str]:
        fighter1_adv, logs = self.skill_gap_multipliers(fighter1, fighter2, diff, logs)
        absd = abs(diff)
        average = (getattr(fighter1, "_skillset_ratio") + getattr(fighter2, "_skillset_ratio")) / 2

        small_thresh, med_thresh, high_thresh = 0.1, 0.2, 0.3

        logs += "\n\n" + "-" * 80 + "\n"
        logs += "SCALING ADJUSTMENTS".center(80) + "\n"
        logs += "-" * 80 + "\n\n"

        if absd <= self.diff_small:
            logs += "RESULT: MARGINAL RATIO DIFFERENCE. NO SCALING APPLIED.\n"
            return average, logs

        skill_diff = abs(fighter1_adv)
        ratio = 0.9
        if skill_diff < small_thresh:
            ratio = 0.5
        elif skill_diff < med_thresh:
            ratio = 0.67
        elif skill_diff < high_thresh:
            ratio = 0.75

        logs += f"SKILL DIFFERENCE (F1 Advantage): {round(fighter1_adv, 3)}\n"
        logs += f"DETERMINED RATIO: {ratio} : {round(1.0 - ratio, 2)}\n"

        if fighter1_adv > 0.0:
            matchup = (ratio * getattr(fighter1, "_skillset_ratio")) + (
                        (1 - ratio) * getattr(fighter2, "_skillset_ratio"))
            logs += f"MATCHUP CALC: ({ratio} * {getattr(fighter1, '_skillset_ratio')}) + ({round(1 - ratio, 2)} * {getattr(fighter2, '_skillset_ratio')}) = {round(matchup, 3)}\n"
            return matchup, logs

        matchup = (ratio * getattr(fighter2, "_skillset_ratio")) + ((1 - ratio) * getattr(fighter1, "_skillset_ratio"))
        logs += f"MATCHUP CALC: ({round(1 - ratio, 2)} * {getattr(fighter1, '_skillset_ratio')}) + ({ratio} * {getattr(fighter2, '_skillset_ratio')}) = {round(matchup, 3)}\n"
        return matchup, logs

    def predict_gameplan(self, fighter1: Fighter, fighter2: Fighter) -> Tuple[float, float, str]:
        gameplan1 = getattr(fighter1, "_skillset_ratio")
        gameplan2 = getattr(fighter2, "_skillset_ratio")

        logs = "\n" + "=" * 80 + "\n"
        logs += "FIGHT PREDICTION ENGINE LOGS".center(80) + "\n"
        logs += "=" * 80 + "\n\n\n"
        logs += f"{getattr(fighter1, '_personal-info_name'):<40} Striking Ratio: {gameplan1}\n"
        logs += f"{getattr(fighter2, '_personal-info_name'):<40} Striking Ratio: {gameplan2}\n"
        return gameplan1, gameplan2, logs

    def predict_location(self, fighter1: Fighter, fighter2: Fighter, gameplan1: float, gameplan2: float, logs: str) -> \
    Tuple[float, float, str]:
        striking_diff = gameplan1 - gameplan2

        logs += "\n\n" + "_" * 80 + "\n\n"
        logs += "LOCATION PROBABILITY ANALYSIS".center(80) + "\n"
        logs += "_" * 80 + "\n\n"
        logs += f"Initial Ratio Difference: {round(striking_diff, 2)}\n"

        S, logs = self.scale_for_diff(fighter1, fighter2, striking_diff, logs)
        standing_prob = clamp_prop(S)
        grappling_prob = 1.0 - standing_prob

        logs += "\n\n" + "LOCATION RESULTS".center(40).center(80, ".") + "\n\n\n"
        logs += f"{'Standing Probability':<30}: {round(standing_prob * 100, 2)}%\n"
        logs += f"{'Grappling Probability':<30}: {round(grappling_prob * 100, 2)}%\n"
        return standing_prob, grappling_prob, logs

    def build_base_features(self, fighter, style):
        striking_base = {
            "Accuracy": getattr(fighter, "_skillset_striking_overview_accuracy", 0),
            "Power": getattr(fighter, "_skillset_striking_overview_power", 0),
            "Volume": getattr(fighter, "_skillset_striking_overview_volume", 0),
            "LegKicks": getattr(fighter, "_skillset_striking_kicks_low", 0),
            "HeadKicks": getattr(fighter, "_skillset_striking_kicks_head", 0),
            "ClinchStriking": fighter.__dict__.get("_skillset_clinch_clinch-striking", 0),
            "Defense": getattr(fighter, "_skillset_striking_overview_defence", 0),
            "Footwork": getattr(fighter, "_skillset_striking_overview_footwork", 0),
            "Stamina": getattr(fighter, "_skillset_intangibles_stamina", 0),
            "Durability": getattr(fighter, "_skillset_intangibles_durability", 0),
            "FightIQ": fighter.__dict__.get("_skillset_intangibles_fight-iq", 0),
        }
        grappling_base = {
            "TakedownOffense": getattr(fighter, "_skillset_grappling_takedown", 0),
            "TakedownDefense": fighter.__dict__.get("_skillset_grappling_takedown-defence", 0),
            "SubmissionThreat": getattr(fighter, "_skillset_grappling_submissions", 0),
            "Scrambles": getattr(fighter, "_skillset_grappling_scrambles", 0),
            "GroundControl": fighter.__dict__.get("_skillset_grappling_ground-control", 0),
            "GroundAndPound": fighter.__dict__.get("_skillset_grappling_ground-and-pound", 0),
            "BottomGame": fighter.__dict__.get("_skillset_grappling_bottom-game", 0),
            "ClinchControl": fighter.__dict__.get("_skillset_clinch_clinch-control", 0),
            "Stamina": getattr(fighter, "_skillset_intangibles_stamina", 0),
            "Durability": getattr(fighter, "_skillset_intangibles_durability", 0),
            "FightIQ": fighter.__dict__.get("_skillset_intangibles_fight-iq", 0),
        }
        if style in ("s", "S"): return striking_base
        if style in ("g", "G"): return grappling_base
        raise ValueError("style must be 's' or 'g'")

    def calc_style_multiplier(self, fighter1: Fighter, fighter2: Fighter, logs: str) -> Tuple[
        float, float, float, float, str]:

        striking_style_weights = {
            "Counter Striker": {
                "Accuracy": 0.22, "Power": 0.12, "Volume": 0.06, "LegKicks": 0.05,
                "HeadKicks": 0.04, "ClinchStriking": 0.03, "Defense": 0.18,
                "Footwork": 0.12, "Stamina": 0.04, "Durability": 0.05, "FightIQ": 0.09
            },
            "Pressure Striker": {
                "Accuracy": 0.11, "Power": 0.12, "Volume": 0.22, "LegKicks": 0.10,
                "HeadKicks": 0.03, "ClinchStriking": 0.13, "Defense": 0.05,
                "Footwork": 0.06, "Stamina": 0.10, "Durability": 0.07, "FightIQ": 0.01
            },
            "Outside Sniper": {
                "Accuracy": 0.22, "Power": 0.08, "Volume": 0.10, "LegKicks": 0.07,
                "HeadKicks": 0.06, "ClinchStriking": 0.02, "Defense": 0.16,
                "Footwork": 0.14, "Stamina": 0.04, "Durability": 0.03, "FightIQ": 0.08
            },
            "Technical Boxer": {
                "Accuracy": 0.22, "Power": 0.16, "Volume": 0.12, "LegKicks": 0.04,
                "HeadKicks": 0.03, "ClinchStriking": 0.06, "Defense": 0.12,
                "Footwork": 0.10, "Stamina": 0.04, "Durability": 0.04, "FightIQ": 0.07
            },
            "Muay Thai / Kickboxer": {
                "Accuracy": 0.12, "Power": 0.14, "Volume": 0.10, "LegKicks": 0.22,
                "HeadKicks": 0.10, "ClinchStriking": 0.13, "Defense": 0.04,
                "Footwork": 0.04, "Stamina": 0.06, "Durability": 0.04, "FightIQ": 0.01
            }
        }

        grappling_style_weights = {
            "Wrestler": {
                "TakedownOffense": 0.26, "TakedownDefense": 0.16, "SubmissionThreat": 0.03,
                "Scrambles": 0.10, "GroundControl": 0.18, "GroundAndPound": 0.08,
                "BottomGame": 0.03, "ClinchControl": 0.07, "Stamina": 0.05,
                "Durability": 0.02, "FightIQ": 0.02
            },
            "Defensive Grappler": {
                "TakedownOffense": 0.05, "TakedownDefense": 0.28, "SubmissionThreat": 0.06,
                "Scrambles": 0.16, "GroundControl": 0.07, "GroundAndPound": 0.02,
                "BottomGame": 0.12, "ClinchControl": 0.08, "Stamina": 0.06,
                "Durability": 0.06, "FightIQ": 0.04
            },
            "Submission Specialist": {
                "TakedownOffense": 0.10, "TakedownDefense": 0.07, "SubmissionThreat": 0.28,
                "Scrambles": 0.14, "GroundControl": 0.12, "GroundAndPound": 0.02,
                "BottomGame": 0.10, "ClinchControl": 0.04, "Stamina": 0.05,
                "Durability": 0.04, "FightIQ": 0.04
            },
            "Ground and Pound": {
                "TakedownOffense": 0.22, "TakedownDefense": 0.10, "SubmissionThreat": 0.03,
                "Scrambles": 0.09, "GroundControl": 0.18, "GroundAndPound": 0.20,
                "BottomGame": 0.02, "ClinchControl": 0.07, "Stamina": 0.05,
                "Durability": 0.03, "FightIQ": 0.01
            },
            "All-Round Grappler": {
                "TakedownOffense": 0.14, "TakedownDefense": 0.14, "SubmissionThreat": 0.10,
                "Scrambles": 0.12, "GroundControl": 0.12, "GroundAndPound": 0.09,
                "BottomGame": 0.08, "ClinchControl": 0.09, "Stamina": 0.06,
                "Durability": 0.04, "FightIQ": 0.02
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
                "Footwork": +0.10,
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

        style_boost = 1.05

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

            if apply_stance:
                adjusted, s_log = apply_stance_adjustments(base, stance)
                bd += s_log + "\n"
            else:
                adjusted = dict(base)
                bd += f"  Stance adjustments: N/A (grappling is stance-neutral)\n\n"

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
        logs += f"  {f1_name:<38} Stance: {f1_stance}\n"
        logs += f"  {f2_name:<38} Stance: {f2_stance}\n"
        logs += f"  {f1_name:<38} Striking Style : {f1_str_style}\n"
        logs += f"  {f2_name:<38} Striking Style : {f2_str_style}\n"
        logs += f"  {f1_name:<38} Grappling Style: {f1_grp_style}\n"
        logs += f"  {f2_name:<38} Grappling Style: {f2_grp_style}\n"

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

        # --- Updated summary ---
        logs += "\n\n" + "  UPDATED STYLE STRENGTHS (after boost)".ljust(80) + "\n"
        logs += "  " + "-" * 78 + "\n\n"
        logs += f"  {'Fighter':<28} | {'Striking':>10} | {'Grappling':>10}\n"
        logs += "  " + "-" * 54 + "\n"
        logs += f"  {f1_name:<28} | {round(f1_str_updated, 4):>10} | {round(f1_grp_updated, 4):>10}\n"
        logs += f"  {f2_name:<28} | {round(f2_str_updated, 4):>10} | {round(f2_grp_updated, 4):>10}\n"
        logs += "\n" + "=" * 80 + "\n\n"

        return f1_str_updated, f1_grp_updated, f2_str_updated, f2_grp_updated, logs

    def predict_outcome(self, standing_prob: float, grappling_prob: float, fighter1: Fighter, fighter2: Fighter,
                        logs: str, rounds: int, json: int):

        C1, C2 = fighter1.clinch_score, fighter2.clinch_score
        I1, I2 = fighter1.intangibles_score, fighter2.intangibles_score

        specs_adv_1, logs_add = self.specs_adv(fighter1, fighter2)
        specs_adv_2 = -specs_adv_1

        S1, G1, S2, G2, logs = self.calc_style_multiplier(fighter1, fighter2, logs)

        strike_phase_1 = 0.80 * S1 + 0.20 * C1
        strike_phase_2 = 0.80 * S2 + 0.20 * C2
        grapple_phase_1 = G1
        grapple_phase_2 = G2

        skillset_1 = 0.80 * (standing_prob * strike_phase_1 + grappling_prob * grapple_phase_1)
        skillset_2 = 0.80 * (standing_prob * strike_phase_2 + grappling_prob * grapple_phase_2)

        intang_1, intang_2 = 0.20 * I1, 0.20 * I2

        fb1, extra1 = form_boost(fighter1)
        fb2, extra2 = form_boost(fighter2)

        cb1, cb2, cardio_log = cardio_boost(fighter1, fighter2, rounds)
        logs += cardio_log

        R1 = skillset_1 + intang_1 + specs_adv_1 + fb1 + cb1
        R2 = skillset_2 + intang_2 + specs_adv_2 + fb2 + cb2

        raw = R1 - R2
        win_prob = round(1 / (1 + math.exp(-raw)), 3)
        lose_prob = round(1 - win_prob, 3)

        f1_name = getattr(fighter1, "_personal-info_name")
        f2_name = getattr(fighter2, "_personal-info_name")

        logs += logs_add
        logs += "\n\n  RECENT FORM\n"
        logs += "  " + "-" * 78 + "\n"
        logs += extra1 + "\n"
        logs += extra2 + "\n"

        logs += "\n\n" + "=" * 80 + "\n"
        logs += "FINAL TALLY & PREDICTION".center(80) + "\n"
        logs += "=" * 80 + "\n\n"
        logs += f"  {'CATEGORY':<22} | {f1_name:<24} | {f2_name:<24}\n"
        logs += "  " + "-" * 76 + "\n"
        logs += f"  {'Skillset (80%)':<22} | {round(skillset_1, 4):<24} | {round(skillset_2, 4):<24}\n"
        logs += f"  {'Intangibles (20%)':<22} | {round(intang_1, 4):<24} | {round(intang_2, 4):<24}\n"
        logs += f"  {'Specs Boost':<22} | {round(specs_adv_1, 4):<24} | {round(specs_adv_2, 4):<24}\n"
        logs += f"  {'Form Boost':<22} | {round(fb1, 4):<24} | {round(fb2, 4):<24}\n"
        logs += f"  {'Cardio Boost':<22} | {round(cb1, 4):<24} | {round(cb2, 4):<24}\n"
        logs += "  " + "-" * 76 + "\n"
        logs += f"  {'TOTAL SCORE (R)':<22} | {round(R1, 4):<24} | {round(R2, 4):<24}\n\n"

        logs += "\n\n" + "SIGMOID CALCULATION".center(80, "-") + "\n\n\n"
        logs += f"  Score Delta (R1 - R2)  = {round(raw, 4)}\n"
        logs += f"  P(Win)  = 1 / (1 + e^-{round(raw, 4)}) = {round(win_prob * 100, 2)}%\n"
        logs += f"  P(Lose) = 100% - P(Win)              = {round(lose_prob * 100, 2)}%\n\n\n"
        logs += "=" * 80 + "\n\n"

        f1_ko, f1_sub, f1_dec, log1 = self.predict_individual_methods(fighter1, fighter2, standing_prob, grappling_prob)
        f2_ko, f2_sub, f2_dec, log2 = self.predict_individual_methods(fighter2, fighter1, standing_prob, grappling_prob)
        fight_ko, fight_sub, fight_dec, combined_log = self.combine_method_profiles(
            (f1_ko, f1_sub, f1_dec),
            (f2_ko, f2_sub, f2_dec),
            win_prob, lose_prob
        )
        logs += log1 + "\n" + log2 + "\n" + combined_log

        if json == 1:
            winner_name = f1_name if win_prob > lose_prob else f2_name
            winner_conf = win_prob if win_prob > lose_prob else lose_prob

            # 1. Define the methods dictionary based on the winner
            if winner_name == f1_name:
                methods = {"KO": f1_ko, "SUB": f1_sub, "DEC": f1_dec}
            else:
                methods = {"KO": f2_ko, "SUB": f2_sub, "DEC": f2_dec}

            # 2. Get the string name of the best method
            best_method_name = max(methods, key=methods.get)

            # 3. Get the actual numerical value of that method
            best_method_value = methods[best_method_name]

            # 4. Convert to percentage float with one decimal place
            method_perc = math.floor(best_method_value * 1000) / 10.0

            confidence = "Low"
            if winner_conf > 0.60:
                confidence = "Medium"
            if winner_conf > 0.80:
                confidence = "High"

            win_perc = math.floor(win_prob * 1000) / 10.0
            lose_perc = math.floor(lose_prob * 1000) / 10.0
            if round(win_perc + lose_perc, 1) != 100.0:
                win_perc += 0.1

            ko_perc = math.floor(fight_ko * 1000) / 10.0
            sub_perc = math.floor(fight_sub * 1000) / 10.0
            dec_perc = math.floor(fight_dec * 1000) / 10.0

            total = round(ko_perc + sub_perc + dec_perc, 1)
            if total != 100.0:
                diff = round(100.0 - total, 1)
                largest = max(["ko", "sub", "dec"], key=lambda x: {"ko": ko_perc, "sub": sub_perc, "dec": dec_perc}[x])
                if largest == "ko":
                    ko_perc = round(ko_perc + diff, 1)
                elif largest == "sub":
                    sub_perc = round(sub_perc + diff, 1)
                else:
                    dec_perc = round(dec_perc + diff, 1)

            # --- Individual fighter method threats ---
            f1_ko_perc = math.floor(f1_ko * 1000) / 10.0
            f1_sub_perc = math.floor(f1_sub * 1000) / 10.0
            f1_dec_perc = math.floor(f1_dec * 1000) / 10.0

            f2_ko_perc = math.floor(f2_ko * 1000) / 10.0
            f2_sub_perc = math.floor(f2_sub * 1000) / 10.0
            f2_dec_perc = math.floor(f2_dec * 1000) / 10.0

            for _ko, _sub, _dec, _name in [
                (f1_ko_perc, f1_sub_perc, f1_dec_perc, "f1"),
                (f2_ko_perc, f2_sub_perc, f2_dec_perc, "f2"),
            ]:
                _total = round(_ko + _sub + _dec, 1)
                if _total != 100.0:
                    _diff = round(100.0 - _total, 1)
                    _largest = max(["ko", "sub", "dec"], key=lambda x: {"ko": _ko, "sub": _sub, "dec": _dec}[x])
                    if _name == "f1":
                        if _largest == "ko":
                            f1_ko_perc = round(f1_ko_perc + _diff, 1)
                        elif _largest == "sub":
                            f1_sub_perc = round(f1_sub_perc + _diff, 1)
                        else:
                            f1_dec_perc = round(f1_dec_perc + _diff, 1)
                    else:
                        if _largest == "ko":
                            f2_ko_perc = round(f2_ko_perc + _diff, 1)
                        elif _largest == "sub":
                            f2_sub_perc = round(f2_sub_perc + _diff, 1)
                        else:
                            f2_dec_perc = round(f2_dec_perc + _diff, 1)

            # --- Style clash ---
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

            f1_str_style = getattr(fighter1, "_skillset_striking_style", None)
            f2_str_style = getattr(fighter2, "_skillset_striking_style", None)
            f1_grp_style = getattr(fighter1, "_skillset_grappling_style", None)
            f2_grp_style = getattr(fighter2, "_skillset_grappling_style", None)

            str_clash = None
            str_advantage = None
            if f1_str_style and f2_str_style:
                if f2_str_style in STR_STYLE_ADVANTAGE.get(f1_str_style, []):
                    str_clash = True
                    str_advantage = f1_name
                elif f1_str_style in STR_STYLE_ADVANTAGE.get(f2_str_style, []):
                    str_clash = True
                    str_advantage = f2_name
                else:
                    str_clash = False
                    str_advantage = None

            grp_clash = None
            grp_advantage = None
            if f1_grp_style and f2_grp_style:
                if f2_grp_style in GRP_STYLE_ADVANTAGE.get(f1_grp_style, []):
                    grp_clash = True
                    grp_advantage = f1_name
                elif f1_grp_style in GRP_STYLE_ADVANTAGE.get(f2_grp_style, []):
                    grp_clash = True
                    grp_advantage = f2_name
                else:
                    grp_clash = False
                    grp_advantage = None

            # --- Condition score (specs + form, range 5-10, midpoint 7.5) ---
            condition_scale = 2.5  # Adjust steepness (higher = more sensitive to small changes)
            f1_raw = (specs_adv_1 + fb1) * condition_scale
            f2_raw = (specs_adv_2 + fb2) * condition_scale

            # Sigmoid: 5 + 5 / (1 + e^-x) maps any input to (5, 10)
            f1_condition = round(5.0 + 5.0 / (1.0 + math.exp(-f1_raw)), 2)
            f2_condition = round(5.0 + 5.0 / (1.0 + math.exp(-f2_raw)), 2)

            return 0.0, 0.0, {
                "Fighter 1": f1_name,
                "Fighter 2": f2_name,
                "Fighter 1 Final Score": round(R1, 2),
                "Fighter 2 Final Score": round(R2, 2),
                "Rounds": rounds,
                "Winner": winner_name,
                "Winning fighters Confidence": confidence,
                "Fighter 1 % of winning": win_perc,
                "Fighter 2 % of winning": lose_perc,
                "Winners method of victory": best_method_name,
                "Winners method of victory %": method_perc,
                "% of KO": round(ko_perc, 1),
                "% of SUB": round(sub_perc, 1),
                "% of DEC": round(dec_perc, 1),

                # --- Distance ---
                "Goes to distance": dec_perc > (ko_perc + sub_perc),
                "% goes to distance": dec_perc,
                "Standing Probability": standing_prob,
                "Grappling Probability": grappling_prob,

                # --- Fighter 1 info ---
                "Fighter 1 Height": getattr(fighter1, "_specs_height", None),
                "Fighter 1 Age": fighter1.age,
                "Fighter 1 Reach": getattr(fighter1, "_specs_reach", None),
                "Fighter 1 Stance": getattr(fighter1, "_specs_stance", None),
                "Fighter 1 Striking Style": f1_str_style,
                "Fighter 1 Grappling Style": f1_grp_style,
                "Fighter 1 % KO": f1_ko_perc,
                "Fighter 1 % SUB": f1_sub_perc,
                "Fighter 1 % DEC": f1_dec_perc,

                # --- Fighter 2 info ---
                "Fighter 2 Height": getattr(fighter2, "_specs_height", None),
                "Fighter 2 Age": fighter2.age,
                "Fighter 2 Reach": getattr(fighter2, "_specs_reach", None),
                "Fighter 2 Stance": getattr(fighter2, "_specs_stance", None),
                "Fighter 2 Striking Style": f2_str_style,
                "Fighter 2 Grappling Style": f2_grp_style,
                "Fighter 2 % KO": f2_ko_perc,
                "Fighter 2 % SUB": f2_sub_perc,
                "Fighter 2 % DEC": f2_dec_perc,

                # --- Style clash ---
                "Striking style clash": str_clash,
                "Striking style advantage": str_advantage,
                "Grappling style clash": grp_clash,
                "Grappling style advantage": grp_advantage,

                # --- Radar data (all axes 0-10) ---
                "Fighter 1 Radar": {
                    "Striking": round(float(getattr(fighter1, "striking_score", 0) or 0), 2),
                    "Grappling": round(float(getattr(fighter1, "grappling_score", 0) or 0), 2),
                    "Clinch": round(float(getattr(fighter1, "clinch_score", 0) or 0), 2),
                    "Intangibles": round(float(getattr(fighter1, "intangibles_score", 0) or 0), 2),
                    "Condition": f1_condition,
                },
                "Fighter 2 Radar": {
                    "Striking": round(float(getattr(fighter2, "striking_score", 0) or 0), 2),
                    "Grappling": round(float(getattr(fighter2, "grappling_score", 0) or 0), 2),
                    "Clinch": round(float(getattr(fighter2, "clinch_score", 0) or 0), 2),
                    "Intangibles": round(float(getattr(fighter2, "intangibles_score", 0) or 0), 2),
                    "Condition": f2_condition,
                }
            }

        else:
            return win_prob, lose_prob, logs
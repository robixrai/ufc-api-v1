from datetime import date


class Fighter():

    def get_rank(self):

        from core.tools import rankings_db
        name = getattr(self, "_personal-info_name")
        for division, roster in rankings_db.items():
            index = next((index for index, variable in enumerate(roster) if name in variable), None)
            if index is not None:
                return "Champion" if index == 0 else index
        return "Unranked"

    count = 0

    def __init__(self, **kwargs):
        Fighter.count += 1
        for key, value in kwargs.items():
            setattr(self, f"_{key}", value)
        self.numbered_stats = []
        for attribute in self.__dict__:
            if "style" in attribute or "ratio" in attribute:
                continue
            elif "skillset" in attribute:
                self.numbered_stats.append(attribute)
            else:
                pass

    @property
    def age(self):
        today = date.today()
        birthday = self.__dict__["_personal-info_birth-date"]
        birthday = date.fromisoformat(birthday)
        value = today.year - birthday.year - ((today.month, today.day) < (birthday.month, birthday.day))
        return value

    @property
    def reach(self):
        return f"{self._specs_reach} inch reach"

    @property
    def height(self):
        return f"{self._specs_height}cm tall"

    def show_specific_stats(self, wanted_stats):
        specific_stats = [];
        wanted_stats = [wanted_stats]
        for stat in self.numbered_stats:
            found = False
            for wanted_stat in wanted_stats:
                if wanted_stat in stat:
                    found = True
                    break
            if found:
                value = getattr(self, stat)
                specific_stats.append(f"{stat.split('_')[-1].replace('-', ' ').capitalize():<16}:  {value} / 10")
        return "\n".join(specific_stats)

    def category_score(self, category_name):
        total = 0;
        count = 0
        for stat_path in self.numbered_stats:
            if category_name.lower() in stat_path.lower():
                val = getattr(self, stat_path, 0)
                total += val
                count += 1
        return round(total / count, 1) if count > 0 else 0

    @property
    def skillset_score(self):
        ratio = self._skillset_ratio
        ratio1 = 1.0 - ratio
        score = (0.2 * self.intangibles_score) + (0.75 * ratio * self.striking_score) + (
                    0.75 * ratio1 * self.grappling_score) + (0.05 * self.clinch_score)
        return round(score, 2)

    @property
    def intangibles_score(self):
        score = (0.3 * self._skillset_intangibles_chin) + (0.3 * self._skillset_intangibles_stamina) + (
                    0.2 * self.__dict__["_skillset_intangibles_fight-iq"]) + (0.2 * self._skillset_intangibles_recovery)
        return round(score, 1)

    @property
    def striking_score(self):
        ratio = self._skillset_striking_proportion
        ratio1 = 1.0 - ratio
        score = (0.5 * self.overview_score) + (0.5 * ratio * self.punches_score) + (0.5 * ratio1 * self.kicks_score)
        return round(score, 1)

    @property
    def grappling_score(self):
        score = self.category_score("grappling")
        return round(score, 1)

    @property
    def punches_score(self):
        score = (0.4 * self._skillset_striking_punches_jab) + (0.3 * self._skillset_striking_punches_cross) + (
                    0.3 * self._skillset_striking_punches_haymaker)
        return round(score, 1)

    @property
    def kicks_score(self):
        score = (0.4 * self._skillset_striking_kicks_low) + (0.3 * self._skillset_striking_kicks_body) + (
                    0.3 * self._skillset_striking_kicks_head)
        return round(score, 1)

    @property
    def overview_score(self):
        score = (0.3 * self._skillset_striking_overview_defence) + (0.3 * self._skillset_striking_overview_accuracy) + (
                    0.2 * self._skillset_striking_overview_power) + (0.2 * self._skillset_striking_overview_volume)
        return round(score, 1)

    @property
    def clinch_score(self):
        score = self.category_score("clinch")
        return score

    @classmethod
    def numberoffighters(cls):
        output = f"The total number of fighters loaded in the database is {cls.count}."
        return output

    def profile(self):

        # 1. HEADER

        full_name = getattr(self, "_personal-info_name")
        nickname = getattr(self, "_personal-info_nickname")
        name_parts = full_name.split()
        firstname = name_parts[0]
        lastname = " ".join(name_parts[1::])

        print(f"\n{'=' * 160}")
        print(f" {firstname} '{nickname}' {lastname} ".center(160, "="))
        print(f"{'=' * 160}\n")

        # 2. PERSONAL_INFO / SPECS

        print(f"PROFILE\n")
        print(
            f"{'Origins':<16}:  {getattr(self, '_personal-info_nationality')}, fighting out of {getattr(self, '_personal-info_fighting-out-of')}")
        print(f"{'Gym':<16}:  {getattr(self, '_personal-info_gym')}")
        print(f"{'Weight Class':<16}:  {getattr(self, '_personal-info_weight-class')}")
        print(f"{'Physicals':<16}:  {getattr(self, '_personal-info_gender')} {self.height} | {self.reach} | {self.age} years old")
        print(f"{'Stance':<16}:  {getattr(self, '_specs_stance')}")
        print(f"{'Status':<16}:  {getattr(self, '_personal-info_status')}")

        print(f"\n{'-' * 160}\n")

        # 3. CAREER

        wins = getattr(self, '_career_wins')
        losses = getattr(self, '_career_losses')
        draws = getattr(self, '_career_draws')
        NC = getattr(self, '_career_no-contests')

        rank = self.get_rank()

        lastfive = getattr(self, '_career_last-five')
        result_map = {1: "W", 0: "L", 2: "D", 3: "NC"}
        lastfive_string = ", ".join([result_map.get(num, "?") for num in lastfive])

        if NC > 0:
            record = f"{wins}-{losses}-{draws} ({NC} NC)"
        else:
            record = f"{wins}-{losses}-{draws}"

        print(f"CAREER\n")
        print(f"{'Record':<16}:  {record}")
        print(f"{'KO/TKO Wins':<16}:  {getattr(self, '_career_ko-tko-wins')}")
        print(f"{'Submissions Wins':<16}:  {getattr(self, '_career_sub-wins')}")
        print(f"{'Win Streak':<16}:  {getattr(self, '_career_win-streak')}")
        print(f"{'Current Rank':<16}:  {rank}")
        print(f"{'Last Five':<16}:  {lastfive_string}")

        print(f"\n{'-' * 160}\n")

        description = getattr(self, "_description", "No description available.")
        print(f"{'Description':<14}:  {description}\n")
        print(f"\n{'=' * 160}\n\n")

        print(f"Would you like to see {firstname} {lastname}'s profile, skillset, fight history, or exit?".center(160,
                                                                                                                  " "))
        return ""

    def skillset(self):

        full_name = getattr(self, "_personal-info_name")
        nickname = getattr(self, "_personal-info_nickname")
        name_parts = full_name.split()
        firstname = name_parts[0]
        lastname = name_parts[-1]

        print(f"\n{'=' * 160}")
        print(f" {firstname} '{nickname}' {lastname} ".center(160, "="))
        print(f"{'=' * 160}\n")
        print(f"{'OVERALL SCORE':<16}:  {self.skillset_score} / 10\n\n")

        print(f"{'Striking Score':<18}:  {self.striking_score} / 10")
        print(f"{'Style':<18}:  {getattr(self, '_skillset_striking_style')}\n")
        print(self.show_specific_stats("overview") + "\n")

        print(f"{'Punches Score':<17}:  {self.category_score('punches')} / 10")
        print(self.show_specific_stats("punches"))

        print("\n" + f"{'Leg Strikes Score':<17}:  {self.category_score('kicks')} / 10")
        print(self.show_specific_stats("kicks"))

        print("\n\n" + f"{'Clinch Score':<17}:  {self.category_score('clinch')} / 10")
        print(self.show_specific_stats("clinch") + "\n\n")

        print(f"{'Grappling Score':<17}:  {self.category_score('grappling')} / 10")
        print(f"{'Style':<17}:  {getattr(self, '_skillset_grappling_style')}\n")
        print(self.show_specific_stats("grappling"))
        print(f"\n")

        print(f"{'Intangibles Score':<17}:  {self.category_score('intangibles')} / 10\n")
        print(self.show_specific_stats("intangibles") + "\n")

        print(f"\n{'-' * 160}\n\n")

        print(
            f"Would you like to see {getattr(self, '_personal-info_name')}'s profile, skillset, fight history, or exit?".center(
                160, " "))

        return ""
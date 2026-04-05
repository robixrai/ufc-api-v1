from pathlib import Path
import json
from core import tools
from core.fighter import Fighter

from pathlib import Path
import json

DATA_DIR = Path(__file__).resolve().parent / "data"

fighters_path = DATA_DIR / "fighters.json"
rankings_path = DATA_DIR / "rankings.json"


with open(fighters_path, "r") as f:
    fighters = json.load(f)

male_divisions = []
female_divisions = []


def inspect():
    while True:

        name = input("\nWhich fighter would you like to inspect?\n\n")
        if name == 'exit':
            print("\nYou have decided to quit. ".center(160, " ") + "\n\n")
            print("\n" + ("_" * 160) + "\n")
            break

        found_fighter = partial_search(name, tools.fighter_db)

        if found_fighter:
            while True:
                category = input(
                    f"\nEnter the path of the category you would like to open for {getattr(found_fighter, '_personal-info_name')}. Enter 'attribute' to see all of the attributes available. Enter 'profile' to see {getattr(found_fighter, '_personal-info_name')}'s profile.\n\n").strip().lower()

                if category == 'exit':
                    print("\nYou have decided to quit.".center(160, " ") + "\n\n")
                    print("\n" + ("_" * 160) + "\n")
                    break

                elif category == 'profile':
                    print(fighter_search(found_fighter))

                elif category == 'attribute':
                    print("\nHere are all of the attributes:\n\n")
                    print(", ".join(att for att in found_fighter.__dict__))
                    print("\n\n")

                else:
                    category = category.split("_")
                    with open(fighters_path, 'r') as f:
                        raw_list = json.load(f)
                    target_fighter_name = getattr(found_fighter, "_personal-info_name")
                    target_json = next(
                        (item for item in raw_list if item["personal-info"]["name"] == target_fighter_name), None)

                    try:

                        folder = target_json
                        keys = category
                        for k in keys:
                            folder = folder[k]

                        while True:

                            print(f"=" * 160)
                            print(f" Editing Folder: {' > '.join(keys)} ".center(160, "="))
                            print("=" * 160)
                            print(f"{'STAT NAME':<25} | {'CURRENT VALUE'}\n")
                            print("-" * 160 + "\n")

                            for stat, value in folder.items():
                                if stat == 'fight-history':
                                    val = "[Folder]"
                                elif isinstance(value, dict):
                                    val = "[Folder]"
                                else:
                                    val = value

                                print(f"{stat:<25} |  {val}")

                            stat_to_update = input(
                                "\nWhich specific stat do you want to change? Enter 'exit' to leave\n\n").strip().lower()

                            if stat_to_update == 'last-five':

                                while True:
                                    old_val = folder[stat_to_update]
                                    new_val = input(
                                        f"\nCurrent {stat_to_update} is {old_val}. New value (0=L, 1=W, 2=D, 3=NC): ")
                                    if new_val.lower() == 'exit':
                                        break
                                    new_val = int(new_val)
                                    old_val.insert(0, new_val)
                                    if len(old_val) > 5:
                                        old_val.pop()

                                    with open(fighters_path, 'w') as f:
                                        json.dump(raw_list, f, indent=4)

                                    tools.load_data()

                                    print(f"Updated Form: {old_val}")

                            elif stat_to_update == 'fight-history':

                                while True:

                                    history_list = folder[stat_to_update]

                                    print("\n" + "--- Fight History ---".center(160, " ") + "\n")
                                    for fight in history_list:
                                        print(f"{fight}".center(160, " "))
                                    print("\n")
                                    print("-" * 160)
                                    print("\n\n")

                                    choice = input(
                                        "Would you like to add, change, or remove a fight?\n\n").lower().strip()

                                    if choice == 'add':

                                        new_entry = fight_info()
                                        index = int(input(
                                            f"\nAt which index should this fight be placed? (0 for newest, {len(history_list)} for oldest): ").strip())
                                        history_list.insert(index, new_entry)
                                        with open(fighters_path, 'w') as f:
                                            json.dump(raw_list, f, indent=4)
                                        tools.load_data()
                                        print(f"\nAdded: {new_entry}")


                                    elif choice == 'change':

                                        index = int(input(
                                            f"Which fight would you like to change? (0 for newest, {len(history_list) - 1} for oldest):  ").strip())
                                        print("\n\n")

                                        updated_entry = fight_info()
                                        history_list[index] = updated_entry
                                        with open(fighters_path, 'w') as f:
                                            json.dump(raw_list, f, indent=4)
                                        tools.load_data()
                                        print(f"\nAdded: {updated_entry}")

                                    elif choice == 'remove':

                                        index = int(input(
                                            f"Which fight would you like to remove? (0 for newest, {len(history_list)} for oldest):  ").strip())
                                        history_list.remove(index)
                                        with open(fighters_path, 'w') as f:
                                            json.dump(raw_list, f, indent=4)
                                        tools.load_data()
                                        print(f"\nFight at index {index} Removed.")

                                    elif choice == 'exit':
                                        print(f"\nYou have decided to exit\n")
                                        print("\n" + ("_" * 160) + "\n")
                                        break
                                    else:
                                        print("\nSorry, I couldn't understand that\n")

                            elif stat_to_update == 'style':

                                old_val = folder[stat_to_update]
                                print("- - - Fighting Styles - - -".center(160, " ") + "\n\n")
                                print(
                                    f"Striking styles :   Counter Striker, Pressure Striker, Outside Sniper, Technical Boxer, Muay Thai / Kickboxer\n")
                                print(
                                    f"Grappling styles :   Wrestler, Defensive Grappler, Submission Specialist, Ground and Pound, All-Round Grappler\n")
                                new_val = input(f"\nCurrent {stat_to_update} is {old_val}. New Style : ").strip()

                                folder[stat_to_update] = new_val

                                with open(fighters_path, 'w') as f:
                                    json.dump(raw_list, f, indent=4)
                                tools.load_data()

                                print("\n\n" + "Change Saved".center(160, " ") + "\n\n")





                            elif stat_to_update in folder:

                                if isinstance(folder[stat_to_update], dict):

                                    initial_path = ' > '.join(keys) + f" > {stat_to_update}"
                                    result = navigate(folder[stat_to_update], initial_path, stat_to_update)
                                    if result == ("exit", "exit"):
                                        print(f"\nYou have decided to exit\n")
                                        break

                                    copy_folder, copy_final_stat_name = result

                                else:

                                    copy_folder = folder
                                    copy_final_stat_name = stat_to_update

                                old_val = copy_folder[copy_final_stat_name]
                                new_val = input(f"\nCurrent {copy_final_stat_name} is {old_val}. New value is: ")

                                if isinstance(old_val, int):
                                    copy_folder[copy_final_stat_name] = int(new_val)
                                elif isinstance(old_val, float):
                                    copy_folder[copy_final_stat_name] = float(new_val)
                                else:
                                    copy_folder[copy_final_stat_name] = new_val

                                with open(fighters_path, 'w') as f:
                                    json.dump(raw_list, f, indent=4)
                                tools.load_data()

                                print("\n\nChange saved to fighters.json\n\n")


                            elif stat_to_update == 'exit':
                                print(f"\nYou have decided to exit\n")
                                print("\n" + ("_" * 160) + "\n")
                                break
                            else:
                                print(f"\nError: '{stat_to_update}' is not in this folder.\n")
                    except Exception as e:
                        print(f"\nError Type: {type(e).__name__}")
                        print(f"Error Details: {repr(e)}")

    return ""


for div in tools.rankings_db.keys():
    if div.startswith("men's"):
        div = div.title().removeprefix("Men'S_").replace('-', ' ')
        male_divisions.append(div)

for div in tools.rankings_db.keys():
    if div.startswith("women's"):
        div = div.title().removeprefix("Women'S_").replace('-', ' ')
        female_divisions.append(div)


def deep_dive(data, path=""):
    for key, value in data.items():
        current_path = f"{path} > {key}" if path else key

        if isinstance(value, dict):
            result = deep_dive(value, current_path)
            if result == 'exit':
                return data
            elif result == 'cancel':
                return 'cancel'

        else:

            while True:

                try:

                    if current_path == 'skillset > striking > style':
                        new_val = input(
                            f"{current_path} (Counter Striker, Pressure Striker, Outside Sniper, Technical Boxer, Muay Thai / Kickboxer): ").strip()
                    elif current_path == 'career > api-id':
                        print("career > api-id : Unable to create attribute")
                        break
                    elif current_path == 'skillset > grappling > style':
                        new_val = input(
                            f"{current_path} (Wrestler, Defensive Grappler, Submission Specialist, Ground and Pound, All-Round Grappler): ").strip()
                    elif current_path == 'career > last-five':
                        print(f"Enter the results of the last five fights of the opponent. (0=L, 1=W, 2=D, 3=NC).")
                        new_val = []
                        for x in range(0, 5):
                            result = int(input(f"Fight {x + 1} : "))
                            if result == 'exit':
                                return 'exit'
                            elif result == 'cancel':
                                return 'cancel'
                            new_val.append(result)
                    elif current_path == 'career > fight-history':
                        print("career > fight-history : Unable to create attribute")
                        break
                    else:
                        new_val = input(f"{current_path} : ").strip()

                    if new_val == 'exit':
                        return 'exit'
                    elif new_val == 'cancel':
                        return 'cancel'
                    if isinstance(value, int) and new_val:
                        data[key] = int(new_val)
                    elif isinstance(value, float) and new_val:
                        data[key] = float(new_val)
                    else:
                        data[key] = new_val

                    break

                except Exception as e:
                    print(f"\nError Type: {type(e).__name__}")
                    print(f"Error Details: {repr(e)}")

    return data


def create_fighter():
    print(" - - - CREATING FIGHTER - - - ".center(160, " ") + "\n\n")

    blueprint = tools.empty_db.copy()
    blueprint = deep_dive(blueprint)

    if blueprint == 'cancel':
        print("\n\n" + "Creation Stopped.".center(160, " ") + "\n\n")
        return

    with open(fighters_path, 'r') as f:
        raw_list = json.load(f)
    raw_list.append(blueprint)
    with open(fighters_path, 'w') as f:
        json.dump(raw_list, f, indent=4)
    tools.load_data()

    print(f"\n\n" + f"{blueprint['personal-info']['name']} added to the database.".center(160, " ") + "\n\n")

    return ""


def fight_info():
    result = input("Result (W/L/D/NC): ").upper().strip()
    opponent = input("Opponent Name: ").strip().title()
    method = input("Method (e.g., KO/TKO, Sub, U-Dec): ").strip()
    event = input("Event (e.g., UFC 300): ").strip()
    round = input("Round (e.g., 1): ").strip()
    time = input("Time (e.g, 2:22): ").strip()

    new_entry = f"{result} vs {opponent} ({method}) R{round} {time} - {event}"
    return new_entry


def partial_search(term, data):
    term = term.strip().lower()
    found_name = None
    found_name = data.get(term)
    if not found_name:
        for name in data:
            if term in name:
                found_name = data[name]
                break
    return found_name


def fighter_search(name):
    print(Fighter.profile(name))

    while True:

        print("")
        choice = input().strip().lower()
        if choice == 'skillset':
            print(Fighter.skillset(name))
        elif choice == 'fight history':
            fight_history = getattr(found_fighter, "_career_fight-history")
            print("\n" + "--- Fight History ---".center(160, " ") + "\n")
            for fight in fight_history:
                print(f"{fight}".center(160, " "))
            print("\n")
            print("-" * 160)
            print("\n\n")
            print(
                f"Would you like to see {getattr(found_fighter, '_personal-info_name')}'s profile, skillset, fight history, or exit?".center(
                    160, " "))
        elif choice == 'profile':
            print(Fighter.profile(name))
        elif choice == 'help':
            print(
                "Here is every available function:\n\nProfile - See the personal identity of a fighter\nSkillset - See the skill rating of a fighter\nFight history - See the fight history of a fighter\nExit - Exit this page\n")
        elif choice == 'exit':
            print(f"\nYou have decided to exit\n")
            print("\n" + ("_" * 160) + "\n")
            return ""
        else:
            print("Sorry, I didn't understand you there.\n")
            print(
                f"Would you like to see {getattr(found_fighter, '_personal-info_name')}'s profile, skillset, fight history, or exit?".center(
                    160, " "))
    return ""


def navigate(folder, path, stat_to_update):
    if isinstance(folder, dict):
        print("\n" + f"--- Location: {path} ---".center(160, " "))
        print("\n")
        print(f"{'ATTRIBUTE':<25} | {'VALUE'}")
        print("-" * 160)

        for key, value in folder.items():
            display = "[Folder]" if isinstance(value, (dict, list)) else value
            print(f"{key:<25} | {display}")

        stat_to_update = input("\nWhich attribute would you like to open or edit? (or 'exit'): ").strip()

        if stat_to_update == 'exit':
            return "exit", "exit"

        if stat_to_update in folder:
            new_path = f"{path} > {stat_to_update}"
            if isinstance(folder[stat_to_update], dict):
                return navigate(folder[stat_to_update], new_path, stat_to_update)
            else:
                return folder, stat_to_update

        else:
            print("Invalid attribute.")
            return navigate(folder, path, stat_to_update)
    else:
        return folder, stat_to_update


def update_rankings():
    while True:

        print(f"\nWhich gender's divisions would you like to update? Enter 'Male' or 'Female'.".center(160, " ") + "\n")
        search = input("").strip().lower()

        if search == 'exit':
            print("\n" + ("_" * 160) + "\n")
            break

        elif search in ['male', 'female']:

            prefix = "men's_" if search == 'male' else "women's_"

            while True:

                print(
                    f"\nWhich division's rankings would you like to update? Enter 'Divisions' to see all of the divisions in the UFC for {search}s".center(
                        160, " ") + "\n\n")
                search1 = input("").strip().lower().replace(" ", "-")

                full_key = prefix + search1

                print("\n")

                if search1 == 'divisions':
                    if search == 'male':
                        print(", ".join(male_divisions))
                    else:
                        print(", ".join(female_divisions))

                elif full_key in tools.rankings_db:
                    while True:

                        print("\n\n")
                        print(search1.capitalize().replace("_", " ").center(160, " "))
                        print("-" * 160)
                        print("\n\n")
                        division = tools.rankings_db[full_key]
                        for x, fighter in enumerate(division):
                            rank = x
                            if rank == 0:
                                rank = "Champ"
                            print(f"{rank:<6}:   {fighter}")

                        print("\n\n" + "Which rank number would you like to change? (0 for Champ)".center(160,
                                                                                                          " ") + "\n\n")
                        index = input("")
                        if index == 'exit':
                            return ""
                        index = int(index)
                        print(f"Enter the full name of the fighter who is currently rank number {index}\n\n")
                        name = input("").strip()

                        with open(rankings_path, 'r') as f:
                            raw_list = json.load(f)
                        key = "men's" if search == 'male' else "women's"
                        folder = raw_list[key][search1]
                        folder[index] = name

                        with open(rankings_path, 'w') as f:
                            json.dump(raw_list, f, indent=4)
                        tools.load_data()

                        print("\n\nSave Changed.\n\n")




                elif search1 == 'exit':
                    print("\n" + ("_" * 160) + "\n")
                    break

                else:
                    print("\nSorry, I couldn't quite understand that")

        else:
            print("\nSorry, I couldn't quite understand that")


print("\n" + "Robert's UFC Contender and Prospect Database".center(160, " ") + "\n")
print("_" * 160 + "\n")

while True:

    found_fighter = None

    print("\nWhat would you like to do? Enter 'Help' for guidance".center(160, " ") + "\n")
    search = input("").strip().lower()

    if search == 'exit':
        print("\nProject Shutting Down.\n\n")
        print("\n" + ("_" * 160) + "\n")
        break

    elif search == 'help':
        print(
            "\nHere is every current available function:\n\n'Search' - Enter a fighter's name to see all of their available data\n'Database' - See all of the fighters currently available to search in the database\n'Rankings' - See the rankings for certain divisions\n'Exit' - Enter at any time to leave a page".center(
                160, " ") + "\n\n")

    elif search == 'admin':
        password = input("\nEnter the password.\n\n").strip()
        tries = 2

        while password != 'N' and tries != 0:
            password = input(f"Incorrect password. {tries} left. Enter the password.\n").strip()
            tries -= 1

        if password == 'N':
            print("\nAccess Granted. Admin mode activating...")
            print("\n" + ("_" * 160) + "\n")
            print("Admin Mode".center(160, " ") + "\n\n")

            while True:

                choice = input("Enter Command.\n\n").lower().strip()

                if choice == 'inspect':

                    inspect()

                elif choice == 'update':

                    update_rankings()

                elif choice == 'exit':
                    print(f"\nYou have decided to exit.\n\n" + "Admin mode shutting down".center(160, " "))
                    print("\n" + ("_" * 160) + "\n")
                    break

                elif choice == 'create':

                    create_fighter()

                else:
                    print("\n\nNot Understood.\n\n")

    elif search == 'database':
        print("\nHere is all of the currently available fighters in the database:\n")
        print("\n".join(name.title() for name in tools.fighter_db.keys()) + ".")
        print("\n\n")




    elif search == 'search':
        while True:

            found_fighter = None
            print("\n" + "Enter a fighter's name: ".center(160) + "\n")
            search = input("").strip().lower()

            if search == 'exit':
                print("\nYou have decided to quit. Database closing.".center(160, " ") + "\n\n")
                print("\n" + ("_" * 160) + "\n")
                break

            found_fighter = partial_search(search, tools.fighter_db)

            if found_fighter:
                print(fighter_search(found_fighter))
                break

            else:
                print(f"\n Fighter '{search}' not found. \n")




    elif search == 'rankings':
        while True:

            if search == 'exit':
                break

            print(f"\nWhich gender's divisions would you like to see? Enter 'Male' or 'Female'.".center(160, " ") + "\n")
            search = input("").strip().lower()
            gender = search

            if gender == 'exit':
                print("\n" + ("_" * 160) + "\n")
                break

            elif gender in ['male', 'female']:

                prefix = "men's_" if gender == 'male' else "women's_"

                while True:

                    print(
                        f"\nWhich division's rankings would you like to see? Enter 'Divisions' to see all of the divisions in the UFC for {gender}s".center(
                            160, " ") + "\n\n")
                    search = input("").strip().lower().replace(" ", "-")

                    full_key = prefix + search

                    print("\n")

                    if search == 'divisions':
                        if gender == 'male':
                            print(", ".join(male_divisions))
                        else:
                            print(", ".join(female_divisions))

                    elif full_key in tools.rankings_db:
                        print("\n")
                        division = tools.rankings_db[full_key]
                        for x, fighter in enumerate(division):
                            rank = x
                            if rank == 0:
                                rank = "Champ"
                            print(f"{rank:<6}:   {fighter}")


                    elif search == 'exit':
                        print("\n" + ("_" * 160) + "\n")
                        search = 'exit'
                        break

                    else:
                        print("\nSorry, I couldn't quite understand that")

            else:
                print("\nSorry, I couldn't quite understand that")




    else:
        print("\nSorry, I couldn't quite understand that")
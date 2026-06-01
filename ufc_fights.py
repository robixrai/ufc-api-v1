import json
import os
from pathlib import Path

file_path = Path(__file__).resolve().parent / "data" / "ufc_events.json"


class UFCManager:
    def __init__(self, filename=file_path):
        self.filename = filename
        self.data = self._load_data()

    def _load_data(self):
        if os.path.exists(self.filename):
            with open(self.filename, 'r') as f:
                return json.load(f)
        return {}

    def save(self):
        with open(self.filename, 'w') as f:
            json.dump(self.data, f, indent=4)
        print("\n[SUCCESS] Data saved to ufc_events.json")

    def list_events(self):
        if not self.data:
            print("\nNo events found.")
            return []
        events = list(self.data.keys())
        print("\n--- Current Events ---")
        for i, name in enumerate(events):
            print(f"{i}. {name}")
        return events

    def get_menu_choice(self, prompt, options):
        print(f"\n{prompt}")
        for i, opt in enumerate(options, 1):
            print(f"{i}. {opt}")
        while True:
            choice = input("Select (1-{0}) or 'exit': ".format(len(options))).strip().lower()
            if choice in ['exit', 'leave', 'quit']:
                return 'exit'
            try:
                idx = int(choice) - 1
                if 0 <= idx < len(options):
                    return options[idx]
            except ValueError:
                pass
            print("Invalid. Please enter a number from the list.")

    def _fighters_match(self, bout_struct, f1, f2):
        a = bout_struct["fighter1"].strip().lower()
        b = bout_struct["fighter2"].strip().lower()
        f1n = f1.strip().lower()
        f2n = f2.strip().lower()
        return (a == f1n and b == f2n) or (a == f2n and b == f1n)

    def _build_bout(self, event_name, fighter1, fighter2):
        event = self.data[event_name]
        etype = event["type"]

        is_main_event = self._fighters_match(event["main_fight"], fighter1, fighter2)
        is_co_main_event = (not is_main_event) and self._fighters_match(event["comain"], fighter1, fighter2)

        if is_main_event:
            rounds = 5
        elif is_co_main_event and etype == "Numbered Event":
            rounds = 5
        else:
            rounds = 3

        return {
            "fighter1": fighter1,
            "fighter2": fighter2,
            "rounds": rounds,
            "is_main_event": is_main_event,
            "is_co_main_event": is_co_main_event,
        }

    def _recompute_all_bouts(self, event_name):
        event = self.data[event_name]
        for card_key in ("main_card", "prelims"):
            event[card_key] = [
                self._build_bout(event_name, b["fighter1"], b["fighter2"])
                for b in event[card_key]
            ]

    def run(self):
        while True:
            print("\n" + "=" * 35)
            print("     UFC PREDICTOR DB (2026)")
            print("=" * 35)
            print("1. Create New Event")
            print("2. Add Bouts (Bulk Mode)")
            print("3. Edit Event Details")
            print("4. Edit Fighter in Bout")
            print("5. View Event Fights")
            print("6. Remove a Specific Bout")
            print("7. Delete an Entire Event")
            print("8. Save and Exit")

            choice = input("\nMain Menu Selection: ")

            # ------------------------------------------------------------------ 1
            if choice == '1':
                name = input("Event Name (e.g., UFC 328): ").strip()

                etype = self.get_menu_choice(
                    "Event Type:", ["Numbered Event", "Fight Night", "Other"]
                )
                if etype == 'exit':
                    continue

                print("\nMain Event fighters:")
                main_f1 = input("  Fighter 1: ").strip()
                main_f2 = input("  Fighter 2: ").strip()

                print("Co-Main Event fighters:")
                comain_f1 = input("  Fighter 1: ").strip()
                comain_f2 = input("  Fighter 2: ").strip()

                date = input("Date (YYYY-MM-DD): ").strip()
                loc = input("Location: ").strip()

                self.data[name] = {
                    "type": etype,
                    "main_fight": {"fighter1": main_f1, "fighter2": main_f2},
                    "comain": {"fighter1": comain_f1, "fighter2": comain_f2},
                    "date": date,
                    "location": loc,
                    "main_card": [],
                    "prelims": [],
                }
                print(f"\n'{name}' initialised as a {etype}.")

            # ------------------------------------------------------------------ 2
            elif choice == '2':
                events = self.list_events()
                if not events:
                    continue
                try:
                    idx = int(input("\nSelect event index: "))
                    event_name = events[idx]
                except (ValueError, IndexError):
                    print("Invalid event choice.")
                    continue

                section = self.get_menu_choice("Adding to which card?", ["Main Card", "Prelims"])
                if section == 'exit':
                    continue
                card_key = "main_card" if section == "Main Card" else "prelims"

                print(f"\n--- Adding bouts to: {event_name} › {section} ---")
                print("Type 'exit' as Fighter 1 to finish.\n")

                while True:
                    f1 = input("Fighter 1: ").strip()
                    if f1.lower() in ['exit', 'leave', 'quit']:
                        break
                    f2 = input("Fighter 2: ").strip()

                    bout = self._build_bout(event_name, f1, f2)
                    self.data[event_name][card_key].append(bout)

                    flags = []
                    if bout["is_main_event"]: flags.append("MAIN EVENT")
                    if bout["is_co_main_event"]: flags.append("CO-MAIN")
                    tag = f" [{', '.join(flags)}]" if flags else ""
                    print(f"  Added: {f1} vs {f2} — {bout['rounds']} rounds{tag}\n")

            # ------------------------------------------------------------------ 3
            elif choice == '3':
                events = self.list_events()
                if not events:
                    continue
                try:
                    idx = int(input("Select event index: "))
                    old_name = events[idx]
                except (ValueError, IndexError):
                    print("Invalid choice.")
                    continue

                field = self.get_menu_choice(
                    f"Edit '{old_name}':",
                    ["Name", "Type", "Date", "Location", "Main Event", "Co-Main Event"]
                )
                if field == 'exit':
                    continue

                if field == 'Name':
                    new_name = input("New Event Name: ").strip()
                    self.data[new_name] = self.data.pop(old_name)

                elif field == 'Type':
                    new_type = self.get_menu_choice(
                        "New Type:", ["Numbered Event", "Fight Night", "Other"]
                    )
                    if new_type != 'exit':
                        self.data[old_name]["type"] = new_type
                        self._recompute_all_bouts(old_name)
                        print("Type updated — rounds recomputed.")

                elif field == 'Date':
                    self.data[old_name]["date"] = input("New Date (YYYY-MM-DD): ").strip()

                elif field == 'Location':
                    self.data[old_name]["location"] = input("New Location: ").strip()

                elif field == 'Main Event':
                    print("New Main Event fighters:")
                    f1 = input("  Fighter 1: ").strip()
                    f2 = input("  Fighter 2: ").strip()
                    self.data[old_name]["main_fight"] = {"fighter1": f1, "fighter2": f2}
                    self._recompute_all_bouts(old_name)
                    print("Main event updated — flags recomputed.")

                elif field == 'Co-Main Event':
                    print("New Co-Main Event fighters:")
                    f1 = input("  Fighter 1: ").strip()
                    f2 = input("  Fighter 2: ").strip()
                    self.data[old_name]["comain"] = {"fighter1": f1, "fighter2": f2}
                    self._recompute_all_bouts(old_name)
                    print("Co-main updated — flags recomputed.")

            # ------------------------------------------------------------------ 4
            elif choice == '4':
                events = self.list_events()
                if not events:
                    continue
                try:
                    event_name = events[int(input("Select event index: "))]
                except (ValueError, IndexError):
                    print("Invalid choice.")
                    continue

                section = self.get_menu_choice("Which card?", ["Main Card", "Prelims"])
                if section == 'exit':
                    continue
                card_key = "main_card" if section == "Main Card" else "prelims"

                fights = self.data[event_name][card_key]
                if not fights:
                    print("No bouts in that section.")
                    continue

                for i, b in enumerate(fights):
                    print(f"  {i}. {b['fighter1']} vs {b['fighter2']}")

                try:
                    bout_idx = int(input("Select bout index: "))
                    bout = fights[bout_idx]
                except (ValueError, IndexError):
                    print("Invalid index.")
                    continue

                fighter_slot = self.get_menu_choice(
                    f"Edit which fighter in '{bout['fighter1']} vs {bout['fighter2']}'?",
                    ["Fighter 1", "Fighter 2"]
                )
                if fighter_slot == 'exit':
                    continue

                new_name = input(f"New name for {fighter_slot}: ").strip()
                if fighter_slot == "Fighter 1":
                    fights[bout_idx]["fighter1"] = new_name
                else:
                    fights[bout_idx]["fighter2"] = new_name

                self._recompute_all_bouts(event_name)
                print(f"  Updated — bout is now: {fights[bout_idx]['fighter1']} vs {fights[bout_idx]['fighter2']}")

            # ------------------------------------------------------------------ 5
            elif choice == '5':
                events = self.list_events()
                if not events:
                    continue
                try:
                    event_name = events[int(input("Select event index: "))]
                except (ValueError, IndexError):
                    print("Invalid choice.")
                    continue

                event = self.data[event_name]
                print(f"\n{'=' * 50}")
                print(f"  {event_name}")
                print(f"  Type     : {event.get('type', 'N/A')}")
                print(f"  Date     : {event.get('date', 'N/A')}")
                print(f"  Location : {event.get('location', 'N/A')}")
                print(f"  Main Event : {event['main_fight']['fighter1']} vs {event['main_fight']['fighter2']}")
                print(f"  Co-Main    : {event['comain']['fighter1']} vs {event['comain']['fighter2']}")
                print(f"{'=' * 50}")

                main_card = event.get("main_card", [])
                prelims = event.get("prelims", [])

                print("\n  MAIN CARD")
                print("  " + "-" * 40)
                if main_card:
                    for i, b in enumerate(main_card):
                        flags = []
                        if b.get("is_main_event"): flags.append("MAIN EVENT")
                        if b.get("is_co_main_event"): flags.append("CO-MAIN")
                        tag = f" [{', '.join(flags)}]" if flags else ""
                        print(f"  {i}. {b['fighter1']} vs {b['fighter2']} — {b['rounds']} rounds{tag}")
                else:
                    print("  No bouts added yet.")

                print("\n  PRELIMS")
                print("  " + "-" * 40)
                if prelims:
                    for i, b in enumerate(prelims):
                        print(f"  {i}. {b['fighter1']} vs {b['fighter2']} — {b['rounds']} rounds")
                else:
                    print("  No bouts added yet.")

            # ------------------------------------------------------------------ 6
            elif choice == '6':
                events = self.list_events()
                if not events:
                    continue
                try:
                    event_name = events[int(input("Select event index: "))]
                except (ValueError, IndexError):
                    print("Invalid choice.")
                    continue

                section = self.get_menu_choice("From which card?", ["Main Card", "Prelims"])
                if section == 'exit':
                    continue
                card_key = "main_card" if section == "Main Card" else "prelims"

                fights = self.data[event_name][card_key]
                if not fights:
                    print("No bouts in that section.")
                    continue
                for i, f in enumerate(fights):
                    print(f"  {i}. {f['fighter1']} vs {f['fighter2']}")

                try:
                    fights.pop(int(input("Index to remove: ")))
                    print("Bout removed.")
                except (ValueError, IndexError):
                    print("Invalid index.")

            # ------------------------------------------------------------------ 7
            elif choice == '7':
                events = self.list_events()
                if not events:
                    continue
                try:
                    target = events[int(input("Select event index to DELETE: "))]
                except (ValueError, IndexError):
                    print("Invalid choice.")
                    continue
                if input(f"Confirm deleting '{target}'? (y/n): ").lower() == 'y':
                    del self.data[target]
                    print("Event deleted.")

            # ------------------------------------------------------------------ 8
            elif choice == '8':
                self.save()
                break


if __name__ == "__main__":
    manager = UFCManager()
    manager.run()
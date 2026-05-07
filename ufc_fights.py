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
        """Helper for strict numbered menu selection."""
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

    def run(self):
        while True:
            print("\n" + "=" * 35)
            print("     UFC PREDICTOR DB (2026)")
            print("=" * 35)
            print("1. Create New Event")
            print("2. Add Bouts (Bulk Mode)")
            print("3. Edit Event Details")
            print("4. Remove a Specific Bout")
            print("5. DELETE AN ENTIRE EVENT")
            print("6. View Full JSON Data")
            print("7. Save and Exit")

            choice = input("\nMain Menu Selection: ")

            if choice == '1':
                name = input("Event Name (e.g., UFC 328): ")
                # Strictly Numbered vs Fight Night
                etype = self.get_menu_choice("Event Type:", ["Numbered Event", "Fight Night"])
                if etype == 'exit': continue

                main_title = input("Main Event: ")
                comain_title = input("Co-Main: ")
                date = input("Date (YYYY-MM-DD): ")
                loc = input("Location: ")

                self.data[name] = {
                    "type": etype,
                    "main_fight": main_title,
                    "comain": comain_title,
                    "date": date,
                    "location": loc,
                    "main_card": [],
                    "prelims": []
                }
                print(f"\n'{name}' initialized as a {etype}.")

            elif choice == '2':
                events = self.list_events()
                if not events: continue
                try:
                    idx = int(input("\nSelect event index: "))
                    event_name = events[idx]
                except (ValueError, IndexError):
                    print("Invalid event choice.")
                    continue

                print(f"\n--- Adding bouts to: {event_name} ---")
                print("Type 'exit' as the fighter name to return to menu.")

                while True:
                    f1 = input("\nFighter 1: ").strip()
                    if f1.lower() in ['exit', 'leave']: break
                    f2 = input("Fighter 2: ").strip()

                    rounds = self.get_menu_choice("Rounds:", ["3", "5"])
                    if rounds == 'exit': break

                    placement = self.get_menu_choice("Card Placement:", ["Main Card", "Prelims"])
                    if placement == 'exit': break

                    key = "main_card" if placement == "Main Card" else "prelims"
                    self.data[event_name][key].append({
                        "fighter1": f1,
                        "fighter2": f2,
                        "rounds": int(rounds)
                    })
                    print(f"Added to {placement}: {f1} vs {f2}")

            elif choice == '3':
                events = self.list_events()
                if not events: continue
                idx = int(input("Select event index: "))
                old_name = events[idx]

                field = self.get_menu_choice(f"Edit {old_name}:",
                                             ["Name", "Type", "Date", "Location", "Main Event Title"])
                if field == 'Name':
                    new_name = input("New Event Name: ")
                    self.data[new_name] = self.data.pop(old_name)
                elif field == 'Type':
                    self.data[old_name]["type"] = self.get_menu_choice("New Type:", ["Numbered Event", "Fight Night"])
                elif field == 'Date':
                    self.data[old_name]["date"] = input("New Date: ")
                elif field == 'Location':
                    self.data[old_name]["location"] = input("New Location: ")
                elif field == 'Main Event Title':
                    self.data[old_name]["main_fight"] = input("New Main Event: ")

            elif choice == '4':
                events = self.list_events()
                if not events: continue
                event_name = events[int(input("Select event index: "))]
                section = self.get_menu_choice("From which list?", ["Main Card", "Prelims"])
                key = "main_card" if section == "Main Card" else "prelims"

                fights = self.data[event_name][key]
                for i, f in enumerate(fights):
                    print(f"{i}. {f['fighter1']} vs {f['fighter2']}")

                f_idx = int(input("Index to remove: "))
                fights.pop(f_idx)
                print("Bout removed.")

            elif choice == '5':
                events = self.list_events()
                if not events: continue
                idx = int(input("Select event index to PURGE: "))
                if input(f"Confirm deleting {events[idx]}? (y/n): ").lower() == 'y':
                    del self.data[events[idx]]
                    print("Event deleted.")

            elif choice == '6':
                print(json.dumps(self.data, indent=4))

            elif choice == '7':
                self.save()
                break


if __name__ == "__main__":
    manager = UFCManager()
    manager.run()
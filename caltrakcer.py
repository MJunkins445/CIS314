from datetime import date, datetime
import json
from pathlib import Path

DATA_FILE = Path(__file__).with_name("caltracker_data.json")

def load_data():
    # Load tracker state from disk
    if not DATA_FILE.exists():
        return {"entries": [], "daily_goal": None, "next_id": 1}

    try:
        with DATA_FILE.open("r", encoding="utf-8") as handle:
            raw = json.load(handle)
    except (json.JSONDecodeError, OSError):
        print("Could not read existing data file")
        return {"entries": [], "daily_goal": None, "next_id": 1}

    # sets inputs to ids stored on json
    entries = raw.get("entries", [])
    if not isinstance(entries, list):
        entries = []

    cleaned_entries = []
    max_id = 0
    for entry in entries:
        try:
            entry_id = int(entry.get("id"))
            entry_date = str(entry.get("date"))
            meal = str(entry.get("meal"))
            calories = int(entry.get("calories"))
        except (TypeError, ValueError):
            continue
        

        max_id = max(max_id, entry_id)
        cleaned_entries.append(
            {
                "id": entry_id,
                "date": entry_date,
                "meal": meal,
                "calories": calories,
                "category": str(entry.get("category") or ""),
                "notes": str(entry.get("notes") or ""),
            }
        )

    # Sort by actual date object for consistency
    def parse_date(d):
        try:
            return datetime.strptime(d, "%m-%d-%Y")
        except ValueError:
            return datetime.min

    cleaned_entries.sort(key=lambda item: (parse_date(item["date"]), item["id"]))

    # Set/Remove daily calorie goal
    daily_goal = raw.get("daily_goal")
    try:
        daily_goal = int(daily_goal) if daily_goal is not None else None
        if daily_goal is not None and daily_goal <= 0:
            daily_goal = None
    except (TypeError, ValueError):
        daily_goal = None

    next_id = raw.get("next_id")
    if not isinstance(next_id, int) or next_id <= max_id:
        next_id = max_id + 1

    return {"entries": cleaned_entries, "daily_goal": daily_goal, "next_id": next_id}

# Saves input to id number and create new ID number in Json
def save_data(data):
    payload = {
        "entries": sorted(data["entries"], key=lambda item: (
            datetime.strptime(item["date"], "%m-%d-%Y"), item["id"])),
        "daily_goal": data.get("daily_goal"),
        "next_id": data.get("next_id", 1),
    }
    with DATA_FILE.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2)
        handle.write("\n")

# Date format requirements
def prompt_date(prompt_text, default_value):
    default_hint = f" (default {default_value})" if default_value else ""
    while True:
        response = input(f"{prompt_text}{default_hint}: ").strip()
        if not response:
            return default_value
        try:
            parsed = datetime.strptime(response, "%m-%d-%Y").date()
            return parsed.strftime("%m-%d-%Y")
        except ValueError:
            print("Please use the MM-DD-YYYY date format.")

# Value requirements
def prompt_positive_int(prompt_text):
    while True:
        response = input(f"{prompt_text}: ").strip()
        try:
            value = int(response)
        except ValueError:
            print("Enter a whole number please.")
            continue
        if value <= 0:
            print("Value must be greater than zero.")
            continue
        return value
# Entrys
def add_entry(data):
    today = date.today().strftime("%m-%d-%Y")
    entry_date = prompt_date("Date", today)
    meal = input("Meal description: ").strip() or "Meal"
    calories = prompt_positive_int("Calories")
    category = input("Category (optional): ").strip()
    notes = input("Notes (optional): ").strip()

    entry = {
        "id": data["next_id"],
        "date": entry_date,
        "meal": meal,
        "calories": calories,
        "category": category,
        "notes": notes,
    }
    data["entries"].append(entry)
    data["next_id"] += 1
    save_data(data)
    print(f"Added {calories} calories for {meal} on {entry_date}.")

def list_entries(data, filter_date=None):
    entries = data["entries"]
    if filter_date:
        entries = [item for item in entries if item["date"] == filter_date]
    if not entries:
        message = "No entries logged yet." if not filter_date else f"No entries for {filter_date}."
        print(message)
        return

    print("ID   Date        Meal                 Cal  Category        Notes")
    print("=" * 70)
    for entry in entries:
        meal = entry["meal"][:20].ljust(20)
        category = (entry["category"] or "-")[:14].ljust(14)
        notes = (entry["notes"] or "-")
        print(
            f"{entry['id']:>3}  {entry['date']}  {meal}  {entry['calories']:>4}  {category}  {notes}"
        )
# Views a daily summary of entries
def view_daily_summary(data):
    today = date.today().strftime("%m-%d-%Y")
    target_date = prompt_date("Which day", today)
    entries = [item for item in data["entries"] if item["date"] == target_date]
    if not entries:
        print(f"No entries for {target_date}.")
        return
# Views all entries
    list_entries(data, filter_date=target_date)
    total = sum(item["calories"] for item in entries)
    print("=" * 70)
    print(f"Total: {total} calories on {target_date}")
    goal = data.get("daily_goal")
    if goal:
        diff = goal - total
        if diff > 0:
            print(f"You are {diff} calories under your goal of {goal}.")
        elif diff < 0:
            print(f"You are {-diff} calories over your goal of {goal}.")
        else:
            print("You hit your goal exactly today!")
# Daily goal
def set_daily_goal(data):
    response = input("Enter new daily calorie goal (blank to clear): ").strip()
    if not response:
        data["daily_goal"] = None
        save_data(data)
        print("Daily goal cleared.")
        return

    try:
        goal = int(response)
        if goal <= 0:
            raise ValueError
    except ValueError:
        print("Goal must be a positive whole number.")
        return

    data["daily_goal"] = goal
    save_data(data)
    print(f"Daily goal set to {goal} calories.")
# Delete entry
def delete_entry(data):
    if not data["entries"]:
        print("No entries to delete.")
        return

    list_entries(data)
    response = input("Enter the ID of the entry to delete (blank to cancel): ").strip()
    if not response:
        print("Delete cancelled.")
        return

    try:
        target_id = int(response)
    except ValueError:
        print("ID must be a number.")
        return

    for idx, entry in enumerate(data["entries"]):
        if entry["id"] == target_id:
            removed = data["entries"].pop(idx)
            save_data(data)
            print(f"Removed entry {removed['id']} for {removed['meal']} on {removed['date']}.")
            return

    print(f"No entry found with ID {target_id}.")
# Daily goal 
def print_menu(data):
    print("\nCalorie Tracker")
    print("===============")
    goal = data.get("daily_goal")
    if goal:
        print(f"Daily goal: {goal} calories")
    else:
        print("No daily goal set")
    print("1) Add a meal")
    print("2) View a day's summary")
    print("3) List all entries")
    print("4) Set daily goal")
    print("5) Delete an entry")
    print("6) Quit")

# Main menu
def main():
    data = load_data()
    print("Welcome to the calorie tracker. Type the menu number to pick an option.")

    try:
        while True:
            print_menu(data)
            choice = input("Select an option: ").strip()
            if choice == "1":
                add_entry(data)
            elif choice == "2":
                view_daily_summary(data)
            elif choice == "3":
                list_entries(data)
            elif choice == "4":
                set_daily_goal(data)
            elif choice == "5":
                delete_entry(data)
            elif choice in {"6", "q", "quit", "exit"}:
                print("Goodbye! Stay on track!")
                break
            else:
                print("Please choose a valid option from the menu.")
    except KeyboardInterrupt:
        print("\nExiting... Goodbye!")

if __name__ == "__main__":
    main()

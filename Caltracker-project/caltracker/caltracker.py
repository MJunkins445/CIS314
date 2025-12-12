import json
import os
from pathlib import Path
from datetime import date, datetime

import requests
import tkinter as tk
from tkinter import messagebox, ttk

DATA_FILE = Path(__file__).with_name("caltracker_data.json")
DATE_FMT = "%m/%d/%Y"
USDA_SEARCH_URL = "https://api.nal.usda.gov/fdc/v1/foods/search"


def iso_to_display(iso_str: str | None) -> str:
    if not iso_str:
        return ""
    try:
        return datetime.strptime(iso_str, "%Y-%m-%d").strftime(DATE_FMT)
    except ValueError:
        return str(iso_str)


def parse_display_date(text: str) -> str:
    """Convert display date (MM/DD/YYYY) to ISO string."""
    return datetime.strptime(text, DATE_FMT).date().isoformat()


def fetch_usda(query: str) -> dict:
    """
    Look up nutrition data via USDA FoodData Central (macros only).

    Requires env var: USDA_API_KEY.
    """
    api_key = os.getenv("USDA_API_KEY")
    if not api_key:
        raise RuntimeError("USDA API key missing. Set USDA_API_KEY.")

    if not query.strip():
        raise ValueError("Query cannot be empty.")

    params = {
        "query": query,
        "pageSize": 1,
        "pageNumber": 1,
        "dataType": "Foundation,SR Legacy,Branded,Survey (FNDDS)",
        "api_key": api_key,
    }
    try:
        search_resp = requests.get(
            USDA_SEARCH_URL,
            params=params,
            headers={
                "Accept": "application/json",
                "User-Agent": "caltracker/1.0",
                "X-Api-Key": api_key,
            },
            timeout=10,
        )
        search_resp.raise_for_status()
    except requests.HTTPError as exc:
        if search_resp.status_code == 403:
            raise RuntimeError(
                "USDA API rejected the request (403 Forbidden). Verify USDA_API_KEY is set and active, and try again."
            ) from exc
        raise
    payload = search_resp.json()
    foods = payload.get("foods") or []
    if not foods:
        raise ValueError("No foods found for that query.")

    food = foods[0]
    food_name = food.get("description") or query
    nutrients = food.get("foodNutrients") or []

    def get_nutrient(nutrient_id, default=0.0):
        for item in nutrients:
            if item.get("nutrientId") == nutrient_id:
                try:
                    return float(item.get("value") or default)
                except (TypeError, ValueError):
                    return float(default)
        return float(default)

    return {
        "food_name": str(food_name).title(),
        "calories": get_nutrient(1008, 0),  # Energy (kcal)
        "protein_g": get_nutrient(1003, 0),
        "carbs_g": get_nutrient(1005, 0),
        "fat_g": get_nutrient(1004, 0),
        "saturated_fat_g": get_nutrient(1258, 0),
        "sugars_g": get_nutrient(2000, 0),
        "fiber_g": get_nutrient(1079, 0),
        "sodium_mg": get_nutrient(1093, 0),
        "cholesterol_mg": get_nutrient(1253, 0),
    }




def load_data():
    #Load tracker state from disk
    if not DATA_FILE.exists():
        return {"entries": [], "daily_goal": None, "next_id": 1}

    try:
        with DATA_FILE.open("r", encoding="utf-8") as handle:
            raw = json.load(handle)
    except (json.JSONDecodeError, OSError):
        print("Could not read existing data file")
        return {"entries": [], "daily_goal": None, "next_id": 1}

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

    cleaned_entries.sort(key=lambda item: (item["date"], item["id"]))

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


def save_data(data):
    payload = {
        "entries": sorted(data["entries"], key=lambda item: (item["date"], item["id"])),
        "daily_goal": data.get("daily_goal"),
        "next_id": data.get("next_id", 1),
    }
    with DATA_FILE.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2)
        handle.write("\n")


def prompt_date(prompt_text, default_value):
    default_display = iso_to_display(default_value)
    default_hint = f" (default {default_display})" if default_display else ""
    while True:
        response = input(f"{prompt_text}{default_hint}: ").strip()
        if not response:
            return default_value
        try:
            return parse_display_date(response)
        except ValueError:
            print("Please use the MM/DD/YYYY date format.")


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


def add_entry(data):
    today = date.today().isoformat()
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
    print("-" * 50)
    for entry in entries:
        display_date = iso_to_display(entry["date"])
        meal = entry["meal"][:20].ljust(20)
        category = (entry["category"] or "-")[:14].ljust(14)
        notes = (entry["notes"] or "-")
        print(
            f"{entry['id']:>3}  {display_date}  {meal}  {entry['calories']:>4}  {category}  {notes}"
        )


def view_daily_summary(data):
    today_iso = date.today().isoformat()
    target_date = prompt_date("Which day", today_iso)
    entries = [item for item in data["entries"] if item["date"] == target_date]
    if not entries:
        print(f"No entries for {iso_to_display(target_date)}.")
        return

    list_entries(data, filter_date=target_date)
    total = sum(item["calories"] for item in entries)
    print("-" * 50)
    print(f"Total: {total} calories on {iso_to_display(target_date)}")
    goal = data.get("daily_goal")
    if goal:
        diff = goal - total
        if diff > 0:
            print(f"You are {diff} calories under your goal of {goal}.")
        elif diff < 0:
            print(f"You are {-diff} calories over your goal of {goal}.")
        else:
            print("You hit your goal exactly today!")


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

def main():
    """GUI entry point (replaces the old CLI)."""
    gui_main()


# ---------- GUI ----------
PRIMARY = "#2563eb"
PRIMARY_LIGHT = "#3b82f6"
BG = "#0b1224"
CARD_BG = "#11182b"
MUTED = "#cbd5f5"
TEXT = "#e2e8f0"
ACCENT = "#22c55e"


class CalorieTrackerApp:
    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title("CalTracker - Modern UI")
        self.root.configure(bg=BG)
        self.root.geometry("1366x900")
        self.root.minsize(1200, 780)

        self.data = load_data()
        self.selected_id: int | None = None

        self.filter_date_var = tk.StringVar()
        self.goal_var = tk.StringVar(value=str(self.data.get("daily_goal") or ""))
        self.date_var = tk.StringVar(value=iso_to_display(date.today().isoformat()))
        self.meal_var = tk.StringVar()
        self.calories_var = tk.StringVar()
        self.category_var = tk.StringVar()
        self.notes_var = tk.StringVar()
        self.lookup_var = tk.StringVar()
        self.lookup_info_var = tk.StringVar(value="")

        self._configure_styles()
        self._build_layout()
        self._refresh_table()
        self._update_summary()

    def _configure_styles(self) -> None:
        style = ttk.Style(self.root)
        style.theme_use("clam")

        style.configure("TFrame", background=BG, borderwidth=0)
        style.configure("Card.TFrame", background=CARD_BG, relief="flat", borderwidth=0)
        style.configure("TLabel", background=BG, foreground=TEXT, font=("Segoe UI", 11))
        style.configure(
            "Card.TLabel", background=CARD_BG, foreground=TEXT, font=("Segoe UI", 11)
        )
        style.configure(
            "Heading.TLabel",
            background=BG,
            foreground=TEXT,
            font=("Segoe UI Semibold", 22),
        )
        style.configure(
            "Accent.TButton",
            background=PRIMARY,
            foreground="white",
            font=("Segoe UI Semibold", 11),
            padding=(14, 8),
            borderwidth=0,
        )
        style.map("Accent.TButton", background=[("active", PRIMARY_LIGHT)])
        style.configure(
            "Ghost.TButton",
            background=CARD_BG,
            foreground=TEXT,
            font=("Segoe UI", 10),
            padding=(10, 6),
            borderwidth=0,
        )
        style.map("Ghost.TButton", background=[("active", "#1e2538")])
        style.configure(
            "TEntry",
            fieldbackground=CARD_BG,
            background=CARD_BG,
            foreground=TEXT,
            bordercolor="#1f2937",
            relief="flat",
            padding=8,
            insertcolor=TEXT,
            font=("Segoe UI", 11),
        )
        style.configure(
            "Treeview",
            background=CARD_BG,
            foreground=TEXT,
            fieldbackground=CARD_BG,
            rowheight=30,
            bordercolor=BG,
            highlightthickness=0,
        )
        style.map(
            "Treeview",
            background=[("selected", PRIMARY)],
            foreground=[("selected", "white")],
        )
        style.configure(
            "Horizontal.TProgressbar",
            background=PRIMARY,
            troughcolor="#0f172a",
            bordercolor=CARD_BG,
            thickness=14,
        )

    def _build_layout(self) -> None:
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(2, weight=1)

        header = ttk.Frame(self.root, padding=(20, 18, 20, 10))
        header.grid(row=0, column=0, sticky="ew")
        ttk.Label(header, text="Calorie Dashboard", style="Heading.TLabel").grid(
            row=0, column=0, sticky="w"
        )
        ttk.Label(
            header,
            text="Track meals, stay on goal, and keep a clean history.",
            foreground=MUTED,
        ).grid(row=1, column=0, sticky="w")

        cards = ttk.Frame(self.root, padding=(20, 0, 20, 10))
        cards.grid(row=1, column=0, sticky="ew")
        cards.columnconfigure((0, 1, 2), weight=1, uniform="card")
        self.summary_card = self._build_summary_card(cards)
        self.form_card = self._build_form_card(cards)
        self.goal_card = self._build_goal_card(cards)

        table_frame = ttk.Frame(self.root, padding=(20, 10, 20, 20))
        table_frame.grid(row=2, column=0, sticky="nsew")
        table_frame.columnconfigure(0, weight=1)
        table_frame.rowconfigure(1, weight=1)
        self._build_table(table_frame)

    def _build_summary_card(self, parent: ttk.Frame) -> ttk.Frame:
        card = ttk.Frame(parent, style="Card.TFrame", padding=16)
        card.grid(row=0, column=0, sticky="nsew", padx=(0, 12))
        ttk.Label(card, text="Today / Filtered day", style="Card.TLabel").grid(
            row=0, column=0, sticky="w"
        )
        self.total_label = ttk.Label(
            card, text="Total: 0 cal", style="Card.TLabel", font=("Segoe UI", 14, "bold")
        )
        self.total_label.grid(row=1, column=0, sticky="w", pady=(6, 0))

        self.goal_hint = ttk.Label(card, text="No daily goal set", foreground=MUTED, style="Card.TLabel")
        self.goal_hint.grid(row=2, column=0, sticky="w", pady=(2, 10))

        self.progress = ttk.Progressbar(
            card,
            style="Horizontal.TProgressbar",
            orient="horizontal",
            mode="determinate",
            maximum=1,
            value=0,
            length=320,
        )
        self.progress.grid(row=3, column=0, sticky="ew", pady=(8, 6))

        self.progress_caption = ttk.Label(
            card, text="", style="Card.TLabel", foreground=MUTED
        )
        self.progress_caption.grid(row=4, column=0, sticky="w")
        return card

    def _build_form_card(self, parent: ttk.Frame) -> ttk.Frame:
        card = ttk.Frame(parent, style="Card.TFrame", padding=16)
        card.grid(row=0, column=1, sticky="nsew", padx=12)
        ttk.Label(card, text="Add a meal", style="Card.TLabel").grid(
            row=0, column=0, sticky="w"
        )

        lookup_row = ttk.Frame(card, style="Card.TFrame")
        lookup_row.grid(row=1, column=0, sticky="ew", pady=(8, 2))
        lookup_row.columnconfigure(0, weight=1)
        ttk.Label(lookup_row, text="Lookup food (USDA)", style="Card.TLabel").grid(
            row=0, column=0, sticky="w"
        )
        lookup_entry = ttk.Entry(lookup_row, textvariable=self.lookup_var)
        lookup_entry.grid(row=1, column=0, sticky="ew", pady=(4, 0), padx=(0, 8))
        ttk.Button(
            lookup_row, text="Fetch macros", style="Ghost.TButton", command=self._lookup_food
        ).grid(row=1, column=1, sticky="ew")

        self.lookup_info_label = ttk.Label(
            card,
            textvariable=self.lookup_info_var,
            style="Card.TLabel",
            foreground=MUTED,
            wraplength=420,
        )
        self.lookup_info_label.grid(row=2, column=0, sticky="w", pady=(2, 6))

        form = ttk.Frame(card, style="Card.TFrame")
        form.grid(row=3, column=0, sticky="nsew", pady=(8, 0))
        for i in range(2):
            form.columnconfigure(i, weight=1, uniform="form")

        self._labeled_entry(form, "Date (MM/DD/YYYY)", self.date_var, 0, 0)
        self._labeled_entry(form, "Calories", self.calories_var, 0, 1)
        self._labeled_entry(form, "Meal", self.meal_var, 1, 0, colspan=2)
        self._labeled_entry(form, "Category", self.category_var, 2, 0)
        self._labeled_entry(form, "Notes", self.notes_var, 2, 1)

        add_btn = ttk.Button(form, text="Add entry", style="Accent.TButton", command=self._add_entry)
        add_btn.grid(row=6, column=0, columnspan=2, sticky="ew", pady=(14, 0))
        return card

    def _build_goal_card(self, parent: ttk.Frame) -> ttk.Frame:
        card = ttk.Frame(parent, style="Card.TFrame", padding=16)
        card.grid(row=0, column=2, sticky="nsew", padx=(12, 0))
        ttk.Label(card, text="Daily goal", style="Card.TLabel").grid(
            row=0, column=0, sticky="w"
        )
        goal_entry = ttk.Entry(card, textvariable=self.goal_var, width=12)
        goal_entry.grid(row=1, column=0, sticky="ew", pady=(8, 4))
        ttk.Label(card, text="Calories per day", foreground=MUTED, style="Card.TLabel").grid(
            row=2, column=0, sticky="w"
        )
        buttons = ttk.Frame(card, style="Card.TFrame")
        buttons.grid(row=3, column=0, sticky="ew", pady=(10, 0))
        buttons.columnconfigure((0, 1), weight=1)
        ttk.Button(
            buttons, text="Save goal", style="Accent.TButton", command=self._set_goal
        ).grid(row=0, column=0, sticky="ew", padx=(0, 6))
        ttk.Button(
            buttons, text="Clear", style="Ghost.TButton", command=self._clear_goal
        ).grid(row=0, column=1, sticky="ew", padx=(6, 0))
        return card

    def _build_table(self, parent: ttk.Frame) -> None:
        filter_row = ttk.Frame(parent, padding=(0, 0, 0, 10))
        filter_row.grid(row=0, column=0, sticky="ew")
        filter_row.columnconfigure(0, weight=1)

        ttk.Label(filter_row, text="Filter by date (MM/DD/YYYY)", foreground=MUTED).grid(
            row=0, column=0, sticky="w"
        )
        filter_entry = ttk.Entry(
            filter_row, textvariable=self.filter_date_var, width=16
        )
        filter_entry.grid(row=1, column=0, sticky="w", pady=(4, 0))
        filter_entry.bind("<KeyRelease>", lambda _: self._apply_filter())

        ttk.Button(
            filter_row,
            text="Clear filter",
            style="Ghost.TButton",
            command=self._clear_filter,
        ).grid(row=1, column=1, sticky="e", padx=(10, 0))

        columns = ("id", "date", "meal", "calories", "category", "notes")
        self.tree = ttk.Treeview(
            parent,
            columns=columns,
            show="headings",
            selectmode="browse",
        )
        self.tree.grid(row=1, column=0, sticky="nsew")
        parent.grid_rowconfigure(1, weight=1)

        headings = {
            "id": "ID",
            "date": "Date",
            "meal": "Meal",
            "calories": "Calories",
            "category": "Category",
            "notes": "Notes",
        }
        widths = {
            "id": 80,
            "date": 150,
            "meal": 320,
            "calories": 120,
            "category": 180,
            "notes": 480,
        }
        for col in columns:
            self.tree.heading(col, text=headings[col])
            self.tree.column(col, width=widths[col], anchor="w")

        self.tree.bind("<<TreeviewSelect>>", self._on_select)

        actions = ttk.Frame(parent, padding=(0, 10, 0, 0))
        actions.grid(row=2, column=0, sticky="ew")
        ttk.Button(
            actions,
            text="Delete selected",
            style="Ghost.TButton",
            command=self._delete_selected,
        ).grid(row=0, column=0, sticky="w")

        scrollbar = ttk.Scrollbar(parent, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)
        scrollbar.grid(row=1, column=1, sticky="ns")

    def _labeled_entry(
        self,
        parent: ttk.Frame,
        label: str,
        variable: tk.StringVar,
        row: int,
        column: int,
        colspan: int = 1,
    ) -> None:
        ttk.Label(parent, text=label, style="Card.TLabel").grid(
            row=row * 2, column=column, columnspan=colspan, sticky="w", pady=(0, 2)
        )
        entry = ttk.Entry(parent, textvariable=variable)
        entry.grid(
            row=row * 2 + 1,
            column=column,
            columnspan=colspan,
            sticky="ew",
            padx=(0, 10),
            pady=(0, 8),
        )
        for col_idx in range(column, column + colspan):
            parent.grid_columnconfigure(col_idx, weight=1, uniform="form")

    def _add_entry(self) -> None:
        try:
            entry_date = parse_display_date(self.date_var.get().strip())
        except ValueError:
            messagebox.showerror("Invalid date", "Please use MM/DD/YYYY for the date.")
            return

        meal = self.meal_var.get().strip() or "Meal"
        try:
            calories = int(self.calories_var.get())
            if calories <= 0:
                raise ValueError
        except ValueError:
            messagebox.showerror("Invalid calories", "Calories must be a positive whole number.")
            return

        entry = {
            "id": self.data["next_id"],
            "date": entry_date,
            "meal": meal,
            "calories": calories,
            "category": self.category_var.get().strip(),
            "notes": self.notes_var.get().strip(),
        }
        self.data["entries"].append(entry)
        self.data["next_id"] += 1
        save_data(self.data)

        self.meal_var.set("")
        self.calories_var.set("")
        self.category_var.set("")
        self.notes_var.set("")
        self.date_var.set(iso_to_display(entry_date))

        self._refresh_table()
        self._update_summary()
        messagebox.showinfo("Added", f"Logged {calories} calories for {meal}.")

    def _lookup_food(self) -> None:
        query = self.lookup_var.get().strip() or self.meal_var.get().strip()
        if not query:
            messagebox.showinfo("Enter food", "Type a food name to look up.")
            return
        try:
            result = fetch_usda(query)
        except Exception as exc:
            self.lookup_info_var.set(str(exc))
            messagebox.showerror("Lookup failed", str(exc))
            return

        calories = int(round(result["calories"]))
        self.calories_var.set(str(calories))
        if not self.meal_var.get().strip():
            self.meal_var.set(result["food_name"])

        macro_text = (
            f"{result['food_name']} • {calories} kcal | "
            f"P {result['protein_g']:.1f}g | "
            f"C {result['carbs_g']:.1f}g | "
            f"F {result['fat_g']:.1f}g | "
            f"Na {int(round(result['sodium_mg']))} mg"
        )
        self.lookup_info_var.set(macro_text)
        if not self.notes_var.get().strip():
            self.notes_var.set(macro_text)

    def _delete_selected(self) -> None:
        if self.selected_id is None:
            messagebox.showinfo("Select an entry", "Pick a row to delete.")
            return

        confirm = messagebox.askyesno(
            "Delete entry", "Delete this entry permanently?"
        )
        if not confirm:
            return

        self.data["entries"] = [
            item for item in self.data["entries"] if item["id"] != self.selected_id
        ]
        save_data(self.data)
        self.selected_id = None
        self._refresh_table()
        self._update_summary()

    def _set_goal(self) -> None:
        value = self.goal_var.get().strip()
        if not value:
            self._clear_goal()
            return
        try:
            goal = int(value)
            if goal <= 0:
                raise ValueError
        except ValueError:
            messagebox.showerror("Invalid goal", "Goal must be a positive whole number.")
            return
        self.data["daily_goal"] = goal
        save_data(self.data)
        self._update_summary()

    def _clear_goal(self) -> None:
        self.goal_var.set("")
        self.data["daily_goal"] = None
        save_data(self.data)
        self._update_summary()

    def _apply_filter(self) -> None:
        self._refresh_table()
        self._update_summary()

    def _clear_filter(self) -> None:
        self.filter_date_var.set("")
        self._refresh_table()
        self._update_summary()

    def _on_select(self, _event: object) -> None:
        selected = self.tree.selection()
        if not selected:
            self.selected_id = None
            return
        item_id = int(selected[0])
        self.selected_id = item_id

    def _refresh_table(self) -> None:
        for row in self.tree.get_children():
            self.tree.delete(row)

        filter_text = self.filter_date_var.get().strip()
        filter_iso = None
        if filter_text:
            try:
                filter_iso = parse_display_date(filter_text)
            except ValueError:
                filter_iso = None

        entries = sorted(self.data["entries"], key=lambda item: (item["date"], item["id"]))
        if filter_text:
            if filter_iso:
                entries = [item for item in entries if item["date"] == filter_iso]
            else:
                entries = []

        for entry in entries:
            display_date = iso_to_display(entry["date"])
            self.tree.insert(
                "",
                "end",
                iid=entry["id"],
                values=(
                    entry["id"],
                    display_date,
                    entry["meal"],
                    entry["calories"],
                    entry.get("category") or "-",
                    entry.get("notes") or "-",
                ),
            )

    def _update_summary(self) -> None:
        filter_text = self.filter_date_var.get().strip()
        if filter_text:
            try:
                target_iso = parse_display_date(filter_text)
                display_date = filter_text
            except ValueError:
                target_iso = None
                display_date = "Invalid date"
        else:
            target_iso = date.today().isoformat()
            display_date = iso_to_display(target_iso)

        entries = [item for item in self.data["entries"] if target_iso and item["date"] == target_iso] if target_iso else []
        total = sum(item["calories"] for item in entries)
        self.total_label.configure(text=f"Total: {total} cal on {display_date}")

        goal = self.data.get("daily_goal")
        if goal:
            self.goal_hint.configure(text=f"Goal: {goal} cal/day", foreground=MUTED)
            progress_value = min(total / goal, 1.0)
            self.progress.configure(value=progress_value, maximum=1.0)
            diff = goal - total
            if diff > 0:
                caption = f"{diff} cal remaining"
                color = ACCENT
            elif diff < 0:
                caption = f"{-diff} cal over"
                color = "#f97316"
            else:
                caption = "Goal met today"
                color = ACCENT
            self.progress_caption.configure(text=caption, foreground=color)
        else:
            self.goal_hint.configure(text="No daily goal set", foreground=MUTED)
            self.progress.configure(value=0, maximum=1.0)
            self.progress_caption.configure(text="Set a goal to track progress", foreground=MUTED)

    def run(self) -> None:
        self.root.mainloop()


def gui_main() -> None:
    root = tk.Tk()
    app = CalorieTrackerApp(root)
    app.run()


if __name__ == "__main__":
    gui_main()

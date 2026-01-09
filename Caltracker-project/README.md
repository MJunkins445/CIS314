# Caltracker

Caltracker is calorie tracking application with a GUI.

It lets you:

- Add meal entries with calories, category, and notes  
- View a daily summary and total calories  
- Set a daily calorie goal  
- List and delete entries  

GUI:
- Launch the Tkinter dashboard with `python -m caltracker.caltracker` (or `caltracker` / `caltracker-ui` if installed as scripts). WHEN USING VERSION WITH API USE $env:USDA_API_KEY = "tfsDLA94751nrGNQHSiiyVeBNwMRG8rxEgOTqD72"
python -m caltracker.caltracker
- Nutrition lookup (USDA FoodData Central): set `USDA_API_KEY` env var, then use the "Fetch macros" control to autofill calories and see macros (carbs, protein, fat, sodium, etc.).


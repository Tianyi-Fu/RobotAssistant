# README

This project implements a **virtual home assistant** that leverages ASP (Answer Set Programming) for automated planning and an LLM (Large Language Model) for high-level command generation. The system allows a user to specify a desired goal state in ASP syntax (e.g., `has(user, milk)`) along with a natural-language command (e.g., “give me the milk”), and then produces and executes a predicted plan in a simulated environment.

---

## Directory Structure

project-root/ ├─ asp/ │ ├─ goals.py # Functions to add user or predicted goals, run solver │ ├─ file_manager.py # Code for reading/writing ASP files and initial conditions │ ├─ revert_predicted_goal.py │ └─ solution_finder.py # SPARC or solver invocation ├─ commands/ │ └─ processor.py # LLM prompt/response logic, user feedback loop ├─ config/ │ └─ config.py # Paths to files, environment config, ASP file name ├─ kg/ │ ├─ context_analysis.py # Retrieve top contexts & items from knowledge graph │ ├─ history_analyzer.py # Analyze user’s command history, find similar lines │ ├─ history_manager.py # Load/append user history lines, skip lines without '|' │ ├─ kg_updater.py # Merges solver results into the knowledge graph │ └─ loader.py # RDFLib graph loading, EX namespace ├─ simulation/ │ ├─ handler.py # Unity simulator invocation │ └─ unity_simulator/... ├─ main.py # Main loop with multi-round user input, predicted goal acceptance ├─ requirements.txt # Python dependencies └─ README.md # This readme

yaml
Copy

---

## Setup and Installation

1. **Create** a Python virtual environment (optional but recommended):
   ```bash
   python -m venv venv
   source venv/bin/activate  # Linux/macOS
   # or venv\Scripts\activate on Windows
Install dependencies:

bash
Copy
pip install -r requirements.txt
Make sure you have any needed dependencies for nltk, rdflib, your LLM, etc.

Configuration:

In config/config.py, confirm or adjust paths like LIVINGROOM_TTL, SPARC_JAR_PATH, ENABLE_SIMULATOR, etc.
Usage
1) Reset or Keep Existing History
If you have a backup file, you can restore with:
bash
Copy
python -c "from kg.history_manager import reset_history_from_backup; reset_history_from_backup()"
Otherwise, ensure your existing user_history.txt lines have a valid format:
pgsql
Copy
has(user, milk) | give me the milk
switched_on(tablelamp) | turn on the table lamp
so that each line has a pipe | dividing the ASP predicate from the user text.
2) Run main.py
bash
Copy
python main.py
It will prompt:

Test ID: a string identifying the current run, creating a subfolder for round logs (like test_1).
Goal condition (ASP style): e.g. has(user, book)
Your natural command: e.g. give me the book
This repeats for 5 rounds.

3) Observing Each Round
The system loads the knowledge graph, extracts initial conditions, and inserts them into your ASP file.
It executes your user’s goal in ASP, e.g. goal_1(I) :- holds(has(user, book), I).
It consults the user’s history for a possible next step, or calls the LLM for a predicted next step if no exact match is found.
If the user accepts the predicted goal, it merges it into the ASP, runs the solver, updates the knowledge graph, and optionally simulates the commands in a Unity environment (if ENABLE_SIMULATOR=True).
You can revert the predicted goal if you don’t want it.
4) Where Are Logs Stored?
A subfolder named after your “Test ID” (e.g. test_1) is created to store round logs if you added code to do so in main.py.
The user history is appended to user_history.txt, with lines like:
java
Copy
has(user, bananas) | give me the bananas
switched_on(tablelamp) | PredictedGoalExecuted
Common Format for History Lines
Each line in user_history.txt looks like:

less
Copy
[ASP_Predicate] | [Natural Text or Action]
For example:

sql
Copy
open(fridge) | open the fridge
has(user, magazine) | give me the magazine
No lines that lack a pipe (|) are loaded for the LLM, and lines like === New Session === are purely markers and ignored by code.

Example Flow
Round 1:

User inputs:
ASP goal: has(user, plate)
Natural command: “give me the plate”
The system records has(user, plate) | give me the plate.
If accepted, it merges into the ASP, runs solver, updates KG, etc.
Round 2:

User might do:
ASP goal: open(microwave)
Natural command: “open microwave”
The system tries to guess next step from history, e.g. “put milk in microwave.” The user can accept or reject with feedback (“no, close fridge”), etc.
Troubleshooting
Lines Not Being Loaded?
Make sure each line in user_history.txt has a pipe |. The function load_user_history() ignores lines without it.

Regex or Parse Errors
If you see confusion with “switchon tablelamp,” note that you must store a valid ASP predicate like switched_on(tablelamp) on the left side, not just “switchon tablelamp.”

“Too many values to unpack”
Ensure the return values of process_command(...) match how many variables you capture. If you only want 4, but the function returns 8, either remove the extras or use placeholders.

Simulator Not Starting
If ENABLE_SIMULATOR = True but Unity fails to launch, double-check the path to your Unity build in UNITY_EXEC_PATH, or set ENABLE_SIMULATOR = False if you do not need it.

Contributing
Feel free to open pull requests for new features or actions.
For major changes, please open an issue to discuss.
License
This project is provided under [Your Preferred License]. See LICENSE for details.

pgsql
Copy

---

### How to Use

1. **Copy** the above text (between the triple backticks) and **paste** it into a new file named `README.md` in your project root (or open in VSCode).
2. Adjust any references (like `Your Preferred License`, or mention your actual file paths).
3. Commit it to your repository.  

You’ll now have a full readme explaining your system and how to run it.





You said:

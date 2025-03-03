# asp/solution_finder.py
import subprocess
from config.config import SPARC_JAR_PATH, ASP_FILE

def run_sparc_solution_finder(display_predicates=None):
    if display_predicates is None:

        display_predicates = ["occurs","show_operated_holds_name","show_changed_holds","show_changed_holds_name","show_start_holds","show_last_holds"]

    try:

        import os
        os.environ["DISPLAY_PREDICATES"] = ",".join(display_predicates)

        command = f"python asp_solution_finder_runner.py"
        subprocess.run(command, shell=True, check=True)
    except subprocess.CalledProcessError as e:
        print(f"Error running ASP solution finder: {e}")
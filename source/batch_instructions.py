from asp.file_manager import (
    remove_initial_conditions_from_asp,
    insert_initial_conditions_to_asp,
    extract_initial_conditions,
    clean_existing_goals_and_success,
    add_goal_to_asp_file,
)
from asp.solution_finder import run_sparc_solution_finder
from kg.kg_updater import revert_kg_to_backup, update_kg_from_asp_outputs
from config.config import OCCURS_OUTPUT
import time



def batch_run_instructions():
    instructions = [
        "on(coffeetable, magazine)",
        "on(sofa, waterglass)",
    "has(user, alcohol)",
    "open(microwave)"
    ]


    print("These are the 5 instructions to be executed:")
    for idx, instr in enumerate(instructions, start=1):
        print(f"{idx}. {instr}")
    print("\nStarting execution...\n")

    revert_kg_to_backup()

    start = time.time()
    for idx, instr in enumerate(instructions, start=1):
        print(f"========== Executing instruction {idx}: {instr} ==========")




        remove_initial_conditions_from_asp()
        extract_initial_conditions()
        insert_initial_conditions_to_asp()


        clean_existing_goals_and_success()


        add_goal_to_asp_file(instr)


        display_predicates = [
            "occurs",
            "show_operated_holds_name",
            "show_changed_holds",
            "show_changed_holds_name",
            "show_start_holds",
            "show_last_holds"
        ]
        run_sparc_solution_finder(display_predicates=display_predicates)


        update_kg_from_asp_outputs(
            start_holds_file="show_start_holds_output.txt",
            last_holds_file="show_last_holds_output.txt",
            changed_holds_file="show_changed_holds_output.txt",
            changed_names_file="show_changed_holds_name_output.txt"
        )


        #     script = process_events_and_simulate(OCCURS_OUTPUT)
        #     print("\nSimulator script:")
        #     for line in script:
        #         print(line)


        print(f"---------- Finished instruction {idx} ----------\n")


    end = time.time()
    print(f"Completed in {end-start} seconds.")


if __name__ == "__main__":
    batch_run_instructions()
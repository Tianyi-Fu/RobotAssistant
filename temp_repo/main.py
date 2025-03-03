import os
import sys
import time
import io
import re
import contextlib
from datetime import datetime

from kg.loader import g
from config.config import (
    LIVINGROOM_TTL,
    OCCURS_OUTPUT,
    UNITY_OUTPUT_PATH,
    ENABLE_SIMULATOR,
    HISTORY_FILE
)
from kg.kg_updater import revert_kg_to_backup, update_kg_from_asp_outputs
from kg.context_analysis import get_results
from kg.history_analyzer import analyze_and_predict_next
from asp.goals import execute_user_goal, execute_predicted_goal
from asp.file_manager import (
    extract_initial_conditions,
    insert_initial_conditions_to_asp,
    remove_initial_conditions_from_asp
)
from kg.history_manager import append_to_history, reset_history_from_backup
from commands.processor import process_command
from simulation.handler import process_events_and_simulate, simulator_instance
from simulation.unity_simulator.utils_viz import generate_video
from asp.revert_predicted_goal import revert_predicted_goal_full

class Tee:
    def __init__(self, *targets):
        self.targets = targets
    def write(self, data):
        for t in self.targets:
            t.write(data)
    def flush(self):
        for t in self.targets:
            t.flush()

def refresh_initial_conditions():
    extract_initial_conditions()
    remove_initial_conditions_from_asp()
    insert_initial_conditions_to_asp()
    print("[INFO] Initial conditions updated in ASP with new KG states.\n")

def read_occurs_output():
    if os.path.exists(OCCURS_OUTPUT):
        with open(OCCURS_OUTPUT, "r", encoding="utf-8") as f:
            return f.read().strip()
    return "No occurs output available."

def log_run_info(user_goal, user_command, llm_attempt_logs, final_asp_goal, asp_solver_logs, occurs_output, llm_time, sim_time, alt_pred_count, alt_obj_count, substitution_log):
    predicted_cmds = "\n".join(
        line for line in llm_attempt_logs.splitlines() if line.strip().startswith("Predicted Command:")
    )
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    substitution_str = "\n".join(substitution_log) if substitution_log else "None"
    log_entry = f"""
==================== {timestamp} ====================
User-entered goal: {user_goal}
User-entered command: {user_command}

LLM Prediction Attempts (only predicted commands):
{predicted_cmds}

LLM Prediction Time (excluding user wait): {llm_time:.2f} seconds
Simulator Execution Time: {sim_time:.2f} seconds
Alternative predicate calls: {alt_pred_count}
Alternative object calls: {alt_obj_count}
KG Substitution Log:
{substitution_str}

Final ASP execution command: {final_asp_goal}

SPARC Solver Output:
{asp_solver_logs}

OCCURS Output:
{occurs_output}
======================================================
"""
    with open("execution_log.txt", "a", encoding="utf-8") as log_file:
        log_file.write(log_entry)

def main_loop():
    previous_command = None
    first_command = True
    round_count = 0

    while round_count < 5:
        round_count += 1
        print(f"\n========== ROUND {round_count} ==============")

        g.parse(LIVINGROOM_TTL, format="turtle")

        extract_initial_conditions()

        user_goal = input("Enter the goal condition (e.g., has(user, book)) or 'exit' to quit: ").strip()
        if user_goal.lower() == 'exit':
            print("Exiting the program.")
            break
        user_command = input("Enter your command (e.g., give me the book): ").strip()
        if user_command.lower() == 'exit':
            print("Exiting the program.")
            break
        append_to_history(user_goal, user_command)

        remove_initial_conditions_from_asp()
        insert_initial_conditions_to_asp()

        execute_user_goal(user_goal)

        top_context, top_items = get_results()
        print(f"Top Context: {top_context}")
        print(f"Top Items: {top_items}")

        predicted_history_command, context_info = analyze_and_predict_next(user_goal)
        if predicted_history_command is None:
            print("[INFO] No suitable prediction from history. Let LLM guess next step.")
        else:
            print(f"[INFO] Predicted next command based on history: {predicted_history_command}")
            print(f"[INFO] Context info from KG (expanded items): {context_info}")

        merged_top_items = top_items
        if "expanded" in context_info:
            if isinstance(merged_top_items, list):
                print("Expanded keys:", list(context_info["expanded"].keys()))
            elif isinstance(merged_top_items, dict):
                merged_top_items.update(context_info["expanded"])
        potential_contexts = [top_context] if top_context else []

        llm_start_time = time.time()
        old_stdout = sys.stdout
        pc_buffer = io.StringIO()
        sys.stdout = Tee(old_stdout, pc_buffer)
        try:
            (predicted_command,
             asp_goal,
             reason,
             goals,
             llm_regenerations,
             kg_substitutions,
             user_feedback_count,
             user_feedback_content,
             llm_processing_time,
             alt_pred_count,
             alt_obj_count,
             substitution_log) = process_command(
                user_command=user_command,
                previous_command=previous_command,
                first_command=first_command,
                potential_contexts=potential_contexts,
                top_items=merged_top_items,
                history_suggestion=predicted_history_command,
                context_expanded_info=context_info
            )
        finally:
            sys.stdout = old_stdout
        llm_attempt_logs = pc_buffer.getvalue()

        print(f"\nCurrent Command: {user_command}")
        print(f"Predicted Command: {predicted_command}")
        print(f"ASP goals: {asp_goal}")

        asp_solver_logs = ""
        if asp_goal:
            asp_buffer = io.StringIO()
            with contextlib.redirect_stdout(asp_buffer), contextlib.redirect_stderr(asp_buffer):
                _ = execute_predicted_goal(asp_goal)
            asp_solver_logs = asp_buffer.getvalue()

            print("\n[INFO] Executing PredictedGoal actions in simulator...")
            sim_start_time = time.time()
            try:
                script = process_events_and_simulate(OCCURS_OUTPUT)
                sim_elapsed_time = time.time() - sim_start_time
                print("\nGenerated Script for PredictedGoal:")
                for line in script:
                    print(line)
                print("\nSimulation of PredictedGoal completed successfully.")
            except Exception as e:
                sim_elapsed_time = 0
                print(f"Error during simulation of PredictedGoal: {e}")

            print("\n[INFO] Updating KG from PredictedGoal solution results...")
            show_start_file = "show_start_holds_output.txt"
            show_last_file = "show_last_holds_output.txt"
            show_changed_file = "show_changed_holds_output.txt"
            update_kg_from_asp_outputs(
                start_holds_file=show_start_file,
                last_holds_file=show_last_file,
                changed_holds_file=show_changed_file
            )
            print("[INFO] KG updated after PredictedGoal.\n")

            refresh_initial_conditions()

            revert_decision = input("\nDo you want to revert the predicted goal? (yes/no): ").strip().lower()
            if revert_decision not in ("yes", "no"):
                revert_decision = "no"
            if revert_decision == "yes":
                print("[INFO] Reverting predicted goal...")
                revert_predicted_goal_full(
                    user_changed_file="show_changed_holds_output_user.txt",
                    predicted_changed_file="show_changed_holds_output_predicted.txt",
                    start_holds_file="show_start_holds_output.txt",
                    occurs_file="occurs_output.txt"
                )
                try:
                    script = process_events_and_simulate("occurs_output.txt")
                    print("[INFO] Simulation after revert completed.")
                except Exception as e:
                    print(f"Error simulating after revert: {e}")
                print("\n[INFO] Re-extracting initial conditions from updated KG (after Revert).")
                refresh_initial_conditions()
                print("[INFO] Predicted goal has been reverted.")
            else:
                print("[INFO] Predicted goal accepted, adding to history.")
                append_to_history(predicted_command, "PredictedGoalExecuted")
        else:
            print("No valid ASP Goal to execute.")
            sim_elapsed_time = 0

        remove_initial_conditions_from_asp()
        print("\nSimulation step skipped as simulation was already handled during PredictedGoal execution/revert.")

        
        output_dir = "output"
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
        print("\nStarting video generation...")
        try:
            
            generate_video(input_path=UNITY_OUTPUT_PATH, prefix='test', output_path=output_dir)
           
            original_video = os.path.join(output_dir, "test_video.mp4")
            if os.path.exists(original_video):
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                new_video = os.path.join(output_dir, f"video_{timestamp}.mp4")
                os.rename(original_video, new_video)
                print(f"Video generation completed successfully. Video saved as: {new_video}")
            else:
                print("Video file not found after generation.")
        except Exception as e:
            print(f"Video generation failed: {e}")

        occurs_output = read_occurs_output()

        log_run_info(user_goal, user_command, llm_attempt_logs, asp_goal, asp_solver_logs, occurs_output, llm_processing_time, sim_elapsed_time, alt_pred_count, alt_obj_count, substitution_log)

        previous_command = user_command
        first_command = False

    print("\n[INFO] Reached preset number of rounds or exit => Program terminated.")

if __name__ == "__main__":
    revert_kg_to_backup()
    reset_history_from_backup()

    if os.path.exists(HISTORY_FILE):
        with open(HISTORY_FILE, 'a', encoding='utf-8') as f:
            f.write("\n\n=== New Session ===\n")

    if ENABLE_SIMULATOR:
        try:
            simulator = simulator_instance
            print("Simulator is enabled and initialized.")
        except Exception as e:
            print(f"Failed to initialize simulator: {e}")
            print("Proceeding without simulator.")
            simulator = None
    else:
        simulator = None
        print("Simulator is disabled via configuration.")

    main_loop()

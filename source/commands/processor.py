import os
import sys
import time
import json
import re
import platform
from threading import Thread

if os.name == 'nt':
    import msvcrt
else:
    import select
    import tty
    import termios

from llm.utils import generate_prompt_for_goals, predict_next_action, extract_response_details
from kg.checker import (
    check_predicate_in_kg, get_expected_object_type, check_object_in_kg,
    check_action_in_kg, get_available_actions
)
from kg.alternative_finder import find_alternative_object, find_alternative_action, find_alternative_predicate
from asp.file_manager import read_asp_file, write_asp_file
from config.config import COMMAND_INFO_JSON

ALTERNATIVE_PREDICATE_COUNT = 0
ALTERNATIVE_OBJECT_COUNT = 0

class TimeoutOccurred(Exception):
    pass

def input_with_timeout(prompt, timeout):
    print(prompt, end='', flush=True)
    current_os = platform.system()
    if current_os == 'Windows':
        return _windows_input_with_timeout(timeout)
    else:
        return _unix_input_with_timeout(timeout)

def _windows_input_with_timeout(timeout):
    start_time = time.time()
    user_input = ''
    while True:
        if msvcrt.kbhit():
            char = msvcrt.getwche()
            if char in ('\r', '\n'):
                return user_input
            elif char == '\b':
                user_input = user_input[:-1]
            else:
                user_input += char
        if time.time() - start_time > timeout:
            raise TimeoutOccurred
        time.sleep(0.05)

def _unix_input_with_timeout(timeout):
    fd = sys.stdin.fileno()
    old_settings = termios.tcgetattr(fd)
    try:
        tty.setcbreak(fd)
        start_time = time.time()
        user_input = ''
        while True:
            dr, dw, de = select.select([sys.stdin], [], [], 0)
            if dr:
                char = sys.stdin.read(1)
                if char in ('\n', '\r'):
                    return user_input
                elif char == '\x7f':
                    user_input = user_input[:-1]
                else:
                    user_input += char
                    print(char, end='', flush=True)
            if time.time() - start_time > timeout:
                raise TimeoutOccurred
            time.sleep(0.05)
    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)

def parse_goal(goal):
    match = re.match(r"(\w+)\(([^,]+),\s*([^)]+)\)", goal)
    if match:
        predicate = match.group(1).strip()
        arg1 = match.group(2).strip()
        arg2 = match.group(3).strip()
        return predicate, arg1, arg2
    else:
        match = re.match(r"(\w+)\(([^)]+)\)", goal)
        if match:
            predicate = match.group(1).strip()
            arg1 = match.group(2).strip()
            return predicate, arg1, None
        else:
            return None, None, None

def enforce_allowed_predicates(goals, potential_contexts=None):
    inside_furniture = {"bookshelf", "fridge", "microwave"}
    on_furniture = {"sofa", "kitchentable", "desk", "kitchencounter", "coffeetable", "dishbowl", "tvstand", "amplifier", "desk_1"}
    new_goals = []
    for g in goals:
        m_in = re.match(r"in\(([^,]+),\s*([^)]+)\)", g)
        if m_in:
            item = m_in.group(1).strip()
            furn = m_in.group(2).strip()
            new_pred = "inside"
            if furn.lower() in on_furniture:
                new_pred = "on"
            new_goal = f"{new_pred}({furn}, {item})"
            print(f"Converting goal '{g}' to '{new_goal}' because 'in' is not allowed.")
            new_goals.append(new_goal)
            continue

        m = re.match(r"(\w+)\(([^,]+),\s*([^)]+)\)", g)
        if m:
            pred = m.group(1)
            arg1 = m.group(2).strip()
            arg2 = m.group(3).strip()
            if pred == "has":
                if arg1.lower() != "user":
                    if check_object_in_kg(arg1, "Item") and check_object_in_kg(arg2, "Furniture"):
                        new_goal = f"has(user, {arg1})"
                        print(f"Swapping arguments in goal '{g}' to enforce user possession: converted to '{new_goal}'.")
                        new_goals.append(new_goal)
                    elif check_object_in_kg(arg1, "Furniture"):
                        if arg1.lower() in inside_furniture:
                            new_goal = f"inside({arg1}, {arg2})"
                            print(f"Converting goal '{g}' to '{new_goal}' based on inside_furniture set.")
                            new_goals.append(new_goal)
                        elif arg1.lower() in on_furniture:
                            new_goal = f"on({arg1}, {arg2})"
                            print(f"Converting goal '{g}' to '{new_goal}' based on on_furniture set.")
                            new_goals.append(new_goal)
                        else:
                            new_goal = f"has(user, {arg2})"
                            print(f"Replacing goal '{g}' with '{new_goal}' to enforce user possession.")
                            new_goals.append(new_goal)
                    else:
                        new_goal = f"has(user, {arg2})"
                        print(f"Replacing goal '{g}' with '{new_goal}' to enforce user possession.")
                        new_goals.append(new_goal)
                else:
                    new_goals.append(g)
            elif pred in ("inside", "on"):
                valid_arg1 = check_object_in_kg(arg1, "Furniture")
                valid_arg2 = check_object_in_kg(arg2, "Item")
                if (not valid_arg1) and check_object_in_kg(arg2, "Furniture") and check_object_in_kg(arg1, "Item"):
                    print(f"Swapping arguments in goal '{g}' to enforce allowed order for '{pred}'.")
                    new_goals.append(f"{pred}({arg2}, {arg1})")
                else:
                    if not valid_arg1 and potential_contexts:
                        alt = find_alternative_object("Furniture", potential_contexts, arg1)
                        if alt:
                            print(f"Replacing first argument '{arg1}' with '{alt}' in goal '{g}'.")
                            arg1 = alt
                    if not valid_arg2 and potential_contexts:
                        alt = find_alternative_object("Item", potential_contexts, arg2)
                        if alt:
                            print(f"Replacing second argument '{arg2}' with '{alt}' in goal '{g}'.")
                            arg2 = alt
                    new_goals.append(f"{pred}({arg1}, {arg2})")
            elif pred in ("turn_on", "switched_off"):
                
                if not check_object_in_kg(arg1, "Furniture"):
                    print(f"Argument '{arg1}' not found as Furniture. Replacing it with 'switch_furniture_light' in goal '{g}' for predicate '{pred}'.")
                    arg1 = "switch_furniture_light"
                else:
                    print(f"Argument '{arg1}' is recognized as Furniture. No replacement needed for predicate '{pred}'.")
                new_goals.append(f"{pred}({arg1})")
            else:
                new_goals.append(g)
        else:
            m1 = re.match(r"(\w+)\(([^)]+)\)", g)
            if m1:
                pred = m1.group(1)
                arg = m1.group(2).strip()
                if pred in ("open", "closed"):
                    if not check_object_in_kg(arg, "Furniture") and potential_contexts:
                        alt = find_alternative_object("Furniture", potential_contexts, arg)
                        if alt:
                            print(f"Replacing argument '{arg}' with '{alt}' in goal '{g}' for predicate '{pred}'.")
                            arg = alt
                    new_goals.append(f"{pred}({arg})")
                elif pred == "heated":
                    if not check_object_in_kg(arg, "Item") and potential_contexts:
                        alt = find_alternative_object("Item", potential_contexts, arg)
                        if alt:
                            print(f"Replacing argument '{arg}' with '{alt}' in goal '{g}' for predicate '{pred}'.")
                            arg = alt
                    new_goals.append(f"{pred}({arg})")
                else:
                    new_goals.append(g)
            else:
                new_goals.append(g)
    return new_goals

def process_command(user_command,
                    previous_command,
                    first_command,
                    potential_contexts,
                    top_items,
                    history_suggestion=None,
                    context_expanded_info=None,
                    user_asp=None,
                    llm_regenerations=0,
                    kg_substitutions=0,
                    user_feedback_count=0,
                    user_feedback_content=None):

    global ALTERNATIVE_PREDICATE_COUNT, ALTERNATIVE_OBJECT_COUNT
    if user_feedback_content is None:
        user_feedback_content = []

    
    substitution_log = []

    asp_goal_substituted = False
    max_attempts = 4
    attempt = 0
    missing_predicates = []
    predicted_command = None
    asp_goal = None
    reason = None
    goals = None
    user_feedback = None

  
    llm_processing_start = time.time()
    waiting_total = 0

    while attempt < max_attempts:
        attempt += 1
        print(f"\nAttempt {attempt}:")

        current_missing_components = missing_predicates[:]
        if user_feedback and user_feedback not in current_missing_components:
            current_missing_components.append(user_feedback)

        prompt = generate_prompt_for_goals(
            current_command=user_command,
            previous_command=previous_command if not first_command else None,
            context=potential_contexts,
            context_items=top_items,
            missing_components=current_missing_components if attempt > 1 or user_feedback else None,
            predicted_history_command=history_suggestion,
            context_expanded_info=context_expanded_info
        )

        response = predict_next_action(prompt)
        print(f"LLM Response:\n{response}")
        predicted_command, asp_goal, reason, goals = extract_response_details(response)
        print(f"Extracted Predicted Command: {predicted_command}")
        print(f"Extracted ASP Goal: {asp_goal}")
        print(f"Extracted Reason: {reason}")
        print(f"Extracted Goals: {goals}")

        predicted_command_formatted = (predicted_command.replace('_', ' ').strip()
                                       if predicted_command else None)
        print(f"Formatted Predicted Command: {predicted_command_formatted}")

        if predicted_command_formatted and " " in predicted_command_formatted:
            action, obj = predicted_command_formatted.split(" ", 1)
            action = action.strip().lower()
            obj = obj.strip()
            print(f"Action: {action}")
            print(f"Object: {obj}")
        else:
            print("Warning: Predicted command does not contain both an action and an object.")
            action = (predicted_command_formatted.strip().lower()
                      if predicted_command_formatted else None)
            obj = None

        if action:
           
            _ = check_action_in_kg(action)

        missing_predicates = []

        if not goals:
            print("No goals returned by LLM. Will try again if attempts remain.")
            if attempt >= max_attempts:
                print("Max attempts reached. Exiting.")
                break
            else:
                continue

        print(f"Original Goals list: {goals}")

        for goal in goals:
            if '(' in goal and ')' in goal:
                predicate, arg1, arg2 = parse_goal(goal)
                if not predicate:
                    print(f"Invalid goal format: {goal}")
                    missing_predicates.append(goal)
                    continue

                print(f"Parsed Predicate: {predicate}, Arg1: {arg1}, Arg2: {arg2}")

              
                _ = check_predicate_in_kg(predicate)
                predicate_exists, predicate_type = check_predicate_in_kg(predicate)
                if not predicate_exists:
                    print(f"Predicate '{predicate}' is missing in KG. Attempting to find an alternative...")
                    ALTERNATIVE_PREDICATE_COUNT += 1
                    alt_predicate = find_alternative_predicate(predicate)
                    if alt_predicate:
                        substitution_log.append(f"Predicate substitution: {predicate} -> {alt_predicate} (success)")
                        print(f"Found alternative predicate '{alt_predicate}' for '{predicate}'.")
                        goals = [re.sub(r'\b' + re.escape(predicate) + r'\b', alt_predicate, g)
                                 for g in goals]
                        kg_substitutions += 1
                        predicate = alt_predicate
                       
                        _ = check_predicate_in_kg(predicate)
                        predicate_exists, predicate_type = check_predicate_in_kg(predicate)
                        if not predicate_exists:
                            print(f"Even after substitution, predicate '{predicate}' is not found in KG.")
                            missing_predicates.append(predicate)
                            continue
                    else:
                        substitution_log.append(f"Predicate substitution: {predicate} (failure)")
                        print(f"No alternative predicate found for '{predicate}'.")
                        missing_predicates.append(predicate)
                        continue

                print(f"Predicate '{predicate}' is available in KG as a {predicate_type}.")

                if predicate_type == 'Property':
                    if predicate in ("inside", "on"):
                        furniture_candidate = arg1
                        item_candidate = arg2

                        _ = check_object_in_kg(furniture_candidate, "Furniture")
                        _ = check_object_in_kg(item_candidate, "Item")
                        is_furniture = check_object_in_kg(furniture_candidate, "Furniture")
                        is_item = check_object_in_kg(item_candidate, "Item")

                        if (not is_furniture) and check_object_in_kg(item_candidate, "Furniture") and check_object_in_kg(furniture_candidate, "Item"):
                            print(f"Swapping arguments in goal '{goal}' to enforce allowed order for '{predicate}'.")
                            goals = [re.sub(re.escape(goal), f"{predicate}({item_candidate}, {furniture_candidate})", goal)]
                            continue
                        else:
                            if not is_furniture:
                                print(f"'{furniture_candidate}' is NOT recognized as Furniture. Attempting alternative.")
                                ALTERNATIVE_OBJECT_COUNT += 1
                                alt_furniture = find_alternative_object(
                                    "Furniture",
                                    contexts=potential_contexts,
                                    original_object=furniture_candidate
                                )
                                if alt_furniture:
                                    substitution_log.append(f"Furniture substitution: {furniture_candidate} -> {alt_furniture} (success)")
                                    print(f"Found alternative furniture '{alt_furniture}' for '{furniture_candidate}'.")
                                    goals = [
                                        re.sub(r'\b' + re.escape(furniture_candidate) + r'\b', alt_furniture, g)
                                        for g in goals
                                    ]
                                    kg_substitutions += 1
                                else:
                                    substitution_log.append(f"Furniture substitution: {furniture_candidate} (failure)")
                                    print(f"No alternative furniture found for '{furniture_candidate}'.")
                                    missing_predicates.append(furniture_candidate)
                                    continue
                            if not is_item:
                                print(f"'{item_candidate}' is NOT recognized as an Item. Attempting alternative item.")
                                ALTERNATIVE_OBJECT_COUNT += 1
                                alt_item = find_alternative_object(
                                    "Item",
                                    contexts=potential_contexts,
                                    original_object=item_candidate
                                )
                                if alt_item:
                                    substitution_log.append(f"Item substitution: {item_candidate} -> {alt_item} (success)")
                                    print(f"Found alternative item '{alt_item}' for '{item_candidate}'.")
                                    goals = [
                                        re.sub(r'\b' + re.escape(item_candidate) + r'\b', alt_item, gg)
                                        for gg in goals
                                    ]
                                    kg_substitutions += 1
                                else:
                                    substitution_log.append(f"Item substitution: {item_candidate} (failure)")
                                    print(f"No alternative item found for '{item_candidate}'.")
                                    missing_predicates.append(item_candidate)
                                    continue
                    else:
                        obj_target = arg2 if arg2 else arg1
                        expected_type = get_expected_object_type(predicate)
                        if expected_type:
                            _ = check_object_in_kg(obj_target, expected_type)
                            object_exists = check_object_in_kg(obj_target, expected_type)
                            if not object_exists:
                                print(f"Object '{obj_target}' does not exist in KG as a {expected_type}. Attempting to find alternative...")
                                ALTERNATIVE_OBJECT_COUNT += 1
                                alternative_obj = find_alternative_object(
                                    expected_type,
                                    contexts=potential_contexts,
                                    original_object=obj_target
                                )
                                if alternative_obj:
                                    substitution_log.append(f"Object substitution: {obj_target} -> {alternative_obj} (success)")
                                    print(f"Found alternative object '{alternative_obj}' for '{obj_target}'.")
                                    goals = [
                                        re.sub(r'\b' + re.escape(obj_target) + r'\b', alternative_obj, g)
                                        for g in goals
                                    ]
                                    kg_substitutions += 1
                                else:
                                    substitution_log.append(f"Object substitution: {obj_target} (failure)")
                                    print(f"No alternative object found for '{obj_target}'.")
                                    missing_predicates.append(obj_target)
            else:
                print(f"Invalid goal format: {goal}")
                missing_predicates.append(goal)

        if missing_predicates:
            print(f"Warning: Missing predicates/objects: {', '.join(set(missing_predicates))}")
            if attempt >= max_attempts:
                print("Max attempts reached. Proceeding with current results or asking for user confirmation.")
                break
            else:
                continue

        goals = enforce_allowed_predicates(goals, potential_contexts)
        print(f"Goals after enforcing allowed predicates: {goals}")

        if goals:
            asp_goal_substituted = "goal_2(I) :- " + ', '.join([f"holds({g}, I)" for g in goals]) + "."
            print(f"Goals after substitutions: {asp_goal_substituted}")
        else:
            asp_goal_substituted = ""
            print("Error: No valid goals to construct ASP Goal.")

        if asp_goal_substituted:
           
            waiting_start = time.time()
            try:
                user_input_answer = input_with_timeout("A suitable ASP goal was found. Accept this goal? (yes/no): ", 500).strip().lower()
            except TimeoutOccurred:
                print("\nNo input received within 500 seconds. Automatically accepting the goal.")
                user_input_answer = 'yes'
            waiting_end = time.time()
            waiting_total += (waiting_end - waiting_start)

            if user_input_answer == 'yes':
                print("Goal accepted.")
                break
            else:
                print("Goal rejected. Please provide feedback or type 'skip':")
                waiting_start = time.time()
                try:
                    user_fallback = input_with_timeout("Feedback> ", 500).strip()
                except TimeoutOccurred:
                    print("\nNo input received within 500 seconds. Automatically skipping.")
                    user_fallback = 'skip'
                waiting_end = time.time()
                waiting_total += (waiting_end - waiting_start)

                if user_fallback.lower() == 'skip':
                    print("User skipped. Exiting.")
                    asp_goal_substituted = ""
                    break
                else:
                    print(f"Using user feedback => {user_fallback}")
                    user_feedback = user_fallback
                    user_feedback_count += 1
                    user_feedback_content.append(f"Goal feedback => {user_fallback}")
                    asp_goal_substituted = ""
                    continue
        else:
            print("No valid ASP Goal generated. Exiting.")
            break

    llm_processing_time = time.time() - llm_processing_start - waiting_total
    print(f"LLM processing time (excluding user input wait): {llm_processing_time:.2f} seconds")
    print(f"Alternative predicate calls: {ALTERNATIVE_PREDICATE_COUNT}")
    print(f"Alternative object calls: {ALTERNATIVE_OBJECT_COUNT}")
    print("KG substitution log:")
    for log in substitution_log:
        print("  ", log)
    return (
        predicted_command,
        asp_goal_substituted,
        reason,
        goals,
        llm_regenerations,
        kg_substitutions,
        user_feedback_count,
        user_feedback_content,
        llm_processing_time,
        ALTERNATIVE_PREDICATE_COUNT,
        ALTERNATIVE_OBJECT_COUNT,
        substitution_log
    )

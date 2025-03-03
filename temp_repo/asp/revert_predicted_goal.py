
# asp/revert_predicted_goal.py

import os
import re
from asp.file_manager import (
    read_asp_file, append_to_asp_file,
    clean_existing_goals_and_success
)
from asp.solution_finder import run_sparc_solution_finder
from kg.kg_updater import update_kg_from_asp_outputs


def revert_predicted_goal_full(
    user_changed_file="show_changed_holds_output_user.txt",
    predicted_changed_file="show_changed_holds_output_predicted.txt",
    start_holds_file="show_start_holds_output.txt",
    occurs_file="occurs_output.txt"
):
    ALLOWED_ROLLBACK_PREDICATES = {
        "on", "closed","inside", "has", "open", "switched_on", "switched_off", "heated"
    }

    print("[REVERT] Starting revert_predicted_goal_full...")

    user_set = parse_changed_holds_file(user_changed_file)
    pred_set = parse_changed_holds_file(predicted_changed_file)
    predicted_only = pred_set - user_set
    if not predicted_only:
        print("[REVERT] No extra predicted changes to revert. Exiting.")
        return

    print(f"[REVERT] predicted_only changes => {predicted_only}")

    rollback_candidates = [p for p in predicted_only if not p.startswith("location(")]
    if not rollback_candidates:
        print("[REVERT] Only 'location(...)' changed; skipping rollback.")
        return

    changed_entities = find_entities_in_predicates(rollback_candidates)
    print(f"[REVERT] Changed entities => {changed_entities}")

    start_holds_map = parse_start_holds_for_entities(start_holds_file, changed_entities)

    rollback_goals = []
    for ent, preds in start_holds_map.items():
        for p in preds:
            match = re.match(r'(\w+)\(', p)
            if match:
                pred_name = match.group(1).strip()
                if pred_name in ALLOWED_ROLLBACK_PREDICATES:
                    rollback_goals.append(p)
                else:
                    print(f"[REVERT] Skipping '{p}' (predicate={pred_name}) - not in allowed rollback set.")

    if not rollback_goals:
        print("[REVERT] No suitable rollback goals from start_holds. Possibly item had no prior state.")
        return

    print("[REVERT] Final rollback_goals (from start_holds) =>")
    for rg in rollback_goals:
        print("   ", rg)

    clean_existing_goals_and_success()
    add_rollback_goal_to_asp_file(rollback_goals)

    print("[REVERT] *** Starting solver with rollback goal ***")
    run_sparc_solution_finder(display_predicates=[
        "occurs","show_operated_holds_name","show_changed_holds",
        "show_changed_holds_name","show_start_holds","show_last_holds"
    ])
    print("[REVERT] *** Solver finished ***")

    print("[REVERT] Updating KG from rollback solution results...")
    update_kg_from_asp_outputs(
        start_holds_file="show_start_holds_output.txt",
        last_holds_file="show_last_holds_output.txt",
        changed_holds_file="show_changed_holds_output.txt",
        changed_names_file="show_changed_holds_name_output.txt"
    )
    print("[REVERT] KG updated. Now we are back to user-only state if rollback succeeded.")

    print("[REVERT] Running simulation for rollback occurs if needed...")
    

    print("[REVERT] revert_predicted_goal_full completed.")


    try:
        open(predicted_changed_file, 'w').close()
        print(f"[REVERT] Cleared predicted changes file: {predicted_changed_file}")
    except Exception as e:
        print(f"[WARN] Failed to clear predicted changes file: {e}")


def parse_changed_holds_file(changed_file):

    if not os.path.exists(changed_file):
        print(f"[REVERT] {changed_file} not found.")
        return set()

    with open(changed_file, 'r', encoding='utf-8') as f:
        text = f.read()


    text = text.replace('{', '').replace('}', '')


    blocks = text.split("show_changed_holds(")
    results = set()

    for block in blocks:
        block = block.strip()

        if not block:
            continue


        pos = block.find(')')
        if pos == -1:

            continue

        content = block[:pos].strip()

        content = content.rstrip(') ,')


        if not content.endswith(')'):
            content += ")"

        content = content.strip()
        if content:
            results.add(content)

    return results

def find_entities_in_predicates(predicates):
    ents = set()
    for p in predicates:
        match = re.match(r'(\w+)\(([^)]*)\)', p)
        if match:
            args = [a.strip() for a in match.group(2).split(',')]
            for a in args:
                ents.add(a)
    return ents

def parse_start_holds_for_entities(start_file, entity_set):

    res = {}
    if not os.path.exists(start_file):
        print(f"[REVERT] start_file={start_file} not found.")
        return res

    txt = open(start_file,'r',encoding='utf-8').read()
    txt = txt.replace('{','').replace('}','')
    pattern = r'show_start_holds\s*\(\s*([^)]*)\s*\)'
    blocks = re.findall(pattern, txt)

    for block in blocks:
        parts = re.split(r'\)\s*,', block)
        for p in parts:
            p = p.strip()
            if not p.endswith(')'):
                p += ')'

            for e in entity_set:
                if e in p:
                    if e not in res:
                        res[e] = []
                    if p not in res[e]:
                        res[e].append(p)
    return res

def add_rollback_goal_to_asp_file(rollback_goals):

    if not rollback_goals:
        print("[REVERT] No rollback_goals, skipping.")
        return

    conds = ", ".join([f"holds({g}, I)" for g in rollback_goals])
    rollback_str = f"goal_rollback(I) :- {conds}.\n"
    success_str = "success :- goal_rollback(I), goal_furniture_restored(I).\n"

    print("[REVERT] Writing rollback goal to ASP:\n", rollback_str, success_str)
    lines = read_asp_file()
    already = any("goal_rollback(I)" in line for line in lines)
    if not already:
        append_to_asp_file(rollback_str)
        append_to_asp_file(success_str)
    else:
        print("[REVERT] rollback goal already present in ASP. Possibly from previous run.")

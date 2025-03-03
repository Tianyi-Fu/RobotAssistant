#asp/file_manager.py
import os
import sys
from config.config import ASP_FILE, PROJECT_ROOT
import logging
from rdflib import URIRef, RDF, RDFS, Literal
from kg.loader import load_kg, save_kg, get_graph, EX, OWL, XSD

logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s', stream=sys.stderr)

BOOLEAN_PROPERTIES = {
    "open": {"InsideFurniture", "MicrowaveFurniture"},

    "switched_on": {"SwitchFurniture"},
    "heated": {"HotDrink", "HotFood"},
    "changed": {"InsideFurniture", "MicrowaveFurniture"}
}
OPPOSITE_BOOLEAN_PROPERTIES = {
    "switched_on": "switched_off",
    "open": "closed",
    "closed": "open",
}

def read_asp_file():
    with open(ASP_FILE, "r", encoding="utf-8") as f:
        return f.readlines()

def write_asp_file(lines):
    with open(ASP_FILE, "w", encoding="utf-8") as f:
        f.writelines(lines)

def append_to_asp_file(text):
    with open(ASP_FILE, "a", encoding="utf-8") as f:
        f.write(text)

def clean_existing_goals_and_success():
    lines = read_asp_file()
    lines_to_keep = [
        "success :- goal_1(I).\n",
        "success().\n",
        "goal_1(#step).\n",
        "goal_2(#step).\n",
        "goal_rollback(#step).\n",
        "goal_furniture_restored(#step).\n"
    ]

    cleaned_lines = [
        line for line in lines if (
            line.strip().startswith('%') or
            line in lines_to_keep or
            not (line.strip().startswith("goal_1") or
                 line.strip().startswith("success") or
                 line.strip().startswith("goal_2")or
                 line.strip().startswith("goal_rollback"))
        )
    ]

    write_asp_file(cleaned_lines)
    print("Cleaned existing goals and success rules from ASP file, while preserving specified lines.")

def add_goal_to_asp_file(goal_condition):
    lines = read_asp_file()
    formatted_goal = f"goal_1(I) :- holds({goal_condition}, I).\n"
    success_rule = "success :- goal_1(I).\n"

    goal_present = any(line.strip() == formatted_goal.strip() for line in lines if not line.strip().startswith('%'))
    success_present = any(line.strip() == success_rule.strip() for line in lines if not line.strip().startswith('%'))

    if not goal_present:
        append_to_asp_file(formatted_goal)
        print(f"Added goal to ASP file: {formatted_goal.strip()}")
    else:
        print("Goal already exists in ASP file; skipping addition.")

    if not success_present:
        append_to_asp_file(success_rule)
        print(f"Added success rule to ASP file: {success_rule.strip()}")
    else:
        print("Success rule already exists in ASP file; skipping addition.")

def add_predicted_goal_to_asp_file(goal_condition_2):
    lines = read_asp_file()

    formatted_goal_2 = f"{goal_condition_2}\n"
    updated_success_rule = "success :- goal_1(I), goal_2(I).\n"

    new_asp_lines = []
    inside_initial_conditions = False

    for line in lines:
        line_stripped = line.strip()
        if (line_stripped.startswith("%") or
            line_stripped.endswith("(#step).") or
            (not line_stripped.startswith("goal_2") and not line_stripped.startswith("success :-"))):
            new_asp_lines.append(line)

    new_asp_lines.append(formatted_goal_2)
    print(f"Added goal_2 to ASP file: {formatted_goal_2.strip()}")
    new_asp_lines.append(updated_success_rule)
    print(f"Updated success rule in ASP file: {updated_success_rule.strip()}")

    with open(ASP_FILE, "w", encoding="utf-8") as f:
        f.writelines(new_asp_lines)

def get_local_name(uri):
    if isinstance(uri, URIRef):
        name = uri.split("/")[-1]
        return name
    return str(uri)

def get_all_superclasses(g, cls):
    superclasses = set()
    for superclass in g.objects(cls, RDFS.subClassOf):
        local_super = get_local_name(superclass)
        superclasses.add(local_super)
        superclasses.update(get_all_superclasses(g, superclass))
    return superclasses

def is_heatable(g, item):
    types = set(get_local_name(t) for t in g.objects(item, RDF.type))
    return bool(types.intersection({"HotDrink", "HotFood"}))

def extract_initial_conditions():
    g = get_graph()
    g.remove((None, None, None))
    load_kg(os.path.join(PROJECT_ROOT, "kg", "living_room.ttl"))

    initial_conditions = set()

    for furniture in g.subjects(RDF.type, EX.Furniture):
        furniture_name = get_local_name(furniture)


        furniture_location = g.value(furniture, EX.furniture_location) or g.value(furniture, EX.location)
        if furniture_location:
            room_name = get_local_name(furniture_location)
            initial_conditions.add(f"holds(furniture_location({furniture_name}, {room_name}), 0).")
        else:
            logging.warning(f"Furniture '{furniture_name}' has no defined location.")


        furniture_classes = set(get_local_name(cls) for cls in g.objects(furniture, RDF.type))
        for cls in g.objects(furniture, RDFS.subClassOf):
            furniture_classes.update(get_all_superclasses(g, cls))

        for prop, applicable_classes in BOOLEAN_PROPERTIES.items():
           
            if not applicable_classes.intersection(furniture_classes):
                continue


            prop_value = g.value(furniture, EX[prop])
            if prop_value is not None:
                prop_value_str = str(prop_value).lower()
                if isinstance(prop_value, Literal) and prop_value.datatype == XSD.boolean:
                    prop_value_bool = prop_value.toPython()  
                else:
                    prop_value_bool = prop_value_str in {"true", "1"}
                logging.info(f"Property '{prop}' for '{furniture_name}' has value: {prop_value_bool}")
            else:

                prop_value_bool = False
                logging.warning(
                    f"Property '{prop}' not set for furniture '{furniture_name}'. Defaulting to False.")

            if prop in OPPOSITE_BOOLEAN_PROPERTIES:

                if prop_value_bool:

                    initial_conditions.add(f"holds({prop}({furniture_name}), 0).")
                    opp = OPPOSITE_BOOLEAN_PROPERTIES[prop]
                    initial_conditions.add(f"-holds({opp}({furniture_name}), 0).")
                else:

                    initial_conditions.add(f"-holds({prop}({furniture_name}), 0).")
                    opp = OPPOSITE_BOOLEAN_PROPERTIES[prop]
                    initial_conditions.add(f"holds({opp}({furniture_name}), 0).")
            else:

                if prop_value_bool:
                    initial_conditions.add(f"holds({prop}({furniture_name}), 0).")
                else:
                    initial_conditions.add(f"-holds({prop}({furniture_name}), 0).")

    for item in g.subjects(RDF.type, EX.Item):
        item_name = get_local_name(item)


        heatable = is_heatable(g, item)

        if heatable:
            initial_conditions.add(f"-holds(heated({item_name}), 0).")


        on_furniture = g.value(item, EX.on)
        if on_furniture:
            furniture_name = get_local_name(on_furniture)

            furniture_location = g.value(on_furniture, EX.furniture_location) or g.value(on_furniture, EX.location)
            if furniture_location:
                room_name = get_local_name(furniture_location)
                initial_conditions.add(f"holds(location({item_name}, {room_name}, {furniture_name}), 0).")
                initial_conditions.add(f"holds(on({furniture_name}, {item_name}), 0).")
            else:
                logging.warning(f"Furniture '{furniture_name}' does not have a defined location.")
        else:

            inside_furniture = g.value(item, EX.inside)
            if inside_furniture:
                furniture_name = get_local_name(inside_furniture)

                furniture_location = g.value(inside_furniture, EX.furniture_location) or g.value(inside_furniture, EX.location)
                if furniture_location:
                    room_name = get_local_name(furniture_location)
                    initial_conditions.add(f"holds(location({item_name}, {room_name}, {furniture_name}), 0).")
                    initial_conditions.add(f"holds(inside({furniture_name}, {item_name}), 0).")
                else:
                    logging.warning(f"Furniture '{furniture_name}' does not have a defined location.")
            else:
                logging.warning(f"Item '{item_name}' is neither on nor inside any furniture.")


    for agent in g.subjects(RDF.type, EX.Agent):
        agent_name = get_local_name(agent)

        agent_in = g.value(agent, EX["in"])
        if agent_in:
            room_name = get_local_name(agent_in)
            initial_conditions.add(f"holds(in({agent_name}, {room_name}), 0).")
        else:
            logging.warning(f"Agent '{agent_name}' does not have an 'in' property defined.")


    for agent in g.subjects(RDF.type, EX.Agent):
        agent_name = get_local_name(agent)
        rooms = set(get_local_name(r) for r in g.objects(agent, EX["in"]))
        if len(rooms) > 1:
            logging.warning(f"Agent '{agent_name}' is defined in multiple rooms: {rooms}")

            rooms = list(rooms)
            kept_room = rooms[0]
            for room in rooms[1:]:
                condition_to_remove = f"holds(in({agent_name}, {room}), 0)."

                condition_to_remove_standardized = condition_to_remove.strip().replace(" ", "")

                initial_conditions_standardized = {cond.strip().replace(" ", "") for cond in initial_conditions}
                if condition_to_remove_standardized in initial_conditions_standardized:
                    initial_conditions = {
                        cond for cond in initial_conditions
                        if cond.strip().replace(" ", "") != condition_to_remove_standardized
                    }
                    logging.info(f"Removed location of agent '{agent_name}' in room '{room}'.")
                else:
                    logging.info(f"Did not find condition '{condition_to_remove}' to remove location of agent '{agent_name}' in room '{room}'.")

        elif len(rooms) == 0:
            logging.warning(f"Agent '{agent_name}' does not have any room location defined.")


    for user in g.subjects(RDF.type, EX.User):
        user_name = get_local_name(user)

        user_location = g.value(user, EX.user_location)
        if user_location:
            room_name = get_local_name(user_location)
            initial_conditions.add(f"holds(user_location({room_name}), 0).")
        else:
            logging.warning(f"User '{user_name}' does not have a location defined.")


    all_items = set(g.subjects(RDF.type, EX.Item))
    all_item_names = {get_local_name(item) for item in all_items}

    agents = set(g.subjects(RDF.type, EX.Agent))
    users = set(g.subjects(RDF.type, EX.User))

    agent_names = {get_local_name(agent) for agent in agents}
    user_names = {get_local_name(user) for user in users}

    for agent_name in agent_names:
        for item_name in all_item_names:
            initial_conditions.add(f"-holds(has({agent_name}, {item_name}), 0).")

    for user_name in user_names:
        for item_name in all_item_names:
            initial_conditions.add(f"-holds(has({user_name}, {item_name}), 0).")


    for s, p, o in g.triples((None, EX.has, None)):
        subject = get_local_name(s)
        obj = get_local_name(o)

        hold_add = f"holds(has({subject}, {obj}), 0)."
        hold_remove = f"-holds(has({subject}, {obj}), 0)."

        if hold_remove in initial_conditions:
            initial_conditions.remove(hold_remove)
            logging.info(f"Removed '{hold_remove}' to add '{hold_add}'.")
        initial_conditions.add(hold_add)
        logging.info(f"Set '{subject}' to hold item '{obj}'.")


    for furniture in g.subjects(RDF.type, EX.Furniture):
        furniture_name = get_local_name(furniture)

        furniture_classes = set(get_local_name(cls) for cls in g.objects(furniture, RDF.type))
        for cls in g.objects(furniture, RDFS.subClassOf):
            furniture_classes.update(get_all_superclasses(g, cls))

        if any(cls in BOOLEAN_PROPERTIES["changed"] for cls in furniture_classes):
            initial_conditions.add(f"-holds(changed({furniture_name}), 0).")


    for drink in g.subjects(RDF.type, EX.HotDrink):
        drink_name = get_local_name(drink)
        initial_conditions.add(f"-holds(heated({drink_name}), 0).")

    for food in g.subjects(RDF.type, EX.HotFood):
        food_name = get_local_name(food)
        initial_conditions.add(f"-holds(heated({food_name}), 0).")

    with open("initial_conditions.txt", "w", encoding="utf-8") as f:
        for condition in initial_conditions:
            f.write(condition + "\n")

    logging.info("Initial conditions have been successfully extracted and saved to 'initial_conditions.txt")


def insert_initial_conditions_to_asp():
    initial_conditions_file = "initial_conditions.txt"
    with open(initial_conditions_file, "r", encoding="utf-8") as f:
        initial_conditions = f.read()

    with open(ASP_FILE, "r", encoding="utf-8") as f:
        asp_lines = f.readlines()

    start_marker = "% ===== INITIAL CONDITIONS START ====="
    end_marker = "% ===== INITIAL CONDITIONS END ====="

    new_asp_lines = []
    inside_initial_conditions = False

    for line in asp_lines:
        if line.strip() == start_marker:
            inside_initial_conditions = True
            new_asp_lines.append(line)
            new_asp_lines.append(initial_conditions)
            continue
        if line.strip() == end_marker:
            inside_initial_conditions = False
        if not inside_initial_conditions:
            new_asp_lines.append(line)

    with open(ASP_FILE, "w", encoding="utf-8") as f:
        f.writelines(new_asp_lines)

    print("Inserted initial conditions into ASP file.")

def remove_initial_conditions_from_asp():
    with open(ASP_FILE, "r", encoding="utf-8") as f:
        asp_lines = f.readlines()

    start_marker = "% ===== INITIAL CONDITIONS START ====="
    end_marker = "% ===== INITIAL CONDITIONS END ====="

    new_asp_lines = []
    inside_initial_conditions = False

    for line in asp_lines:
        if line.strip() == start_marker:
            inside_initial_conditions = True
            new_asp_lines.append(line)
            continue
        if line.strip() == end_marker:
            inside_initial_conditions = False
            new_asp_lines.append(line)
            continue
        if not inside_initial_conditions:
            new_asp_lines.append(line)

    with open(ASP_FILE, "w", encoding="utf-8") as f:
        f.writelines(new_asp_lines)

    print("Removed initial conditions from ASP file.")

def update_user_holds(user, item, action):

    if action == 'add':

        hold_add = f"holds(has({user}, {item}), 1)."

        hold_remove = f"-holds(has({user}, {item}), 0)."
        return [hold_add, hold_remove]
    elif action == 'remove':

        hold_remove = f"-holds(has({user}, {item}), 0)."

        hold_add = f"holds(has({user}, {item}), 1)."
        return [hold_remove, hold_add]
    else:
        print(f"[WARN] Unknown action '{action}' for updating user holds.")
        return []


def map_hold_to_triples(predicate, subject, obj=None):

    if predicate == "hasContextWeight":
        logging.info(f"Skipping predicate '{predicate}' in map_hold_to_triples.")
        return []

    predicate_mapping = {
        "switched_on": EX.switched_on,
        "switched_off": EX.switched_off,
        "has": EX.has,
        "changed": EX.changed,
        "at_furniture": EX.at_furniture,
        "open": EX.open,
        "closed": EX.closed,
        "inside": EX.inside,
        "in": EX.in_,
        "location": EX.location,
        "on": EX.on,
        "holds": EX.holds,
    }

    triples = []
    if predicate in predicate_mapping:
        pred_uri = predicate_mapping[predicate]
        subj_uri = URIRef(f"http://example.org/{subject}")
        if obj:
            obj_uri = URIRef(f"http://example.org/{obj}")
            triples.append((subj_uri, pred_uri, obj_uri))
        else:
            if predicate in {"switched_on", "switched_off", "open", "closed", "changed"}:
                triples.append((subj_uri, pred_uri, Literal(True, datatype=XSD.boolean)))
            else:
                triples.append((subj_uri, pred_uri, Literal(True)))
    else:
        logging.warning(f"map_hold_to_triples: predicate '{predicate}' not recognized.")
        return None

    return triples



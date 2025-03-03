#simulation/handler.py
import os
import re
import time
import logging

from simulation.unity_simulator.comm_unity import UnityCommunication
from config.config import UNITY_EXEC_PATH
from simulation.unity_simulator.utils_viz import generate_video
from simulation.utils_demo import *


from simulation.diagnosis import update_two_goals_dig, run_sparc


from kg.alternative_finder import find_alternative_object
from kg.context_analysis import get_results

from kg.kg_updater import update_kg_from_asp_outputs

logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')


class SimulatorHandler:
    

    def __init__(self, unity_file_path):
        try:
            self.comm = UnityCommunication(file_name=unity_file_path)
            self.comm.reset(6)
            logging.info("Scene #6 loaded (default arrangement).")
            self.available = True

            # Add two characters
            self.comm.add_character('Chars/Female2', initial_room='livingroom')
            self.comm.add_character('Chars/Female1', initial_room='bedroom')
            logging.info("Simulator initialized, 2 characters added.")
        except Exception as e:
            logging.error(f"Failed to initialize simulator: {e}")
            self.available = False

        self.static_id_to_class = {
            56:"kitchen",
            282:"bedroom",
            197:"livingroom",
            11:"bathroom",
            115:"folder",
            120:"notes",
            245:"bookshelf",
            262:"book",
            314:"desk",
            251:"bananas",
            257:"dishbowl",
            249:"apple",
            246:"coffeetable",
            194:"milk",
            129:"kitchentable",
            248:"alcohol",
            195:"cereal",
            268:"cellphone",
            254:"peach",
            269:"crackers",
            234:"tvstand",
            260:"mug",  
            319:"cupcake",
            243:"desk_1",
            321:"juice",
            173:"cutlets",
            140:"kitchencounter",
            358:"magazine",
            335:"amplifier",
            175:"poundcake",
            99:"plate",
            220:"tablelamp",
            247:"sofa",
            244:"chair",
            166:"microwave",
            172:"chicken",
            165:"fridge",
            258:"waterglass",
        }

        
        self.sit_done = False

    def get_environment_graph(self):
        if not self.available:
            logging.warning("Simulator is unavailable => skip.")
            return False, None
        try:
            succ, graph = self.comm.environment_graph()
            if succ and graph:
                # update ID->class if new
                for node in graph["nodes"]:
                    if node["id"] not in self.static_id_to_class:
                        self.static_id_to_class[node["id"]] = node["class_name"]
            return succ, graph
        except Exception as e:
            logging.error(f"Error retrieving environment graph: {e}")
            return False, None

    def build_state_map(self, graph):
        state_map = {}
        for node in graph["nodes"]:
            oid = node["id"]
            stlist = node.get("states", [])
            state_map[oid] = frozenset(stlist)
        return state_map

    def build_edge_map(self, graph):
        edge_set = set()
        for e in graph["edges"]:
            f = e["from_id"]
            rel = e["relation_type"]
            t = e["to_id"]
            edge_set.add((f, rel, t))
        return edge_set

    def detect_state_changes(self, before_map, after_map):
        changes = []
        all_ids = set(before_map.keys()) | set(after_map.keys())
        for oid in all_ids:
            oldS = before_map.get(oid, frozenset())
            newS = after_map.get(oid, frozenset())
            if oldS != newS:
                changes.append((oid, oldS, newS))
        return changes

    def detect_edge_changes(self, old_edges, new_edges):
        removed = old_edges - new_edges
        added   = new_edges - old_edges
        return (removed, added)

    def name_of(self, oid):
        return self.static_id_to_class.get(oid, f"???_{oid}")

    def should_filter_relation(self, relation_type):
        skip_relations = {"CLOSE","FACING","LOOK"}
        return (relation_type in skip_relations)

    def process_events_and_simulate(self, input_file_path):
        """
        parse occurs(...) => build final_script => run => if impossible => diagnose => ...
        always return a list
        """
        if not self.available:
            logging.warning("Simulator is unavailable => skip.")
            return []

        if not os.path.isfile(input_file_path):
            raise FileNotFoundError(f"File '{input_file_path}' not found.")

        with open(input_file_path,'r',encoding='utf-8') as f:
            txt = f.read()

        pattern = r'occurs\((\w+)\(([^,]+)(?:,([^,]+))?(?:,([^)]*))?\),(\d+)\)'
        events = re.findall(pattern, txt)

        action_mapping = {"give":"put"}
        script_entries = []
        for evt in events:
            action = evt[0].strip()
            agent  = evt[1].strip()
            p2     = evt[2].strip() if evt[2] else None
            p3     = evt[3].strip() if evt[3] else None
            ts     = int(evt[4])

            if action=="walk":
                continue

            a_conv = action_mapping.get(action, action)
            actor = "<char1>"

            if p2=="user":
                p2="sofa"
            if p3=="user":
                p3="sofa"

            def get_id(name):
                if not name:
                    return None
                for k,v in self.static_id_to_class.items():
                    if v==name:
                        return k
                logging.warning(f"'{name}' not recognized => ID=9999 fallback.")
                return 9999

            line_str=""
            if action in ("walktowards","walk"):
                loc_id = get_id(p2)
                if p2:
                    line_str = f"{actor} [{a_conv}] <{p2}> ({loc_id})"
            elif action in ("grab","put","putin","give","open","close","switchon","switchoff"):
                item_id = get_id(p2)
                loc_id  = get_id(p3) if p3 else None
                if p3:
                    line_str = f"{actor} [{a_conv}] <{p2}> ({item_id}) <{p3}> ({loc_id})"
                else:
                    line_str = f"{actor} [{a_conv}] <{p2}> ({item_id})"
            else:
                logging.warning(f"Action '{action}' not recognized => treat param2 as item, param3 as loc.")
                item_id = get_id(p2)
                loc_id  = get_id(p3) if p3 else None
                if p3:
                    line_str = f"{actor} [{a_conv}] <{p2}> ({item_id}) <{p3}> ({loc_id})"
                else:
                    line_str = f"{actor} [{a_conv}] <{p2}> ({item_id})"

            if line_str:
                script_entries.append((ts,line_str))

       
        if not self.sit_done:
            script_entries.insert(0, (-1, "<char0> [sit] <sofa> (247)"))
            self.sit_done = True

        script_entries.sort(key=lambda x: x[0])
        executed = []
        overall_ok = True

        for i,(timestamp,line_str) in enumerate(script_entries):
            logging.info(f"--- Step {i} => T={timestamp} => line: {line_str}")

            ok1, old_g = self.get_environment_graph()
            if not ok1 or not old_g:
                logging.error("Cannot get old_graph => break.")
                overall_ok=False
                break

            old_states = self.build_state_map(old_g)
            old_edges  = self.build_edge_map(old_g)

            try:
                success, msg = self.comm.render_script(
                    script=[line_str],
                    skip_animation=False,
                    image_synthesis=['normal'],
                    camera_mode=['PERSON_FROM_BACK'],
                    recording=True,
                    save_pose_data=True,
                    frame_rate=10,
                    file_name_prefix=f'test_step{i}',
                    find_solution=False
                )
                step_ok = success

                for k,v in msg.items():
                    if "impossible" in v["message"].lower():
                        step_ok=False
                        self._do_diagnosis(line_str, timestamp, v["message"])
                        break

                if step_ok:
                    logging.info(f"[Step {i}] => success, msg={msg}")
                    executed.append(line_str)
                else:
                    logging.warning(f"[Step {i}] => IMPOSSIBLE => stop. {msg}")
                    overall_ok=False
                    break
            except Exception as e:
                logging.error(f"[ERROR] Step {i}, line='{line_str}' => {e}")
                overall_ok=False
                break

            if overall_ok:
                ok2, new_g = self.get_environment_graph()
                if ok2 and new_g:
                    new_states = self.build_state_map(new_g)
                    new_edges  = self.build_edge_map(new_g)
                    st_changes = self.detect_state_changes(old_states, new_states)
                    for (oid,oldS,newS) in st_changes:
                        logging.info(f"[Step {i}] {self.name_of(oid)}({oid}) states changed from {list(oldS)} to {list(newS)}")

                    removed,added = self.detect_edge_changes(old_edges,new_edges)
                    for (f,r,t) in removed:
                        if not self.should_filter_relation(r):
                            logging.info(f"[Step {i}] Edge REMOVED => {self.interpret_edge(f,r,t)}")
                    for (f,r,t) in added:
                        if not self.should_filter_relation(r):
                            logging.info(f"[Step {i}] Edge ADDED   => {self.interpret_edge(f,r,t)}")
                else:
                    logging.warning(f"[Step {i}] new_g not available => skip changes check.")
            else:
                logging.info(f"Stop further actions at step {i}.")
                break

        if overall_ok:
            logging.info("All actions executed successfully without error.")
        else:
            logging.info("Stopped early => rollback or diagnose.")

        return executed

    def _do_diagnosis(self, line_str, step, reason=""):
        logging.info(f"[DIAG] Start diagnosing => line_str={line_str}, step={step}, reason={reason}")

   
        action_asp, item_name = self._convert_line_to_asp_action(line_str)
        hpd_line = f"hpd({action_asp},{step})."
        obs_line = f"obs(has(agent1,{item_name}), false, {step+1})."

        domain_file = "two_goals_dig.sp"
        items_list = [item_name]
        facts_list = [hpd_line, obs_line]

      
        update_two_goals_dig(domain_file, items_list, facts_list)
        try:
            run_sparc(domain_file, jar_path="sparc.jar")  
        except Exception as e:
            logging.error(f"[DIAG] run_sparc => {e}")
            return  

        logging.info("[DIAG] Done diagnosing with SPARC.")
        if "(9999)" in line_str:
            
            top_context, top_items = get_results()
            logging.info(f"[DIAG] top_context={top_context}, top_items={top_items}")

            alt_item = None
            if top_context:
           
                alt_item = find_alternative_object("Item",[top_context], item_name)
                
                if not alt_item or alt_item.lower() == item_name.lower():
                    alt_item = find_alternative_object("Item", [], item_name)

       
            if not alt_item or alt_item.lower() == item_name.lower():
                logging.info("[DIAG] No suitable alt_item from KG yet => forcibly pick an item recognized by simulator.")
                alt_item = None
                recognized_lower = {v.lower(): v for _,v in self.static_id_to_class.items()}
                for it in top_items:
                    candidate_name = it['name']  # e.g. "milk"
                    if candidate_name.lower() != item_name.lower() and candidate_name.lower() in recognized_lower:
                        alt_item = candidate_name
                        break

                
                if not alt_item:
                    for sid, cls_name in self.static_id_to_class.items():
                        if cls_name.lower() != item_name.lower():
                            alt_item = cls_name
                            break

            if alt_item:
                
                self._replace_item_in_occurs_file("occurs_output.txt", item_name, alt_item)

                logging.info("[DIAG] re-sim with replaced item => occurs_output.txt")
                from simulation.handler import process_events_and_simulate
                try:
                    script2 = process_events_and_simulate("occurs_output.txt")
                    if script2:
                        logging.info(f"[DIAG] re-simulation => {script2}")
                        
                        logging.info("[DIAG] re-sim success => update KG now.")
                        start_file = "show_start_holds_output.txt"
                        last_file  = "show_last_holds_output.txt"
                        changed_file = "show_changed_holds_output.txt"
                        update_kg_from_asp_outputs(
                            start_holds_file=start_file,
                            last_holds_file=last_file,
                            changed_holds_file=changed_file
                        )
                        logging.info("[DIAG] KG updated after fallback re-simulation.")
                    else:
                        logging.info("[DIAG] re-simulation script empty => skip KG update.")
                except Exception as e:
                    logging.error(f"[DIAG] re-simulation failed => {e}")
            else:
                logging.info(f"[DIAG] could not find ANY alt for '{item_name}', but must replace => no further fallback.")


    def _replace_item_in_occurs_file(self, file_path, old_item, new_item):
        
        if not os.path.exists(file_path):
            logging.warning(f"[DIAG] occurs file not found => {file_path}")
            return

        pattern = re.compile(r'occurs\((\w+)\(([^,]+)(?:,([^,]+))?(?:,([^)]*))?\),(\d+)\)')

        def replacer(m):
           
            action = m.group(1)  
            p1 = (m.group(2) or "").strip()  
            p2 = (m.group(3) or "").strip()  
            p3 = (m.group(4) or "").strip()  
            time_str = m.group(5)          

         
            if p2.lower() == old_item.lower():
                p2 = new_item
           
            if p3.lower() == old_item.lower():
                p3 = new_item

           
            if p3: 
                return f"occurs({action}({p1},{p2},{p3}),{time_str})"
            elif p2: 
                return f"occurs({action}({p1},{p2}),{time_str})"
            else:    
                return f"occurs({action}({p1}),{time_str})"

        new_lines = []
        with open(file_path, 'r', encoding='utf-8') as f:
            for line in f:
                new_line = pattern.sub(replacer, line)
                new_lines.append(new_line)

        with open(file_path, 'w', encoding='utf-8') as f:
            f.writelines(new_lines)

        logging.info(f"[DIAG] Replaced '{old_item}' with '{new_item}' in {file_path} SUCCESSFULLY!")






    def interpret_edge(self, f, r, t):
        fname = self.name_of(f)
        tname = self.name_of(t)
        return f"({fname}, {r}, {tname})"

    def _convert_line_to_asp_action(self, line_str):
        action_name = "unknown_action"
        item_name   = "unknown_item"
        loc_name    = "unknown_loc"

        m_action = re.search(r"\[([^\]]+)\]", line_str)
        if m_action:
            action_name = m_action.group(1).strip()

        bracket_vals = re.findall(r"<([^>]+)>", line_str)
        agent_asp = "agent1"

        if len(bracket_vals)>=2:
            item_name = bracket_vals[1]
        if len(bracket_vals)>=3:
            loc_name = bracket_vals[2]

        action_asp = f"{action_name}({agent_asp},{item_name},{loc_name})"
        return action_asp, item_name



simulator_instance = SimulatorHandler(unity_file_path=UNITY_EXEC_PATH)

def process_events_and_simulate(input_file_path):
    return simulator_instance.process_events_and_simulate(input_file_path)

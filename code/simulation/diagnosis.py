# simulation/diagnosis.py
import os
import subprocess
import logging

logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')

def update_two_goals_dig(domain_file, items_list, facts_list):
    
    if not os.path.isfile(domain_file):
        logging.warning(f"[DIAG] Domain file not found: {domain_file}")
        return

    items_start_marker = "% ================ ITEMS START ================"
    items_end_marker   = "% ================ ITEMS END ================"
    facts_start_marker = "% ================ FACTS START ================"
    facts_end_marker   = "% ================ FACTS END ================"

    with open(domain_file, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    out_lines = []
    inside_items_block = False
    inside_facts_block = False

    if items_list:
        items_line = "#item = { " + ",".join(items_list) + " }."
    else:
        items_line = "#item = {}."

    for line in lines:
        stripped = line.strip()

        
        if stripped == items_start_marker.strip():
            out_lines.append(line)  
            
            out_lines.append(items_line + "\n")
            inside_items_block = True
            continue
        
        if stripped == items_end_marker.strip():
            out_lines.append(line)
            inside_items_block = False
            continue

        if stripped == facts_start_marker.strip():
            out_lines.append(line)
            
            for fact in facts_list:
                out_lines.append(fact.strip() + "\n")
            inside_facts_block = True
            continue
        
        if stripped == facts_end_marker.strip():
            out_lines.append(line)
            inside_facts_block = False
            continue
        
        if inside_items_block or inside_facts_block:
            continue
        else:
            out_lines.append(line)

    
    with open(domain_file, 'w', encoding='utf-8') as f:
        f.writelines(out_lines)

    logging.info(f"[DIAG] Updated {domain_file}: #item => {items_list}, wrote {len(facts_list)} facts.")


def run_sparc(domain_file, jar_path="sparc.jar"):
    
    if not os.path.isfile(domain_file):
        logging.warning(f"[DIAG] domain_file not found: {domain_file}")
        return
    
    if not os.path.isfile(jar_path):
        logging.warning(f"[DIAG] SPARC jar not found: {jar_path}")
        return


    cmd = ["java", "-jar", jar_path, domain_file, "-A"]
    logging.info("[DIAG] Running => " + " ".join(cmd))

    try:
       
        ret = subprocess.run(cmd, capture_output=True, text=True)
        if ret.returncode != 0:
            logging.warning(f"[DIAG] SPARC returned non-zero exit code = {ret.returncode}")

        print("[DIAG] SPARC output:\n", ret.stdout)
        if ret.stderr:
            print("[DIAG] SPARC errors:\n", ret.stderr)

    except Exception as e:
        logging.error(f"[DIAG] Could not run solver => {e}")

#kg/history_manager.py
import os

import shutil
from config.config import HISTORY_FILE, BACKUP_FILE

def load_user_history():
    lines = []
    if os.path.exists(HISTORY_FILE):
        with open(HISTORY_FILE, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                if line == "[" or line == "]":
                    continue
                if '|' not in line:
                    continue
                lines.append(line)
    return lines

def load_all_sessions():
    if not os.path.exists(HISTORY_FILE):
        return []
    with open(HISTORY_FILE, 'r', encoding='utf-8') as f:
        content = f.read()

    raw_blocks = content.split("=== New Session ===")
    sessions = []
    for block in raw_blocks:
        block_lines = []
        for line in block.strip().splitlines():
            l = line.strip()
            if l and l != "[" and l != "]" and '|' in l:
                block_lines.append(l)
        if block_lines:
            sessions.append(block_lines)
    return sessions

def append_to_history(asp_command, user_command):
    with open(HISTORY_FILE, 'a', encoding='utf-8') as f:
        f.write(f"{asp_command} | {user_command}\n")

def reset_history_from_backup():
    if os.path.exists(BACKUP_FILE):
        shutil.copyfile(BACKUP_FILE, HISTORY_FILE)
        print("[INFO] User history has been reset from backup.")
    else:
        print(f"[WARN] Backup file not found: {BACKUP_FILE}. Skipping reset.")

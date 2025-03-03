# config/config.py
import os

OPENAI_API_KEY = "Replace with your OpenAI API key"
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
SPARC_JAR_PATH = os.path.join(PROJECT_ROOT, "sparc.jar")
ASP_FILE = os.path.join(PROJECT_ROOT, "two_goals.sp")
OCCURS_OUTPUT = os.path.join(PROJECT_ROOT, "occurs_output.txt")
OPERATED_OUTPUT = os.path.join(PROJECT_ROOT, "show_operated_holds_name_output.txt")
LIVINGROOM_TTL = os.path.join(PROJECT_ROOT, "kg", "living_room.ttl")
LIVINGROOM_BACKUP_TTL = os.path.join(PROJECT_ROOT, "kg", "living_room_backup.ttl")
COMMAND_INFO_JSON = os.path.join(PROJECT_ROOT, "command_info.json")
INITIAL_CONDITIONS_FILE = os.path.join(PROJECT_ROOT, "initial_conditions.txt")
UNITY_EXEC_PATH = "Path/To/virtualhome/virtualhome/simulation/macos_exec.v2.3.0.app"
UNITY_OUTPUT_PATH = "Path/To/virtualhome/virtualhome/simulation/Output/"
LLM_MODEL = "gpt-4o"
ENABLE_SIMULATOR = True
HISTORY_FILE = os.path.join(PROJECT_ROOT, "user_history.txt")
BACKUP_FILE = os.path.join(PROJECT_ROOT, "user_history_backup.txt")

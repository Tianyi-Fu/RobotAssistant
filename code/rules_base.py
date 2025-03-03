#rules_base.py
import sqlite3

"""
Rules and Input Database Management Script

Manages a SQLite database to store and retrieve user commands and environment-based rules. 
It initializes tables to store user commands, environmental contexts, and dynamic rules for guiding 
task predictions. It supports storing input records, checking for repeated commands, and saving new 
rules if they do not already exist.

"""

def initialize_database():
    conn = sqlite3.connect('robot_assistants/rules.db')
    c = conn.cursor()

    c.execute('''
    CREATE TABLE IF NOT EXISTS input_base (
        id INTEGER PRIMARY KEY,
        user_command TEXT,
        environment_details TEXT,
        previous_command TEXT,
        next_command TEXT,
        last_environment TEXT,  -- Add the last_environment column
        timestamp DATETIME DEFAULT CURRENT_TIMESTAMP  
    )
    ''')

    c.execute('''
    CREATE TABLE IF NOT EXISTS rules_base (
        id INTEGER PRIMARY KEY,
        current_command TEXT,
        next_command TEXT,
        environment_details TEXT
    )
    ''')

    c.execute('CREATE INDEX IF NOT EXISTS idx_rules ON rules_base(current_command, next_command, environment_details)')

    conn.commit()
    conn.close()


def clear_database():
    conn = sqlite3.connect('robot_assistants/rules.db')
    c = conn.cursor()

 
    c.execute('DROP TABLE IF EXISTS input_base')
    c.execute('''
    CREATE TABLE IF NOT EXISTS input_base (
        id INTEGER PRIMARY KEY,
        user_command TEXT,
        environment_details TEXT,
        previous_command TEXT,
        next_command TEXT,
        last_environment TEXT,  -- Add the last_environment column
        timestamp DATETIME DEFAULT CURRENT_TIMESTAMP  
    )
    ''')

    c.execute('DELETE FROM rules_base')

    conn.commit()
    conn.close()
    print("Database cleared.")


def store_input_record(input_record):
    conn = sqlite3.connect('robot_assistants/rules.db')
    c = conn.cursor()

  
    context_details = f"Context: {', '.join(input_record['context'])}" if input_record.get('context') else "Context: N/A"
    context_items_details = "\n".join([f"Item: {item['name']}, State: {item['state']}, Weight: {item['weight']}"
                                       for item in input_record.get('context_items', [])])

    c.execute('''
    INSERT INTO input_base (user_command, environment_details, previous_command, next_command, last_environment)
    VALUES (?, ?, ?, ?, ?)
    ''', (
        input_record['user_command'],
        context_details,               
        input_record['previous_command'],
        input_record['next_command'],
        context_items_details           
    ))

    conn.commit()
    conn.close()


def is_repeated_command(user_command, environment_details, previous_command):
    conn = sqlite3.connect('robot_assistants/rules.db')
    c = conn.cursor()
    location = environment_details.get('location')
    time_of_day = environment_details.get('time')

    c.execute('''
    SELECT COUNT(*) FROM input_base
    WHERE user_command = ? 
    AND environment_details LIKE '%' || ? || '%'  
    AND previous_command = ?
    ''', (user_command, location, previous_command))
    count = c.fetchone()[0]
    conn.close()
    return count >= 3


def store_rule(current_command, next_command, environment_details):
    conn = sqlite3.connect('robot_assistants/rules.db')
    c = conn.cursor()


    c.execute('''
    SELECT COUNT(*) FROM rules_base
    WHERE current_command = ? AND next_command = ? AND environment_details = ?
    ''', (current_command, next_command, str(environment_details)))

    count = c.fetchone()[0]

    if count == 0:
        
        c.execute('''
        INSERT INTO rules_base (current_command, next_command, environment_details)
        VALUES (?, ?, ?)
        ''', (current_command, next_command, str(environment_details)))
    else:
        print("Duplicate rule detected, skipping insertion.")

    conn.commit()
    conn.close()


def get_all_rules():
    conn = sqlite3.connect('robot_assistants/rules.db')
    c = conn.cursor()
    c.execute('SELECT * FROM rules_base')
    rules = c.fetchall()
    conn.close()
    return rules


def get_all_input_records():
    conn = sqlite3.connect('robot_assistants/rules.db')
    c = conn.cursor()
    c.execute('SELECT * FROM input_base')
    input_records = c.fetchall()
    conn.close()
    return input_records


initialize_database()


initial_rules = [
    ('read a book', 'drink tea', {'location': 'living room', 'time': 'afternoon'}),
    ('collect package', 'open package', {'location': 'door', 'time': 'morning'}),
    ('make tea', 'drink tea', {'location': 'kitchen', 'time': 'evening'}),
    ('retrieve book', 'get tea leaves', {'location': 'living room', 'time': 'afternoon'})
]

for rule in initial_rules:
    store_rule(rule[0], rule[1], rule[2])

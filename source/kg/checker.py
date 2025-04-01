# checker.py
import sys
import difflib
from rdflib import RDF, RDFS
from nltk.corpus import wordnet as wn
from kg.loader import g, Namespace

EX = Namespace("http://example.org/")

def get_expected_object_type(predicate):
    query = f"""
    PREFIX ex: <{EX}>
    PREFIX rdf: <{RDF}>
    PREFIX rdfs: <{RDFS}>

    SELECT ?type WHERE {{
        ex:{predicate} ex:expectsObjectType ?type .
    }}
    """
    try:
        results = g.query(query)
        for row in results:
            obj_type = str(row.type).replace(str(EX), '').strip()
            return obj_type
    except Exception as e:
        print(f"Error querying expected object type for predicate '{predicate}': {e}")

    return None

def check_predicate_in_kg(predicate):
    query = f"""
    PREFIX ex: <{EX}>
    PREFIX rdf: <{RDF}>
    PREFIX rdfs: <{RDFS}>

    ASK {{
        ex:{predicate} a rdf:Property .
    }}
    """
    try:
        result = g.query(query)
        exists = False
        for row in result:
            if isinstance(row, bool):
                exists = row
            elif isinstance(row, tuple) and len(row) == 1 and isinstance(row[0], bool):
                exists = row[0]

        if exists:
           
            action_predicates = ["walk", "walktowards", "grab", "putin", "put", "give",
                                 "switchon", "switchoff", "open", "close"]
            if predicate.lower() in action_predicates:
                return (True, 'Action')
            else:
                return (True, 'Property')
        else:
            return (False, None)
    except Exception as e:
        print(f"Error querying KG for predicate '{predicate}': {e}")
        return (False, None)

def check_action_in_kg(action):
    query = f"""
    PREFIX ex: <{EX}>
    ASK {{
        ex:{action} a ex:Action .
    }}
    """
    try:
        result = g.query(query)
        exists = False
        for row in result:
            if isinstance(row, bool):
                exists = row
            elif isinstance(row, tuple) and len(row) == 1 and isinstance(row[0], bool):
                exists = row[0]

        return exists
    except Exception as e:
        print(f"Error executing query for action '{action}': {e}")
        return False

def check_object_in_kg(obj, expected_type):
    query = f"""
    PREFIX ex: <{EX}>
    ASK WHERE {{ ex:{obj} a ex:{expected_type} . }}
    """
    try:
        result = g.query(query)
        exists = False
        for row in result:
            if isinstance(row, bool):
                exists = row
            elif isinstance(row, tuple) and len(row) == 1 and isinstance(row[0], bool):
                exists = row[0]
        return exists
    except Exception as e:
        print(f"Error executing query for object '{obj}': {e}")
        return False

def get_available_actions():
    query = f"""
    PREFIX ex: <{EX}>
    SELECT ?action WHERE {{
        ?action a ex:Action .
    }}
    """
    actions = []
    try:
        results = g.query(query)
        for row in results:
            action_name = str(row.action).replace(str(EX), '').strip()
            actions.append(action_name)
        return actions
    except Exception as e:
        print(f"Error retrieving available actions: {e}")
    return actions

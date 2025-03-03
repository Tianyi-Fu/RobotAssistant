# kg/context_analysis.py
import re
from kg.loader import g
from config.config import OPERATED_OUTPUT


def read_entities_from_file(file_path):
    entities = set()
    pattern = re.compile(r"\((\w+)\)")
    with open(file_path, "r") as file:
        for line in file:
            match = pattern.findall(line)
            if match:
                entities.update(match)
    return entities

def get_item_context_and_weights(item):
    query = f"""
    PREFIX ex: <http://example.org/>
    SELECT ?context ?weight
    WHERE {{
      ex:{item} ex:hasContextWeight ?blankNode .
      ?blankNode ex:context ?context ;
                 ex:importanceWeight ?weight .
    }}
    """
    contexts = []
    weights = []
    for row in g.query(query):
        contexts.append(str(row['context']).split('/')[-1])
        weights.append(float(row['weight']))
    return contexts, weights

def calculate_context_relevance(entities):
    total_context_scores = {}
    for item in entities:
        contexts, weights = get_item_context_and_weights(item)
        for context, weight in zip(contexts, weights):
            if context not in total_context_scores:
                total_context_scores[context] = 0
            total_context_scores[context] += weight
    return total_context_scores

def get_top_items_and_furniture_for_context(context, limit=7):
    context_name = context
    query = f"""
    PREFIX ex: <http://example.org/>
    SELECT ?item ?state ?weight
    WHERE {{
        ?item ex:hasContextWeight ?blankNode .
        ?blankNode ex:context ex:{context_name} ;
                   ex:importanceWeight ?weight .
        OPTIONAL {{ ?item ex:state ?state }}
    }}
    ORDER BY DESC(?weight)
    """
    results = []
    unique_items = set()

    for row in g.query(query):
        item = str(row["item"]).split('/')[-1]
        if item not in unique_items and len(results) < limit:
            unique_items.add(item)
            state = str(row["state"]).split('/')[-1] if row["state"] else "No state information"
            weight = round(float(row["weight"]), 2)
            results.append({"name": item, "state": state, "weight": weight})
    return results

def get_results():

    operated_entities = read_entities_from_file(OPERATED_OUTPUT)
    print(operated_entities)
    context_relevance_scores = calculate_context_relevance(operated_entities)

    top_context = None
    top_items = []

    if context_relevance_scores:
        sorted_contexts = sorted(context_relevance_scores.items(), key=lambda x: x[1], reverse=True)
        top_context = sorted_contexts[0][0]
        top_items = get_top_items_and_furniture_for_context(top_context)

    return top_context, top_items

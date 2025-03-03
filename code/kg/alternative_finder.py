# kg/alternative_finder.py
import difflib
from nltk.corpus import wordnet as wn
from kg.loader import g, Namespace
from kg.checker import get_available_actions

EX = Namespace("http://example.org/")

def find_alternative_object(expected_type, contexts, original_object):
    substring_matched_objects = []
    similar_objects = []

    for context in contexts:
        alternatives = query_alternative_objects_in_context(expected_type, context)
        for alt, weight in alternatives:
            if original_object.lower() in alt.lower():
                substring_matched_objects.append((alt, weight))

    if substring_matched_objects:
        substring_matched_objects.sort(
            key=lambda x: (x[1], difflib.SequenceMatcher(None, original_object.lower(), x[0].lower()).ratio()),
            reverse=True
        )
        return substring_matched_objects[0][0]

    for context in contexts:
        alternatives = query_alternative_objects_in_context(expected_type, context)
        for alt, weight in alternatives:
            similarity = difflib.SequenceMatcher(None, original_object.lower(), alt.lower()).ratio()
            similar_objects.append((alt, similarity, weight))

    if similar_objects:
        similar_objects.sort(key=lambda x: (x[1], x[2]), reverse=True)
        return similar_objects[0][0]

    alternative = query_alternative_in_any_context(expected_type)
    if alternative:
        return alternative

    alternative = find_wordnet_similar_object(expected_type, original_object)
    if alternative:
        return alternative

    return None

def find_alternative_action(original_action):
    actions = get_available_actions()
    if not actions:
        return None

    best_match = None
    best_ratio = 0.0
    for act in actions:
        ratio = difflib.SequenceMatcher(None, original_action.lower(), act.lower()).ratio()
        if ratio > best_ratio:
            best_ratio = ratio
            best_match = act

    if best_ratio > 0.5:
        return best_match

    return None

def query_alternative_objects_in_context(expected_type, context):
    query = f"""
    PREFIX ex: <http://example.org/>
    SELECT ?obj ?weight WHERE {{
        ex:{context} a ex:Context .
        ?obj a ex:{expected_type} ;
             ex:hasContextWeight ?blankNode .
        ?blankNode ex:context ex:{context} ;
                   ex:importanceWeight ?weight .
    }}
    ORDER BY DESC(?weight)
    """
    alternatives = []
    try:
        results = g.query(query)
        for row in results:
            obj_uri = str(row.obj)
            obj_name = obj_uri.split('/')[-1]
            weight = float(row.weight)
            alternatives.append((obj_name, weight))
    except Exception as e:
        print(f"Error querying alternative objects in context '{context}': {e}")
    return alternatives

def query_alternative_in_any_context(expected_type):
    query = f"""
    PREFIX ex: <http://example.org/>
    SELECT ?obj ?weight WHERE {{
        ?obj a ex:{expected_type} ;
             ex:hasContextWeight ?blankNode .
        ?blankNode ex:importanceWeight ?weight .
    }}
    ORDER BY DESC(?weight)
    LIMIT 1
    """
    try:
        result = g.query(query)
        for row in result:
            obj_uri = str(row.obj)
            obj_name = obj_uri.split('/')[-1]
            return obj_name
    except Exception as e:
        print(f"Error querying alternative objects in any context: {e}")
    return None

def find_wordnet_similar_object(expected_type, original_object):
    query = f"""
    PREFIX ex: <http://example.org/>
    SELECT ?obj WHERE {{
        ?obj a ex:{expected_type} .
    }}
    """
    objects = []
    try:
        results = g.query(query)
        for row in results:
            obj_uri = str(row.obj)
            obj_name = obj_uri.split('/')[-1]
            objects.append(obj_name)
    except Exception as e:
        print(f"Error querying objects for WordNet similarity: {e}")
        return None

    similar_objects = []
    synsets_orig = wn.synsets(original_object)
    for obj in objects:
        synsets_obj = wn.synsets(obj)
        max_similarity = 0
        for syn_orig in synsets_orig:
            for syn_obj in synsets_obj:
                similarity = syn_orig.wup_similarity(syn_obj)
                if similarity and similarity > max_similarity:
                    max_similarity = similarity
        if max_similarity > 0:
            similar_objects.append((obj, max_similarity))

    if similar_objects:
        similar_objects.sort(key=lambda x: x[1], reverse=True)
        return similar_objects[0][0]

    return None

def find_alternative_predicate(original_predicate):

    available_predicates = [
        "switched_on", "switched_off", "open", "closed",
        "has", "changed", "inside", "in", "location", "on"
    ]


    best_match = None
    best_ratio = 0.0
    for pred in available_predicates:
        ratio = difflib.SequenceMatcher(None, original_predicate.lower(), pred.lower()).ratio()
        if ratio > best_ratio:
            best_ratio = ratio
            best_match = pred

    if best_ratio > 0.5:
        return best_match


    synonyms = set()
    for syn in wn.synsets(original_predicate):
        for lemma in syn.lemma_names():
            synonyms.add(lemma.lower())

    best_syn_match = None
    best_syn_ratio = 0.0
    for pred in available_predicates:
        for syn in synonyms:
            ratio = difflib.SequenceMatcher(None, syn, pred.lower()).ratio()
            if ratio > best_syn_ratio:
                best_syn_ratio = ratio
                best_syn_match = pred

    if best_syn_ratio > 0.5:
        return best_syn_match
    else:
        return None

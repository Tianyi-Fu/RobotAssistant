import requests
from nltk.corpus import wordnet as wn



def query_conceptnet(keyword):
    url = f"http://api.conceptnet.io/c/en/{keyword}"
    response = requests.get(url).json()
    related_keywords = set()

    for edge in response.get("edges", []):
        if "rel" in edge and edge["rel"]["label"] in ["RelatedTo", "Synonym", "UsedFor", "IsA"]:
            related_keywords.add(edge["end"]["label"])

    return list(related_keywords)



context_keywords = {
    "ReadingContext": query_conceptnet("reading") + ["book", "literature", "study", "learn"],
    "DiningContext": query_conceptnet("dining") + ["eat", "food", "meal", "drink"],
    "RelaxationContext": query_conceptnet("relaxation") + ["rest", "lounge", "sofa", "sleep"],
    "CleaningContext": query_conceptnet("cleaning") + ["wash", "sanitize", "mop", "sweep"],
    "CookingContext": query_conceptnet("cooking") + ["cook", "stove", "bake", "fry", "prepare food"],
    "EntertainmentContext": query_conceptnet("entertainment") + ["play", "watch", "game", "music", "movie"],
    "StudyingContext": query_conceptnet("studying") + ["study", "write", "work", "desk", "computer"],
    "StorageContext": query_conceptnet("storage") + ["store", "hold", "contain", "organize", "keep safe"],
    "LightingContext": query_conceptnet("lighting") + ["light", "lamp", "bright", "illumination", "shine"],
    "WorkContext": query_conceptnet("work") + ["office", "task", "job", "productivity", "workspace"]
}

print("Generated Context Keywords:", context_keywords)


def get_main_synset(item):
    words = item.replace("_", " ").split()
    synsets = [wn.synsets(word)[0] for word in words if wn.synsets(word)]
    return synsets if synsets else None



def context_similarity_with_weight(item, context_keywords):
    item_synsets = get_main_synset(item)
    scores = {}

    for context, keywords in context_keywords.items():
        context_scores = []
        for keyword in keywords:
            keyword_synset = get_main_synset(keyword)
            if item_synsets and keyword_synset:
                # Calculate average similarity
                score = max((item_synset.wup_similarity(keyword_synset[0]) or 0) for item_synset in item_synsets)
                context_scores.append(score)


        scores[context] = sum(context_scores) / len(context_scores) if context_scores else 0
    return scores


# items = [
#     "cellphone",
#     "folder",
#     "book",
#     "mug",
#     "notes",
#     "magazine",
#     "milk",
#
#     "chicken",
#     "cutlets",
#     "alcohol",
#     "juice",
#     "apple",
#     "bananas",
#     "peach",
#     "cereal",
#     "cupcake",
#     "crackers",
#     "pound_cake",
#     "plate",
#     "bookshelf",
#     "microwave",
#     "fridge",
#     "sofa",
#     "kitchen_table",
#     "desk",
#     "kitchen_counter",
#     "coffee_table",
#     "dish_bowl",
#     "tv_stand",
#     "amplifier",
#     "table_lamp"
#
# ]
items=["water_glass"]



context_weights = {}
for item in items:
    context_weights[item] = context_similarity_with_weight(item, context_keywords)

for item, weights in context_weights.items():
    best_context = max(weights, key=weights.get)
    best_weight = weights[best_context]
    print(f"Context weights for '{item}': {weights}")
    print(f"'{item}' is most associated with '{best_context}' with weight: {best_weight:.2f}\n")

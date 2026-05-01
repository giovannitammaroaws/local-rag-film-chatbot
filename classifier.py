LABELS = {
    "factual":        "Wants a specific fact about a film",
    "recommendation": "Wants personalized recommendations",
    "comparison":     "Wants to compare two films",
}

# Keyword-based router: maps a query to one of three intent labels.
def classify(query: str) -> str:
    q = query.lower()
    if any(w in q for w in ["chi ha", "quando", "diretto", "anno", "budget", "oscar", "quanti"]):
        return "factual"
    if any(w in q for w in ["meglio", "vs", "confronta", "differenza", "oppure"]):
        return "comparison"
    return "recommendation"

# Returns a human-readable description for a given intent label.
def label_description(label: str) -> str:
    return LABELS[label]

"""Medical knowledge tools — symptom checking, drug interactions, literature search."""

RED_FLAG_SYMPTOMS = {
    "chest pain",
    "shortness of breath",
    "severe headache",
    "loss of consciousness",
    "uncontrolled bleeding",
}


def check_symptoms(symptoms: list[str]) -> dict:
    if not symptoms:
        return {
            "urgency_score": 1,
            "recommended_care_level": "self-care",
            "rationale": "No symptoms provided. Monitor and consult a provider if concerns arise.",
            "confidence": 0.3,
        }

    normalized = [s.lower().strip() for s in symptoms]
    red_flags = [s for s in normalized if s in RED_FLAG_SYMPTOMS or any(rf in s for rf in RED_FLAG_SYMPTOMS)]

    if red_flags:
        return {
            "urgency_score": 9,
            "recommended_care_level": "emergency",
            "rationale": f"Red-flag symptoms detected: {', '.join(red_flags)}. Seek immediate medical attention.",
            "confidence": 0.9,
        }

    if "fever" in normalized:
        return {
            "urgency_score": 5,
            "recommended_care_level": "primary_care",
            "rationale": "Fever present. Schedule a primary care visit if persistent or worsening.",
            "confidence": 0.7,
        }

    return {
        "urgency_score": 3,
        "recommended_care_level": "self-care",
        "rationale": "Symptoms appear mild. Rest, hydrate, and monitor. See a provider if symptoms persist >48h.",
        "confidence": 0.6,
    }


def lookup_drug_interactions(query: str) -> str:
    return (
        f"Drug Interaction Check for: '{query}'\n"
        "Note: Connect to a real drug interaction API (e.g., RxNorm, DrugBank) in production.\n"
        "No major interactions found in demo dataset."
    )


def search_literature(query: str) -> str:
    return (
        f"Literature Search: '{query}'\n"
        "Note: Connect to PubMed, Semantic Scholar, or institutional databases in production.\n"
        "Demo result: 3 relevant articles found (placeholder)."
    )

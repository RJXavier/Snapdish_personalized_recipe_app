"""Dietary preference filtering.

Recipes only store ingredient names, so preferences are enforced with keyword
rules over those names. This is a best-effort filter, not an allergen guarantee.
"""
import re
from typing import Dict, Iterable, List, Set

_MEAT = [
    "beef", "steak", "brisket", "veal", "sirloin", "hamburger", "ground chuck", "pork", "bacon",
    "ham", "sausage", "prosciutto", "pepperoni", "salami", "chorizo", "pancetta", "lard",
    "chicken", "turkey", "lamb", "duck", "meat", "meatball", "venison", "rib", "gelatin",
    "hot dog", "kielbasa", "bratwurst", "roast",
]
_SEAFOOD = [
    "fish", "salmon", "tuna", "shrimp", "prawn", "crab", "crabmeat", "lobster", "clam", "oyster",
    "mussel", "scallop", "anchovy", "anchovies", "cod", "tilapia", "halibut", "sardine", "squid",
    "calamari", "catfish", "trout", "snapper", "worcestershire sauce",
]
_DAIRY = [
    "milk", "butter", "cheese", "cream", "yogurt", "yoghurt", "whey", "ghee", "buttermilk",
    "parmesan", "mozzarella", "cheddar", "feta", "ricotta", "half-and-half", "custard",
    "margarine", "velveeta", "provolone", "romano", "gruyere", "mascarpone", "ice cream",
]
_EGG = ["egg", "mayonnaise", "mayo", "meringue"]
_NUTS = [
    "nut", "almond", "walnut", "pecan", "cashew", "pistachio", "hazelnut", "macadamia",
    "peanut", "pine nut", "nutella", "marzipan", "praline",
]
_GLUTEN = [
    "flour", "bread", "breadcrumb", "pasta", "noodle", "spaghetti", "macaroni", "wheat",
    "barley", "rye", "couscous", "tortilla", "cracker", "soy sauce", "beer", "bun", "pita",
    "bagel", "biscuit", "croissant", "lasagna", "penne", "fettuccine", "linguine", "orzo",
    "bulgur", "semolina", "seitan", "pastry", "pie crust", "pie shell", "dough", "cake mix",
    "crouton", "roll", "stuffing", "pancake mix", "baguette", "ramen", "wonton",
]

# Phrases that contain a keyword above but are fine for that rule.
_SAFE_PHRASES: Dict[str, List[str]] = {
    "dairy": [
        "coconut milk", "almond milk", "soy milk", "oat milk", "rice milk", "peanut butter",
        "almond butter", "cashew butter", "cocoa butter", "apple butter", "butter bean",
        "cream of tartar", "coconut cream", "creamed corn", "cream-style corn",
    ],
    "gluten": [
        "rice flour", "almond flour", "corn flour", "cornflour", "coconut flour",
        "rice noodle", "corn tortilla", "gluten-free", "buckwheat", "egg roll wrapper",
    ],
    "nuts": ["nutmeg", "coconut", "butternut", "water chestnut", "doughnut", "donut"],
    "meat": ["roasted", "liquid smoke"],
}

_BEEF = ["beef", "steak", "brisket", "veal", "sirloin", "hamburger", "ground chuck"]
_PORK = [
    "pork", "bacon", "ham", "sausage", "prosciutto", "pepperoni", "salami", "chorizo",
    "pancetta", "lard", "kielbasa", "bratwurst",
]
_SHRIMP = ["shrimp", "prawn"]

# preference label (lower-case) -> list of (rule group, keywords)
_RULES = {
    "vegan": [("meat", _MEAT), ("seafood", _SEAFOOD), ("dairy", _DAIRY), ("egg", _EGG),
              ("honey", ["honey"])],
    "vegetarian": [("meat", _MEAT), ("seafood", _SEAFOOD)],
    "dairy-free": [("dairy", _DAIRY)],
    "nut-free": [("nuts", _NUTS)],
    "gluten-free": [("gluten", _GLUTEN)],
    "no beef": [("meat", _BEEF)],
    "no pork": [("meat", _PORK)],
    "no shrimp": [("seafood", _SHRIMP)],
}


def _compile(keywords: Iterable[str]) -> re.Pattern:
    parts = [re.escape(k) for k in sorted(set(keywords), key=len, reverse=True)]
    # whole words only, tolerating a plural ending ("eggs", "tomatoes")
    return re.compile(r"\b(?:" + "|".join(parts) + r")(?:s|es)?\b")


_COMPILED = {
    pref: [(group, _compile(words)) for group, words in rules] for pref, rules in _RULES.items()
}


def parse_preferences(raw) -> List[str]:
    """Accept a ','-separated string or a list and return clean labels."""
    if not raw:
        return []
    items = raw.split(",") if isinstance(raw, str) else list(raw)
    return [str(item).strip() for item in items if str(item).strip()]


def _strip_safe_phrases(name: str, group: str) -> str:
    for phrase in _SAFE_PHRASES.get(group, []):
        name = name.replace(phrase, " ")
    return name


def violated_preferences(ingredient_names: Iterable[str], preferences: Iterable[str]) -> Set[str]:
    """Return the preferences that a recipe with these ingredients breaks."""
    names = [str(n).lower() for n in ingredient_names]
    broken: Set[str] = set()
    for pref in preferences:
        rules = _COMPILED.get(pref.strip().lower())
        if not rules:
            continue
        for group, pattern in rules:
            if any(pattern.search(_strip_safe_phrases(n, group)) for n in names):
                broken.add(pref)
                break
    return broken


def is_allowed(ingredient_names: Iterable[str], preferences: Iterable[str]) -> bool:
    return not violated_preferences(ingredient_names, preferences)

"""Unit tests for the dietary filter and the detector's label mapping."""
from load_json import match_base_ingredient
from services.detection import KNOWN_INGREDIENTS, FoodIngredientDetector, map_class_name
from services.diet import is_allowed, violated_preferences
from services.recipe_service import decode_steps, encode_steps


def test_vegan_blocks_animal_products():
    assert not is_allowed(["ground beef", "onion"], ["Vegan"])
    assert not is_allowed(["eggs", "flour"], ["Vegan"])
    assert not is_allowed(["honey", "oats"], ["Vegan"])
    assert is_allowed(["eggplant", "coconut milk", "peanut butter", "tofu"], ["Vegan"])


def test_other_preferences():
    assert not is_allowed(["bacon"], ["No pork"])
    assert is_allowed(["graham cracker crumbs"], ["No pork"])       # "ham" inside a word
    assert not is_allowed(["jumbo shrimp"], ["No Shrimp"])
    assert not is_allowed(["walnuts"], ["Nut-free"])
    assert is_allowed(["nutmeg", "coconut", "butternut squash"], ["Nut-free"])
    assert not is_allowed(["all-purpose flour"], ["Gluten-free"])
    assert is_allowed(["rice flour", "corn tortillas"], ["Gluten-free"])
    assert not is_allowed(["cream cheese"], ["Dairy-free"])
    assert is_allowed(["cream of tartar", "almond milk"], ["Dairy-free"])
    assert violated_preferences(["beef", "milk"], ["No beef", "Dairy-free", "Nut-free"]) == {
        "No beef", "Dairy-free"}
    assert is_allowed(["beef"], [])


def test_steps_round_trip_keeps_commas():
    steps = ["Chop the onion, carrot and celery", "Fry until soft"]
    assert decode_steps(encode_steps(steps)) == steps
    assert decode_steps("one,two") == ["one", "two"]   # legacy comma-joined rows
    assert decode_steps(None) == []


def test_detector_label_mapping():
    assert map_class_name("Potato") == "potatoes"
    assert map_class_name("tomato") == "tomatoes"
    assert map_class_name("chicken_breast") == "chicken breast"
    assert map_class_name("eggs") == "egg"
    # every label of the bundled model maps to an ingredient in the database
    labels = ["Cooked_Rice", "Egg", "Tofu", "Onion", "Carrot", "Tomato", "Capsicum",
              "Chicken_Breast", "Prawn", "Butter", "Potato", "Beef_Steak"]
    assert sorted(map_class_name(label) for label in labels) == sorted(KNOWN_INGREDIENTS)
    detector = FoodIngredientDetector()
    merged = detector.process_detection([
        {"class_name": "beef", "confidence": 0.4},
        {"class_name": "Beef", "confidence": 0.9},
        {"class_name": "egg", "confidence": 0.5},
    ])
    assert merged == [{"class_name": "beef", "confidence": 0.9},
                      {"class_name": "egg", "confidence": 0.5}]


def test_seed_ingredient_matching():
    assert match_base_ingredient("ground beef") == "beef"
    assert match_base_ingredient("cherry tomatoes") == "tomatoes"
    assert match_base_ingredient("boneless skinless chicken breasts") == "chicken breast"
    assert match_base_ingredient("eggs") == "egg"
    assert match_base_ingredient("eggplant") is None
    assert match_base_ingredient("rice vinegar") is None
    assert match_base_ingredient("beef broth") is None

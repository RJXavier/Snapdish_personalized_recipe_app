"""End-to-end API tests. Run from the server folder with:  pytest"""
from conftest import signup_and_login

from services.diet import is_allowed


def test_requires_token(client):
    assert client.get("/recipe/recipesList").json()["code"] == 1001
    assert client.get("/health").json() == {"status": "ok"}


def test_demo_login_and_profile(client):
    body = client.post("/auth/login", json={"username": "demo", "password": "demo1234"}).json()
    assert body["code"] == 0
    headers = {"Authorization": f"Bearer {body['data']['access_token']}"}
    me = client.get("/auth/me", headers=headers).json()["data"]
    assert me["birthday"] == "1998-05-17"
    assert isinstance(me["age"], int) and me["age"] >= 27
    assert me["user_recipe_count"] == 0


def test_wrong_password_rejected(client):
    body = client.post("/auth/login", json={"username": "demo", "password": "nope"}).json()
    assert body["code"] != 0


def test_signup_validation(client):
    base = {"username": "valid_user", "nickname": "Valid", "email": "valid@example.com",
            "password": "secret123", "gender": "Other", "birthday": "1990-01-01",
            "food_preferences": []}
    assert client.post("/auth/signup", json={**base, "password": "123"}).json()["code"] == 1003
    assert client.post("/auth/signup", json={**base, "email": "nope"}).json()["code"] == 1004
    assert client.post("/auth/signup", json={**base, "birthday": "27"}).json()["code"] == 1011
    assert client.post("/auth/signup", json=base).json()["code"] == 0
    # duplicates are reported with a readable message instead of a database error
    duplicate = client.post("/auth/signup", json={**base, "username": "other_user",
                                                  "email": "other@example.com"}).json()
    assert duplicate["code"] != 0 and "Nickname" in duplicate["message"]


def test_update_profile_keeps_birthday(client):
    headers = signup_and_login(client, "profile_user")
    update = {"nickname": "Renamed", "email": "renamed@example.com", "gender": "Female",
              "birthday": "1991-12-31", "food_preferences": "Vegan,Nut-free"}
    assert client.post("/auth/updateProfile", json=update, headers=headers).json()["code"] == 0
    me = client.get("/auth/me", headers=headers).json()["data"]
    assert me["birthday"] == "1991-12-31"
    assert me["nickname"] == "Renamed"
    assert me["food_preferences"] == "Vegan,Nut-free"
    # an age or empty value is rejected rather than stored as the birthday
    for bad in ("34", ""):
        body = client.post("/auth/updateProfile", json={**update, "birthday": bad},
                           headers=headers).json()
        assert body["code"] == 1011
    assert client.get("/auth/me", headers=headers).json()["data"]["birthday"] == "1991-12-31"


def test_change_password(client):
    headers = signup_and_login(client, "pw_user", password="oldpass1")
    wrong = client.post("/auth/changePassword", headers=headers,
                        json={"current_password": "bad", "new_password": "newpass1"}).json()
    assert wrong["code"] != 0
    ok = client.post("/auth/changePassword", headers=headers,
                     json={"current_password": "oldpass1", "new_password": "newpass1"}).json()
    assert ok["code"] == 0
    assert client.post("/auth/login", json={"username": "pw_user", "password": "oldpass1"}) \
        .json()["code"] != 0
    assert client.post("/auth/login", json={"username": "pw_user", "password": "newpass1"}) \
        .json()["code"] == 0


def test_recipe_list_and_detail_steps(client):
    headers = signup_and_login(client, "reader", preferences=[])
    listing = client.get("/recipe/recipesList", params={"page": 1, "page_size": 5},
                         headers=headers).json()["data"]
    assert len(listing["recipes"]) == 5 and listing["total"] > 400
    recipe_id = listing["recipes"][0]["recipe_id"]
    detail = client.get(f"/recipe/recipeIngredients/{recipe_id}", headers=headers).json()["data"]
    # the first recipe has a step containing commas; it must stay one step
    assert any("," in step for step in detail["cook_steps"])
    assert len(detail["cook_steps"]) == 11
    assert client.get("/recipe/recipeIngredients/999999", headers=headers).json()["code"] == 1013
    history = client.get("/recipe/historyRecipes", headers=headers).json()["data"]
    assert [r["recipe_id"] for r in history] == [recipe_id]


def test_new_user_gets_feed_and_empty_lists(client):
    headers = signup_and_login(client, "newbie", preferences=["Vegan"])
    feed = client.post("/recipe/feedRecipe", json={"ingredients": []}, headers=headers).json()
    assert feed["code"] == 0 and len(feed["data"]["recipes"]) > 0
    for path in ("historyRecipes", "collectRecipes", "historyIngredients"):
        body = client.get(f"/recipe/{path}", headers=headers).json()
        assert body["code"] == 0 and body["data"] == []


def test_dietary_preferences_are_enforced(client):
    vegan = signup_and_login(client, "vegan_user", preferences=["Vegan"])
    anything = signup_and_login(client, "omnivore", preferences=[])
    payload = {"ingredients": ["beef", "onion"], "page": 1, "page_size": 50}

    omnivore_names = [
        i["ingredient_name"]
        for r in client.post("/recipe/recipesByIngredients", json=payload,
                             headers=anything).json()["data"]["recipes"]
        for i in r["ingredients"]
    ]
    assert "beef" in omnivore_names

    for path, body in (("recipesByIngredients", payload),
                       ("feedRecipe", {"ingredients": ["beef", "onion"]})):
        recipes = client.post(f"/recipe/{path}", json=body, headers=vegan).json()["data"]["recipes"]
        assert recipes, path
        for recipe in recipes:
            names = [i["ingredient_name"] for i in recipe["ingredients"]]
            assert is_allowed(names, ["Vegan"]), (path, recipe["recipe_name"], names)
            assert "beef" not in names


def test_recommendations_rank_by_selected_ingredients(client):
    headers = signup_and_login(client, "ranker", preferences=[])
    recipes = client.post("/recipe/feedRecipe", json={"ingredients": ["egg", "butter"]},
                          headers=headers).json()["data"]["recipes"]
    scores = [r["match_ratio"] for r in recipes]
    assert scores == sorted(scores, reverse=True)
    top = {i["ingredient_name"] for i in recipes[0]["ingredients"]}
    assert {"egg", "butter"} <= top
    searched = client.get("/recipe/historyIngredients", headers=headers).json()["data"]
    assert {s["ingredient_name"] for s in searched} == {"egg", "butter"}


def test_save_and_unsave_recipe(client):
    headers = signup_and_login(client, "saver", preferences=[])
    recipe_id = client.get("/recipe/recipesList", headers=headers).json()["data"]["recipes"][0]["recipe_id"]
    client.post("/auth/collectRecipe", json={"recipe_id": recipe_id, "is_collect": True},
                headers=headers)
    saved = client.get("/recipe/collectRecipes", headers=headers).json()["data"]
    assert [r["recipe_id"] for r in saved] == [recipe_id]
    assert client.get("/auth/me", headers=headers).json()["data"]["user_collect_recipe_count"] == 1
    client.post("/auth/collectRecipe", json={"recipe_id": recipe_id, "is_collect": False},
                headers=headers)
    assert client.get("/recipe/collectRecipes", headers=headers).json()["data"] == []


def test_upload_rules_and_path_safety(client):
    headers = signup_and_login(client, "uploader", preferences=[])
    bad = client.post("/upload", files={"file": ("notes.txt", b"hello", "text/plain")},
                      headers=headers).json()
    assert bad["code"] == 1020
    good = client.post("/upload", files={"file": ("fridge.jpg", b"\xff\xd8\xff fake", "image/jpeg")},
                       headers=headers).json()
    name = good["data"]["filename"]
    assert "/" not in name and "\\" not in name
    # arbitrary server paths can no longer be passed to the detector
    for path in ("/etc/passwd", "../main.py", "C:\\Windows\\win.ini"):
        body = client.post("/recipe/detectionIngredients", json={"ingredients_img": path},
                           headers=headers).json()
        assert body["code"] == 1000

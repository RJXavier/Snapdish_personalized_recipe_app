# The Pantry — AI recipe recommendations from what's in your fridge

**The Pantry** is a Flutter mobile app with a FastAPI backend. Take a photo of your
ingredients (or pick them from a list) and get recipes ranked for you, filtered by your
dietary preferences.

- **Ingredient recognition** — a YOLOv10-Nano model detects 12 common ingredients in a photo.
- **Personalised recommendations** — content-based scoring over each recipe's ingredients,
  using what you selected, what you saved and what you viewed.
- **Dietary preferences** — Vegan, Gluten-free, Dairy-free, Nut-free, No beef, No pork,
  No shrimp. Recipes that break a preference are never shown.
- **Accounts** — sign up, log in (JWT), edit your profile, change your password.
- **Saved recipes and history** — favourite recipes, and see the recipes and ingredients
  you used most.

<!--
## Screenshots

Capture these with the app running (see docs/screenshots/README.md), then remove this
comment so the table shows on GitHub.

| Login | Home | Pick ingredients |
|---|---|---|
| ![Login](docs/screenshots/01_login.png) | ![Home](docs/screenshots/02_home.png) | ![Ingredients](docs/screenshots/03_ingredients.png) |

| Snap your food | Recommended recipes | Recipe details | Profile |
|---|---|---|---|
| ![Snap](docs/screenshots/04_snap.png) | ![Recipes](docs/screenshots/05_recipes.png) | ![Details](docs/screenshots/06_recipe_details.png) | ![Profile](docs/screenshots/07_profile.png) |
-->

## Tech stack

| Layer | Technology |
|---|---|
| Mobile app | Flutter (Dart), `dio`, `image_picker`, `shared_preferences` |
| API | FastAPI, SQLAlchemy |
| Database | MySQL, or SQLite for a zero-setup local run |
| Detection | Ultralytics YOLOv10-Nano (`server/best.pt`) |
| Auth | JWT (HS256), bcrypt password hashes |

```
Flutter app ──HTTP/JSON──▶ FastAPI ──▶ MySQL / SQLite
                              │
                              ├─▶ YOLOv10-Nano  (photo → ingredients)
                              └─▶ Recommender   (ingredients + history → ranked recipes)
```

## Quick start

### 1. Backend

Requires Python 3.10+.

```bash
cd server
python -m venv venv
venv\Scripts\activate            # macOS/Linux: source venv/bin/activate
pip install -r requirements.txt
python load_json.py              # creates the tables and loads 499 recipes
uvicorn main:app --host 0.0.0.0 --port 7777
```

`load_json.py` also creates a demo account the first time: **`demo` / `demo1234`**.

Check it is running at <http://localhost:7777/health>. Interactive API docs are at
<http://localhost:7777/docs>.

With no configuration the server stores data in `server/rec_app.db` (SQLite). To use
MySQL instead, create an empty database and point the server at it:

```bash
copy .env.example .env           # macOS/Linux: cp .env.example .env
# then edit .env:
# DATABASE_URL=mysql+pymysql://root:your_password@localhost:3306/rec_app
python load_json.py
```

> `ultralytics` pulls in PyTorch, which is a large download. Everything except photo
> detection works without it, so you can remove that line from `requirements.txt` for a
> quick try.

### 2. Mobile app

Requires the Flutter SDK (Dart 3.8+).

```bash
flutter pub get
flutter run
```

The app needs to know where the backend is. The default suits the Android emulator;
override it for anything else:

| Target | Command |
|---|---|
| Android emulator | `flutter run` (uses `http://10.0.2.2:7777`) |
| iOS simulator | `flutter run --dart-define=API_URL=http://127.0.0.1:7777` |
| Real device on the same Wi-Fi | `flutter run --dart-define=API_URL=http://<your-computer-ip>:7777` |

Log in with the demo account or create your own.

## Configuration

All settings are optional environment variables, read from `server/.env`
(see [`server/.env.example`](server/.env.example)).

| Variable | Default | Purpose |
|---|---|---|
| `DATABASE_URL` | SQLite file `server/rec_app.db` | SQLAlchemy database URL |
| `JWT_SECRET_KEY` | generated once into `server/.jwt_secret` | Signs login tokens |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | `1440` | Login lifetime |
| `MAX_UPLOAD_MB` | `10` | Largest accepted photo |
| `MODEL_PATH` | `server/best.pt` | YOLO weights |

## How recommendations work

Each recipe is described by its set of ingredients. For a request, every recipe that
passes the user's dietary filter gets three scores between 0 and 1:

| Signal | Weight | Meaning |
|---|---|---|
| Selected ingredients | 60% | Share of the ingredients you picked that the recipe uses |
| Saved recipes | 30% | Overlap with the most common ingredients in your favourites |
| History | 10% | How often you viewed the recipe and searched for its ingredients |

The weighted total is scaled by the best score available to that user, so a recipe that
uses everything a new user selected scores 1.0. A user with no signals at all simply
gets recipes that fit their diet. The code is in
[`server/services/recommend_service.py`](server/services/recommend_service.py).

**Dietary filtering** works from keyword rules over ingredient names
([`server/services/diet.py`](server/services/diet.py)), because the dataset has no
allergen labels. It is a best-effort filter and not a substitute for reading labels if
you have an allergy.

## API overview

Every response is `{"code": 0, "message": "...", "data": ...}`; a non-zero `code` is an
error. All routes except login, signup and `/health` need `Authorization: Bearer <token>`.

| Method | Path | Description |
|---|---|---|
| POST | `/auth/signup` | Create an account |
| POST | `/auth/login` | Get an access token |
| GET | `/auth/me` | Profile, age and usage counters |
| POST | `/auth/updateProfile` | Update name, email, gender, birthday, preferences |
| POST | `/auth/changePassword` | Change password (needs the current one) |
| POST | `/auth/collectRecipe` | Save or un-save a recipe |
| POST | `/upload` | Upload a photo (`.jpg`, `.jpeg`, `.png`) |
| POST | `/recipe/detectionIngredients` | Detect ingredients in an uploaded photo |
| POST | `/recipe/feedRecipe` | Personalised recommendations |
| POST | `/recipe/recipesByIngredients` | Recipes containing given ingredients, paginated |
| GET | `/recipe/recipesList` | All recipes that fit the user's diet, paginated |
| GET | `/recipe/recipeIngredients/{id}` | Recipe details and steps |
| GET | `/recipe/allIngredientsWithCategories` | Selectable ingredients |
| GET | `/recipe/historyRecipes` · `/recipe/historyIngredients` · `/recipe/collectRecipes` | History and favourites |

## Tests

```bash
cd server
pip install pytest httpx
pytest                 # API, dietary filter and detector tests on a temporary database

cd ..
flutter analyze
flutter test           # model parsing tests
```

## Project structure

```
lib/                    Flutter app
  api/                  HTTP calls
  common/               models, networking, config (server URL)
  screens/              UI
  services/             session handling
server/                 FastAPI backend
  core/                 configuration and database session
  models/               SQLAlchemy tables and response types
  routes/               HTTP endpoints
  services/             detection, recommender, dietary filter, users, recipes
  test/                 pytest suite and sample photos
  load_json.py          database seeding
  best.pt               YOLOv10-Nano weights (Git LFS)
  fridge_recipes.recipes.json   recipe dataset
```

Images and model weights are stored with [Git LFS](https://git-lfs.com); run
`git lfs install` once before cloning.

## Notes for production use

This is a university capstone project. Before deploying it publicly you would want
HTTPS (the Android and iOS configs currently allow plain HTTP so the app can reach a
development server), rate limiting on login, and database migrations.

## Team

Seven Yue, Cheng Fei, Jing Cong, Michael Le, Raj Xavier Rozario, Xiaowen Wu —
Future Interns Team, University of Wollongong capstone project.
Supervisor: Dr. Hui Luo.

## License

[MIT](LICENSE) © 2025 Future Interns Team

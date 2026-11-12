# Screenshots

The main README has a screenshot table that expects these files in this folder:

| File | Screen |
|---|---|
| `01_login.png` | Login |
| `02_home.png` | Home menu |
| `03_ingredients.png` | Select ingredients |
| `04_snap.png` | Snap your food, after analysing a photo |
| `05_recipes.png` | Recommended recipes |
| `06_recipe_details.png` | Recipe details sheet |
| `07_profile.png` | Profile |

With the backend running and the app open on an emulator or device, go to each screen
and run:

```bash
flutter screenshot -o docs/screenshots/01_login.png
```

`server/test/beef_00003.jpg` is a good photo for the detection screen. When all seven
are saved, remove the `<!--` and `-->` lines around the Screenshots section in the main
README.

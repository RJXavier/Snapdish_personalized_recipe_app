import 'package:flutter_test/flutter_test.dart';

import 'package:recipe_app/common/models/detection_model.dart';
import 'package:recipe_app/common/models/recipe_info_model.dart';
import 'package:recipe_app/common/models/recipe_model.dart';
import 'package:recipe_app/common/models/user_model.dart';
import 'package:recipe_app/common/net/result_data.dart';

void main() {
  group('UserInfo', () {
    test('parses the /auth/me response', () {
      final user = UserInfo.fromJson({
        'nickname': 'Demo User',
        'email': 'demo@example.com',
        'gender': 'Other',
        'birthday': '1998-05-17',
        'age': 28,
        'user_recipe_count': 3,
        'user_ingredient_count': null,
        'user_collect_recipe_count': '2',
        'food_preferences': 'Vegan, Nut-free',
      });
      expect(user.birthday, '1998-05-17');
      expect(user.age, 28);
      expect(user.userRecipeCount, 3);
      expect(user.userIngredientCount, 0);
      expect(user.userCollectRecipeCount, 2);
      expect(user.foodPreferenceList, ['Vegan', 'Nut-free']);
    });

    test('has no preferences and no age when the server sends none', () {
      final user = UserInfo.fromJson({'nickname': 'x', 'food_preferences': ''});
      expect(user.age, isNull);
      expect(user.foodPreferenceList, isEmpty);
      expect(UserInfo.empty().foodPreferenceList, isEmpty);
    });
  });

  group('Recipe models', () {
    test('accepts whole numbers for match_ratio', () {
      final list = ListRecipeModel.fromJson({
        'total': 1,
        'recipes': [
          {
            'recipe_id': 7,
            'recipe_name': 'Beef stew',
            'difficulty': 'easy',
            'cook_time': '55 min',
            'match_ratio': 1,
            'ingredients': [
              {'ingredient_name': 'beef', 'quantity': 0, 'unit': null},
            ],
          },
        ],
      });
      expect(list.total, 1);
      expect(list.recipes.single.matchRatio, 1.0);
      expect(list.recipes.single.ingredients.single.unit, '');
    });

    test('parses recipe details', () {
      final recipe = RecipeInfoModel.fromJson({
        'recipe_id': 7,
        'recipe_name': 'Beef stew',
        'difficulty': 'easy',
        'cook_time': '55 min',
        'cook_steps': ['Chop the onion, carrot and celery', 'Simmer'],
        'ingredients': ['beef', 'onion'],
        'is_collected': true,
      });
      expect(recipe.cookSteps.length, 2);
      expect(recipe.isCollected, isTrue);
    });

    test('parses detections', () {
      final detection = DetectionModel.fromJson({
        'class_name': 'beef',
        'confidence': 1,
      });
      expect(detection.className, 'beef');
      expect(detection.confidence, 1.0);
    });
  });

  test('ResultData reads the server envelope', () {
    final ok = ResultData.fromJson({'code': 0, 'message': 'success', 'data': []});
    expect(ok.isSuccess(), isTrue);
    final failed = ResultData.fromJson({'message': 'nope'});
    expect(failed.isSuccess(), isFalse);
  });
}

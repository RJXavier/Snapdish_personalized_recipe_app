import 'package:recipe_app/common/values/server.dart';

import '../common/models/user_model.dart';
import '../common/net/init_dio.dart';

class LoginResult {
  final String? token;
  final String message;

  LoginResult({this.token, this.message = ''});
}

class UserApi {
  static Future<LoginResult> authLogin(String username, String password) async {
    final response = await httpManager.post(
      '/auth/login',
      data: {'username': username, 'password': password},
    );
    if (response.code == 0 && response.data is Map) {
      return LoginResult(token: response.data['access_token']?.toString());
    }
    return LoginResult(message: response.message);
  }

  static Future<UserInfo?> aboutMe() async {
    final response = await httpManager.get('/auth/me');
    if (response.code == 0 && response.data is Map) {
      return UserInfo.fromJson(Map<String, dynamic>.from(response.data));
    }
    logger.e('aboutMe failed: ${response.message}');
    return null;
  }

  /// Returns an empty string on success, otherwise an error message.
  static Future<String> signUp(SignUpUserInfo signUpInfo) async {
    final response = await httpManager.post(
      '/auth/signup',
      data: signUpInfo.toJson(),
    );
    if (response.code == 0) {
      return "";
    }
    return response.message.isNotEmpty ? response.message : 'Sign up failed';
  }

  /// Returns an empty string on success, otherwise an error message.
  static Future<String> updateProfile(UserInfo profile) async {
    final response = await httpManager.post(
      '/auth/updateProfile',
      data: {
        'nickname': profile.nickname,
        'email': profile.email,
        'gender': profile.gender,
        'birthday': profile.birthday,
        'food_preferences': profile.foodPreferences,
      },
    );
    if (response.code == 0) {
      return "";
    }
    return response.message.isNotEmpty
        ? response.message
        : 'Profile update failed';
  }

  /// Returns an empty string on success, otherwise an error message.
  static Future<String> changePassword(
    String currentPassword,
    String newPassword,
  ) async {
    final response = await httpManager.post(
      '/auth/changePassword',
      data: {
        'current_password': currentPassword,
        'new_password': newPassword,
      },
    );
    if (response.code == 0) {
      return "";
    }
    return response.message.isNotEmpty
        ? response.message
        : 'Password change failed';
  }
}

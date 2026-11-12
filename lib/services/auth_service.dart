import 'package:flutter/foundation.dart';
import 'package:recipe_app/api/user_api.dart';
import 'package:shared_preferences/shared_preferences.dart';

class AuthService extends ChangeNotifier {
  static final AuthService _instance = AuthService._internal();
  factory AuthService() => _instance;
  AuthService._internal();

  static const _tokenKey = 'token';

  bool _loggedIn = false;
  String? _token;
  bool get loggedIn => _loggedIn;
  String? get token => _token;

  /// Restores the saved session when the app starts.
  Future<void> load() async {
    final sp = await SharedPreferences.getInstance();
    final saved = sp.getString(_tokenKey);
    _token = (saved != null && saved.isNotEmpty) ? saved : null;
    _loggedIn = _token != null;
    notifyListeners();
  }

  Future<String?> getTokenForInterceptor() async {
    if (_token != null) {
      return _token;
    }
    final sp = await SharedPreferences.getInstance();
    final saved = sp.getString(_tokenKey);
    _token = (saved != null && saved.isNotEmpty) ? saved : null;
    _loggedIn = _token != null;
    return _token;
  }

  /// Returns an empty string on success, otherwise an error message.
  Future<String?> login(String username, String password) async {
    final result = await UserApi.authLogin(username, password);
    final token = result.token;
    if (token == null) {
      return result.message.isNotEmpty
          ? result.message
          : 'Invalid username or password';
    }
    _token = token;
    _loggedIn = true;
    final sp = await SharedPreferences.getInstance();
    await sp.setBool('loggedIn', true);
    await sp.setString(_tokenKey, token);
    notifyListeners();
    return "";
  }

  Future<void> logout() async {
    _loggedIn = false;
    _token = null;
    final sp = await SharedPreferences.getInstance();
    await sp.setBool('loggedIn', false);
    await sp.remove(_tokenKey);
    notifyListeners();
  }
}

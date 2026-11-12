import 'package:recipe_app/common/net/request_interceptors.dart';
import 'package:recipe_app/common/net/result_data.dart';

import '../../services/auth_service.dart';
import '../values/server.dart';
import 'package:dio/dio.dart';

import 'code.dart';

class HttpManager {
  final Dio _dio = Dio(
    BaseOptions(
      baseUrl: SERVER_API_URL,
      connectTimeout: const Duration(seconds: 15),
      // ingredient detection can take a while on a CPU-only server
      receiveTimeout: const Duration(seconds: 60),
    ),
  );

  Dio getDio() {
    return _dio;
  }

  HttpManager() {
    _dio.interceptors.add(RequestInterceptors());
  }

  Future<ResultData> get(String path, {dynamic params}) async {
    try {
      final response = await _dio.get(
        path,
        queryParameters: params == null
            ? null
            : Map<String, dynamic>.from(params),
        options: Options(responseType: ResponseType.json),
      );
      return _parse(response, path);
    } on DioException catch (e) {
      logger.d(e);
      return resultError(e, path);
    }
  }

  Future<ResultData> uploadFile(String path, FormData formData) async {
    try {
      final response = await _dio.post(
        path,
        data: formData,
        options: Options(contentType: 'multipart/form-data'),
      );
      return _parse(response, path);
    } on DioException catch (e) {
      logger.d(e);
      return resultError(e, path);
    }
  }

  Future<ResultData> post(String path, {dynamic data}) async {
    try {
      final response = await _dio.post(path, data: data);
      return _parse(response, path);
    } on DioException catch (e) {
      logger.d(e);
      return resultError(e, path);
    }
  }

  ResultData _parse(Response response, String path) {
    final body = response.data;
    if (body is! Map) {
      return ResultData(
        'Unexpected response from server',
        null,
        Code.NETWORK_ERROR,
      );
    }
    final result = ResultData.fromJson(Map<String, dynamic>.from(body));
    if (result.code == Code.UNAUTHORIZED) {
      _onSessionExpired();
    }
    return result;
  }

  /// The saved token is no longer accepted: sign out and return to login.
  void _onSessionExpired() {
    final auth = AuthService();
    if (!auth.loggedIn) return;
    auth.logout();
    navigatorKey.currentState?.pushNamedAndRemoveUntil(
      '/login',
      (route) => false,
    );
  }

  Future<ResultData> resultError(DioException e, String path) async {
    int statusCode = e.response?.statusCode ?? Code.NETWORK_ERROR;
    if (e.type == DioExceptionType.connectionTimeout ||
        e.type == DioExceptionType.receiveTimeout ||
        e.type == DioExceptionType.sendTimeout) {
      statusCode = Code.NETWORK_TIMEOUT;
    }
    return ResultData(
      Code.errorHandleFunction(
        statusCode,
        "Server connection failed, please check network settings",
      ),
      null,
      statusCode,
    );
  }
}

final HttpManager httpManager = HttpManager();

import 'package:logger/logger.dart';
import 'package:flutter/material.dart';

/// Base URL of the FastAPI backend.
///
/// The default works on the Android emulator, where 10.0.2.2 is the host
/// machine. Override it at build time for other targets, for example:
///   flutter run --dart-define=API_URL=http://127.0.0.1:7777      (iOS simulator)
///   flutter run --dart-define=API_URL=http://192.168.1.20:7777   (real device)
const SERVER_API_URL = String.fromEnvironment(
  'API_URL',
  defaultValue: 'http://10.0.2.2:7777',
);

/// Lets code outside the widget tree (e.g. the network layer) navigate.
final GlobalKey<NavigatorState> navigatorKey = GlobalKey<NavigatorState>();

final logger = Logger(
  printer: PrettyPrinter(lineLength: 20),
  output: DebugPrintConsoleOutput(),
);

class DebugPrintConsoleOutput extends LogOutput {
  @override
  void output(OutputEvent event) {
    for (final element in event.lines) {
      debugPrint(element);
    }
  }
}

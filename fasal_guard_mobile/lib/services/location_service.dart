import 'package:flutter/foundation.dart' show debugPrint;
import 'package:geolocator/geolocator.dart';

import '../models/farmer_report.dart';

/// GPS capture for the report (plan section 18). Never throws: a denied
/// permission or a failed fix only flags the report, it never blocks it.
class LocationService {
  Future<ReportLocation> capture() async {
    try {
      final serviceEnabled = await Geolocator.isLocationServiceEnabled();
      if (!serviceEnabled) {
        return const ReportLocation(status: 'unavailable');
      }

      var permission = await Geolocator.checkPermission();
      if (permission == LocationPermission.denied) {
        permission = await Geolocator.requestPermission();
      }
      if (permission == LocationPermission.denied ||
          permission == LocationPermission.deniedForever) {
        return const ReportLocation(status: 'permission_denied');
      }

      final position = await Geolocator.getCurrentPosition(
        locationSettings: const LocationSettings(
          accuracy: LocationAccuracy.low,
          timeLimit: Duration(seconds: 15),
        ),
      );
      return ReportLocation(
        latitude: position.latitude,
        longitude: position.longitude,
        accuracyM: position.accuracy,
        status: 'captured',
      );
    } catch (e) {
      debugPrint('[location] capture failed: $e');
      return const ReportLocation(status: 'unavailable');
    }
  }
}

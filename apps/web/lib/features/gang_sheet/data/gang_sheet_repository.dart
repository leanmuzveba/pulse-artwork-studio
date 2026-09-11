import "package:dio/dio.dart";
import "package:flutter_riverpod/flutter_riverpod.dart";

import "../../../core/api/api_client.dart";
import "../../../core/api/api_envelope.dart";
import "../../../core/api/api_exception.dart";
import "../../../core/models/gang_sheet.dart";

final gangSheetRepositoryProvider = Provider<GangSheetRepository>((ref) {
  return GangSheetRepository(ref.watch(apiClientProvider));
});

class GangSheetRepository {
  GangSheetRepository(this._dio);
  final Dio _dio;

  Future<GangSheet> create({
    required String projectId,
    required int sheetWidthMm,
    required int spacingMm,
    required int dpi,
    required List<GangSheetItem> items,
  }) async {
    try {
      final response = await _dio.post<Map<String, dynamic>>(
        "/gang-sheets",
        data: {
          "project_id": projectId,
          "sheet_width_mm": sheetWidthMm,
          "spacing_mm": spacingMm,
          "dpi": dpi,
          "items": items.map((i) => i.toJson()).toList(),
        },
      );
      return await unwrap(
          response, (json) => GangSheet.fromJson(json as Map<String, dynamic>));
    } on DioException catch (e) {
      throw ApiException.fromDioError(e);
    }
  }

  Future<GangSheet> get(String gangSheetId) async {
    try {
      final response =
          await _dio.get<Map<String, dynamic>>("/gang-sheets/$gangSheetId");
      return await unwrap(
          response, (json) => GangSheet.fromJson(json as Map<String, dynamic>));
    } on DioException catch (e) {
      throw ApiException.fromDioError(e);
    }
  }
}

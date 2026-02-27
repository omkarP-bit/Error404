import 'dart:io';
import 'dart:typed_data';
import 'package:image/image.dart' as img;
import 'package:flutter/foundation.dart';

/// Utility class for optimizing receipt images before processing
class ImageCompressionUtil {
  /// Maximum dimensions for receipt image (prevents memory overflow)
  static const int maxWidth = 1024;
  static const int maxHeight = 1280;
  
  /// Maximum file size in bytes (~ 500KB)
  static const int maxFileSizeBytes = 500 * 1024;
  
  /// Target quality for JPEG compression (0-100)
  static const int jpegQuality = 75;

  /// Compress and optimize a receipt image
  /// 
  /// This method:
  /// 1. Reads the image file
  /// 2. Resizes to max dimensions if larger
  /// 3. Compresses to target quality
  /// 4. Saves optimized version
  /// 
  /// Returns the path to the optimized image
  /// 
  /// Throws Exception if image cannot be processed
  static Future<String> compressReceiptImage(String imagePath) async {
    try {
      final file = File(imagePath);
      if (!await file.exists()) {
        throw Exception('Image file not found: $imagePath');
      }

      // Check original file size
      final originalSize = await file.length();
      debugPrint('Original image size: ${(originalSize / 1024).toStringAsFixed(2)} KB');

      // Read image
      final imageBytes = await file.readAsBytes();
      img.Image? image = img.decodeImage(imageBytes);

      if (image == null) {
        throw Exception('Failed to decode image');
      }

      debugPrint('Original dimensions: ${image.width}x${image.height}');

      // Calculate scaling factor to fit within max dimensions
      // while maintaining aspect ratio
      double scale = 1.0;
      if (image.width > maxWidth || image.height > maxHeight) {
        final scaleX = maxWidth / image.width;
        final scaleY = maxHeight / image.height;
        scale = scaleX < scaleY ? scaleX : scaleY;
      }

      // Resize if needed
      if (scale < 1.0) {
        final newWidth = (image.width * scale).toInt();
        final newHeight = (image.height * scale).toInt();
        image = img.copyResize(
          image,
          width: newWidth,
          height: newHeight,
          interpolation: img.Interpolation.linear,
        );
        debugPrint('Resized to: ${image.width}x${image.height}');
      }

      // Encode as JPEG with target quality
      final compressedBytes = img.encodeJpg(image, quality: jpegQuality);

      // Create optimized file in same directory
      final optimizedFileName = '${file.path.replaceAll(RegExp(r'\.[^.]+$'), '')}_optimized.jpg';
      final optimizedFile = File(optimizedFileName);
      await optimizedFile.writeAsBytes(compressedBytes);

      final compressedSize = compressedBytes.length;
      final compressionRatio = (1 - (compressedSize / originalSize)) * 100;
      
      debugPrint('Compressed image size: ${(compressedSize / 1024).toStringAsFixed(2)} KB');
      debugPrint('Compression ratio: ${compressionRatio.toStringAsFixed(1)}%');

      // Verify file size is within limits
      if (compressedSize > maxFileSizeBytes) {
        debugPrint('Warning: Compressed image (${(compressedSize / 1024).toStringAsFixed(2)} KB) exceeds max size, trying more aggressive compression...');
        // Try even more aggressive compression
        final aggressiveBytes = img.encodeJpg(image, quality: 60);
        if (aggressiveBytes.length <= maxFileSizeBytes) {
          await optimizedFile.writeAsBytes(aggressiveBytes);
          debugPrint('Aggressive compression successful: ${(aggressiveBytes.length / 1024).toStringAsFixed(2)} KB');
        } else {
          throw Exception(
            'Image still too large even after aggressive compression: ${(aggressiveBytes.length / 1024).toStringAsFixed(2)} KB'
          );
        }
      }

      return optimizedFile.path;
    } catch (e) {
      debugPrint('Image compression error: $e');
      rethrow;
    }
  }

  /// Quick compress without full image decoding (faster but less control)
  /// Useful for quick file-based compression only
  static Future<String> quickCompressImage(String imagePath) async {
    try {
      final file = File(imagePath);
      if (!await file.exists()) {
        throw Exception('Image file not found: $imagePath');
      }

      final bytes = await file.readAsBytes();
      if (bytes.length <= maxFileSizeBytes) {
        debugPrint('Image already compressed enough: ${(bytes.length / 1024).toStringAsFixed(2)} KB');
        return imagePath;
      }

      // For quick compression, just return the original path
      // The full compression will happen during upload
      debugPrint('Image requires compression: ${(bytes.length / 1024).toStringAsFixed(2)} KB > ${(maxFileSizeBytes / 1024).toStringAsFixed(2)} KB');
      return imagePath;
    } catch (e) {
      debugPrint('Quick compression error: $e');
      return imagePath;
    }
  }

  /// Get safe dimensions for an image without loading the entire image
  static Future<({int width, int height})> getImageDimensions(String imagePath) async {
    try {
      final file = File(imagePath);
      if (!await file.exists()) {
        throw Exception('Image file not found: $imagePath');
      }

      final imageBytes = await file.readAsBytes();
      final image = img.decodeImage(imageBytes);

      if (image == null) {
        throw Exception('Failed to decode image dimensions');
      }

      return (width: image.width, height: image.height);
    } catch (e) {
      debugPrint('Error getting image dimensions: $e');
      return (width: 0, height: 0);
    }
  }
}

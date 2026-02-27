import 'package:flutter/material.dart';
import 'package:camera/camera.dart';
import 'package:google_mlkit_text_recognition/google_mlkit_text_recognition.dart';
import '../../services/api_service.dart';

class ARReceiptScannerScreen extends StatefulWidget {
  const ARReceiptScannerScreen({Key? key}) : super(key: key);

  @override
  State<ARReceiptScannerScreen> createState() => _ARReceiptScannerScreenState();
}

class _ARReceiptScannerScreenState extends State<ARReceiptScannerScreen> {
  CameraController? _cameraController;
  final TextRecognizer _textRecognizer = TextRecognizer();
  final ApiService _apiService = ApiService();
  bool _isProcessing = false;
  String? _detectedText;
  double? _detectedAmount;
  String? _detectedMerchant;

  @override
  void initState() {
    super.initState();
    _initializeCamera();
  }

  Future<void> _initializeCamera() async {
    final cameras = await availableCameras();
    if (cameras.isEmpty) return;

    _cameraController = CameraController(
      cameras.first,
      ResolutionPreset.high,
      enableAudio: false,
    );

    await _cameraController!.initialize();
    if (mounted) setState(() {});
  }

  @override
  void dispose() {
    _cameraController?.dispose();
    _textRecognizer.close();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    if (_cameraController == null || !_cameraController!.value.isInitialized) {
      return const Scaffold(
        body: Center(child: CircularProgressIndicator()),
      );
    }

    return Scaffold(
      appBar: AppBar(
        title: const Text('AR Receipt Scanner'),
        backgroundColor: Colors.transparent,
        elevation: 0,
      ),
      body: Stack(
        children: [
          CameraPreview(_cameraController!),
          CustomPaint(
            painter: ScanOverlayPainter(),
            child: Container(),
          ),
          if (_detectedAmount != null)
            Positioned(
              top: 100,
              left: 20,
              right: 20,
              child: Card(
                color: Colors.green.withOpacity(0.9),
                child: Padding(
                  padding: const EdgeInsets.all(16),
                  child: Column(
                    children: [
                      const Icon(Icons.check_circle, color: Colors.white, size: 40),
                      const SizedBox(height: 8),
                      Text(
                        '₹${_detectedAmount!.toStringAsFixed(2)}',
                        style: const TextStyle(
                          color: Colors.white,
                          fontSize: 24,
                          fontWeight: FontWeight.bold,
                        ),
                      ),
                      if (_detectedMerchant != null)
                        Text(
                          _detectedMerchant!,
                          style: const TextStyle(color: Colors.white),
                        ),
                    ],
                  ),
                ),
              ),
            ),
          Positioned(
            bottom: 40,
            left: 0,
            right: 0,
            child: Center(
              child: Column(
                children: [
                  FloatingActionButton.extended(
                    onPressed: _isProcessing ? null : _scanReceipt,
                    icon: _isProcessing
                        ? const SizedBox(
                            width: 20,
                            height: 20,
                            child: CircularProgressIndicator(
                              strokeWidth: 2,
                              color: Colors.white,
                            ),
                          )
                        : const Icon(Icons.camera),
                    label: Text(_isProcessing ? 'Processing...' : 'Scan Receipt'),
                  ),
                  if (_detectedAmount != null) ...[
                    const SizedBox(height: 16),
                    ElevatedButton(
                      onPressed: _saveTransaction,
                      child: const Text('Save Transaction'),
                    ),
                  ],
                ],
              ),
            ),
          ),
        ],
      ),
    );
  }

  Future<void> _scanReceipt() async {
    if (_isProcessing || _cameraController == null) return;

    setState(() => _isProcessing = true);

    try {
      final image = await _cameraController!.takePicture();
      final inputImage = InputImage.fromFilePath(image.path);
      final recognizedText = await _textRecognizer.processImage(inputImage);

      _extractReceiptData(recognizedText.text);
    } catch (e) {
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('Error scanning receipt: $e')),
      );
    } finally {
      setState(() => _isProcessing = false);
    }
  }

  void _extractReceiptData(String text) {
    final amountRegex = RegExp(r'(?:₹|Rs\.?|INR)\s*(\d+(?:,\d+)*(?:\.\d{2})?)');
    final match = amountRegex.firstMatch(text);

    if (match != null) {
      final amountStr = match.group(1)!.replaceAll(',', '');
      setState(() {
        _detectedAmount = double.tryParse(amountStr);
        _detectedText = text;
        _detectedMerchant = _extractMerchantName(text);
      });
    } else {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('No amount detected. Try again.')),
      );
    }
  }

  String? _extractMerchantName(String text) {
    final lines = text.split('\n');
    return lines.isNotEmpty ? lines.first.trim() : null;
  }

  Future<void> _saveTransaction() async {
    if (_detectedAmount == null) return;

    try {
      await _apiService.createTransaction({
        'amount': _detectedAmount,
        'description': _detectedMerchant ?? 'Receipt scan',
        'txn_type': 'debit',
        'category': 'Shopping',
      });

      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Transaction saved successfully')),
      );

      setState(() {
        _detectedAmount = null;
        _detectedMerchant = null;
        _detectedText = null;
      });
    } catch (e) {
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('Error saving transaction: $e')),
      );
    }
  }
}

class ScanOverlayPainter extends CustomPainter {
  @override
  void paint(Canvas canvas, Size size) {
    final paint = Paint()
      ..color = Colors.white.withOpacity(0.5)
      ..style = PaintingStyle.stroke
      ..strokeWidth = 3;

    final rect = Rect.fromCenter(
      center: Offset(size.width / 2, size.height / 2),
      width: size.width * 0.8,
      height: size.height * 0.4,
    );

    canvas.drawRRect(
      RRect.fromRectAndRadius(rect, const Radius.circular(12)),
      paint,
    );

    final cornerLength = 30.0;
    final cornerPaint = Paint()
      ..color = Colors.greenAccent
      ..style = PaintingStyle.stroke
      ..strokeWidth = 4;

    canvas.drawLine(
      Offset(rect.left, rect.top),
      Offset(rect.left + cornerLength, rect.top),
      cornerPaint,
    );
    canvas.drawLine(
      Offset(rect.left, rect.top),
      Offset(rect.left, rect.top + cornerLength),
      cornerPaint,
    );

    canvas.drawLine(
      Offset(rect.right, rect.top),
      Offset(rect.right - cornerLength, rect.top),
      cornerPaint,
    );
    canvas.drawLine(
      Offset(rect.right, rect.top),
      Offset(rect.right, rect.top + cornerLength),
      cornerPaint,
    );

    canvas.drawLine(
      Offset(rect.left, rect.bottom),
      Offset(rect.left + cornerLength, rect.bottom),
      cornerPaint,
    );
    canvas.drawLine(
      Offset(rect.left, rect.bottom),
      Offset(rect.left, rect.bottom - cornerLength),
      cornerPaint,
    );

    canvas.drawLine(
      Offset(rect.right, rect.bottom),
      Offset(rect.right - cornerLength, rect.bottom),
      cornerPaint,
    );
    canvas.drawLine(
      Offset(rect.right, rect.bottom),
      Offset(rect.right, rect.bottom - cornerLength),
      cornerPaint,
    );
  }

  @override
  bool shouldRepaint(covariant CustomPainter oldDelegate) => false;
}

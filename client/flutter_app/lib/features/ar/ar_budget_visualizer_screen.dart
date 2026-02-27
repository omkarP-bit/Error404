import 'package:flutter/material.dart';
import 'package:camera/camera.dart';
import 'package:sensors_plus/sensors_plus.dart';
import 'dart:async';
import 'dart:math' as math;
import '../../models/finance_models.dart';
import '../../services/api_service.dart';

class ARBudgetVisualizerScreen extends StatefulWidget {
  const ARBudgetVisualizerScreen({super.key});

  @override
  State<ARBudgetVisualizerScreen> createState() => _ARBudgetVisualizerScreenState();
}

class _ARBudgetVisualizerScreenState extends State<ARBudgetVisualizerScreen> {
  final ApiService _apiService = ApiService();
  List<Budget> _budgets = [];
  bool _isLoading = true;
  bool _showVisualization = false;
  CameraController? _cameraController;
  double _tiltX = 0.0;
  double _tiltY = 0.0;
  StreamSubscription? _gyroscopeSubscription;

  @override
  void initState() {
    super.initState();
    _loadBudgets();
    _initCamera();
    _initSensors();
  }

  Future<void> _loadBudgets() async {
    try {
      final budgets = await _apiService.getBudgets();
      setState(() {
        _budgets = budgets;
        _isLoading = false;
      });
    } catch (e) {
      setState(() => _isLoading = false);
    }
  }

  Future<void> _initCamera() async {
    try {
      final cameras = await availableCameras();
      if (cameras.isEmpty) return;
      
      _cameraController = CameraController(
        cameras.first,
        ResolutionPreset.medium,
        enableAudio: false,
      );
      await _cameraController!.initialize();
      if (mounted) setState(() {});
    } catch (e) {
      debugPrint('Camera error: $e');
    }
  }

  void _initSensors() {
    _gyroscopeSubscription = gyroscopeEventStream().listen((event) {
      setState(() {
        _tiltX = (event.y * 20).clamp(-30.0, 30.0);
        _tiltY = (event.x * 20).clamp(-30.0, 30.0);
      });
    });
  }

  @override
  void dispose() {
    _cameraController?.dispose();
    _gyroscopeSubscription?.cancel();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('AR Budget Visualizer'),
        backgroundColor: Colors.transparent,
        elevation: 0,
      ),
      body: Stack(
        children: [
          if (_cameraController?.value.isInitialized ?? false)
            SizedBox.expand(
              child: CameraPreview(_cameraController!),
            )
          else
            Container(color: Colors.black),
          
          if (_showVisualization && _budgets.isNotEmpty)
            Center(
              child: Transform(
                transform: Matrix4.identity()
                  ..setEntry(3, 2, 0.001)
                  ..rotateX(_tiltX * math.pi / 180)
                  ..rotateY(_tiltY * math.pi / 180),
                alignment: Alignment.center,
                child: _build3DBudgetBars(),
              ),
            ),
          
          if (_isLoading)
            const Center(child: CircularProgressIndicator()),
          
          Positioned(
            bottom: 20,
            left: 20,
            right: 20,
            child: Card(
              color: Colors.black.withValues(alpha: 0.7),
              child: Padding(
                padding: const EdgeInsets.all(16),
                child: Column(
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    const Text(
                      'Budget Overview',
                      style: TextStyle(
                        fontSize: 18,
                        fontWeight: FontWeight.bold,
                        color: Colors.white,
                      ),
                    ),
                    const SizedBox(height: 8),
                    ..._budgets.take(3).map((budget) => Padding(
                      padding: const EdgeInsets.symmetric(vertical: 4),
                      child: Row(
                        mainAxisAlignment: MainAxisAlignment.spaceBetween,
                        children: [
                          Text(
                            budget.category,
                            style: const TextStyle(color: Colors.white),
                          ),
                          Text(
                            '${budget.percentageUsed.toStringAsFixed(0)}%',
                            style: TextStyle(
                              color: budget.percentageUsed > 80
                                  ? Colors.red
                                  : Colors.green,
                              fontWeight: FontWeight.bold,
                            ),
                          ),
                        ],
                      ),
                    )),
                  ],
                ),
              ),
            ),
          ),
        ],
      ),
      floatingActionButton: FloatingActionButton(
        onPressed: () {
          setState(() => _showVisualization = !_showVisualization);
        },
        child: Icon(_showVisualization ? Icons.visibility_off : Icons.visibility),
      ),
    );
  }

  Widget _build3DBudgetBars() {
    return SizedBox(
      height: 300,
      child: Row(
        mainAxisAlignment: MainAxisAlignment.center,
        crossAxisAlignment: CrossAxisAlignment.end,
        children: _budgets.take(5).map((budget) {
          final height = (budget.percentageUsed * 2.5).clamp(20.0, 250.0);
          final color = budget.percentageUsed > 80
              ? Colors.red
              : budget.percentageUsed > 60
                  ? Colors.orange
                  : Colors.green;
          
          return Padding(
            padding: const EdgeInsets.symmetric(horizontal: 8),
            child: Column(
              mainAxisSize: MainAxisSize.min,
              children: [
                Container(
                  width: 50,
                  height: height,
                  decoration: BoxDecoration(
                    gradient: LinearGradient(
                      begin: Alignment.topCenter,
                      end: Alignment.bottomCenter,
                      colors: [
                        color.withValues(alpha: 0.8),
                        color,
                      ],
                    ),
                    borderRadius: BorderRadius.circular(8),
                    boxShadow: [
                      BoxShadow(
                        color: color.withValues(alpha: 0.5),
                        blurRadius: 10,
                        spreadRadius: 2,
                      ),
                    ],
                  ),
                  child: Center(
                    child: RotatedBox(
                      quarterTurns: 3,
                      child: Text(
                        '${budget.percentageUsed.toStringAsFixed(0)}%',
                        style: const TextStyle(
                          color: Colors.white,
                          fontWeight: FontWeight.bold,
                          fontSize: 12,
                        ),
                      ),
                    ),
                  ),
                ),
                const SizedBox(height: 8),
                SizedBox(
                  width: 50,
                  child: Text(
                    budget.category,
                    style: const TextStyle(
                      color: Colors.white,
                      fontSize: 10,
                      fontWeight: FontWeight.bold,
                    ),
                    textAlign: TextAlign.center,
                    maxLines: 2,
                    overflow: TextOverflow.ellipsis,
                  ),
                ),
              ],
            ),
          );
        }).toList(),
      ),
    );
  }
}

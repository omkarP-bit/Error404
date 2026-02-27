import 'package:flutter/material.dart';
import 'package:ar_flutter_plugin/ar_flutter_plugin.dart';
import 'package:ar_flutter_plugin/datatypes/config_planedetection.dart';
import 'package:ar_flutter_plugin/managers/ar_anchor_manager.dart';
import 'package:ar_flutter_plugin/managers/ar_location_manager.dart';
import 'package:ar_flutter_plugin/managers/ar_object_manager.dart';
import 'package:ar_flutter_plugin/managers/ar_session_manager.dart';
import 'package:ar_flutter_plugin/datatypes/node_types.dart';
import 'package:ar_flutter_plugin/models/ar_node.dart';
import 'package:vector_math/vector_math_64.dart' as vector;
import '../../models/transaction.dart';
import '../../services/api_service.dart';

class ARSpendingTrackerScreen extends StatefulWidget {
  const ARSpendingTrackerScreen({Key? key}) : super(key: key);

  @override
  State<ARSpendingTrackerScreen> createState() => _ARSpendingTrackerScreenState();
}

class _ARSpendingTrackerScreenState extends State<ARSpendingTrackerScreen> {
  ARSessionManager? arSessionManager;
  ARObjectManager? arObjectManager;
  ARAnchorManager? arAnchorManager;
  final ApiService _apiService = ApiService();
  List<Transaction> _transactions = [];
  Map<String, double> _categorySpending = {};
  bool _isLoading = true;

  @override
  void initState() {
    super.initState();
    _loadTransactions();
  }

  Future<void> _loadTransactions() async {
    try {
      final transactions = await _apiService.getTransactions(limit: 50);
      final spending = <String, double>{};
      
      for (var txn in transactions) {
        if (txn.txnType == 'debit') {
          final category = txn.category ?? 'Other';
          spending[category] = (spending[category] ?? 0) + txn.amount;
        }
      }

      setState(() {
        _transactions = transactions;
        _categorySpending = spending;
        _isLoading = false;
      });
    } catch (e) {
      setState(() => _isLoading = false);
    }
  }

  @override
  void dispose() {
    arSessionManager?.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('AR Spending Tracker'),
        backgroundColor: Colors.transparent,
        elevation: 0,
      ),
      body: Stack(
        children: [
          ARView(
            onARViewCreated: _onARViewCreated,
            planeDetectionConfig: PlaneDetectionConfig.horizontal,
          ),
          if (_isLoading)
            const Center(child: CircularProgressIndicator()),
          Positioned(
            top: 20,
            left: 20,
            right: 20,
            child: Card(
              child: Padding(
                padding: const EdgeInsets.all(12),
                child: Column(
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    const Text(
                      'Category Spending',
                      style: TextStyle(fontSize: 16, fontWeight: FontWeight.bold),
                    ),
                    const SizedBox(height: 8),
                    ..._categorySpending.entries.take(4).map((entry) => Row(
                      mainAxisAlignment: MainAxisAlignment.spaceBetween,
                      children: [
                        Text(entry.key),
                        Text('₹${entry.value.toStringAsFixed(0)}'),
                      ],
                    )),
                  ],
                ),
              ),
            ),
          ),
        ],
      ),
      floatingActionButton: FloatingActionButton(
        onPressed: _visualizeSpending,
        child: const Icon(Icons.bar_chart),
      ),
    );
  }

  void _onARViewCreated(
    ARSessionManager sessionManager,
    ARObjectManager objectManager,
    ARAnchorManager anchorManager,
    ARLocationManager locationManager,
  ) {
    arSessionManager = sessionManager;
    arObjectManager = objectManager;
    arAnchorManager = anchorManager;

    arSessionManager!.onInitialize(
      showFeaturePoints: false,
      showPlanes: true,
      showWorldOrigin: false,
    );
  }

  Future<void> _visualizeSpending() async {
    if (arObjectManager == null || _categorySpending.isEmpty) return;

    final maxSpending = _categorySpending.values.reduce((a, b) => a > b ? a : b);
    int index = 0;

    for (var entry in _categorySpending.entries.take(5)) {
      final normalizedHeight = (entry.value / maxSpending) * 0.5;
      
      final node = ARNode(
        type: NodeType.webGLB,
        uri: 'https://github.com/KhronosGroup/glTF-Sample-Models/raw/master/2.0/Box/glTF-Binary/Box.glb',
        scale: vector.Vector3(0.08, normalizedHeight, 0.08),
        position: vector.Vector3(index * 0.12 - 0.24, normalizedHeight / 2, -0.8),
        rotation: vector.Vector4(0, 0, 0, 0),
      );

      await arObjectManager!.addNode(node);
      index++;
    }

    ScaffoldMessenger.of(context).showSnackBar(
      const SnackBar(content: Text('Spending visualization added')),
    );
  }
}

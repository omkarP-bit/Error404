import 'package:ar_flutter_plugin/ar_flutter_plugin.dart';
import 'package:ar_flutter_plugin/datatypes/node_types.dart';
import 'package:ar_flutter_plugin/managers/ar_anchor_manager.dart';
import 'package:ar_flutter_plugin/managers/ar_location_manager.dart';
import 'package:ar_flutter_plugin/managers/ar_object_manager.dart';
import 'package:ar_flutter_plugin/managers/ar_session_manager.dart';
import 'package:vector_math/vector_math_64.dart' as vector;

class ARService {
  ARSessionManager? arSessionManager;
  ARObjectManager? arObjectManager;
  ARAnchorManager? arAnchorManager;

  void onARViewCreated(
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

  Future<void> addFinancialDataNode({
    required String label,
    required double value,
    required vector.Vector3 position,
  }) async {
    if (arObjectManager == null) return;

    final node = ARNode(
      type: NodeType.webGLB,
      uri: 'https://github.com/KhronosGroup/glTF-Sample-Models/raw/master/2.0/Box/glTF-Binary/Box.glb',
      scale: vector.Vector3(value / 1000, value / 1000, value / 1000),
      position: position,
    );

    await arObjectManager!.addNode(node);
  }

  void dispose() {
    arSessionManager?.dispose();
  }
}

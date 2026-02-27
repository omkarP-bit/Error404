import 'package:flutter/material.dart';
import 'services/api_service.dart';

class InsightsScreen extends StatefulWidget {
  const InsightsScreen({Key? key}) : super(key: key);

  @override
  State<InsightsScreen> createState() => _InsightsScreenState();
}

class _InsightsScreenState extends State<InsightsScreen> {
  final ApiService _apiService = ApiService();
  final int _userId = 1;
  
  AnomalyScanResult? _anomalyScanResult;
  bool _isLoading = true;
  String? _errorMessage;
  bool _showAnomaliesExpanded = false;

  @override
  void initState() {
    super.initState();
    _loadAnomalyData();
  }

  Future<void> _loadAnomalyData() async {
    try {
      if (mounted) setState(() => _isLoading = true);
      final result = await _apiService.scanAnomalies(userId: _userId);
      if (mounted) {
        setState(() {
          _anomalyScanResult = result;
          _isLoading = false;
        });
      }
    } catch (e) {
      if (mounted) {
        setState(() {
          _errorMessage = 'Failed to load anomaly data: $e';
          _isLoading = false;
        });
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: bgColor,
      body: SafeArea(
        child: SingleChildScrollView(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              _buildHeader(),
              const SizedBox(height: 24),
              Padding(
                padding: const EdgeInsets.symmetric(horizontal: 20.0),
                child: Column(
                  children: [
                    _buildSummaryCard(),
                    const SizedBox(height: 32),
                    
                    // Anomaly Detection Section
                    if (_isLoading)
                      const Center(
                        child: CircularProgressIndicator(
                          valueColor: AlwaysStoppedAnimation<Color>(accentGreen),
                        ),
                      )
                    else if (_errorMessage != null)
                      Center(
                        child: Text(
                          _errorMessage!,
                          style: const TextStyle(color: Colors.red),
                        ),
                      )
                    else if (_anomalyScanResult != null)
                      _buildAnomalyDetectionSection()
                    else
                      const Center(child: Text('No data available')),

                    const SizedBox(height: 32),
                    const Align(
                      alignment: Alignment.centerLeft,
                      child: Text(
                        'BEHAVIORAL PATTERNS',
                        style: TextStyle(
                          color: Color(0xFF6B7E82),
                          fontSize: 13,
                          fontWeight: FontWeight.w800,
                          letterSpacing: 1.2,
                        ),
                      ),
                    ),
                    const SizedBox(height: 16),
                    _buildBehaviorCard(
                      icon: Icons.shopping_bag_outlined,
                      iconColor: Colors.redAccent,
                      iconBgColor: const Color(0xFFFFEAEA),
                      title: 'Weekend Overspend',
                      content: RichText(
                        text: const TextSpan(
                          style: TextStyle(
                            color: Color(0xFF6B7E82),
                            fontSize: 15,
                            height: 1.5,
                          ),
                          children: [
                            TextSpan(text: 'You spend '),
                            TextSpan(
                              text: '2.3x more',
                              style: TextStyle(color: textDark, fontWeight: FontWeight.bold),
                            ),
                            TextSpan(text: ' on\nweekends. Fri-Sun avg:\n₹1,840/day.'),
                          ],
                        ),
                      ),
                      actionWidget: Container(
                        margin: const EdgeInsets.only(top: 16),
                        padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
                        decoration: BoxDecoration(
                          color: const Color(0xFFF5F9F8),
                          borderRadius: BorderRadius.circular(12),
                        ),
                        child: const Row(
                          mainAxisSize: MainAxisSize.min,
                          children: [
                            Text('💡 ', style: TextStyle(fontSize: 16)),
                            Text(
                              'Tip: Set a weekend budget cap',
                              style: TextStyle(
                                color: Colors.teal,
                                fontSize: 14,
                                fontWeight: FontWeight.w600,
                              ),
                            ),
                          ],
                        ),
                      ),
                    ),
                    const SizedBox(height: 16),
                    _buildBehaviorCard(
                      icon: Icons.trending_up,
                      iconColor: Colors.blue,
                      iconBgColor: const Color(0xFFE5EEFF),
                      title: 'Category Trend',
                      content: RichText(
                        text: const TextSpan(
                          style: TextStyle(
                            color: Color(0xFF6B7E82),
                            fontSize: 15,
                            height: 1.5,
                          ),
                          children: [
                            TextSpan(text: 'Food spending up '),
                            TextSpan(
                              text: '18%',
                              style: TextStyle(color: Colors.redAccent, fontWeight: FontWeight.bold),
                            ),
                            TextSpan(text: ' vs last\nmonth.'),
                          ],
                        ),
                      ),
                      actionWidget: Container(
                        margin: const EdgeInsets.only(top: 16),
                        height: 48,
                        child: Row(
                          crossAxisAlignment: CrossAxisAlignment.end,
                          children: [
                            _buildBarChartBar(24, const Color(0xFFD6E4FF)),
                            const SizedBox(width: 8),
                            _buildBarChartBar(32, const Color(0xFFD6E4FF)),
                            const SizedBox(width: 8),
                            _buildBarChartBar(20, const Color(0xFFD6E4FF)),
                            const SizedBox(width: 8),
                            _buildBarChartBar(48, Colors.blue),
                          ],
                        ),
                      ),
                    ),
                    const SizedBox(height: 16),
                    _buildBehaviorCard(
                      icon: Icons.attach_money,
                      iconColor: accentGreen,
                      iconBgColor: const Color(0xFFE5F9EF),
                      title: 'Investment Consistency',
                      content: RichText(
                        text: const TextSpan(
                          style: TextStyle(
                            color: Color(0xFF6B7E82),
                            fontSize: 15,
                            height: 1.5,
                          ),
                          children: [
                            TextSpan(text: 'You\'ve invested consistently for '),
                            TextSpan(
                              text: '8\nmonths.',
                              style: TextStyle(color: accentGreen, fontWeight: FontWeight.bold),
                            ),
                            TextSpan(text: ' Great job!'),
                          ],
                        ),
                      ),
                    ),
                    const SizedBox(height: 40),
                  ],
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }

  Widget _buildAnomalyDetectionSection() {
    final result = _anomalyScanResult!;
    final anomalies = result.anomalies;

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        const Align(
          alignment: Alignment.centerLeft,
          child: Text(
            'ANOMALY DETECTION',
            style: TextStyle(
              color: Color(0xFF6B7E82),
              fontSize: 13,
              fontWeight: FontWeight.w800,
              letterSpacing: 1.2,
            ),
          ),
        ),
        const SizedBox(height: 16),
        
        // Summary Card - Clickable to expand/collapse
        GestureDetector(
          onTap: () {
            if (mounted && anomalies.isNotEmpty) {
              setState(() => _showAnomaliesExpanded = !_showAnomaliesExpanded);
            }
          },
          child: Container(
            padding: const EdgeInsets.all(16),
            decoration: BoxDecoration(
              color: anomalies.isNotEmpty 
                ? const Color(0xFFFFF3E0) 
                : const Color(0xFFE5F9EF),
              borderRadius: BorderRadius.circular(16),
              border: Border.all(
                color: anomalies.isNotEmpty 
                  ? const Color(0xFFFFB74D) 
                  : accentGreen,
              ),
            ),
            child: Row(
              children: [
                Icon(
                  anomalies.isNotEmpty 
                    ? Icons.warning_amber_rounded 
                    : Icons.check_circle_rounded,
                  color: anomalies.isNotEmpty ? Colors.orange : accentGreen,
                  size: 32,
                ),
                const SizedBox(width: 16),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        anomalies.isNotEmpty 
                          ? '${anomalies.length} Anomalies Detected'
                          : 'All Transactions Normal',
                        style: TextStyle(
                          color: anomalies.isNotEmpty ? Colors.orange : accentGreen,
                          fontSize: 16,
                          fontWeight: FontWeight.bold,
                        ),
                      ),
                      const SizedBox(height: 4),
                      Text(
                        anomalies.isNotEmpty
                          ? 'Out of ${result.totalScanned} transactions scanned'
                          : 'No unusual activity detected',
                        style: const TextStyle(
                          color: Color(0xFF6B7E82),
                          fontSize: 13,
                        ),
                      ),
                    ],
                  ),
                ),
                if (anomalies.isNotEmpty)
                  Icon(
                    _showAnomaliesExpanded 
                      ? Icons.expand_less 
                      : Icons.expand_more,
                    color: Colors.orange,
                  ),
              ],
            ),
          ),
        ),

        // Anomalies List - Only show when expanded or there's something to show
        if (anomalies.isNotEmpty && _showAnomaliesExpanded) ...[
          const SizedBox(height: 16),
          const Align(
            alignment: Alignment.centerLeft,
            child: Text(
              'Suspicious Transactions',
              style: TextStyle(
                color: textDark,
                fontSize: 16,
                fontWeight: FontWeight.bold,
              ),
            ),
          ),
          const SizedBox(height: 12),
          ...anomalies.map((anomaly) => _buildAnomalyItem(anomaly)).toList(),
        ],
      ],
    );
  }

  Widget _buildAnomalyItem(Transaction anomaly) {
    final severityColor = _getSeverityColor(anomaly.severity ?? 'medium');
    final severityLabel = (anomaly.severity ?? 'medium').toUpperCase();

    return Container(
      margin: const EdgeInsets.only(bottom: 12),
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.circular(16),
        border: Border.all(color: severityColor.withOpacity(0.3)),
        boxShadow: [
          BoxShadow(
            color: Colors.black.withOpacity(0.02),
            blurRadius: 8,
            offset: const Offset(0, 2),
          ),
        ],
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Container(
                padding: const EdgeInsets.all(8),
                decoration: BoxDecoration(
                  color: severityColor.withOpacity(0.1),
                  borderRadius: BorderRadius.circular(8),
                ),
                child: Icon(
                  Icons.warning_amber_rounded,
                  color: severityColor,
                  size: 20,
                ),
              ),
              const SizedBox(width: 12),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      anomaly.rawDescription ?? 'Transaction',
                      style: const TextStyle(
                        color: textDark,
                        fontSize: 15,
                        fontWeight: FontWeight.bold,
                      ),
                      maxLines: 1,
                      overflow: TextOverflow.ellipsis,
                    ),
                    const SizedBox(height: 2),
                    Text(
                      anomaly.category ?? 'Uncategorized',
                      style: const TextStyle(
                        color: Color(0xFF6B7E82),
                        fontSize: 12,
                      ),
                    ),
                  ],
                ),
              ),
              Column(
                crossAxisAlignment: CrossAxisAlignment.end,
                children: [
                  Text(
                    '₹${anomaly.amount.toStringAsFixed(0)}',
                    style: const TextStyle(
                      color: textDark,
                      fontSize: 15,
                      fontWeight: FontWeight.bold,
                    ),
                  ),
                  Container(
                    margin: const EdgeInsets.only(top: 4),
                    padding: const EdgeInsets.symmetric(
                      horizontal: 8,
                      vertical: 2,
                    ),
                    decoration: BoxDecoration(
                      color: severityColor.withOpacity(0.1),
                      borderRadius: BorderRadius.circular(4),
                    ),
                    child: Text(
                      severityLabel,
                      style: TextStyle(
                        color: severityColor,
                        fontSize: 10,
                        fontWeight: FontWeight.bold,
                      ),
                    ),
                  ),
                ],
              ),
            ],
          ),
          const SizedBox(height: 12),
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              Text(
                'Anomaly Score: ${((anomaly.anomalyScore ?? 0) * 100).toStringAsFixed(1)}%',
                style: const TextStyle(
                  color: Color(0xFF6B7E82),
                  fontSize: 12,
                ),
              ),
              Text(
                _formatDate(anomaly.txnTimestamp),
                style: const TextStyle(
                  color: Color(0xFF6B7E82),
                  fontSize: 12,
                ),
              ),
            ],
          ),
        ],
      ),
    );
  }

  Color _getSeverityColor(String severity) {
    switch (severity.toLowerCase()) {
      case 'critical':
        return const Color(0xFFD32F2F);
      case 'high':
        return Colors.orange;
      case 'medium':
        return const Color(0xFFF57C00);
      case 'low':
        return const Color(0xFFFBC02D);
      default:
        return const Color(0xFF6B7E82);
    }
  }

  Widget _buildHeader() {
    return const Padding(
      padding: EdgeInsets.fromLTRB(20, 20, 20, 0),
      child: Text(
        'Insights',
        style: TextStyle(
          color: textPrimary,
          fontSize: 32,
          fontWeight: FontWeight.bold,
        ),
      ),
    );
  }

  Widget _buildSummaryCard() {
    return Container(
      decoration: BoxDecoration(
        color: const Color(0xFFF7F9FA),
        borderRadius: BorderRadius.circular(32),
      ),
      child: Stack(
        children: [
          Positioned(
            right: 20,
            top: 60,
            child: Opacity(
              opacity: 0.1,
              child: CustomPaint(
                size: const Size(120, 60),
                painter: LineChartPainter(),
              ),
            ),
          ),
          Padding(
            padding: const EdgeInsets.all(24.0),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Row(
                  mainAxisAlignment: MainAxisAlignment.spaceBetween,
                  children: [
                    const Text(
                      'February 2025',
                      style: TextStyle(
                        color: Colors.teal,
                        fontSize: 16,
                        fontWeight: FontWeight.w600,
                      ),
                    ),
                    Container(
                      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
                      decoration: BoxDecoration(
                        color: const Color(0xFFE5F9EF),
                        borderRadius: BorderRadius.circular(20),
                      ),
                      child: const Row(
                        children: [
                          Icon(Icons.arrow_upward, color: accentGreen, size: 14),
                          SizedBox(width: 4),
                          Text(
                            '+3 pts',
                            style: TextStyle(
                              color: accentGreen,
                              fontSize: 13,
                              fontWeight: FontWeight.bold,
                            ),
                          ),
                        ],
                      ),
                    ),
                  ],
                ),
                const SizedBox(height: 8),
                Row(
                  mainAxisAlignment: MainAxisAlignment.spaceBetween,
                  crossAxisAlignment: CrossAxisAlignment.end,
                  children: [
                    const Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text(
                          '₹28,500',
                          style: TextStyle(
                            color: Color(0xFF133C3B),
                            fontSize: 40,
                            fontWeight: FontWeight.w800,
                            height: 1.1,
                          ),
                        ),
                        SizedBox(height: 4),
                        Text(
                          'Total Spend',
                          style: TextStyle(
                            color: Colors.teal,
                            fontSize: 15,
                            fontWeight: FontWeight.w500,
                          ),
                        ),
                      ],
                    ),
                    const Padding(
                      padding: EdgeInsets.only(bottom: 24.0),
                      child: Text(
                        'Stability',
                        style: TextStyle(
                          color: Colors.teal,
                          fontSize: 14,
                          fontWeight: FontWeight.w600,
                        ),
                      ),
                    ),
                  ],
                ),
                const SizedBox(height: 24),
                Row(
                  children: [
                    Expanded(
                      child: Container(
                        padding: const EdgeInsets.all(16),
                        decoration: BoxDecoration(
                          color: Colors.white,
                          borderRadius: BorderRadius.circular(16),
                        ),
                        child: const Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            Text(
                              'Savings',
                              style: TextStyle(
                                color: Colors.teal,
                                fontSize: 13,
                                fontWeight: FontWeight.w500,
                              ),
                            ),
                            SizedBox(height: 8),
                            Text(
                              '₹16,500',
                              style: TextStyle(
                                color: accentGreen,
                                fontSize: 20,
                                fontWeight: FontWeight.w800,
                              ),
                            ),
                          ],
                        ),
                      ),
                    ),
                    const SizedBox(width: 16),
                    Expanded(
                      child: Container(
                        padding: const EdgeInsets.all(16),
                        decoration: BoxDecoration(
                          color: Colors.white,
                          borderRadius: BorderRadius.circular(16),
                        ),
                        child: const Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            Text(
                              'Vs Jan',
                              style: TextStyle(
                                color: Colors.teal,
                                fontSize: 13,
                                fontWeight: FontWeight.w500,
                              ),
                            ),
                            SizedBox(height: 8),
                            Text(
                              '+12%',
                              style: TextStyle(
                                color: Colors.orange,
                                fontSize: 20,
                                fontWeight: FontWeight.w800,
                              ),
                            ),
                          ],
                        ),
                      ),
                    ),
                  ],
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildBehaviorCard({
    required IconData icon,
    required Color iconColor,
    required Color iconBgColor,
    required String title,
    required RichText content,
    Widget? actionWidget,
  }) {
    return Container(
      width: double.infinity,
      padding: const EdgeInsets.all(20),
      decoration: BoxDecoration(
        color: cardBg,
        borderRadius: BorderRadius.circular(24),
      ),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Container(
            padding: const EdgeInsets.all(12),
            decoration: BoxDecoration(
              color: iconBgColor,
              borderRadius: BorderRadius.circular(16),
            ),
            child: Icon(icon, color: iconColor, size: 28),
          ),
          const SizedBox(width: 16),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  title,
                  style: const TextStyle(
                    color: textDark,
                    fontSize: 18,
                    fontWeight: FontWeight.bold,
                  ),
                ),
                const SizedBox(height: 8),
                content,
                if (actionWidget != null) actionWidget,
              ],
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildBarChartBar(double height, Color color) {
    return Container(
      width: 12,
      height: height,
      decoration: BoxDecoration(
        color: color,
        borderRadius: BorderRadius.circular(6),
      ),
    );
  }

  String _formatDate(DateTime date) {
    return '${date.day}/${date.month}/${date.year}';
  }
}

class LineChartPainter extends CustomPainter {
  @override
  void paint(Canvas canvas, Size size) {
    var paint = Paint()
      ..color = Colors.black
      ..strokeWidth = 12
      ..style = PaintingStyle.stroke
      ..strokeCap = StrokeCap.round
      ..strokeJoin = StrokeJoin.round;

    var path = Path();
    path.moveTo(0, size.height);
    path.lineTo(size.width * 0.4, size.height * 0.2);
    path.lineTo(size.width * 0.6, size.height * 0.6);
    path.lineTo(size.width, 0);
    
    path.moveTo(size.width, 0);
    path.lineTo(size.width * 0.85, 0);
    path.moveTo(size.width, 0);
    path.lineTo(size.width, size.height * 0.3);

    canvas.drawPath(path, paint);
  }

  @override
  bool shouldRepaint(CustomPainter oldDelegate) {
    return false;
  }
}

// Extended theme colors for accessibility
const Color bgColor = Color(0xFF163339);
const Color cardBg = Colors.white;
const Color accentGreen = Color(0xFF5DF22A);
const Color textPrimary = Colors.white;
const Color textSecondary = Color(0xFF8BA5A8);
const Color textDark = Color(0xFF1D2F35);
const Color iconBgLight = Color(0xFFF5F7F8);

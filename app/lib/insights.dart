import 'package:flutter/material.dart';

class InsightsScreen extends StatelessWidget {
  const InsightsScreen({Key? key}) : super(key: key);

  // Theme Colors
  static const Color bgColor = Color(0xFF163339); // Dark blue from dashboard
  static const Color cardBg = Colors.white;
  static const Color accentGreen = Color(0xFF5DF22A);
  static const Color textPrimary = Colors.white;
  static const Color textSecondary = Color(0xFF8BA5A8);
  static const Color textDark = Color(0xFF1D2F35);
  static const Color iconBgLight = Color(0xFFF5F7F8);

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
                          color: const Color(0xFFF5F9F8), // Very light teal tint
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
                            _buildBarChartBar(48, Colors.blue), // Current month highlighted
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
                    const SizedBox(height: 40), // Space before bottom nav
                  ],
                ),
              ),
            ],
          ),
        ),
      ),
    );
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
        color: const Color(0xFFF7F9FA), // Slightly off-white to match screenshot
        borderRadius: BorderRadius.circular(32),
      ),
      child: Stack(
        children: [
          // Faint background chart graphic
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
                            color: Color(0xFF133C3B), // Very dark teal
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

}

// Simple custom painter to draw a line chart path similar to the screenshot's background element
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
    
    // Add arrow head at the end
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

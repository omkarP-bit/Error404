import 'package:flutter/material.dart';

class DashboardScreen extends StatelessWidget {
  const DashboardScreen({Key? key}) : super(key: key);

  // Theme Colors based on the provided screenshots
  static const Color bgColor = Color(0xFF163339);
  static const Color accentGreen = Color(0xFF5DF22A);
  static const Color textPrimary = Colors.white;
  static const Color textSecondary = Color(0xFF8BA5A8);
  
  static const Color whiteCardColor = Colors.white;
  static const Color darkCardColor = Color(0xFF21444A);
  static const Color textDark = Color(0xFF1D2F35);

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: bgColor,
      body: SafeArea(
        child: SingleChildScrollView(
          padding: const EdgeInsets.symmetric(horizontal: 20.0, vertical: 10.0),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.center,
            children: [
              _buildHeader(),
              const SizedBox(height: 40),
              _buildStabilityScore(),
              const SizedBox(height: 30),
              _buildIncomeSavingsRow(),
              const SizedBox(height: 20),
              _buildBudgetStatus(),
              const SizedBox(height: 30),
              _buildAlertsSection(),
              const SizedBox(height: 20),
            ],
          ),
        ),
      ),
    );
  }

  Widget _buildHeader() {
    return Row(
      mainAxisAlignment: MainAxisAlignment.spaceBetween,
      children: [
        Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            const Row(
              children: [
                Text(
                  'Hi, Rahul',
                  style: TextStyle(
                    color: textPrimary,
                    fontSize: 28,
                    fontWeight: FontWeight.bold,
                  ),
                ),
                SizedBox(width: 8),
                Text('👋', style: TextStyle(fontSize: 24)),
              ],
            ),
            const SizedBox(height: 4),
            Text(
              'Welcome back to Stocki',
              style: TextStyle(
                color: textSecondary,
                fontSize: 16,
                fontWeight: FontWeight.w500,
              ),
            ),
          ],
        ),
        Container(
          height: 48,
          width: 48,
          decoration: BoxDecoration(
            shape: BoxShape.circle,
            color: accentGreen.withOpacity(0.5),
            border: Border.all(color: accentGreen.withOpacity(0.8), width: 2),
          ),
          child: const Center(
            child: Text(
              'R',
              style: TextStyle(
                color: Color(0xFF0F262B),
                fontSize: 20,
                fontWeight: FontWeight.bold,
              ),
            ),
          ),
        ),
      ],
    );
  }

  Widget _buildStabilityScore() {
    return Column(
      children: [
        SizedBox(
          height: 220,
          width: 220,
          child: Stack(
            fit: StackFit.expand,
            alignment: Alignment.center,
            children: [
              // Outer Glow
              Container(
                decoration: BoxDecoration(
                  shape: BoxShape.circle,
                  boxShadow: [
                    BoxShadow(
                      color: accentGreen.withOpacity(0.15),
                      blurRadius: 50,
                      spreadRadius: 10,
                    ),
                  ],
                ),
              ),
              CircularProgressIndicator(
                value: 0.74,
                strokeWidth: 16,
                backgroundColor: Colors.white.withOpacity(0.05),
                color: accentGreen,
                strokeCap: StrokeCap.round,
              ),
              Column(
                mainAxisAlignment: MainAxisAlignment.center,
                children: [
                  const Text(
                    '74',
                    style: TextStyle(
                      color: textPrimary,
                      fontSize: 64,
                      fontWeight: FontWeight.w800,
                      height: 1.1,
                    ),
                  ),
                  const SizedBox(height: 8),
                  Container(
                    padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 6),
                    decoration: BoxDecoration(
                      color: accentGreen.withOpacity(0.2),
                      borderRadius: BorderRadius.circular(20),
                      border: Border.all(color: accentGreen.withOpacity(0.5)),
                    ),
                    child: const Text(
                      'STABLE',
                      style: TextStyle(
                        color: accentGreen,
                        fontSize: 14,
                        fontWeight: FontWeight.w700,
                        letterSpacing: 1.0,
                      ),
                    ),
                  ),
                ],
              ),
            ],
          ),
        ),
        const SizedBox(height: 24),
        const Text(
          'Financial Stability Score',
          style: TextStyle(
            color: textSecondary,
            fontSize: 18,
            fontWeight: FontWeight.w600,
          ),
        ),
      ],
    );
  }

  Widget _buildIncomeSavingsRow() {
    return Row(
      children: [
        Expanded(
          child: _buildInfoCard(
            title: 'Income vs Exp',
            amount: '₹45k',
            changeText: '₹28.5k ↘',
            isPositiveChange: false,
            iconData: Icons.arrow_outward,
            iconColor: Colors.teal,
          ),
        ),
        const SizedBox(width: 16),
        Expanded(
          child: _buildInfoCard(
            title: 'Savings Rate',
            amount: '36.7%',
            changeText: '+2.4% vs last mo',
            isPositiveChange: true,
            iconData: Icons.trending_up,
            iconColor: accentGreen,
          ),
        ),
      ],
    );
  }

  Widget _buildInfoCard({
    required String title,
    required String amount,
    required String changeText,
    required bool isPositiveChange,
    required IconData iconData,
    required Color iconColor,
  }) {
    return Container(
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: whiteCardColor,
        borderRadius: BorderRadius.circular(24),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Container(
            padding: const EdgeInsets.all(8),
            decoration: BoxDecoration(
              color: iconColor.withOpacity(0.1),
              shape: BoxShape.circle,
            ),
            child: Icon(iconData, color: iconColor, size: 24),
          ),
          const SizedBox(height: 24),
          Text(
            title,
            style: const TextStyle(
              color: Color(0xFF6B7E82),
              fontSize: 14,
              fontWeight: FontWeight.w500,
            ),
          ),
          const SizedBox(height: 8),
          Text(
            amount,
            style: const TextStyle(
              color: textDark,
              fontSize: 26,
              fontWeight: FontWeight.w800,
            ),
          ),
          const SizedBox(height: 8),
          Text(
            changeText,
            style: TextStyle(
              color: isPositiveChange ? accentGreen : Colors.redAccent,
              fontSize: 13,
              fontWeight: FontWeight.w600,
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildBudgetStatus() {
    return Container(
      padding: const EdgeInsets.all(20),
      decoration: BoxDecoration(
        color: whiteCardColor,
        borderRadius: BorderRadius.circular(24),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              const Text(
                'Budget Status',
                style: TextStyle(
                  color: textDark,
                  fontSize: 20,
                  fontWeight: FontWeight.bold,
                ),
              ),
              Text(
                'View All',
                style: TextStyle(
                  color: accentGreen.withOpacity(0.8),
                  fontSize: 14,
                  fontWeight: FontWeight.bold,
                ),
              ),
            ],
          ),
          const SizedBox(height: 24),
          _buildBudgetProgressRow('🍔', 'Food & Dining', '₹8.2k / 10k', 0.82, Colors.orange),
          const SizedBox(height: 20),
          _buildBudgetProgressRow('🚗', 'Transport', '₹2.1k / 4k', 0.525, accentGreen),
          const SizedBox(height: 20),
          _buildBudgetProgressRow('🛍️', 'Shopping', '₹6.8k / 6k', 1.13, Colors.redAccent),
        ],
      ),
    );
  }

  Widget _buildBudgetProgressRow(String emoji, String title, String value, double progress, Color color) {
    return Column(
      children: [
        Row(
          mainAxisAlignment: MainAxisAlignment.spaceBetween,
          children: [
            Row(
              children: [
                Text(emoji, style: const TextStyle(fontSize: 16)),
                const SizedBox(width: 8),
                Text(
                  title,
                  style: const TextStyle(
                    color: textDark,
                    fontSize: 16,
                    fontWeight: FontWeight.w600,
                  ),
                ),
              ],
            ),
            Text(
              value,
              style: const TextStyle(
                color: Color(0xFF6B7E82),
                fontSize: 14,
                fontWeight: FontWeight.w600,
              ),
            ),
          ],
        ),
        const SizedBox(height: 10),
        ClipRRect(
          borderRadius: BorderRadius.circular(4),
          child: LinearProgressIndicator(
            value: progress > 1 ? 1 : progress,
            minHeight: 8,
            backgroundColor: Colors.grey.withOpacity(0.2),
            valueColor: AlwaysStoppedAnimation<Color>(color),
          ),
        ),
      ],
    );
  }

  Widget _buildAlertsSection() {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        const Text(
          'Alerts',
          style: TextStyle(
            color: textPrimary,
            fontSize: 22,
            fontWeight: FontWeight.bold,
          ),
        ),
        const SizedBox(height: 16),
        _buildAlertCard(
          iconData: Icons.error_outline,
          iconColor: Colors.redAccent,
          title: 'Overspending Alert',
          message: 'Shopping exceeded budget by ₹800',
        ),
        const SizedBox(height: 12),
        _buildAlertCard(
          iconData: Icons.warning_amber_rounded,
          iconColor: Colors.orangeAccent,
          title: 'Burn Rate Warning',
          message: 'At current pace, savings will drop 12% this month',
        ),
      ],
    );
  }

  Widget _buildAlertCard({
    required IconData iconData,
    required Color iconColor,
    required String title,
    required String message,
  }) {
    return ClipRRect(
      borderRadius: BorderRadius.circular(16),
      child: Container(
        color: darkCardColor,
        child: IntrinsicHeight(
          child: Row(
            children: [
              Container(width: 4, color: iconColor),
              Padding(
                padding: const EdgeInsets.all(16.0),
                child: Icon(iconData, color: iconColor, size: 24),
              ),
              Expanded(
                child: Padding(
                  padding: const EdgeInsets.symmetric(vertical: 16.0).copyWith(right: 16.0),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    mainAxisAlignment: MainAxisAlignment.center,
                    children: [
                      Text(
                        title,
                        style: const TextStyle(
                          color: textPrimary,
                          fontSize: 16,
                          fontWeight: FontWeight.w700,
                        ),
                      ),
                      const SizedBox(height: 4),
                      Text(
                        message,
                        style: const TextStyle(
                          color: textSecondary,
                          fontSize: 14,
                          fontWeight: FontWeight.w400,
                        ),
                      ),
                    ],
                  ),
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }

}

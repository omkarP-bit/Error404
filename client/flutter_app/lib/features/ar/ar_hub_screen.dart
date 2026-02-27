import 'package:flutter/material.dart';
import 'ar_budget_visualizer_screen.dart';
import 'ar_spending_tracker_screen.dart';
import 'ar_receipt_scanner_screen.dart';

class ARHubScreen extends StatelessWidget {
  const ARHubScreen({Key? key}) : super(key: key);

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('AR Finance Hub'),
      ),
      body: Padding(
        padding: const EdgeInsets.all(16),
        child: GridView.count(
          crossAxisCount: 2,
          crossAxisSpacing: 16,
          mainAxisSpacing: 16,
          children: [
            _buildARCard(
              context,
              'Budget Visualizer',
              Icons.pie_chart,
              Colors.blue,
              'View your budgets in 3D AR space',
              () => Navigator.push(
                context,
                MaterialPageRoute(builder: (_) => const ARBudgetVisualizerScreen()),
              ),
            ),
            _buildARCard(
              context,
              'Spending Tracker',
              Icons.bar_chart,
              Colors.green,
              'Visualize spending by category',
              () => Navigator.push(
                context,
                MaterialPageRoute(builder: (_) => const ARSpendingTrackerScreen()),
              ),
            ),
            _buildARCard(
              context,
              'Receipt Scanner',
              Icons.camera_alt,
              Colors.orange,
              'Scan receipts with AR overlay',
              () => Navigator.push(
                context,
                MaterialPageRoute(builder: (_) => const ARReceiptScannerScreen()),
              ),
            ),
            _buildARCard(
              context,
              'Coming Soon',
              Icons.stars,
              Colors.purple,
              'More AR features',
              null,
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildARCard(
    BuildContext context,
    String title,
    IconData icon,
    Color color,
    String description,
    VoidCallback? onTap,
  ) {
    return Card(
      elevation: 4,
      child: InkWell(
        onTap: onTap,
        child: Padding(
          padding: const EdgeInsets.all(16),
          child: Column(
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              Icon(icon, size: 48, color: color),
              const SizedBox(height: 12),
              Text(
                title,
                style: const TextStyle(
                  fontSize: 16,
                  fontWeight: FontWeight.bold,
                ),
                textAlign: TextAlign.center,
              ),
              const SizedBox(height: 8),
              Text(
                description,
                style: TextStyle(
                  fontSize: 12,
                  color: Colors.grey[600],
                ),
                textAlign: TextAlign.center,
              ),
            ],
          ),
        ),
      ),
    );
  }
}

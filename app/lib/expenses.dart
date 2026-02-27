import 'package:flutter/material.dart';
import 'package:fl_chart/fl_chart.dart';

class ExpensesScreen extends StatelessWidget {
  const ExpensesScreen({Key? key}) : super(key: key);

  // Theme Colors based on the provided screenshots
  static const Color bgColor = Color(0xFFF5F7F8); // Lighter background for expenses
  static const Color bottomNavColor = Color(0xFF163339); // Dark blue from dashboard
  static const Color accentGreen = Color(0xFF5DF22A);
  static const Color textDark = Color(0xFF1D2F35);
  static const Color textSecondary = Color(0xFF8BA5A8);
  static const Color redAccent = Color(0xFFFF4D4D);
  static const Color dividerColor = Color(0xFFE5E9EA);

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: bgColor,
      appBar: AppBar(
        backgroundColor: bgColor,
        elevation: 0,
        title: const Text(
          'Expenses',
          style: TextStyle(
            color: textDark,
            fontSize: 28,
            fontWeight: FontWeight.bold,
          ),
        ),
        actions: [
          Container(
            margin: const EdgeInsets.only(right: 20, top: 8, bottom: 8),
            padding: const EdgeInsets.symmetric(horizontal: 16),
            decoration: BoxDecoration(
              color: Colors.white,
              borderRadius: BorderRadius.circular(20),
              border: Border.all(color: dividerColor),
            ),
            child: const Row(
              children: [
                Text(
                  'This Month',
                  style: TextStyle(
                    color: Color(0xFF6B7E82),
                    fontSize: 14,
                    fontWeight: FontWeight.w500,
                  ),
                ),
                SizedBox(width: 4),
                Icon(Icons.keyboard_arrow_down, color: Color(0xFF6B7E82), size: 20),
              ],
            ),
          ),
        ],
      ),
      body: SafeArea(
        child: SingleChildScrollView(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              _buildFilterChips(),
              const SizedBox(height: 20),
              const Divider(color: dividerColor, height: 1),
              Padding(
                padding: const EdgeInsets.symmetric(horizontal: 20.0, vertical: 24.0),
                child: Column(
                  children: [
                    _buildExpenseItem(
                      icon: Icons.fastfood,
                      iconBgColor: const Color(0xFFFFF0E5),
                      iconColor: Colors.deepOrange,
                      title: 'Swiggy',
                      category: 'Food & Dining',
                      paymentMethod: 'Card',
                      amount: '-₹450',
                      isPositiveAmount: false,
                    ),
                    const SizedBox(height: 16),
                    _buildExpenseItem(
                      icon: Icons.directions_car,
                      iconBgColor: const Color(0xFFE5EEFF),
                      iconColor: Colors.blueAccent,
                      title: 'Uber',
                      category: 'Transport',
                      paymentMethod: 'Wallet',
                      amount: '-₹180',
                      isPositiveAmount: false,
                    ),
                    const SizedBox(height: 16),
                    _buildExpenseItem(
                      icon: Icons.shopping_bag,
                      iconBgColor: const Color(0xFFFFEAEA),
                      iconColor: Colors.redAccent,
                      title: 'Amazon',
                      category: 'Shopping',
                      paymentMethod: 'Card',
                      amount: '-₹2340',
                      isPositiveAmount: false,
                    ),
                    const SizedBox(height: 16),
                    _buildExpenseItem(
                      icon: Icons.local_pharmacy,
                      iconBgColor: const Color(0xFFE5F9EF),
                      iconColor: Colors.teal,
                      title: 'Apollo Pharmacy',
                      category: 'Health',
                      paymentMethod: 'Cash',
                      amount: '-₹320',
                      isPositiveAmount: false,
                      showUpArrow: true,
                    ),
                    const SizedBox(height: 16),
                    _buildExpenseItem(
                      icon: Icons.movie_creation,
                      iconBgColor: const Color(0xFFF3E5F5),
                      iconColor: Colors.deepPurple,
                      title: 'Netflix',
                      category: 'Entertainment',
                      paymentMethod: 'Card',
                      amount: '-₹649',
                      isPositiveAmount: false,
                    ),
                    const SizedBox(height: 16),
                    _buildExpenseItem(
                      icon: Icons.bolt,
                      iconBgColor: const Color(0xFFECEFF1),
                      iconColor: Colors.orange,
                      title: 'Electricity Bill',
                      category: 'Bills',
                      paymentMethod: 'Net Banking',
                      amount: '-₹1200',
                      isPositiveAmount: false,
                    ),
                    const SizedBox(height: 30),
                    _buildCategoryBreakdown(),
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

  Widget _buildFilterChips() {
    return Padding(
      padding: const EdgeInsets.only(left: 20.0, top: 16.0),
      child: SingleChildScrollView(
        scrollDirection: Axis.horizontal,
        child: Row(
          children: [
            _buildChip('All', isSelected: true),
            const SizedBox(width: 12),
            _buildChip('Food'),
            const SizedBox(width: 12),
            _buildChip('Transport'),
            const SizedBox(width: 12),
            _buildChip('Shopping'),
            const SizedBox(width: 16),
            Container(
              padding: const EdgeInsets.all(12),
              decoration: const BoxDecoration(
                color: accentGreen,
                shape: BoxShape.circle,
                boxShadow: [
                  BoxShadow(
                    color: Color(0x335DF22A),
                    blurRadius: 10,
                    spreadRadius: 2,
                    offset: Offset(0, 4),
                  ),
                ],
              ),
              child: const Icon(Icons.add, color: textDark),
            ),
            const SizedBox(width: 20),
          ],
        ),
      ),
    );
  }

  Widget _buildChip(String label, {bool isSelected = false}) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 10),
      decoration: BoxDecoration(
        color: isSelected ? textDark : Colors.transparent,
        borderRadius: BorderRadius.circular(24),
        border: Border.all(
          color: isSelected ? textDark : dividerColor,
        ),
      ),
      child: Text(
        label,
        style: TextStyle(
          color: isSelected ? Colors.white : const Color(0xFF6B7E82),
          fontSize: 14,
          fontWeight: isSelected ? FontWeight.w600 : FontWeight.w500,
        ),
      ),
    );
  }

  Widget _buildExpenseItem({
    required IconData icon,
    required Color iconBgColor,
    required Color iconColor,
    required String title,
    required String category,
    required String paymentMethod,
    required String amount,
    required bool isPositiveAmount,
    bool showUpArrow = false,
  }) {
    return Container(
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.circular(24),
        boxShadow: [
          BoxShadow(
            color: Colors.black.withOpacity(0.02),
            blurRadius: 10,
            offset: const Offset(0, 4),
          ),
        ],
      ),
      child: Row(
        children: [
          Container(
            padding: const EdgeInsets.all(12),
            decoration: BoxDecoration(
              color: iconBgColor,
              shape: BoxShape.circle,
            ),
            child: Icon(icon, color: iconColor, size: 24),
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
                    fontSize: 16,
                    fontWeight: FontWeight.bold,
                  ),
                ),
                const SizedBox(height: 6),
                Row(
                  children: [
                    Text(
                      category,
                      style: const TextStyle(
                        color: textSecondary,
                        fontSize: 13,
                        fontWeight: FontWeight.w500,
                      ),
                    ),
                    const SizedBox(width: 8),
                    Container(
                      padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
                      decoration: BoxDecoration(
                        color: bgColor,
                        borderRadius: BorderRadius.circular(6),
                        border: Border.all(color: dividerColor),
                      ),
                      child: Text(
                        paymentMethod,
                        style: const TextStyle(
                          color: Color(0xFF6B7E82),
                          fontSize: 11,
                          fontWeight: FontWeight.w500,
                        ),
                      ),
                    ),
                  ],
                ),
              ],
            ),
          ),
          Column(
            crossAxisAlignment: CrossAxisAlignment.end,
            children: [
              Text(
                amount,
                style: TextStyle(
                  color: isPositiveAmount ? accentGreen : redAccent,
                  fontSize: 18,
                  fontWeight: FontWeight.bold,
                ),
              ),
              const SizedBox(height: 4),
              Icon(
                showUpArrow ? Icons.arrow_upward : Icons.arrow_downward,
                color: showUpArrow ? accentGreen : redAccent.withOpacity(0.7),
                size: 14,
              ),
            ],
          ),
        ],
      ),
    );
  }

  Widget _buildCategoryBreakdown() {
    return Container(
      padding: const EdgeInsets.all(24),
      decoration: BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.circular(24),
        boxShadow: [
          BoxShadow(
            color: Colors.black.withOpacity(0.02),
            blurRadius: 10,
            offset: const Offset(0, 4),
          ),
        ],
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const Text(
            'Category Breakdown',
            style: TextStyle(
              color: textDark,
              fontSize: 20,
              fontWeight: FontWeight.bold,
            ),
          ),
          const SizedBox(height: 30),
          Row(
            children: [
              SizedBox(
                height: 160,
                width: 160,
                child: Stack(
                  alignment: Alignment.center,
                  children: [
                    PieChart(
                      PieChartData(
                        sectionsSpace: 4,
                        centerSpaceRadius: 50,
                        sections: [
                          PieChartSectionData(
                            color: const Color(0xFFFEA04C), // Orange for Food
                            value: 45,
                            title: '',
                            radius: 20,
                          ),
                          PieChartSectionData(
                            color: const Color(0xFF4A85F6), // Blue for Transport
                            value: 15,
                            title: '',
                            radius: 20,
                          ),
                          PieChartSectionData(
                            color: const Color(0xFFFF5656), // Red for Shopping
                            value: 25,
                            title: '',
                            radius: 20,
                          ),
                           PieChartSectionData(
                            color: const Color(0xFF2BDB7C), // Green
                            value: 5,
                            title: '',
                            radius: 20,
                          ),
                          PieChartSectionData(
                            color: const Color(0xFFA55EED), // Purple
                            value: 10,
                            title: '',
                            radius: 20,
                          ),
                        ],
                      ),
                    ),
                    const Column(
                      mainAxisAlignment: MainAxisAlignment.center,
                      children: [
                        Text(
                          'Total',
                          style: TextStyle(
                            color: textSecondary,
                            fontSize: 14,
                            fontWeight: FontWeight.w500,
                          ),
                        ),
                        Text(
                          '₹21k',
                          style: TextStyle(
                            color: textDark,
                            fontSize: 22,
                            fontWeight: FontWeight.bold,
                          ),
                        ),
                      ],
                    ),
                  ],
                ),
              ),
              const SizedBox(width: 24),
              Expanded(
                child: Column(
                  mainAxisAlignment: MainAxisAlignment.center,
                  children: [
                    _buildLegendItem(color: const Color(0xFFFEA04C), title: 'Food', amount: '₹8200'),
                    const SizedBox(height: 12),
                    _buildLegendItem(color: const Color(0xFF4A85F6), title: 'Transport', amount: '₹2100'),
                    const SizedBox(height: 12),
                    _buildLegendItem(color: const Color(0xFFFF5656), title: 'Shopping', amount: '₹6800'),
                    const SizedBox(height: 20),
                    const Divider(color: dividerColor),
                    const SizedBox(height: 12),
                    Row(
                      mainAxisAlignment: MainAxisAlignment.spaceBetween,
                      children: [
                        const Text(
                          'Budget Used',
                          style: TextStyle(
                            color: textSecondary,
                            fontSize: 14,
                            fontWeight: FontWeight.w500,
                          ),
                        ),
                        const Text(
                          '78%',
                          style: TextStyle(
                            color: textDark,
                            fontSize: 16,
                            fontWeight: FontWeight.bold,
                          ),
                        ),
                      ],
                    ),
                  ],
                ),
              ),
            ],
          ),
        ],
      ),
    );
  }

  Widget _buildLegendItem({required Color color, required String title, required String amount}) {
    return Row(
      children: [
        Container(
          width: 8,
          height: 8,
          decoration: BoxDecoration(
            color: color,
            shape: BoxShape.circle,
          ),
        ),
        const SizedBox(width: 8),
        Expanded(
          child: Text(
            title,
            style: const TextStyle(
              color: Color(0xFF6B7E82),
              fontSize: 14,
              fontWeight: FontWeight.w500,
            ),
          ),
        ),
        Text(
          amount,
          style: const TextStyle(
            color: textDark,
            fontSize: 14,
            fontWeight: FontWeight.bold,
          ),
        ),
      ],
    );
  }

}

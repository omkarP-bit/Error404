import 'package:flutter/material.dart';
import 'package:fl_chart/fl_chart.dart';
import 'package:image_picker/image_picker.dart';
import 'dart:io';
import 'services/api_service.dart';
import 'utils/image_compression.dart';

class ExpensesScreen extends StatefulWidget {
  const ExpensesScreen({Key? key}) : super(key: key);

  @override
  State<ExpensesScreen> createState() => _ExpensesScreenState();
}

class _ExpensesScreenState extends State<ExpensesScreen> {
  final ApiService _apiService = ApiService();
  final int _userId = 1; // Replace with actual user ID from auth
  final int _accountId = 1; // Replace with actual account ID
  
  List<Transaction> _transactions = [];
  CategoryBreakdown? _categoryBreakdown;
  bool _isLoadingTransactions = true;
  bool _isLoadingBreakdown = true;
  String? _errorMessage;
  AnomalyScanResult? _anomalyScanResult;
  
  // Filter state
  String _selectedCategory = 'All';
  String _selectedTimePeriod = 'This Month';
  bool _showAnomaliesExpanded = false;

  @override
  void initState() {
    super.initState();
    _loadData();
  }

  Future<void> _loadData() async {
    await Future.wait([
      _loadTransactions(),
      _loadCategoryBreakdown(),
    ]);
  }

  Future<void> _loadTransactions() async {
    try {
      if (mounted) setState(() => _isLoadingTransactions = true);
      final response = await _apiService.getTransactions(
        userId: _userId,
        limit: 50,
      );
      if (mounted) {
        setState(() {
          _transactions = response.transactions;
          _isLoadingTransactions = false;
        });
      }
    } catch (e) {
      if (mounted) {
        setState(() {
          _errorMessage = 'Failed to load transactions: $e';
          _isLoadingTransactions = false;
        });
      }
      if (mounted) _showErrorSnackBar(_errorMessage!);
    }
  }

  Future<void> _loadCategoryBreakdown() async {
    try {
      if (mounted) setState(() => _isLoadingBreakdown = true);
      final breakdown = await _apiService.getCategoryBreakdown(userId: _userId);
      if (mounted) {
        setState(() {
          _categoryBreakdown = breakdown;
          _isLoadingBreakdown = false;
        });
      }
    } catch (e) {
      if (mounted) {
        setState(() {
          _errorMessage = 'Failed to load category breakdown: $e';
          _isLoadingBreakdown = false;
        });
      }
    }
  }

  Future<void> _scanAnomalies() async {
    try {
      final result = await _apiService.scanAnomalies(userId: _userId);
      if (mounted) {
        setState(() => _anomalyScanResult = result);
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text('Detected ${result.totalAnomalies} anomalies in ${result.totalScanned} transactions'),
            duration: const Duration(seconds: 3),
          ),
        );
      }
    } catch (e) {
      if (mounted) _showErrorSnackBar('Failed to scan anomalies: $e');
    }
  }

  void _showAddTransactionDialog() {
    showDialog(
      context: context,
      builder: (context) => _AddTransactionDialog(
        userId: _userId,
        accountId: _accountId,
        apiService: _apiService,
        onTransactionAdded: (transaction) {
          _loadData();
          Navigator.pop(context);
          ScaffoldMessenger.of(context).showSnackBar(
            SnackBar(
              content: Text('Transaction added: ${transaction.category}'),
              duration: const Duration(seconds: 2),
            ),
          );
        },
      ),
    );
  }

  void _showErrorSnackBar(String message) {
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(
        content: Text(message),
        backgroundColor: Colors.red,
        duration: const Duration(seconds: 3),
      ),
    );
  }

  String _extractMerchantName(String? rawName) {
    // Use raw_name directly from database
    if (rawName == null || rawName.isEmpty) {
      return 'Unknown Merchant';
    }
    
    // Return the merchant name, with truncation if too long
    return rawName.length > 25 
      ? '${rawName.substring(0, 22)}...'
      : rawName;
  }

  List<Transaction> _getFilteredTransactions() {
    var filtered = _transactions
        .where((t) => t.txnType == 'debit')
        .toList();

    // Filter by category
    if (_selectedCategory != 'All') {
      filtered = filtered
          .where((t) => (t.category ?? '').toLowerCase().contains(_selectedCategory.toLowerCase()))
          .toList();
    }

    // Filter by date
    final now = DateTime.now();
    DateTime startDate;
    
    switch (_selectedTimePeriod) {
      case 'Daily':
        startDate = DateTime(now.year, now.month, now.day);
        break;
      case 'Weekly':
        startDate = now.subtract(Duration(days: now.weekday - 1));
        break;
      case 'This Month':
      default:
        startDate = DateTime(now.year, now.month, 1);
    }

    filtered = filtered
        .where((t) => t.txnTimestamp.isAfter(startDate))
        .toList();

    // Sort by date descending
    filtered.sort((a, b) => b.txnTimestamp.compareTo(a.txnTimestamp));
    
    return filtered;
  }

  @override
  Widget build(BuildContext context) {
    final filteredTransactions = _getFilteredTransactions();

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
          Tooltip(
            message: 'Scan for anomalies',
            child: Container(
              margin: const EdgeInsets.only(right: 10),
              child: Material(
                color: Colors.transparent,
                child: InkWell(
                  onTap: _scanAnomalies,
                  child: Container(
                    padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
                    decoration: BoxDecoration(
                      color: Colors.white,
                      borderRadius: BorderRadius.circular(20),
                      border: Border.all(color: dividerColor),
                    ),
                    child: Row(
                      mainAxisSize: MainAxisSize.min,
                      children: [
                        Icon(
                          Icons.warning_amber,
                          color: _anomalyScanResult != null && _anomalyScanResult!.totalAnomalies > 0
                              ? Colors.orange
                              : Color(0xFF6B7E82),
                          size: 18,
                        ),
                        const SizedBox(width: 6),
                        Text(
                          _anomalyScanResult != null
                              ? '${_anomalyScanResult!.totalAnomalies} Anomalies'
                              : 'Scan',
                          style: TextStyle(
                            color: _anomalyScanResult != null && _anomalyScanResult!.totalAnomalies > 0
                                ? Colors.orange
                                : Color(0xFF6B7E82),
                            fontSize: 13,
                            fontWeight: FontWeight.w500,
                          ),
                        ),
                      ],
                    ),
                  ),
                ),
              ),
            ),
          ),
          PopupMenuButton<String>(
            offset: const Offset(0, 40),
            onSelected: (value) {
              if (mounted) {
                setState(() => _selectedTimePeriod = value);
              }
            },
            itemBuilder: (BuildContext context) => [
              const PopupMenuItem(
                value: 'Daily',
                child: Text('Daily'),
              ),
              const PopupMenuItem(
                value: 'Weekly',
                child: Text('Weekly'),
              ),
              const PopupMenuItem(
                value: 'This Month',
                child: Text('This Month'),
              ),
            ],
            child: Container(
              margin: const EdgeInsets.only(right: 20, top: 8, bottom: 8),
              padding: const EdgeInsets.symmetric(horizontal: 16),
              decoration: BoxDecoration(
                color: Colors.white,
                borderRadius: BorderRadius.circular(20),
                border: Border.all(color: dividerColor),
              ),
              child: Row(
                mainAxisSize: MainAxisSize.min,
                children: [
                  Text(
                    _selectedTimePeriod,
                    style: const TextStyle(
                      color: Color(0xFF6B7E82),
                      fontSize: 14,
                      fontWeight: FontWeight.w500,
                    ),
                  ),
                  const SizedBox(width: 4),
                  const Icon(Icons.keyboard_arrow_down, color: Color(0xFF6B7E82), size: 20),
                ],
              ),
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
                    // Category Breakdown at top
                    if (_isLoadingBreakdown)
                      const Center(
                        child: CircularProgressIndicator(
                          valueColor: AlwaysStoppedAnimation<Color>(accentGreen),
                        ),
                      )
                    else if (_categoryBreakdown != null)
                      _buildCategoryBreakdown(_categoryBreakdown!)
                    else
                      _buildEmptyBreakdown(),

                    const SizedBox(height: 30),

                    // Display anomaly warning if detected
                    if (_anomalyScanResult != null && _anomalyScanResult!.totalAnomalies > 0)
                      _buildAnomalyAlert(),
                    if (_anomalyScanResult != null && _anomalyScanResult!.totalAnomalies > 0)
                      const SizedBox(height: 20),

                    // Display transactions from backend
                    if (_isLoadingTransactions)
                      const Center(
                        child: CircularProgressIndicator(
                          valueColor: AlwaysStoppedAnimation<Color>(accentGreen),
                        ),
                      )
                    else if (filteredTransactions.isEmpty)
                      _buildEmptyState()
                    else
                      ...filteredTransactions.take(10).map((transaction) {
                        final isAnomalous = _anomalyScanResult?.anomalies
                                .any((a) => a.txnId == transaction.txnId) ??
                            false;
                        return Column(
                          children: [
                            _buildTransactionItem(transaction, isAnomalous),
                            const SizedBox(height: 16),
                          ],
                        );
                      }).toList(),

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

  Widget _buildAnomalyAlert() {
    return Container(
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: const Color(0xFFFFF3E0),
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: const Color(0xFFFFB74D)),
      ),
      child: Row(
        children: [
          const Icon(Icons.error_outline, color: Colors.orange, size: 24),
          const SizedBox(width: 12),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                const Text(
                  'Anomalies Detected',
                  style: TextStyle(
                    color: Colors.orange,
                    fontSize: 16,
                    fontWeight: FontWeight.bold,
                  ),
                ),
                const SizedBox(height: 4),
                Text(
                  '${_anomalyScanResult!.totalAnomalies} unusual transaction(s) found',
                  style: const TextStyle(
                    color: Color(0xFF6B7E82),
                    fontSize: 13,
                  ),
                ),
              ],
            ),
          ),
          TextButton(
            onPressed: () {
              ScaffoldMessenger.of(context).showSnackBar(
                const SnackBar(content: Text('View anomalies in Insights tab')),
              );
            },
            child: const Text('View', style: TextStyle(color: Colors.orange)),
          ),
        ],
      ),
    );
  }

  Widget _buildEmptyState() {
    return Center(
      child: Padding(
        padding: const EdgeInsets.all(32.0),
        child: Column(
          children: [
            Icon(Icons.inbox_outlined, size: 64, color: dividerColor),
            const SizedBox(height: 16),
            const Text(
              'No transactions yet',
              style: TextStyle(
                color: textSecondary,
                fontSize: 18,
                fontWeight: FontWeight.w500,
              ),
            ),
            const SizedBox(height: 8),
            const Text(
              'Add your first transaction to get started',
              style: TextStyle(
                color: textSecondary,
                fontSize: 14,
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildEmptyBreakdown() {
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
      child: const Center(
        child: Text(
          'Category data will appear here',
          style: TextStyle(color: textSecondary),
        ),
      ),
    );
  }

  Widget _buildTransactionItem(Transaction transaction, bool isAnomalous) {
    final iconData = _getIconForCategory(transaction.category ?? 'Other');
    final iconBgColor = _getColorForCategory(transaction.category ?? 'Other');

    return Container(
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: isAnomalous ? const Color(0xFFFFF3E0) : Colors.white,
        borderRadius: BorderRadius.circular(24),
        border: isAnomalous
            ? Border.all(color: const Color(0xFFFFB74D), width: 1.5)
            : null,
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
              color: iconBgColor.withOpacity(0.2),
              shape: BoxShape.circle,
            ),
            child: Icon(iconData, color: iconBgColor, size: 24),
          ),
          const SizedBox(width: 16),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Row(
                  children: [
                    Expanded(
                      child: Text(
                        _extractMerchantName(transaction.rawName),
                        style: const TextStyle(
                          color: textDark,
                          fontSize: 16,
                          fontWeight: FontWeight.bold,
                        ),
                        maxLines: 1,
                        overflow: TextOverflow.ellipsis,
                      ),
                    ),
                    if (isAnomalous)
                      Container(
                        margin: const EdgeInsets.only(left: 8),
                        padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
                        decoration: BoxDecoration(
                          color: Colors.orange,
                          borderRadius: BorderRadius.circular(6),
                        ),
                        child: const Text(
                          'Anomaly',
                          style: TextStyle(
                            color: Colors.white,
                            fontSize: 10,
                            fontWeight: FontWeight.bold,
                          ),
                        ),
                      ),
                  ],
                ),
                const SizedBox(height: 6),
                Row(
                  children: [
                    Text(
                      transaction.category ?? 'Uncategorized',
                      style: const TextStyle(
                        color: textSecondary,
                        fontSize: 13,
                        fontWeight: FontWeight.w500,
                      ),
                    ),
                    if (transaction.confidenceScore != null)
                      Padding(
                        padding: const EdgeInsets.only(left: 8),
                        child: Container(
                          padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
                          decoration: BoxDecoration(
                            color: bgColor,
                            borderRadius: BorderRadius.circular(6),
                            border: Border.all(color: dividerColor),
                          ),
                          child: Text(
                            '${(transaction.confidenceScore! * 100).toStringAsFixed(0)}%',
                            style: const TextStyle(
                              color: Color(0xFF6B7E82),
                              fontSize: 11,
                              fontWeight: FontWeight.w500,
                            ),
                          ),
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
                        transaction.paymentMode ?? 'Unknown',
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
                '-₹${transaction.amount.toStringAsFixed(0)}',
                style: const TextStyle(
                  color: redAccent,
                  fontSize: 18,
                  fontWeight: FontWeight.bold,
                ),
              ),
              const SizedBox(height: 4),
              Text(
                _formatDate(transaction.txnTimestamp),
                style: const TextStyle(
                  color: textSecondary,
                  fontSize: 12,
                ),
              ),
            ],
          ),
        ],
      ),
    );
  }

  Widget _buildFilterChips() {
    final categories = ['All', 'Food', 'Transport', 'Shopping'];
    
    return Padding(
      padding: const EdgeInsets.only(left: 20.0, top: 16.0),
      child: SingleChildScrollView(
        scrollDirection: Axis.horizontal,
        child: Row(
          children: [
            ...categories.map((category) {
              final isSelected = _selectedCategory == category;
              return Row(
                children: [
                  GestureDetector(
                    onTap: () {
                      if (mounted) {
                        setState(() => _selectedCategory = category);
                      }
                    },
                    child: _buildChip(category, isSelected: isSelected),
                  ),
                  const SizedBox(width: 12),
                ],
              );
            }).toList(),
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
              child: GestureDetector(
                onTap: _showAddTransactionDialog,
                child: const Icon(Icons.add, color: textDark),
              ),
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

  Widget _buildCategoryBreakdown(CategoryBreakdown breakdown) {
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
          if (breakdown.categories.isEmpty)
            const Center(
              child: Text('No expense data available'),
            )
          else
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
                          sections: breakdown.categories
                              .take(5)
                              .map((item) {
                            return PieChartSectionData(
                              color: item.displayColor ??
                                  const Color(0xFF8BA5A8),
                              value: item.percentage,
                              title: '',
                              radius: 20,
                            );
                          }).toList(),
                        ),
                      ),
                      Column(
                        mainAxisAlignment: MainAxisAlignment.center,
                        children: [
                          const Text(
                            'Total',
                            style: TextStyle(
                              color: textSecondary,
                              fontSize: 14,
                              fontWeight: FontWeight.w500,
                            ),
                          ),
                          Text(
                            '₹${(breakdown.totalExpense / 1000).toStringAsFixed(1)}k',
                            style: const TextStyle(
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
                      ...breakdown.categories
                          .take(3)
                          .map((item) => Column(
                            children: [
                              _buildLegendItem(
                                color: item.displayColor ??
                                    const Color(0xFF8BA5A8),
                                title: item.category,
                                amount:
                                    '₹${item.totalAmount.toStringAsFixed(0)}',
                              ),
                              const SizedBox(height: 12),
                            ],
                          ))
                          .toList(),
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
                          Text(
                            '78%',
                            style: const TextStyle(
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

  // Helper methods
  IconData _getIconForCategory(String category) {
    final lower = category.toLowerCase();
    if (lower.contains('food') || lower.contains('dining'))
      return Icons.fastfood;
    if (lower.contains('transport') || lower.contains('travel'))
      return Icons.directions_car;
    if (lower.contains('shop') || lower.contains('retail'))
      return Icons.shopping_bag;
    if (lower.contains('health') || lower.contains('medical'))
      return Icons.local_pharmacy;
    if (lower.contains('entertain') || lower.contains('movie'))
      return Icons.movie_creation;
    if (lower.contains('bill') || lower.contains('utility'))
      return Icons.bolt;
    return Icons.local_offer;
  }

  Color _getColorForCategory(String category) {
    final lower = category.toLowerCase();
    if (lower.contains('food') || lower.contains('dining'))
      return Colors.deepOrange;
    if (lower.contains('transport') || lower.contains('travel'))
      return Colors.blueAccent;
    if (lower.contains('shop') || lower.contains('retail'))
      return Colors.redAccent;
    if (lower.contains('health') || lower.contains('medical'))
      return Colors.teal;
    if (lower.contains('entertain') || lower.contains('movie'))
      return Colors.deepPurple;
    if (lower.contains('bill') || lower.contains('utility'))
      return Colors.orange;
    return Colors.grey;
  }

  String _formatDate(DateTime date) {
    return '${date.day}/${date.month}/${date.year}';
  }

  // Theme Colors
  static const Color bgColor = Color(0xFFF5F7F8);
  static const Color textDark = Color(0xFF1D2F35);
  static const Color textSecondary = Color(0xFF8BA5A8);
  static const Color redAccent = Color(0xFFFF4D4D);
  static const Color accentGreen = Color(0xFF5DF22A);
  static const Color dividerColor = Color(0xFFE5E9EA);
}

// ────────────────────────────────────────────────────────
// ADD TRANSACTION DIALOG
// ────────────────────────────────────────────────────────

class _AddTransactionDialog extends StatefulWidget {
  final int userId;
  final int accountId;
  final ApiService apiService;
  final Function(Transaction) onTransactionAdded;

  const _AddTransactionDialog({
    required this.userId,
    required this.accountId,
    required this.apiService,
    required this.onTransactionAdded,
  });

  @override
  State<_AddTransactionDialog> createState() => _AddTransactionDialogState();
}

class _AddTransactionDialogState extends State<_AddTransactionDialog> {
  final _descriptionController = TextEditingController();
  final _amountController = TextEditingController();
  final _merchantController = TextEditingController();
  final ImagePicker _imagePicker = ImagePicker();
  
  CategorizationResult? _categorizationResult;
  bool _isLoading = false;
  bool _isConfirmingCategory = false;
  bool _isScanningOCR = false;
  String? _selectedCategory;
  String? _selectedSubcategory;
  String _paymentMode = 'UPI';
  String _transactionType = 'debit';
  XFile? _selectedImage;
  bool _merchantExists = false;
  String? _merchantCheckMessage;

  @override
  void dispose() {
    _descriptionController.dispose();
    _amountController.dispose();
    _merchantController.dispose();
    super.dispose();
  }

  /// Scan receipt using camera/gallery and send to backend for OCR processing
  Future<void> _scanReceipt() async {
    try {
      if (mounted) setState(() => _isScanningOCR = true);

      // Show option to pick from camera or gallery
      final source = await showDialog<ImageSource>(
        context: context,
        builder: (context) => AlertDialog(
          title: const Text('Capture Receipt'),
          content: const Text('Choose to take a photo or select from gallery'),
          actions: [
            TextButton(
              onPressed: () => Navigator.pop(context, ImageSource.camera),
              child: const Text('Camera'),
            ),
            TextButton(
              onPressed: () => Navigator.pop(context, ImageSource.gallery),
              child: const Text('Gallery'),
            ),
            TextButton(
              onPressed: () => Navigator.pop(context),
              child: const Text('Cancel'),
            ),
          ],
        ),
      );

      if (source == null) {
        if (mounted) setState(() => _isScanningOCR = false);
        return;
      }

      // Pick image with initial compression
      final image = await _imagePicker.pickImage(
        source: source,
        // Reduce resolution/quality to avoid large buffers on device
        // and speed up upload/processing.
        imageQuality: 70,
        maxWidth: 1280,
        maxHeight: 1280,
      );

      if (image == null) {
        if (mounted) setState(() => _isScanningOCR = false);
        return;
      }

      if (mounted) setState(() => _selectedImage = image);

      // Further compress the image before sending to backend
      debugPrint('Original image path: ${image.path}');
      String imagePath = image.path;
      
      try {
        imagePath = await ImageCompressionUtil.compressReceiptImage(image.path);
        debugPrint('Using compressed image: $imagePath');
      } catch (e) {
        debugPrint('Image compression failed, using original: $e');
        // Continue with original image if compression fails
      }

      // Send to backend for OCR processing
      debugPrint('Processing receipt image: $imagePath');
      final ocrResult = await widget.apiService.processReceiptImage(
        imagePath: imagePath,
      );

      if (mounted) {
        setState(() {
          if (ocrResult.merchantName != null && ocrResult.merchantName!.isNotEmpty) {
            _merchantController.text = ocrResult.merchantName!;
          }
          if (ocrResult.description != null && ocrResult.description!.isNotEmpty) {
            _descriptionController.text = ocrResult.description!;
          }
          if (ocrResult.amount != null && ocrResult.amount! > 0) {
            _amountController.text = ocrResult.amount!.toStringAsFixed(2);
          }
          _isScanningOCR = false;
        });

        // Check merchant after OCR
        if (ocrResult.merchantName != null && ocrResult.merchantName!.length > 2) {
          _checkMerchantExists();
        }

        // Show success feedback
        if (mounted) {
          ScaffoldMessenger.of(context).showSnackBar(
            SnackBar(
              content: Text(
                'Receipt scanned! Extracted: ${ocrResult.merchantName ?? "merchant"}, ₹${ocrResult.amount ?? "0"}',
              ),
              backgroundColor: const Color(0xFF2BDB7C),
              duration: const Duration(seconds: 3),
            ),
          );
        }
      }
    } catch (e) {
      if (mounted) {
        setState(() => _isScanningOCR = false);
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text('Scan failed: $e'),
            backgroundColor: Colors.red,
            duration: const Duration(seconds: 4),
          ),
        );
      }
    }
  }

  /// Show receipt preview dialog for verification
  void _showReceiptPreviewDialog(XFile image) {
    showDialog(
      context: context,
      barrierDismissible: true,
      builder: (context) => AlertDialog(
        title: const Text('Receipt Preview'),
        content: SingleChildScrollView(
          child: Column(
            mainAxisSize: MainAxisSize.min,
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              // Receipt image preview
              Container(
                width: double.maxFinite,
                height: 250,
                decoration: BoxDecoration(
                  borderRadius: BorderRadius.circular(8),
                  border: Border.all(color: Colors.grey[300]!),
                ),
                child: Image.file(
                  File(image.path),
                  fit: BoxFit.cover,
                ),
              ),
              const SizedBox(height: 12),
              Container(
                padding: const EdgeInsets.all(12),
                decoration: BoxDecoration(
                  color: Colors.green.withOpacity(0.1),
                  borderRadius: BorderRadius.circular(8),
                ),
                child: const Row(
                  children: [
                    Icon(Icons.check_circle, color: Colors.green, size: 20),
                    SizedBox(width: 8),
                    Expanded(
                      child: Text(
                        'Receipt scanned successfully. Fields auto-filled.',
                        style: TextStyle(fontSize: 12, color: Colors.green),
                      ),
                    ),
                  ],
                ),
              ),
            ],
          ),
        ),
        actions: [
          TextButton(
            onPressed: () {
              Navigator.pop(context);
              _selectedImage = null;
              if (mounted) setState(() {});
            },
            child: const Text('Retake'),
          ),
          ElevatedButton(
            onPressed: () => Navigator.pop(context),
            child: const Text('Done'),
          ),
        ],
      ),
    );
  }

  /// Check if merchant already exists in database
  Future<void> _checkMerchantExists() async {
    if (_merchantController.text.isEmpty) return;

    try {
      final result = await widget.apiService.checkMerchantExists(
        merchantName: _merchantController.text.trim(),
        userId: widget.userId,
      );

      if (mounted) {
        setState(() {
          _merchantExists = result.exists;
          _merchantCheckMessage = result.message;
        });

        if (_merchantExists) {
          ScaffoldMessenger.of(context).showSnackBar(
            SnackBar(
              content: Text('Merchant "${_merchantController.text}" already exists'),
              backgroundColor: const Color(0xFF2BDB7C),
            ),
          );
        }
      }
    } catch (e) {
      debugPrint('Merchant check error: $e');
      // Non-blocking error - continue anyway
    }
  }

  /// Add new merchant if it doesn't exist
  Future<bool> _addMerchantIfNeeded() async {
    if (_merchantController.text.isEmpty || _merchantExists) {
      return true; // Skip if merchant already exists or no merchant name
    }

    try {
      final merchantId = await widget.apiService.addMerchant(
        merchantName: _merchantController.text.trim(),
        userId: widget.userId,
        category: _selectedCategory ?? 'Unknown',
      );

      if (merchantId > 0) {
        if (mounted) {
          ScaffoldMessenger.of(context).showSnackBar(
            SnackBar(
              content: Text('New merchant "${_merchantController.text}" added'),
              backgroundColor: Colors.blue,
            ),
          );
        }
        return true;
      }
    } catch (e) {
      debugPrint('Error adding merchant: $e');
      // Non-blocking error - continue with transaction
    }
    return true;
  }

  Future<void> _categorizeTransaction() async {
    if (_descriptionController.text.isEmpty || _amountController.text.isEmpty) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Please fill all required fields')),
      );
      return;
    }

    try {
      if (mounted) setState(() => _isLoading = true);

      final result = await widget.apiService.categorizeTransaction(
        rawDescription: _descriptionController.text,
        amount: double.parse(_amountController.text),
        accountId: widget.accountId,
        merchantName: _merchantController.text,
        txnType: _transactionType,
      );

      if (mounted) {
        setState(() {
          _categorizationResult = result;
          _selectedCategory = result.category;
          _selectedSubcategory = result.subcategory;
          _isLoading = false;
          _isConfirmingCategory = true;
        });
      }

      // Always show the prediction dialog so the user can
      // see the confidence score and choose to add or
      // correct the category, regardless of confidence.
      if (mounted) {
        _showCategoryConfirmationDialog();
      }
    } catch (e) {
      if (mounted) setState(() => _isLoading = false);
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('Categorization failed: $e')),
        );
      }
    }
  }

  void _showCategoryConfirmationDialog() {
    showDialog(
      context: context,
      barrierDismissible: false,
      builder: (context) => AlertDialog(
        backgroundColor: Colors.white,
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
        title: const Text(
          '📊 Prediction Result',
          style: TextStyle(
            fontSize: 20,
            fontWeight: FontWeight.bold,
            color: Color(0xFF1D2F35),
          ),
        ),
        content: SizedBox(
          width: double.maxFinite,
          child: SingleChildScrollView(
            child: Column(
              mainAxisSize: MainAxisSize.min,
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                // Confidence Score Display
                _buildConfidenceScoreWidget(),
                const SizedBox(height: 20),
                
                // Category Suggestion
                Container(
                  padding: const EdgeInsets.all(16),
                  decoration: BoxDecoration(
                    color: const Color(0xFFF5F7F8),
                    borderRadius: BorderRadius.circular(12),
                    border: Border.all(
                      color: const Color(0xFFE5E9EA),
                      width: 1.5,
                    ),
                  ),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      const Text(
                        'Suggested Category',
                        style: TextStyle(
                          fontSize: 12,
                          color: Color(0xFF8BA5A8),
                          fontWeight: FontWeight.w500,
                        ),
                      ),
                      const SizedBox(height: 8),
                      Text(
                        _categorizationResult?.category ?? 'Unknown',
                        style: const TextStyle(
                          fontSize: 18,
                          fontWeight: FontWeight.bold,
                          color: Color(0xFF1D2F35),
                        ),
                      ),
                      if (_categorizationResult?.subcategory != null &&
                          _categorizationResult!.subcategory.isNotEmpty) ...[
                        const SizedBox(height: 8),
                        Row(
                          children: [
                            const Text(
                              'Subcategory: ',
                              style: TextStyle(
                                fontSize: 12,
                                color: Color(0xFF8BA5A8),
                              ),
                            ),
                            Expanded(
                              child: Text(
                                _categorizationResult!.subcategory,
                                style: const TextStyle(
                                  fontSize: 12,
                                  color: Color(0xFF1D2F35),
                                  fontWeight: FontWeight.w500,
                                ),
                              ),
                            ),
                          ],
                        ),
                      ],
                    ],
                  ),
                ),
                const SizedBox(height: 16),
                
                // Transaction Details Summary
                Container(
                  padding: const EdgeInsets.all(12),
                  decoration: BoxDecoration(
                    color: Colors.grey[100],
                    borderRadius: BorderRadius.circular(8),
                  ),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      _buildDetailRow('Amount', '₹${_amountController.text}'),
                      const SizedBox(height: 8),
                      _buildDetailRow('Description', _descriptionController.text, maxLines: 2),
                      if (_merchantController.text.isNotEmpty) ...[
                        const SizedBox(height: 8),
                        _buildDetailRow('Merchant', _merchantController.text),
                      ],
                    ],
                  ),
                ),
              ],
            ),
          ),
        ),
        actions: [
          TextButton.icon(
            onPressed: () {
              Navigator.pop(context);
              _showCategoryPickerDialog();
            },
            icon: const Icon(Icons.edit),
            label: const Text('Correct Category'),
            style: TextButton.styleFrom(
              foregroundColor: const Color(0xFF5DF22A),
            ),
          ),
          ElevatedButton.icon(
            onPressed: () {
              Navigator.pop(context);
              _submitTransaction();
            },
            icon: const Icon(Icons.check),
            label: const Text('Add Transaction'),
            style: ElevatedButton.styleFrom(
              backgroundColor: const Color(0xFF5DF22A),
              foregroundColor: const Color(0xFF1D2F35),
              padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildConfidenceScoreWidget() {
    final confidence = _categorizationResult?.confidenceScore ?? 0.0;
    final percentage = (confidence * 100).toInt();
    final isHighConfidence = confidence >= 0.85;
    
    return Container(
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        gradient: LinearGradient(
          colors: isHighConfidence
              ? [const Color(0xFF5DF22A).withOpacity(0.1), const Color(0xFF5DF22A).withOpacity(0.05)]
              : [const Color(0xFFFFA500).withOpacity(0.1), const Color(0xFFFFA500).withOpacity(0.05)],
          begin: Alignment.topLeft,
          end: Alignment.bottomRight,
        ),
        borderRadius: BorderRadius.circular(12),
        border: Border.all(
          color: isHighConfidence
              ? const Color(0xFF5DF22A).withOpacity(0.3)
              : const Color(0xFFFFA500).withOpacity(0.3),
          width: 1.5,
        ),
      ),
      child: Column(
        children: [
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              const Text(
                'Confidence Score',
                style: TextStyle(
                  fontSize: 14,
                  color: Color(0xFF8BA5A8),
                  fontWeight: FontWeight.w500,
                ),
              ),
              Text(
                '$percentage%',
                style: TextStyle(
                  fontSize: 16,
                  fontWeight: FontWeight.bold,
                  color: isHighConfidence
                      ? const Color(0xFF5DF22A)
                      : const Color(0xFFFFA500),
                ),
              ),
            ],
          ),
          const SizedBox(height: 12),
          ClipRRect(
            borderRadius: BorderRadius.circular(8),
            child: LinearProgressIndicator(
              value: confidence,
              minHeight: 8,
              backgroundColor: Colors.grey[300],
              valueColor: AlwaysStoppedAnimation<Color>(
                isHighConfidence
                    ? const Color(0xFF5DF22A)
                    : const Color(0xFFFFA500),
              ),
            ),
          ),
          const SizedBox(height: 12),
          Text(
            isHighConfidence
                ? '✓ High confidence - ready to save'
                : '⚠ Medium confidence - review before saving',
            style: TextStyle(
              fontSize: 12,
              color: isHighConfidence
                  ? const Color(0xFF5DF22A)
                  : const Color(0xFFFFA500),
              fontWeight: FontWeight.w500,
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildDetailRow(String label, String value, {int maxLines = 1}) {
    return Row(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        SizedBox(
          width: 80,
          child: Text(
            label,
            style: const TextStyle(
              fontSize: 12,
              color: Color(0xFF8BA5A8),
              fontWeight: FontWeight.w500,
            ),
          ),
        ),
        Expanded(
          child: Text(
            value,
            maxLines: maxLines,
            overflow: TextOverflow.ellipsis,
            style: const TextStyle(
              fontSize: 13,
              color: Color(0xFF1D2F35),
              fontWeight: FontWeight.w500,
            ),
          ),
        ),
      ],
    );
  }

  void _showCategoryPickerDialog() {
    final categories = [
      'Food & Dining',
      'Transport',
      'Shopping',
      'Health & Medical',
      'Entertainment',
      'Bills & Utilities',
      'Education',
      'Investment',
      'Savings',
      'Other',
    ];

    showDialog(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('Select Category'),
        content: SizedBox(
          width: double.maxFinite,
          child: ListView.builder(
            itemCount: categories.length,
            itemBuilder: (context, index) {
              final category = categories[index];
              final isSelected = _selectedCategory == category;
              return ListTile(
                title: Text(category),
                trailing: isSelected ? const Icon(Icons.check, color: Color(0xFF5DF22A)) : null,
                onTap: () {
                  setState(() {
                    _selectedCategory = category;
                    _selectedSubcategory = '';
                  });
                  Navigator.pop(context);
                  _showCategoryConfirmationDialog();
                },
                selected: isSelected,
                selectedTileColor: const Color(0xFFF5F7F8),
              );
            },
          ),
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(context),
            child: const Text('Cancel'),
          ),
        ],
      ),
    );
  }

  Future<void> _submitTransaction() async {
    if (_selectedCategory == null) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Please select a category')),
      );
      return;
    }

    try {
      if (mounted) setState(() => _isLoading = true);

      // Add merchant if it doesn't exist
      await _addMerchantIfNeeded();

      final response = await widget.apiService.addTransaction(
        userId: widget.userId,
        amount: double.parse(_amountController.text),
        description: _descriptionController.text,
      );

      if (mounted) setState(() => _isLoading = false);

      if (response.success && response.txnId != null) {
        // Create transaction object from response
        final transaction = Transaction(
          txnId: response.txnId!,
          userId: widget.userId,
          accountId: widget.accountId,
          amount: double.parse(_amountController.text),
          txnType: _transactionType,
          category: _selectedCategory,
          subcategory: _selectedSubcategory,
          rawDescription: _descriptionController.text,
          rawName: _merchantController.text,
          paymentMode: _paymentMode,
          userVerified: true,
          isRecurring: false,
          txnTimestamp: DateTime.now(),
        );

        // Trigger callback to update parent with new transaction
        if (mounted) {
          widget.onTransactionAdded(transaction);
        }

        // Show success message
        if (mounted) {
          ScaffoldMessenger.of(context).showSnackBar(
            SnackBar(
              content: Text('✓ Transaction saved! #${response.txnId}'),
              backgroundColor: const Color(0xFF2BDB7C),
              duration: const Duration(seconds: 2),
            ),
          );
        }

        // Clear form for next entry
        if (mounted) {
          setState(() {
            _descriptionController.clear();
            _amountController.clear();
            _merchantController.clear();
            _selectedCategory = null;
            _selectedSubcategory = null;
            _categorizationResult = null;
            _selectedImage = null;
            _isConfirmingCategory = false;
          });
        }
      } else {
        throw Exception(response.error ?? 'Failed to add transaction');
      }
    } catch (e) {
      if (mounted) setState(() => _isLoading = false);
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text('Error saving transaction: $e'),
            backgroundColor: Colors.red,
            duration: const Duration(seconds: 3),
          ),
        );
      }
      debugPrint('Transaction submission error: $e');
    }
  }

  @override
  Widget build(BuildContext context) {
    return Dialog(
      insetPadding: const EdgeInsets.all(20),
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(24)),
      child: Padding(
        padding: const EdgeInsets.all(24),
        child: SingleChildScrollView(
          child: Column(
            mainAxisSize: MainAxisSize.min,
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Row(
                mainAxisAlignment: MainAxisAlignment.spaceBetween,
                children: [
                  const Text(
                    'Add Transaction',
                    style: TextStyle(fontSize: 20, fontWeight: FontWeight.bold),
                  ),
                  ElevatedButton.icon(
                    onPressed: _isScanningOCR || _isConfirmingCategory ? null : _scanReceipt,
                    icon: Icon(
                      _isScanningOCR
                          ? Icons.schedule
                          : _selectedImage != null
                              ? Icons.check_circle
                              : Icons.camera_alt,
                    ),
                    label: Text(_isScanningOCR
                        ? 'Scanning...'
                        : _selectedImage != null
                            ? 'Scanned'
                            : 'Scan Receipt'),
                    style: ElevatedButton.styleFrom(
                      backgroundColor: _selectedImage != null
                          ? const Color(0xFF2BDB7C)
                          : Colors.blue,
                    ),
                  ),
                ],
              ),
              const SizedBox(height: 24),
              // Receipt image preview
              if (_selectedImage != null) ...[
                Container(
                  width: double.maxFinite,
                  height: 180,
                  decoration: BoxDecoration(
                    borderRadius: BorderRadius.circular(12),
                    border: Border.all(color: const Color(0xFFE5E9EA)),
                  ),
                  child: ClipRRect(
                    borderRadius: BorderRadius.circular(12),
                    child: Image.file(
                      File(_selectedImage!.path),
                      fit: BoxFit.cover,
                    ),
                  ),
                ),
                const SizedBox(height: 12),
                Container(
                  padding: const EdgeInsets.all(12),
                  decoration: BoxDecoration(
                    color: const Color(0xFF2BDB7C).withOpacity(0.1),
                    borderRadius: BorderRadius.circular(8),
                  ),
                  child: Row(
                    children: [
                      const Icon(Icons.info, color: Color(0xFF2BDB7C), size: 20),
                      const SizedBox(width: 8),
                      Expanded(
                        child: Text(
                          _isScanningOCR
                              ? 'Processing receipt...'
                              : 'Receipt fields auto-filled. Edit if needed.',
                          style: const TextStyle(
                            fontSize: 11,
                            color: Color(0xFF2BDB7C),
                          ),
                        ),
                      ),
                    ],
                  ),
                ),
                const SizedBox(height: 20),
              ],
              TextField(
                controller: _merchantController,
                enabled: !_isConfirmingCategory,
                onChanged: (_) => _checkMerchantExists(),
                decoration: InputDecoration(
                  labelText: 'Merchant Name *',
                  hintText: 'e.g., Starbucks',
                  border: OutlineInputBorder(
                    borderRadius: BorderRadius.circular(12),
                  ),
                  suffixIcon: _merchantController.text.isNotEmpty
                      ? Icon(
                          _merchantExists ? Icons.check_circle : Icons.cancel,
                          color: _merchantExists ? Colors.orange : Colors.grey,
                        )
                      : null,
                  errorText: _merchantExists
                      ? 'Merchant already exists'
                      : null,
                ),
              ),
              const SizedBox(height: 16),
              TextField(
                controller: _descriptionController,
                enabled: !_isConfirmingCategory,
                decoration: InputDecoration(
                  labelText: 'Transaction Description',
                  hintText: 'e.g., Morning coffee',
                  border: OutlineInputBorder(
                    borderRadius: BorderRadius.circular(12),
                  ),
                ),
              ),
              const SizedBox(height: 16),
              TextField(
                controller: _amountController,
                enabled: !_isConfirmingCategory,
                keyboardType:
                    const TextInputType.numberWithOptions(decimal: true),
                decoration: InputDecoration(
                  labelText: 'Amount (₹) *',
                  hintText: '0.00',
                  border: OutlineInputBorder(
                    borderRadius: BorderRadius.circular(12),
                  ),
                ),
              ),
              const SizedBox(height: 16),
              Row(
                children: [
                  Expanded(
                    child: DropdownButtonFormField<String>(
                      value: _transactionType,
                      decoration: InputDecoration(
                        labelText: 'Type',
                        border: OutlineInputBorder(
                          borderRadius: BorderRadius.circular(12),
                        ),
                      ),
                      items: ['debit', 'credit']
                          .map((type) =>
                              DropdownMenuItem(value: type, child: Text(type.toUpperCase())))
                          .toList(),
                      onChanged: (value) {
                        if (value != null && mounted) {
                          setState(() => _transactionType = value);
                        }
                      },
                    ),
                  ),
                  const SizedBox(width: 12),
                  Expanded(
                    child: DropdownButtonFormField<String>(
                      value: _paymentMode,
                      decoration: InputDecoration(
                        labelText: 'Payment Mode',
                        border: OutlineInputBorder(
                          borderRadius: BorderRadius.circular(12),
                        ),
                      ),
                      items: ['UPI', 'Card', 'Cash', 'Net Banking', 'Wallet']
                          .map((mode) =>
                              DropdownMenuItem(value: mode, child: Text(mode)))
                          .toList(),
                      onChanged: (value) {
                        if (value != null && mounted) setState(() => _paymentMode = value);
                      },
                    ),
                  ),
                ],
              ),
              const SizedBox(height: 24),
              if (_categorizationResult != null)
                Container(
                  padding: const EdgeInsets.all(16),
                  decoration: BoxDecoration(
                    color: const Color(0xFFF5F7F8),
                    borderRadius: BorderRadius.circular(12),
                    border: Border.all(color: const Color(0xFFE5E9EA)),
                  ),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      const Text(
                        'Prediction Result:',
                        style: TextStyle(fontWeight: FontWeight.bold, fontSize: 14),
                      ),
                      const SizedBox(height: 8),
                      Container(
                        padding: const EdgeInsets.all(12),
                        decoration: BoxDecoration(
                          color: Colors.white,
                          borderRadius: BorderRadius.circular(8),
                        ),
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            Row(
                              mainAxisAlignment: MainAxisAlignment.spaceBetween,
                              children: [
                                Text(
                                  _categorizationResult!.category,
                                  style: const TextStyle(
                                    fontSize: 16,
                                    fontWeight: FontWeight.bold,
                                    color: Color(0xFF1D2F35),
                                  ),
                                ),
                                Container(
                                  padding: const EdgeInsets.symmetric(
                                    horizontal: 8,
                                    vertical: 4,
                                  ),
                                  decoration: BoxDecoration(
                                    color: (_categorizationResult!.confidenceScore > 0.7
                                        ? Colors.green
                                        : Colors.orange)
                                    .withOpacity(0.1),
                                    borderRadius: BorderRadius.circular(6),
                                  ),
                                  child: Text(
                                    '${(_categorizationResult!.confidenceScore * 100).toStringAsFixed(0)}%',
                                    style: TextStyle(
                                      fontSize: 12,
                                      fontWeight: FontWeight.bold,
                                      color: (_categorizationResult!.confidenceScore > 0.7
                                          ? Colors.green
                                          : Colors.orange),
                                    ),
                                  ),
                                ),
                              ],
                            ),
                            if (_categorizationResult!.subcategory?.isNotEmpty ?? false) ...[
                              const SizedBox(height: 4),
                              Text(
                                'Sub: ${_categorizationResult!.subcategory}',
                                style: const TextStyle(fontSize: 12, color: Colors.grey),
                              ),
                            ],
                          ],
                        ),
                      ),
                      if ((_categorizationResult?.confidenceScore ?? 0) < 0.7) ...[
                        const SizedBox(height: 8),
                        Container(
                          padding: const EdgeInsets.all(8),
                          decoration: BoxDecoration(
                            color: Colors.orange.withOpacity(0.1),
                            borderRadius: BorderRadius.circular(6),
                          ),
                          child: Row(
                            children: [
                              Icon(Icons.info, size: 16, color: Colors.orange),
                              const SizedBox(width: 8),
                              const Expanded(
                                child: Text(
                                  'Low confidence - please verify category',
                                  style: TextStyle(fontSize: 12, color: Colors.orange),
                                ),
                              ),
                            ],
                          ),
                        ),
                      ],
                    ],
                  ),
                ),
              const SizedBox(height: 24),
              Row(
                mainAxisAlignment: MainAxisAlignment.spaceBetween,
                children: [
                  TextButton(
                    onPressed:
                        _isLoading || _isScanningOCR ? null : () => Navigator.pop(context),
                    child: const Text('Cancel'),
                  ),
                  ElevatedButton(
                    onPressed: (_isLoading || _isScanningOCR)
                        ? null
                        : (_isConfirmingCategory
                            ? _submitTransaction
                            : _categorizeTransaction),
                    child: (_isLoading || _isScanningOCR)
                        ? const SizedBox(
                            width: 20,
                            height: 20,
                            child: CircularProgressIndicator(strokeWidth: 2),
                          )
                        : Text(_isConfirmingCategory
                            ? 'Add Transaction'
                            : 'Get Prediction'),
                  ),
                ],
              ),
            ],
          ),
        ),
      ),
    );
  }
}

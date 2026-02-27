import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../../services/api_service.dart';
import '../../models/transaction.dart';
import '../../models/finance_models.dart';
import '../ar/ar_hub_screen.dart';
import '../ar/ar_test_screen.dart';

class DashboardScreen extends StatefulWidget {
  const DashboardScreen({Key? key}) : super(key: key);

  @override
  State<DashboardScreen> createState() => _DashboardScreenState();
}

class _DashboardScreenState extends State<DashboardScreen> {
  late ApiService _apiService;
  List<Transaction> _transactions = [];
  List<Budget> _budgets = [];
  List<Alert> _alerts = [];
  bool _isLoading = true;

  @override
  void initState() {
    super.initState();
    _apiService = ApiService();
    _loadData();
  }

  Future<void> _loadData() async {
    setState(() => _isLoading = true);
    try {
      final transactions = await _apiService.getTransactions(limit: 10);
      final budgets = await _apiService.getBudgets();
      final alerts = await _apiService.getAlerts();
      
      setState(() {
        _transactions = transactions;
        _budgets = budgets;
        _alerts = alerts;
        _isLoading = false;
      });
    } catch (e) {
      setState(() => _isLoading = false);
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('Error loading data: $e')),
      );
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Dashboard'),
        actions: [
          IconButton(
            icon: const Icon(Icons.notifications),
            onPressed: () {
              // Navigate to alerts
            },
          ),
        ],
      ),
      body: _isLoading
          ? const Center(child: CircularProgressIndicator())
          : RefreshIndicator(
              onRefresh: _loadData,
              child: ListView(
                padding: const EdgeInsets.all(16),
                children: [
                  _buildAlertSection(),
                  const SizedBox(height: 16),
                  _buildARFeatureCard(),
                  const SizedBox(height: 16),
                  _buildBudgetSection(),
                  const SizedBox(height: 16),
                  _buildTransactionSection(),
                ],
              ),
            ),
      floatingActionButton: FloatingActionButton(
        onPressed: () {
          // Navigate to add transaction
        },
        child: const Icon(Icons.add),
      ),
    );
  }

  Widget _buildAlertSection() {
    if (_alerts.isEmpty) return const SizedBox.shrink();
    
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            const Text(
              'Alerts',
              style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold),
            ),
            const SizedBox(height: 12),
            ..._alerts.take(3).map((alert) => ListTile(
              leading: Icon(
                Icons.warning,
                color: alert.severity == 'high' ? Colors.red : Colors.orange,
              ),
              title: Text(alert.message),
              subtitle: Text(alert.alertType),
              dense: true,
            )),
          ],
        ),
      ),
    );
  }

  Widget _buildARFeatureCard() {
    return Card(
      color: Colors.deepPurple.shade50,
      child: InkWell(
        onTap: () {
          Navigator.push(
            context,
            MaterialPageRoute(builder: (_) => const ARTestScreen()),
          );
        },
        child: Padding(
          padding: const EdgeInsets.all(16),
          child: Row(
            children: [
              Container(
                padding: const EdgeInsets.all(12),
                decoration: BoxDecoration(
                  color: Colors.green,
                  borderRadius: BorderRadius.circular(12),
                ),
                child: const Icon(
                  Icons.camera_alt,
                  color: Colors.white,
                  size: 32,
                ),
              ),
              const SizedBox(width: 16),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    const Text(
                      'Test AR Camera',
                      style: TextStyle(
                        fontSize: 18,
                        fontWeight: FontWeight.bold,
                      ),
                    ),
                    const SizedBox(height: 4),
                    Text(
                      'Tap to test camera for AR',
                      style: TextStyle(
                        color: Colors.grey[600],
                        fontSize: 14,
                      ),
                    ),
                  ],
                ),
              ),
              const Icon(Icons.arrow_forward_ios, size: 16),
            ],
          ),
        ),
      ),
    );
  }

  Widget _buildBudgetSection() {
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            const Text(
              'Budget Overview',
              style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold),
            ),
            const SizedBox(height: 12),
            if (_budgets.isEmpty)
              const Text('No budgets set')
            else
              ..._budgets.map((budget) => Padding(
                padding: const EdgeInsets.only(bottom: 12),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Row(
                      mainAxisAlignment: MainAxisAlignment.spaceBetween,
                      children: [
                        Text(budget.category),
                        Text(
                          '₹${budget.spentAmount.toStringAsFixed(0)} / ₹${budget.limitAmount.toStringAsFixed(0)}',
                          style: const TextStyle(fontWeight: FontWeight.bold),
                        ),
                      ],
                    ),
                    const SizedBox(height: 4),
                    LinearProgressIndicator(
                      value: budget.percentageUsed / 100,
                      backgroundColor: Colors.grey[200],
                      color: budget.percentageUsed > 80 ? Colors.red : Colors.green,
                    ),
                  ],
                ),
              )),
          ],
        ),
      ),
    );
  }

  Widget _buildTransactionSection() {
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            const Text(
              'Recent Transactions',
              style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold),
            ),
            const SizedBox(height: 12),
            if (_transactions.isEmpty)
              const Text('No transactions')
            else
              ..._transactions.map((txn) => ListTile(
                leading: CircleAvatar(
                  backgroundColor: txn.txnType == 'credit' 
                      ? Colors.green 
                      : Colors.red,
                  child: Icon(
                    txn.txnType == 'credit' 
                        ? Icons.arrow_downward 
                        : Icons.arrow_upward,
                    color: Colors.white,
                  ),
                ),
                title: Text(txn.cleanDescription ?? txn.rawDescription ?? 'Transaction'),
                subtitle: Text(txn.category ?? 'Uncategorized'),
                trailing: Text(
                  '₹${txn.amount.toStringAsFixed(2)}',
                  style: TextStyle(
                    fontWeight: FontWeight.bold,
                    color: txn.txnType == 'credit' ? Colors.green : Colors.red,
                  ),
                ),
                dense: true,
              )),
          ],
        ),
      ),
    );
  }
}

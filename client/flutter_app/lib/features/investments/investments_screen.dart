import 'package:flutter/material.dart';
import '../../services/api_service.dart';

class InvestmentsScreen extends StatefulWidget {
  const InvestmentsScreen({Key? key}) : super(key: key);

  @override
  State<InvestmentsScreen> createState() => _InvestmentsScreenState();
}

class _InvestmentsScreenState extends State<InvestmentsScreen> {
  final ApiService _apiService = ApiService();
  Map<String, dynamic>? _readiness;
  Map<String, dynamic>? _recommendations;
  bool _isLoading = true;

  @override
  void initState() {
    super.initState();
    _loadData();
  }

  Future<void> _loadData() async {
    setState(() => _isLoading = true);
    try {
      final readiness = await _apiService.getInvestmentReadiness();
      setState(() {
        _readiness = readiness;
        _isLoading = false;
      });

      if (readiness['ready'] == true) {
        final recommendations = await _apiService.getInvestmentRecommendations();
        setState(() => _recommendations = recommendations);
      }
    } catch (e) {
      setState(() => _isLoading = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Investments')),
      body: _isLoading
          ? const Center(child: CircularProgressIndicator())
          : SingleChildScrollView(
              padding: const EdgeInsets.all(16),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  _buildReadinessCard(),
                  const SizedBox(height: 16),
                  if (_readiness?['ready'] == true && _recommendations != null)
                    _buildRecommendationsSection(),
                ],
              ),
            ),
    );
  }

  Widget _buildReadinessCard() {
    final ready = _readiness?['ready'] ?? false;
    final gates = _readiness?['gates'] as Map<String, dynamic>?;

    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                Icon(
                  ready ? Icons.check_circle : Icons.warning,
                  color: ready ? Colors.green : Colors.orange,
                  size: 32,
                ),
                const SizedBox(width: 12),
                Expanded(
                  child: Text(
                    ready ? 'Ready to Invest' : 'Not Ready Yet',
                    style: const TextStyle(
                      fontSize: 20,
                      fontWeight: FontWeight.bold,
                    ),
                  ),
                ),
              ],
            ),
            const SizedBox(height: 16),
            if (gates != null) ...[
              const Text(
                'Investment Readiness Checks:',
                style: TextStyle(fontWeight: FontWeight.bold),
              ),
              const SizedBox(height: 8),
              ...gates.entries.map((entry) => Padding(
                padding: const EdgeInsets.symmetric(vertical: 4),
                child: Row(
                  children: [
                    Icon(
                      entry.value ? Icons.check : Icons.close,
                      color: entry.value ? Colors.green : Colors.red,
                      size: 20,
                    ),
                    const SizedBox(width: 8),
                    Text(_formatGateName(entry.key)),
                  ],
                ),
              )),
            ],
            if (_readiness?['investable_amount'] != null)
              Padding(
                padding: const EdgeInsets.only(top: 16),
                child: Text(
                  'Investable Amount: ₹${_readiness!['investable_amount'].toStringAsFixed(0)}',
                  style: const TextStyle(
                    fontSize: 16,
                    fontWeight: FontWeight.bold,
                    color: Colors.green,
                  ),
                ),
              ),
          ],
        ),
      ),
    );
  }

  Widget _buildRecommendationsSection() {
    final recommendations = _recommendations?['recommendations'] as List? ?? [];

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        const Text(
          'Recommended Investments',
          style: TextStyle(fontSize: 20, fontWeight: FontWeight.bold),
        ),
        const SizedBox(height: 12),
        ...recommendations.map((rec) => Card(
          margin: const EdgeInsets.only(bottom: 12),
          child: ListTile(
            title: Text(rec['name'] ?? 'Investment'),
            subtitle: Text('Risk: ${rec['risk_level']} | Return: ${rec['expected_return']}%'),
            trailing: Text(
              '₹${rec['recommended_amount']?.toStringAsFixed(0) ?? '0'}',
              style: const TextStyle(fontWeight: FontWeight.bold),
            ),
          ),
        )),
      ],
    );
  }

  String _formatGateName(String key) {
    return key.split('_').map((word) => 
      word[0].toUpperCase() + word.substring(1)
    ).join(' ');
  }
}

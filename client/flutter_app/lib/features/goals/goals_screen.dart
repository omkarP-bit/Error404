import 'package:flutter/material.dart';
import '../../services/api_service.dart';
import '../../models/finance_models.dart';

class GoalsScreen extends StatefulWidget {
  const GoalsScreen({Key? key}) : super(key: key);

  @override
  State<GoalsScreen> createState() => _GoalsScreenState();
}

class _GoalsScreenState extends State<GoalsScreen> {
  final ApiService _apiService = ApiService();
  List<Goal> _goals = [];
  bool _isLoading = true;

  @override
  void initState() {
    super.initState();
    _loadGoals();
  }

  Future<void> _loadGoals() async {
    setState(() => _isLoading = true);
    try {
      final goals = await _apiService.getGoals();
      setState(() {
        _goals = goals;
        _isLoading = false;
      });
    } catch (e) {
      setState(() => _isLoading = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Goals')),
      body: _isLoading
          ? const Center(child: CircularProgressIndicator())
          : _goals.isEmpty
              ? const Center(child: Text('No goals yet'))
              : ListView.builder(
                  padding: const EdgeInsets.all(16),
                  itemCount: _goals.length,
                  itemBuilder: (context, index) {
                    final goal = _goals[index];
                    return Card(
                      margin: const EdgeInsets.only(bottom: 16),
                      child: Padding(
                        padding: const EdgeInsets.all(16),
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            Text(
                              goal.goalName,
                              style: const TextStyle(
                                fontSize: 18,
                                fontWeight: FontWeight.bold,
                              ),
                            ),
                            const SizedBox(height: 8),
                            Text(
                              '₹${goal.currentAmount.toStringAsFixed(0)} / ₹${goal.targetAmount.toStringAsFixed(0)}',
                            ),
                            const SizedBox(height: 8),
                            LinearProgressIndicator(
                              value: goal.progress / 100,
                              backgroundColor: Colors.grey[200],
                            ),
                            const SizedBox(height: 8),
                            Text('${goal.progress.toStringAsFixed(1)}% complete'),
                            if (goal.feasibilityScore != null)
                              Text(
                                'Feasibility: ${(goal.feasibilityScore! * 100).toStringAsFixed(0)}%',
                                style: TextStyle(
                                  color: goal.feasibilityScore! > 0.7
                                      ? Colors.green
                                      : Colors.orange,
                                ),
                              ),
                          ],
                        ),
                      ),
                    );
                  },
                ),
      floatingActionButton: FloatingActionButton(
        onPressed: () {
          // Add goal dialog
        },
        child: const Icon(Icons.add),
      ),
    );
  }
}

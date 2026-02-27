import 'dart:convert';
import 'package:http/http.dart' as http;
import '../core/config/app_config.dart';
import '../models/transaction.dart';
import '../models/finance_models.dart';

class ApiService {
  final String baseUrl = AppConfig.apiBaseUrl;
  String? _token;

  void setToken(String token) {
    _token = token;
  }

  Map<String, String> get _headers => {
    'Content-Type': 'application/json',
    if (_token != null) 'Authorization': 'Bearer $_token',
  };

  // Transactions
  Future<List<Transaction>> getTransactions({String? category, int limit = 50}) async {
    final queryParams = {
      if (category != null) 'category': category,
      'limit': limit.toString(),
    };
    
    final uri = Uri.parse('$baseUrl${ApiEndpoints.transactions}')
        .replace(queryParameters: queryParams);
    
    final response = await http.get(uri, headers: _headers);
    
    if (response.statusCode == 200) {
      final data = json.decode(response.body);
      return (data['data'] as List)
          .map((json) => Transaction.fromJson(json))
          .toList();
    }
    throw Exception('Failed to load transactions');
  }

  Future<Transaction> createTransaction(Map<String, dynamic> transactionData) async {
    final response = await http.post(
      Uri.parse('$baseUrl${ApiEndpoints.transactions}'),
      headers: _headers,
      body: json.encode(transactionData),
    );
    
    if (response.statusCode == 201) {
      final data = json.decode(response.body);
      return Transaction.fromJson(data['data']);
    }
    throw Exception('Failed to create transaction');
  }

  // Budgets
  Future<List<Budget>> getBudgets() async {
    final response = await http.get(
      Uri.parse('$baseUrl${ApiEndpoints.budgets}'),
      headers: _headers,
    );
    
    if (response.statusCode == 200) {
      final data = json.decode(response.body);
      return (data['data'] as List)
          .map((json) => Budget.fromJson(json))
          .toList();
    }
    throw Exception('Failed to load budgets');
  }

  Future<Map<String, dynamic>> calculateSavings() async {
    final response = await http.get(
      Uri.parse('$baseUrl${ApiEndpoints.budgets}/savings'),
      headers: _headers,
    );
    
    if (response.statusCode == 200) {
      final data = json.decode(response.body);
      return data['data'];
    }
    throw Exception('Failed to calculate savings');
  }

  // Goals
  Future<List<Goal>> getGoals() async {
    final response = await http.get(
      Uri.parse('$baseUrl${ApiEndpoints.goals}'),
      headers: _headers,
    );
    
    if (response.statusCode == 200) {
      final data = json.decode(response.body);
      return (data['data'] as List)
          .map((json) => Goal.fromJson(json))
          .toList();
    }
    throw Exception('Failed to load goals');
  }

  Future<Goal> createGoal(Map<String, dynamic> goalData) async {
    final response = await http.post(
      Uri.parse('$baseUrl${ApiEndpoints.goals}'),
      headers: _headers,
      body: json.encode(goalData),
    );
    
    if (response.statusCode == 201) {
      final data = json.decode(response.body);
      return Goal.fromJson(data['data']);
    }
    throw Exception('Failed to create goal');
  }

  // Alerts
  Future<List<Alert>> getAlerts({String status = 'active'}) async {
    final uri = Uri.parse('$baseUrl${ApiEndpoints.alerts}')
        .replace(queryParameters: {'status': status});
    
    final response = await http.get(uri, headers: _headers);
    
    if (response.statusCode == 200) {
      final data = json.decode(response.body);
      return (data['data'] as List)
          .map((json) => Alert.fromJson(json))
          .toList();
    }
    throw Exception('Failed to load alerts');
  }

  // Investments
  Future<Map<String, dynamic>> getInvestmentReadiness() async {
    final response = await http.get(
      Uri.parse('$baseUrl${ApiEndpoints.investments}/readiness'),
      headers: _headers,
    );
    
    if (response.statusCode == 200) {
      final data = json.decode(response.body);
      return data['data'];
    }
    throw Exception('Failed to check investment readiness');
  }

  Future<Map<String, dynamic>> getInvestmentRecommendations() async {
    final response = await http.get(
      Uri.parse('$baseUrl${ApiEndpoints.investments}/recommendations'),
      headers: _headers,
    );
    
    if (response.statusCode == 200) {
      final data = json.decode(response.body);
      return data['data'];
    }
    throw Exception('Failed to get recommendations');
  }
}

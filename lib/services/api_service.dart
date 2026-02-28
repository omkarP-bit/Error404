import 'package:http/http.dart' as http;
import 'dart:convert';
import 'dart:io';
import 'package:flutter/foundation.dart';
import 'package:flutter/material.dart';

class ApiService {
  // ── Configuration ──────────────────────────────────────────────────
  // Default to localhost for emulator/development
  // Can be changed at runtime via setApiHost() for physical devices
  static String _apiHost = 'localhost:8000';
  
  static String get baseUrl => 'http://$_apiHost/api';
  
  /// Configure the API host for physical devices or different environments
  /// Example: ApiService.setApiHost('192.168.1.100:8000') for physical Android device
  static void setApiHost(String host) {
    _apiHost = host;
    debugPrint('✓ API Host configured to: http://$_apiHost/api');
  }
  
  /// Get the currently configured API host
  static String getApiHost() => _apiHost;
  
  // Singleton pattern
  static final ApiService _instance = ApiService._internal();
  
  factory ApiService() {
    return _instance;
  }
  
  ApiService._internal();

  // ────────────────────────────────────────────────────────
  // CATEGORIZATION ENDPOINTS
  // ────────────────────────────────────────────────────────

  /// Categorize a single transaction
  /// Returns categorization result with category, subcategory, and confidence score
  Future<CategorizationResult> categorizeTransaction({
    required String rawDescription,
    required double amount,
    required int userId,
    required int accountId,
    String merchantName = '',
    String txnType = 'debit',
    String paymentMode = 'UPI',
  }) async {
    try {
      final requestBody = {
        'raw_description': rawDescription,
        'amount': amount,
        'merchant_name': merchantName,
        'txn_type': txnType,
        'payment_mode': paymentMode,
        'user_id': userId,
        'account_id': accountId,
      };

      final response = await http.post(
        Uri.parse('$baseUrl/categorize'),
        headers: {'Content-Type': 'application/x-www-form-urlencoded'},
        body: requestBody,
      ).timeout(
        const Duration(seconds: 30),
        onTimeout: () => throw TimeoutException('Categorization request timed out'),
      );

      if (response.statusCode == 200) {
        final jsonResponse = jsonDecode(response.body);
        if (jsonResponse['success']) {
          return CategorizationResult.fromJson(jsonResponse['result']);
        } else {
          throw Exception(jsonResponse['error'] ?? 'Unknown error');
        }
      } else {
        throw Exception('Failed to categorize: ${response.statusCode}');
      }
    } catch (e) {
      debugPrint('Error in categorizeTransaction: $e');
      rethrow;
    }
  }

  /// Add a categorized transaction to the database
  Future<TransactionResponse> addTransaction({
    required String rawDescription,
    required double amount,
    required String category,
    required int userId,
    required int accountId,
    String merchantName = '',
    String subcategory = '',
    String txnType = 'debit',
    String paymentMode = 'UPI',
  }) async {
    try {
      final requestBody = {
        'raw_description': rawDescription,
        'amount': amount,
        'merchant_name': merchantName,
        'txn_type': txnType,
        'payment_mode': paymentMode,
        'user_id': userId,
        'account_id': accountId,
        'category': category,
        'subcategory': subcategory,
      };

      final response = await http.post(
        Uri.parse('$baseUrl/categorize/add-transaction'),
        headers: {'Content-Type': 'application/x-www-form-urlencoded'},
        body: requestBody,
      ).timeout(
        const Duration(seconds: 30),
        onTimeout: () => throw TimeoutException('Add transaction request timed out'),
      );

      if (response.statusCode == 200 || response.statusCode == 201) {
        final jsonResponse = jsonDecode(response.body);
        if (jsonResponse['success'] ?? true) {
          return TransactionResponse.fromJson(jsonResponse);
        } else {
          throw Exception(jsonResponse['error'] ?? 'Unknown error');
        }
      } else {
        throw Exception('Failed to add transaction: ${response.statusCode}');
      }
    } catch (e) {
      debugPrint('Error in addTransaction: $e');
      rethrow;
    }
  }

  /// Get list of transactions for a user
  Future<TransactionListResponse> getTransactions({
    required int userId,
    int limit = 50,
    int offset = 0,
  }) async {
    try {
      // Build URL using configurable API host
      final queryParams = {
        'user_id': userId.toString(),
        'limit': limit.toString(),
        'offset': offset.toString(),
      };
      
      // Parse the API host and port from _apiHost
      final hostParts = _apiHost.split(':');
      final host = hostParts[0];
      final port = hostParts.length > 1 ? int.tryParse(hostParts[1]) : 8000;
      
      // Construct URI with configurable host and port
      final uri = port == 80 
        ? Uri.http(host, '/api/transactions/', queryParams)
        : Uri.http(host + ':$port', '/api/transactions/', queryParams);

      debugPrint('Fetching transactions from: $uri');

      final response = await http.get(
        uri,
        headers: {'Content-Type': 'application/json'},
      ).timeout(
        const Duration(seconds: 30),
        onTimeout: () => throw TimeoutException('Get transactions request timed out'),
      );

      debugPrint('Transaction response status: ${response.statusCode}');

      if (response.statusCode == 200) {
        final jsonResponse = jsonDecode(response.body);
        return TransactionListResponse.fromJson(jsonResponse);
      } else {
        throw Exception('Failed to get transactions: ${response.statusCode} - ${response.body}');
      }
    } catch (e) {
      debugPrint('Error in getTransactions: $e');
      rethrow;
    }
  }

  // ────────────────────────────────────────────────────────
  // ANOMALY DETECTION ENDPOINTS
  // ────────────────────────────────────────────────────────

  /// Scan user's transactions for anomalies
  /// Returns all transactions with anomaly scores and flags
  Future<AnomalyScanResult> scanAnomalies({
    required int userId,
  }) async {
    try {
      // Use form-encoded body for POST request
      final response = await http.post(
        Uri.parse('$baseUrl/anomaly/scan'),
        headers: {'Content-Type': 'application/x-www-form-urlencoded'},
        body: {'user_id': userId.toString()},
      ).timeout(
        const Duration(seconds: 60),
        onTimeout: () => throw TimeoutException('Anomaly scan request timed out'),
      );

      debugPrint('Anomaly scan response: ${response.statusCode}');
      debugPrint('Response body: ${response.body}');

      if (response.statusCode == 200) {
        final jsonResponse = jsonDecode(response.body);
        if (jsonResponse['success'] == true) {
          return AnomalyScanResult.fromJson(jsonResponse);
        } else {
          throw Exception(jsonResponse['error'] ?? 'Unknown error from backend');
        }
      } else {
        throw Exception('Failed to scan anomalies: ${response.statusCode} - ${response.body}');
      }
    } catch (e) {
      debugPrint('Error in scanAnomalies: $e');
      rethrow;
    }
  }

  /// Dismiss anomaly alerts for specific transactions
  Future<void> dismissAnomalies({
    required List<int> txnIds,
    required int userId,
  }) async {
    try {
      final requestBody = {
        'txn_ids': txnIds.join(','),
        'user_id': userId,
      };

      final response = await http.post(
        Uri.parse('$baseUrl/anomaly/dismiss'),
        headers: {'Content-Type': 'application/x-www-form-urlencoded'},
        body: requestBody,
      ).timeout(
        const Duration(seconds: 30),
        onTimeout: () => throw TimeoutException('Dismiss anomalies request timed out'),
      );

      if (response.statusCode != 200) {
        throw Exception('Failed to dismiss anomalies: ${response.statusCode}');
      }
    } catch (e) {
      debugPrint('Error in dismissAnomalies: $e');
      rethrow;
    }
  }

  // ────────────────────────────────────────────────────────
  // OCR RECEIPT PROCESSING ENDPOINTS
  // ────────────────────────────────────────────────────────

  /// Upload receipt image for OCR processing
  /// Extracts merchant name, transaction amount, and description
  Future<OCRResult> processReceiptImage({
    required String imagePath,
  }) async {
    try {
      final file = File(imagePath);
      if (!file.existsSync()) {
        throw Exception('Image file not found: $imagePath');
      }

      final request = http.MultipartRequest(
        'POST',
        // FastAPI OCR endpoint is exposed at POST /api/categorize/ocr
        Uri.parse('$baseUrl/categorize/ocr'),
      );

      // Add image file to request
      request.files.add(
        await http.MultipartFile.fromPath('file', imagePath),
      );

      debugPrint('Sending OCR request for: $imagePath');

      final streamedResponse = await request.send().timeout(
        const Duration(seconds: 60),
        onTimeout: () => throw TimeoutException('OCR processing timed out'),
      );

      final response = await http.Response.fromStream(streamedResponse);

      if (response.statusCode == 200) {
        final jsonResponse = jsonDecode(response.body);
        if (jsonResponse['success'] ?? false) {
          return OCRResult.fromJson(jsonResponse);
        } else {
          throw Exception(jsonResponse['error'] ?? 'OCR processing failed');
        }
      } else {
        throw Exception('Failed to process receipt: ${response.statusCode} - ${response.body}');
      }
    } catch (e) {
      debugPrint('Error in processReceiptImage: $e');
      rethrow;
    }
  }

  // ────────────────────────────────────────────────────────
  // MERCHANT MANAGEMENT ENDPOINTS
  // ────────────────────────────────────────────────────────

  /// Check if a merchant already exists in the database
  /// Returns true if merchant exists, false otherwise
  Future<MerchantCheckResult> checkMerchantExists({
    required String merchantName,
    required int userId,
  }) async {
    try {
      final queryParams = {
        'merchant_name': merchantName,
        'user_id': userId.toString(),
      };

      final response = await http.get(
        Uri.parse('$baseUrl/merchants/check').replace(queryParameters: queryParams),
        headers: {'Content-Type': 'application/json'},
      ).timeout(
        const Duration(seconds: 10),
        onTimeout: () => throw TimeoutException('Merchant check request timed out'),
      );

      if (response.statusCode == 200) {
        final jsonResponse = jsonDecode(response.body);
        return MerchantCheckResult.fromJson(jsonResponse);
      } else if (response.statusCode == 404) {
        // Merchant not found
        return MerchantCheckResult(exists: false, message: 'Merchant not found');
      } else {
        throw Exception('Failed to check merchant: ${response.statusCode}');
      }
    } catch (e) {
      debugPrint('Error in checkMerchantExists: $e');
      rethrow;
    }
  }

  /// Add a new merchant to the database
  /// Returns the merchant ID if successful
  Future<int> addMerchant({
    required String merchantName,
    required int userId,
    String category = 'Unknown',
  }) async {
    try {
      final requestBody = {
        'merchant_name': merchantName,
        'user_id': userId.toString(),
        'category': category,
      };

      final response = await http.post(
        Uri.parse('$baseUrl/merchants/add'),
        headers: {'Content-Type': 'application/x-www-form-urlencoded'},
        body: requestBody,
      ).timeout(
        const Duration(seconds: 30),
        onTimeout: () => throw TimeoutException('Add merchant request timed out'),
      );

      if (response.statusCode == 200 || response.statusCode == 201) {
        final jsonResponse = jsonDecode(response.body);
        if (jsonResponse['success'] ?? false) {
          return jsonResponse['merchant_id'] ?? -1;
        } else {
          throw Exception(jsonResponse['error'] ?? 'Failed to add merchant');
        }
      } else {
        throw Exception('Failed to add merchant: ${response.statusCode}');
      }
    } catch (e) {
      debugPrint('Error in addMerchant: $e');
      rethrow;
    }
  }

  /// Get category breakdown statistics
  /// This will be calculated from the transactions list
  Future<CategoryBreakdown> getCategoryBreakdown({
    required int userId,
  }) async {
    try {
      final transactions = await getTransactions(userId: userId, limit: 100);
      return CategoryBreakdown.fromTransactions(transactions.transactions);
    } catch (e) {
      debugPrint('Error in getCategoryBreakdown: $e');
      rethrow;
    }
  }

  /// Fetch dashboard summary (income vs expense, savings rate, budgets)
  Future<DashboardSummary> getDashboardSummary({
    required int userId,
  }) async {
    try {
      final uri = Uri.parse('$baseUrl/dashboard/summary').replace(
        queryParameters: {'user_id': userId.toString()},
      );

      final response = await http.get(
        uri,
        headers: {'Content-Type': 'application/json'},
      ).timeout(
        const Duration(seconds: 30),
        onTimeout: () => throw TimeoutException('Dashboard summary request timed out'),
      );

      if (response.statusCode == 200) {
        final jsonResponse = jsonDecode(response.body);
        if (jsonResponse['success'] == true) {
          return DashboardSummary.fromJson(jsonResponse);
        }
        throw Exception(jsonResponse['error'] ?? 'Failed to load dashboard summary');
      } else {
        throw Exception('Failed to load dashboard summary: ${response.statusCode} - ${response.body}');
      }
    } catch (e) {
      debugPrint('Error in getDashboardSummary: $e');
      rethrow;
    }
  }

  /// Fetch user goals with timeline simulation data
  Future<GoalsListResponse> getGoals({
    required int userId,
  }) async {
    try {
      final uri = Uri.parse('$baseUrl/goals/list').replace(
        queryParameters: {'user_id': userId.toString()},
      );

      final response = await http.get(
        uri,
        headers: {'Content-Type': 'application/json'},
      ).timeout(
        const Duration(seconds: 30),
        onTimeout: () => throw TimeoutException('getGoals request timed out'),
      );

      if (response.statusCode == 200) {
        final jsonResponse = jsonDecode(response.body);
        if (jsonResponse['success'] == true) {
          return GoalsListResponse.fromJson(jsonResponse);
        }
        throw Exception(jsonResponse['error'] ?? 'Failed to load goals');
      } else {
        throw Exception('Failed to load goals: ${response.statusCode} - ${response.body}');
      }
    } catch (e) {
      debugPrint('Error in getGoals: $e');
      rethrow;
    }
  }

  /// Create a new goal for the user
  Future<Map<String, dynamic>> createGoal({
    required int userId,
    required String goalName,
    required String goalType,
    required double targetAmount,
    required double currentSaved,
    double? monthlyContribution,
    String? deadline,
    int priority = 2,
  }) async {
    try {
      final uri = Uri.parse('$baseUrl/goals/create');
      
      final formData = {
        'user_id': userId.toString(),
        'goal_name': goalName,
        'goal_type': goalType,
        'target_amount': targetAmount.toString(),
        'current_saved': currentSaved.toString(),
        'priority': priority.toString(),
      };
      
      if (monthlyContribution != null) {
        formData['monthly_contribution'] = monthlyContribution.toString();
      }
      
      if (deadline != null) {
        formData['deadline'] = deadline;
      }

      final response = await http.post(
        uri,
        headers: {'Content-Type': 'application/x-www-form-urlencoded'},
        body: formData,
      ).timeout(
        const Duration(seconds: 30),
        onTimeout: () => throw TimeoutException('createGoal request timed out'),
      );

      if (response.statusCode == 200) {
        final jsonResponse = jsonDecode(response.body);
        if (jsonResponse['success'] == true) {
          return jsonResponse;
        }
        throw Exception(jsonResponse['error'] ?? 'Failed to create goal');
      } else {
        throw Exception('Failed to create goal: ${response.statusCode} - ${response.body}');
      }
    } catch (e) {
      debugPrint('Error in createGoal: $e');
      rethrow;
    }
  }
}

// ────────────────────────────────────────────────────────
// DATA MODELS - CATEGORIZATION
// ────────────────────────────────────────────────────────

class CategorizationResult {
  final String category;
  final String subcategory;
  final double confidenceScore;
  final bool needsConfirmation;
  final String? reason;

  CategorizationResult({
    required this.category,
    required this.subcategory,
    required this.confidenceScore,
    required this.needsConfirmation,
    this.reason,
  });

  factory CategorizationResult.fromJson(Map<String, dynamic> json) {
    // Helper to safely convert numeric fields
    double? _toDouble(dynamic value) {
      if (value == null) return null;
      if (value is double) return value;
      if (value is int) return value.toDouble();
      if (value is String) return double.tryParse(value);
      return null;
    }

    // Helper to safely convert boolean fields
    bool _toBool(dynamic value) {
      if (value is bool) return value;
      if (value is int) return value != 0;
      if (value is String) return value.toLowerCase() == 'true';
      return false;
    }

    return CategorizationResult(
      category: json['category'] ?? 'Uncategorized',
      subcategory: json['subcategory'] ?? '',
      confidenceScore: _toDouble(json['confidence_score']) ?? 0.0,
      needsConfirmation: _toBool(json['needs_confirmation']),
      reason: json['reason'],
    );
  }

  Map<String, dynamic> toJson() => {
    'category': category,
    'subcategory': subcategory,
    'confidence_score': confidenceScore,
    'needs_confirmation': needsConfirmation,
    'reason': reason,
  };
}

class TransactionResponse {
  final bool success;
  final String? message;
  final int? txnId;
  final String? error;

  TransactionResponse({
    required this.success,
    this.message,
    this.txnId,
    this.error,
  });

  factory TransactionResponse.fromJson(Map<String, dynamic> json) {
    return TransactionResponse(
      success: json['success'] ?? false,
      message: json['message'],
      txnId: json['txn_id'],
      error: json['error'],
    );
  }
}

class Transaction {
  final int txnId;
  final int userId;
  final int accountId;
  final double amount;
  final String txnType;
  final String? category;
  final String? subcategory;
  final String? rawDescription;
  final String? rawName;
  final String? paymentMode;
  final bool userVerified;
  final bool isRecurring;
  final double? confidenceScore;
  final DateTime txnTimestamp;
  final double? anomalyScore;
  final bool? isAnomaly;
  final String? severity;

  Transaction({
    required this.txnId,
    required this.userId,
    required this.accountId,
    required this.amount,
    required this.txnType,
    this.category,
    this.subcategory,
    this.rawDescription,
    this.rawName,
    this.paymentMode,
    required this.userVerified,
    required this.isRecurring,
    this.confidenceScore,
    required this.txnTimestamp,
    this.anomalyScore,
    this.isAnomaly,
    this.severity,
  });

  factory Transaction.fromJson(Map<String, dynamic> json) {
    // Helper to safely convert numeric fields
    double? _toDouble(dynamic value) {
      if (value == null) return null;
      if (value is double) return value;
      if (value is int) return value.toDouble();
      if (value is String) return double.tryParse(value);
      return null;
    }

    int? _toInt(dynamic value) {
      if (value == null) return null;
      if (value is int) return value;
      if (value is double) return value.toInt();
      if (value is String) return int.tryParse(value);
      return null;
    }

    // Helper to safely convert boolean fields
    bool _toBool(dynamic value) {
      if (value is bool) return value;
      if (value is int) return value != 0;
      if (value is String) return value.toLowerCase() == 'true';
      return false;
    }

    // Helper to safely convert severity (should be string or null)
    String? _toSeverity(dynamic value) {
      if (value == null) return null;
      if (value is String) return value;
      return value.toString();
    }

    // Helper to safely convert any value to String
    String? _toString(dynamic value) {
      if (value == null) return null;
      if (value is String) return value;
      return value.toString();
    }

    return Transaction(
      txnId: _toInt(json['txn_id']) ?? 0,
      userId: _toInt(json['user_id']) ?? 0,
      accountId: _toInt(json['account_id']) ?? 0,
      amount: _toDouble(json['amount']) ?? 0.0,
      txnType: _toString(json['txn_type']) ?? 'debit',
      category: _toString(json['category']),
      subcategory: _toString(json['subcategory']),
      rawDescription: _toString(json['raw_description']),
      rawName: _toString(json['raw_name']),
      paymentMode: _toString(json['payment_mode']),
      userVerified: _toBool(json['user_verified']),
      isRecurring: _toBool(json['is_recurring']),
      confidenceScore: _toDouble(json['confidence_score']),
      txnTimestamp: json['txn_timestamp'] != null
        ? DateTime.parse(json['txn_timestamp'].toString())
        : DateTime.now(),
      anomalyScore: _toDouble(json['anomaly_score']),
      isAnomaly: json['is_anomaly'] == true || json['is_anomaly'] == 'true',
      severity: _toSeverity(json['severity']),
    );
  }

  Map<String, dynamic> toJson() => {
    'txn_id': txnId,
    'user_id': userId,
    'account_id': accountId,
    'amount': amount,
    'txn_type': txnType,
    'category': category,
    'subcategory': subcategory,
    'raw_description': rawDescription,
    'raw_name': rawName,
    'payment_mode': paymentMode,
    'user_verified': userVerified,
    'is_recurring': isRecurring,
    'confidence_score': confidenceScore,
    'txn_timestamp': txnTimestamp.toIso8601String(),
    'anomaly_score': anomalyScore,
    'is_anomaly': isAnomaly,
    'severity': severity,
  };
}

class TransactionListResponse {
  final int total;
  final List<Transaction> transactions;

  TransactionListResponse({
    required this.total,
    required this.transactions,
  });

  factory TransactionListResponse.fromJson(Map<String, dynamic> json) {
    final txnsList = (json['transactions'] as List<dynamic>?)
        ?.map((t) => Transaction.fromJson(t as Map<String, dynamic>))
        .toList() ?? [];
    
    return TransactionListResponse(
      total: json['total'] ?? 0,
      transactions: txnsList,
    );
  }
}

// ────────────────────────────────────────────────────────
// DATA MODELS - ANOMALY DETECTION
// ────────────────────────────────────────────────────────

class AnomalyScanResult {
  final bool success;
  final int totalScanned;
  final int totalAnomalies;
  final List<Transaction> transactions;

  AnomalyScanResult({
    required this.success,
    required this.totalScanned,
    required this.totalAnomalies,
    required this.transactions,
  });

  factory AnomalyScanResult.fromJson(Map<String, dynamic> json) {
    final txnsList = (json['transactions'] as List<dynamic>?)
        ?.map((t) => Transaction.fromJson(t as Map<String, dynamic>))
        .toList() ?? [];
    
    return AnomalyScanResult(
      success: json['success'] ?? false,
      totalScanned: json['total_scanned'] ?? 0,
      totalAnomalies: json['total_anomalies'] ?? 0,
      transactions: txnsList,
    );
  }

  List<Transaction> get anomalies => transactions.where((t) => t.isAnomaly ?? false).toList();
  List<Transaction> get normal => transactions.where((t) => !(t.isAnomaly ?? false)).toList();
}

// ────────────────────────────────────────────────────────
// DATA MODELS - CATEGORY BREAKDOWN
// ────────────────────────────────────────────────────────

class CategoryBreakdownItem {
  final String category;
  final double totalAmount;
  final int count;
  final double percentage;
  final Color? displayColor;

  CategoryBreakdownItem({
    required this.category,
    required this.totalAmount,
    required this.count,
    required this.percentage,
    this.displayColor,
  });
}

class CategoryBreakdown {
  final double totalExpense;
  final List<CategoryBreakdownItem> categories;
  final DateTime? scannedAt;

  CategoryBreakdown({
    required this.totalExpense,
    required this.categories,
    this.scannedAt,
  });

  factory CategoryBreakdown.fromTransactions(List<Transaction> transactions) {
    Map<String, double> categoryTotals = {};
    Map<String, int> categoryCounts = {};

    // Only include debit transactions (expenses)
    for (var transaction in transactions) {
      if (transaction.txnType == 'debit' && transaction.category != null) {
        final category = transaction.category!;
        categoryTotals[category] = (categoryTotals[category] ?? 0) + transaction.amount;
        categoryCounts[category] = (categoryCounts[category] ?? 0) + 1;
      }
    }

    final totalExpense = categoryTotals.values.fold<double>(0, (a, b) => a + b);
    
    final categories = categoryTotals.entries.map((entry) {
      return CategoryBreakdownItem(
        category: entry.key,
        totalAmount: entry.value,
        count: categoryCounts[entry.key] ?? 0,
        percentage: totalExpense > 0 ? (entry.value / totalExpense) * 100 : 0,
        displayColor: _getCategoryColor(entry.key),
      );
    }).toList();

    // Sort by amount descending
    categories.sort((a, b) => b.totalAmount.compareTo(a.totalAmount));

    return CategoryBreakdown(
      totalExpense: totalExpense,
      categories: categories,
      scannedAt: DateTime.now(),
    );
  }

  static Color? _getCategoryColor(String category) {
    final categoryLower = category.toLowerCase();
    
    if (categoryLower.contains('food') || categoryLower.contains('dining')) {
      return const Color(0xFFFEA04C); // Orange
    } else if (categoryLower.contains('transport') || categoryLower.contains('travel')) {
      return const Color(0xFF4A85F6); // Blue
    } else if (categoryLower.contains('shop') || categoryLower.contains('retail')) {
      return const Color(0xFFFF5656); // Red
    } else if (categoryLower.contains('health') || categoryLower.contains('medical')) {
      return const Color(0xFF2BDB7C); // Green
    } else if (categoryLower.contains('entertain') || categoryLower.contains('recreation')) {
      return const Color(0xFFA55EED); // Purple
    } else if (categoryLower.contains('bill') || categoryLower.contains('utilities')) {
      return const Color(0xFFFFB627); // Gold
    } else if (categoryLower.contains('subscription')) {
      return const Color(0xFF00BCD4); // Cyan
    }
    
    return const Color(0xFF8BA5A8); // Gray - default
  }
}

// ────────────────────────────────────────────────────────
// DATA MODELS - DASHBOARD SUMMARY
// ────────────────────────────────────────────────────────

class DashboardSummary {
  final IncomeExpenseSummary incomeVsExpense;
  final double savingsRate;
  final List<BudgetStatusItem> budgets;
  final FinancialStability? financialStability;
  final DateTime? monthStart;
  final DateTime? generatedAt;
  final StreakMetrics? streakMetrics;

  DashboardSummary({
    required this.incomeVsExpense,
    required this.savingsRate,
    required this.budgets,
    this.financialStability,
    this.monthStart,
    this.generatedAt,
  });

  factory DashboardSummary.fromJson(Map<String, dynamic> json) {
    double? _toDouble(dynamic value) {
      if (value == null) return null;
      if (value is double) return value;
      if (value is int) return value.toDouble();
      if (value is String) return double.tryParse(value);
      return null;
    }

    DateTime? _toDate(dynamic value) {
      if (value == null) return null;
      return DateTime.tryParse(value.toString());
    }

    final summary = json['summary'] as Map<String, dynamic>? ?? {};
    final timeframe = json['timeframe'] as Map<String, dynamic>? ?? {};

    return DashboardSummary(
      incomeVsExpense: IncomeExpenseSummary.fromJson(
        summary['income_vs_expense'] as Map<String, dynamic>? ?? {},
      ),
      savingsRate: _toDouble(summary['savings_rate']) ?? 0.0,
      budgets: (summary['budgets'] as List<dynamic>? ?? [])
          .map((item) => BudgetStatusItem.fromJson(item as Map<String, dynamic>))
          .toList(),
      financialStability: summary['financial_stability'] is Map<String, dynamic>
          ? FinancialStability.fromJson(summary['financial_stability'] as Map<String, dynamic>)
          : null,
      monthStart: _toDate(timeframe['month_start']),
      generatedAt: _toDate(timeframe['generated_at']),
      streakMetrics: summary['streak_metrics'] is Map<String, dynamic>
          ? StreakMetrics.fromJson(summary['streak_metrics'] as Map<String, dynamic>)
          : null,
    );

}

class StreakMetrics {
  final int streakMonths;
  final int streakDays;
  final double consistencyPct;
  final double score;
  final double totalSipAmount;
  final int missedMonths;

  StreakMetrics({
    required this.streakMonths,
    required this.streakDays,
    required this.consistencyPct,
    required this.score,
    required this.totalSipAmount,
    required this.missedMonths,
  });

  factory StreakMetrics.fromJson(Map<String, dynamic> json) {
    double? _toDouble(dynamic value) {
      if (value == null) return null;
      if (value is double) return value;
      if (value is int) return value.toDouble();
      if (value is String) return double.tryParse(value);
      return null;
    }
    return StreakMetrics(
      streakMonths: json['streak_months'] ?? 0,
      streakDays: json['streak_days'] ?? 0,
      consistencyPct: _toDouble(json['consistency_pct']) ?? 0.0,
      score: _toDouble(json['score']) ?? 0.0,
      totalSipAmount: _toDouble(json['total_sip_amount']) ?? 0.0,
      missedMonths: json['missed_months'] ?? 0,
    );
  }
}
  }
}

class IncomeExpenseSummary {
  final double income;
  final double expense;
  final double net;

  IncomeExpenseSummary({
    required this.income,
    required this.expense,
    required this.net,
  });

  factory IncomeExpenseSummary.fromJson(Map<String, dynamic> json) {
    double? _toDouble(dynamic value) {
      if (value == null) return null;
      if (value is double) return value;
      if (value is int) return value.toDouble();
      if (value is String) return double.tryParse(value);
      return null;
    }

    return IncomeExpenseSummary(
      income: _toDouble(json['income']) ?? 0.0,
      expense: _toDouble(json['expense']) ?? 0.0,
      net: _toDouble(json['net']) ?? 0.0,
    );
  }
}

class BudgetStatusItem {
  final int budgetId;
  final String category;
  final String period;
  final double limitAmount;
  final double spentAmount;
  final double remainingAmount;
  final double utilisationPct;

  BudgetStatusItem({
    required this.budgetId,
    required this.category,
    required this.period,
    required this.limitAmount,
    required this.spentAmount,
    required this.remainingAmount,
    required this.utilisationPct,
  });

  factory BudgetStatusItem.fromJson(Map<String, dynamic> json) {
    double? _toDouble(dynamic value) {
      if (value == null) return null;
      if (value is double) return value;
      if (value is int) return value.toDouble();
      if (value is String) return double.tryParse(value);
      return null;
    }

    int? _toInt(dynamic value) {
      if (value == null) return null;
      if (value is int) return value;
      if (value is double) return value.toInt();
      if (value is String) return int.tryParse(value);
      return null;
    }

    return BudgetStatusItem(
      budgetId: _toInt(json['budget_id']) ?? 0,
      category: (json['category'] ?? 'Unknown').toString(),
      period: (json['period'] ?? 'monthly').toString(),
      limitAmount: _toDouble(json['limit_amount']) ?? 0.0,
      spentAmount: _toDouble(json['spent_amount']) ?? 0.0,
      remainingAmount: _toDouble(json['remaining_amount']) ?? 0.0,
      utilisationPct: _toDouble(json['utilisation_pct']) ?? 0.0,
    );
  }
}

class FinancialStability {
  final double score;
  final String label;
  final Map<String, ComponentScore> components;
  final FinancialStabilityMetrics metrics;

  FinancialStability({
    required this.score,
    required this.label,
    required this.components,
    required this.metrics,
  });

  ComponentScore? component(String key) => components[key];

  factory FinancialStability.fromJson(Map<String, dynamic> json) {
    double? _toDouble(dynamic value) {
      if (value == null) return null;
      if (value is double) return value;
      if (value is int) return value.toDouble();
      if (value is String) return double.tryParse(value);
      return null;
    }

    final rawComponents = json['components'] as Map<String, dynamic>? ?? {};
    final parsedComponents = <String, ComponentScore>{};
    rawComponents.forEach((key, value) {
      if (value is Map<String, dynamic>) {
        parsedComponents[key] = ComponentScore.fromJson(value);
      }
    });

    return FinancialStability(
      score: _toDouble(json['score']) ?? 0.0,
      label: (json['label'] ?? 'Unknown').toString(),
      components: parsedComponents,
      metrics: FinancialStabilityMetrics.fromJson(
        json['metrics'] as Map<String, dynamic>? ?? {},
      ),
    );
  }
}

class ComponentScore {
  final double weight;
  final double score;
  final double? valuePct;
  final double? valueMonths;
  final String? direction;

  ComponentScore({
    required this.weight,
    required this.score,
    this.valuePct,
    this.valueMonths,
    this.direction,
  });

  factory ComponentScore.fromJson(Map<String, dynamic> json) {
    double? _toDouble(dynamic value) {
      if (value == null) return null;
      if (value is double) return value;
      if (value is int) return value.toDouble();
      if (value is String) return double.tryParse(value);
      return null;
    }

    return ComponentScore(
      weight: _toDouble(json['weight']) ?? 0.0,
      score: _toDouble(json['score']) ?? 0.0,
      valuePct: _toDouble(json['value_pct']),
      valueMonths: _toDouble(json['value_months']),
      direction: json['direction']?.toString(),
    );
  }
}

class FinancialStabilityMetrics {
  final double monthlyIncome;
  final double monthlyExpense;
  final double monthlySavings;
  final double savingsRatePct;
  final double expenseRatioPct;
  final double emergencyFundBalance;
  final double emergencyMonths;
  final double emiObligations;
  final double emiRatioPct;
  final double incomeCvPct;
  final List<MonthlyIncomePoint> incomeHistory;

  FinancialStabilityMetrics({
    required this.monthlyIncome,
    required this.monthlyExpense,
    required this.monthlySavings,
    required this.savingsRatePct,
    required this.expenseRatioPct,
    required this.emergencyFundBalance,
    required this.emergencyMonths,
    required this.emiObligations,
    required this.emiRatioPct,
    required this.incomeCvPct,
    required this.incomeHistory,
  });

  factory FinancialStabilityMetrics.fromJson(Map<String, dynamic> json) {
    double? _toDouble(dynamic value) {
      if (value == null) return null;
      if (value is double) return value;
      if (value is int) return value.toDouble();
      if (value is String) return double.tryParse(value);
      return null;
    }

    final historyList = (json['income_history'] as List<dynamic>? ?? [])
        .map((item) => MonthlyIncomePoint.fromJson(item as Map<String, dynamic>))
        .toList();

    return FinancialStabilityMetrics(
      monthlyIncome: _toDouble(json['monthly_income']) ?? 0.0,
      monthlyExpense: _toDouble(json['monthly_expense']) ?? 0.0,
      monthlySavings: _toDouble(json['monthly_savings']) ?? 0.0,
      savingsRatePct: _toDouble(json['savings_rate_pct']) ?? 0.0,
      expenseRatioPct: _toDouble(json['expense_ratio_pct']) ?? 0.0,
      emergencyFundBalance: _toDouble(json['emergency_fund_balance']) ?? 0.0,
      emergencyMonths: _toDouble(json['emergency_months']) ?? 0.0,
      emiObligations: _toDouble(json['emi_obligations']) ?? 0.0,
      emiRatioPct: _toDouble(json['emi_ratio_pct']) ?? 0.0,
      incomeCvPct: _toDouble(json['income_cv_pct']) ?? 0.0,
      incomeHistory: historyList,
    );
  }
}

class MonthlyIncomePoint {
  final String month;
  final double amount;

  MonthlyIncomePoint({
    required this.month,
    required this.amount,
  });

  factory MonthlyIncomePoint.fromJson(Map<String, dynamic> json) {
    double? _toDouble(dynamic value) {
      if (value == null) return null;
      if (value is double) return value;
      if (value is int) return value.toDouble();
      if (value is String) return double.tryParse(value);
      return null;
    }

    return MonthlyIncomePoint(
      month: (json['month'] ?? '').toString(),
      amount: _toDouble(json['amount']) ?? 0.0,
    );
  }
}

// ────────────────────────────────────────────────────────
// DATA MODELS - MERCHANT MANAGEMENT
// ────────────────────────────────────────────────────────

class MerchantCheckResult {
  final bool exists;
  final String message;
  final int? merchantId;

  MerchantCheckResult({
    required this.exists,
    required this.message,
    this.merchantId,
  });

  factory MerchantCheckResult.fromJson(Map<String, dynamic> json) {
    return MerchantCheckResult(
      exists: json['exists'] ?? false,
      message: json['message'] ?? '',
      merchantId: json['merchant_id'],
    );
  }
}

// ────────────────────────────────────────────────────────
// DATA MODELS - OCR RESULT
// ────────────────────────────────────────────────────────

class OCRResult {
  final bool success;
  final String? merchantName;
  final double? amount;
  final String? description;
  final String? fullText;
  final String? error;

  OCRResult({
    required this.success,
    this.merchantName,
    this.amount,
    this.description,
    this.fullText,
    this.error,
  });

  factory OCRResult.fromJson(Map<String, dynamic> json) {
    // Backend OCR endpoint currently returns:
    // { "success": true, "result": { "ocr_merchant", "ocr_amount", "ocr_description", ... } }
    final result = (json['result'] is Map<String, dynamic>)
        ? json['result'] as Map<String, dynamic>
        : <String, dynamic>{};

    double? pickAmount(dynamic value) {
      if (value == null) return null;
      if (value is num) return value.toDouble();
      if (value is String) return double.tryParse(value);
      return null;
    }

    String? pickString(dynamic value) {
      if (value == null) return null;
      if (value is String) return value;
      return value.toString();
    }

    return OCRResult(
      success: json['success'] ?? false,
      // Prefer structured OCR fields from result, fall back to any flat keys
      merchantName: pickString(
        result['ocr_merchant'] ??
        json['ocr_merchant'] ??
        json['merchant_name'] ??
        json['raw_name'],
      ),
      amount: pickAmount(
        result['ocr_amount'] ?? json['ocr_amount'] ?? json['amount'],
      ),
      description: pickString(
        result['ocr_description'] ??
        json['ocr_description'] ??
        json['description'],
      ),
      // Keep fullText/error for potential debugging; backend may not send these
      fullText: pickString(json['full_text']),
      error: pickString(json['error']),
    );
  }
}

// ────────────────────────────────────────────────────────
// DATA MODELS - GOALS
// ────────────────────────────────────────────────────────

class GoalsListResponse {
  final bool success;
  final int userId;
  final int total;
  final List<GoalItem> goals;

  GoalsListResponse({
    required this.success,
    required this.userId,
    required this.total,
    required this.goals,
  });

  factory GoalsListResponse.fromJson(Map<String, dynamic> json) {
    final goalsList = (json['goals'] as List<dynamic>? ?? [])
        .map((item) => GoalItem.fromJson(item as Map<String, dynamic>))
        .toList();

    return GoalsListResponse(
      success: json['success'] ?? false,
      userId: json['user_id'] ?? 1,
      total: json['total'] ?? 0,
      goals: goalsList,
    );
  }
}

class GoalItem {
  final int goalId;
  final String goalName;
  final String? goalType;
  final double targetAmount;
  final double currentAmount;
  final double monthlyContribution;
  final String? deadline;
  final int priority;
  final double progressPct;
  final GoalTimeline timeline;
  final double? feasibilityScore;
  final String? healthTag;
  final String? feasibilityNote;

  GoalItem({
    required this.goalId,
    required this.goalName,
    this.goalType,
    required this.targetAmount,
    required this.currentAmount,
    required this.monthlyContribution,
    this.deadline,
    required this.priority,
    required this.progressPct,
    required this.timeline,
    this.feasibilityScore,
    this.healthTag,
    this.feasibilityNote,
  });

  // Determine icon based on goal type
  IconData get icon {
    final type = goalType?.toLowerCase() ?? '';
    if (type.contains('emergency')) return Icons.health_and_safety;
    if (type.contains('retirement')) return Icons.trending_up;
    if (type.contains('education')) return Icons.school;
    if (type.contains('home')) return Icons.home;
    if (type.contains('trip') || type.contains('travel')) return Icons.flight_takeoff;
    if (type.contains('car') || type.contains('vehicle')) return Icons.directions_car;
    return Icons.track_changes;
  }

  // Color based on status
  Color get statusColor {
    switch (timeline.status) {
      case 'early':
        return const Color(0xFF5DF22A); // Green
      case 'on_time':
        return const Color(0xFF5DF22A); // Green
      case 'late':
        return const Color(0xFFFF9800); // Orange
      default:
        return const Color(0xFFFF6F61); // Red
    }
  }

  factory GoalItem.fromJson(Map<String, dynamic> json) {
    double? toDouble(dynamic value) {
      if (value == null) return null;
      if (value is double) return value;
      if (value is int) return value.toDouble();
      if (value is String) return double.tryParse(value);
      return null;
    }

    int? toInt(dynamic value) {
      if (value == null) return null;
      if (value is int) return value;
      if (value is double) return value.toInt();
      if (value is String) return int.tryParse(value);
      return null;
    }

    return GoalItem(
      goalId: toInt(json['goal_id']) ?? 0,
      goalName: (json['goal_name'] ?? 'Goal').toString(),
      goalType: json['goal_type']?.toString(),
      targetAmount: toDouble(json['target_amount']) ?? 0.0,
      currentAmount: toDouble(json['current_amount']) ?? 0.0,
      monthlyContribution: toDouble(json['monthly_contribution']) ?? 0.0,
      deadline: json['deadline']?.toString(),
      priority: toInt(json['priority']) ?? 2,
      progressPct: toDouble(json['progress_pct']) ?? 0.0,
      timeline: GoalTimeline.fromJson(
        json['timeline'] as Map<String, dynamic>? ?? {},
      ),
      feasibilityScore: toDouble(json['feasibility_score']),
      healthTag: json['health_tag']?.toString(),
      feasibilityNote: json['feasibility_note']?.toString(),
    );
  }
}

class GoalTimeline {
  final int monthsToTarget;
  final int monthsToDeadline;
  final int deltaMonths;
  final String status; // 'on_time', 'early', 'late', 'impossible'
  final double feasibilityPct;
  final double? runwayMonths;

  GoalTimeline({
    required this.monthsToTarget,
    required this.monthsToDeadline,
    required this.deltaMonths,
    required this.status,
    required this.feasibilityPct,
    this.runwayMonths,
  });

  factory GoalTimeline.fromJson(Map<String, dynamic> json) {
    double? toDouble(dynamic value) {
      if (value == null) return null;
      if (value is double) return value;
      if (value is int) return value.toDouble();
      if (value is String) return double.tryParse(value);
      return null;
    }

    int? toInt(dynamic value) {
      if (value == null) return null;
      if (value is int) return value;
      if (value is double) return value.toInt();
      if (value is String) return int.tryParse(value);
      return null;
    }

    return GoalTimeline(
      monthsToTarget: toInt(json['months_to_target']) ?? 0,
      monthsToDeadline: toInt(json['months_to_deadline']) ?? 0,
      deltaMonths: toInt(json['delta_months']) ?? 0,
      status: (json['status'] ?? 'on_time').toString(),
      feasibilityPct: toDouble(json['feasibility_pct']) ?? 0.0,
      runwayMonths: toDouble(json['runway_months']),
    );
  }
}

// Exception classes
class TimeoutException implements Exception {
  final String message;
  TimeoutException(this.message);

  @override
  String toString() => message;
}


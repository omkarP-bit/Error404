class Transaction {
  final int txnId;
  final int userId;
  final double amount;
  final String txnType;
  final String? category;
  final String? subcategory;
  final String? rawDescription;
  final String? cleanDescription;
  final double? confidenceScore;
  final DateTime txnTimestamp;
  final bool isAnomalous;
  final double? anomalyScore;

  Transaction({
    required this.txnId,
    required this.userId,
    required this.amount,
    required this.txnType,
    this.category,
    this.subcategory,
    this.rawDescription,
    this.cleanDescription,
    this.confidenceScore,
    required this.txnTimestamp,
    this.isAnomalous = false,
    this.anomalyScore,
  });

  factory Transaction.fromJson(Map<String, dynamic> json) {
    return Transaction(
      txnId: json['txn_id'],
      userId: json['user_id'],
      amount: double.parse(json['amount'].toString()),
      txnType: json['txn_type'],
      category: json['category'],
      subcategory: json['subcategory'],
      rawDescription: json['raw_description'],
      cleanDescription: json['clean_description'],
      confidenceScore: json['confidence_score'] != null 
          ? double.parse(json['confidence_score'].toString()) 
          : null,
      txnTimestamp: DateTime.parse(json['txn_timestamp']),
      isAnomalous: json['is_anomalous'] ?? false,
      anomalyScore: json['anomaly_score'] != null 
          ? double.parse(json['anomaly_score'].toString()) 
          : null,
    );
  }

  Map<String, dynamic> toJson() {
    return {
      'txn_id': txnId,
      'user_id': userId,
      'amount': amount,
      'txn_type': txnType,
      'category': category,
      'subcategory': subcategory,
      'raw_description': rawDescription,
      'clean_description': cleanDescription,
      'confidence_score': confidenceScore,
      'txn_timestamp': txnTimestamp.toIso8601String(),
      'is_anomalous': isAnomalous,
      'anomaly_score': anomalyScore,
    };
  }
}

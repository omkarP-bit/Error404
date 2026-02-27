import 'package:flutter/foundation.dart';
import 'package:path/path.dart';
import 'package:sqflite/sqflite.dart';
import 'package:sqflite_common_ffi_web/sqflite_ffi_web.dart';
import 'package:intl/intl.dart';

// LocalMomentumDb will later be replaced by SupabaseMomentumRepo with the same methods.
// savings_activity table will become a Supabase table with RLS per user.

class SavingsActivity {
  final int? id;
  final int userId;
  final String monthKey; // YYYY-MM
  final bool contributed;
  final double totalSipAmount;
  final bool missed;
  final DateTime createdAt;

  SavingsActivity({
    this.id,
    required this.userId,
    required this.monthKey,
    required this.contributed,
    required this.totalSipAmount,
    required this.missed,
    required this.createdAt,
  });

  Map<String, dynamic> toMap() {
    return {
      'id': id,
      'user_id': userId,
      'month_key': monthKey,
      'contributed': contributed ? 1 : 0,
      'total_sip_amount': totalSipAmount,
      'missed': missed ? 1 : 0,
      'created_at': createdAt.toIso8601String(),
    };
  }

  factory SavingsActivity.fromMap(Map<String, dynamic> map) {
    return SavingsActivity(
      id: map['id'],
      userId: map['user_id'],
      monthKey: map['month_key'],
      contributed: map['contributed'] == 1,
      totalSipAmount: (map['total_sip_amount'] as num).toDouble(),
      missed: map['missed'] == 1,
      createdAt: DateTime.parse(map['created_at']),
    );
  }
}

class LocalMomentumDb {
  static final LocalMomentumDb _instance = LocalMomentumDb._internal();
  static Database? _database;

  factory LocalMomentumDb() => _instance;

  LocalMomentumDb._internal();

  Future<Database> get db async {
    if (_database != null) return _database!;
    _database = await initDB();
    return _database!;
  }

  Future<Database> initDB() async {
    if (kIsWeb) {
      databaseFactory = databaseFactoryFfiWeb;
      final path = 'my_web_momentum_web.db';
      return await databaseFactory.openDatabase(
        path,
        options: OpenDatabaseOptions(
          version: 1,
          onCreate: _createDb,
        ),
      );
    }
    
    String path = join(await getDatabasesPath(), 'momentum.db');
    return await openDatabase(
      path,
      version: 1,
      onCreate: _createDb,
    );
  }

  Future<void> _createDb(Database db, int version) async {
    await db.execute('''
      CREATE TABLE IF NOT EXISTS savings_activity (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        month_key TEXT NOT NULL,
        contributed INTEGER NOT NULL DEFAULT 1,
        total_sip_amount REAL NOT NULL DEFAULT 0,
        missed INTEGER NOT NULL DEFAULT 0,
        created_at TEXT NOT NULL,
        UNIQUE(user_id, month_key)
      )
    ''');
  }

  Future<void> ensureTablesExist() async {
    // Trigger initialization
    final dbClient = await db;
    // Just in case, ensure it runs for existing web dbs
    await _createDb(dbClient, 1);
  }

  String monthKeyFromDate(DateTime date) {
    return DateFormat('yyyy-MM').format(date);
  }

  List<String> generateLastNMonthKeys(int n, DateTime now) {
    List<String> keys = [];
    for (int i = 0; i < n; i++) {
      int year = now.year;
      int month = now.month - i;
      while (month <= 0) {
        month += 12;
        year -= 1;
      }
      keys.add('${year.toString().padLeft(4, '0')}-${month.toString().padLeft(2, '0')}');
    }
    return keys;
  }

  Future<void> upsertContribution({
    required int userId,
    required String monthKey,
    required double totalSipAmount,
  }) async {
    final dbClient = await db;
    
    final activity = SavingsActivity(
      userId: userId,
      monthKey: monthKey,
      contributed: true,
      totalSipAmount: totalSipAmount,
      missed: false,
      createdAt: DateTime.now(),
    );

    await dbClient.insert(
      'savings_activity',
      activity.toMap(),
      conflictAlgorithm: ConflictAlgorithm.replace,
    );
  }

  Future<void> markMissedMonth({
    required int userId,
    required String monthKey,
  }) async {
    final dbClient = await db;

    final activity = SavingsActivity(
      userId: userId,
      monthKey: monthKey,
      contributed: false,
      totalSipAmount: 0.0,
      missed: true,
      createdAt: DateTime.now(),
    );

    await dbClient.insert(
      'savings_activity',
      activity.toMap(),
      conflictAlgorithm: ConflictAlgorithm.replace,
    );
  }

  Future<List<SavingsActivity>> fetchLastMonths({
    required int userId,
    required int windowMonths,
  }) async {
    final dbClient = await db;
    final now = DateTime.now();
    final keys = generateLastNMonthKeys(windowMonths, now);
    
    final List<Map<String, dynamic>> maps = await dbClient.query(
      'savings_activity',
      where: 'user_id = ? AND month_key IN (${List.filled(keys.length, '?').join(', ')})',
      whereArgs: [userId, ...keys],
      orderBy: 'month_key DESC',
    );

    final dbActivities = maps.map((m) => SavingsActivity.fromMap(m)).toList();
    
    // Fill in missing months with default un-contributed
    List<SavingsActivity> filled = [];
    for (String key in keys) {
      final existing = dbActivities.where((a) => a.monthKey == key).toList();
      if (existing.isNotEmpty) {
        filled.add(existing.first);
      } else {
        filled.add(SavingsActivity(
          userId: userId,
          monthKey: key,
          contributed: false,
          totalSipAmount: 0.0,
          missed: false,
          createdAt: DateTime.now(),
        ));
      }
    }

    return filled;
  }
}

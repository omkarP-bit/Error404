import 'package:flutter/foundation.dart';
import 'package:path/path.dart';
import 'package:sqflite/sqflite.dart';
import 'package:sqflite_common_ffi_web/sqflite_ffi_web.dart';
import '../models/goal.dart';

// Currently using SQLite for offline testing; later swap with SupabaseGoalsRepository with same method signatures.
class LocalGoalsDB {
  static final LocalGoalsDB _instance = LocalGoalsDB._internal();
  static Database? _database;

  factory LocalGoalsDB() => _instance;

  LocalGoalsDB._internal();

  Future<Database> get db async {
    if (_database != null) return _database!;
    _database = await initDB();
    return _database!;
  }

  Future<Database> initDB() async {
    if (kIsWeb) {
      databaseFactory = databaseFactoryFfiWeb;
      final path = 'my_web_web.db';
      return await databaseFactory.openDatabase(
        path,
        options: OpenDatabaseOptions(
          version: 1,
          onCreate: (Database db, int version) async {
            await _createTables(db);
          },
          onUpgrade: (Database db, int oldVersion, int newVersion) async {
            if (oldVersion < 2) {
              await db.execute('ALTER TABLE goals ADD COLUMN feasibility_note TEXT');
            }
          },
        ),
      );
    }
    
    String path = join(await getDatabasesPath(), 'app.db');
    return await openDatabase(
      path,
      version: 2,
      onCreate: (Database db, int version) async {
        await _createTables(db);
      },
      onUpgrade: (Database db, int oldVersion, int newVersion) async {
        if (oldVersion < 2) {
          try {
            await db.execute('ALTER TABLE goals ADD COLUMN feasibility_note TEXT');
          } catch (_) {} // Column may already exist
        }
      },
    );
  }

  Future<void> _createTables(Database db) async {
    await db.execute('''
      CREATE TABLE goals (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        name TEXT NOT NULL,
        type TEXT NOT NULL,
        target_amount REAL NOT NULL,
        saved_amount REAL NOT NULL DEFAULT 0.0,
        monthly_contribution REAL NOT NULL,
        deadline TEXT,
        priority INTEGER NOT NULL,
        status TEXT NOT NULL,
        feasibility_score REAL,
        feasibility_note TEXT,
        created_at TEXT NOT NULL
      )
    ''');
  }

  Future<List<Goal>> fetchGoals(int userId) async {
    final dbClient = await db;
    final List<Map<String, dynamic>> maps = await dbClient.query(
      'goals',
      where: 'user_id = ?',
      whereArgs: [userId],
    );

    List<Goal> goals = List.generate(maps.length, (i) {
      return Goal.fromMap(maps[i]);
    });

    goals.sort((a, b) {
      if (a.type == 'emergency_fund' && b.type != 'emergency_fund') return -1;
      if (b.type == 'emergency_fund' && a.type != 'emergency_fund') return 1;
      
      int priorityComparison = a.priority.compareTo(b.priority);
      if (priorityComparison != 0) return priorityComparison;
      
      if (a.createdAt != null && b.createdAt != null) {
        return b.createdAt!.compareTo(a.createdAt!);
      }
      return (b.id ?? 0).compareTo(a.id ?? 0);
    });

    return goals;
  }

  Future<int> insertGoal(Goal goal) async {
    final dbClient = await db;
    return await dbClient.insert(
      'goals',
      goal.toMap(),
      conflictAlgorithm: ConflictAlgorithm.replace,
    );
  }

  Future<int> updateGoalSavedAmount(int goalId, double savedAmount) async {
    final dbClient = await db;
    return await dbClient.update(
      'goals',
      {'saved_amount': savedAmount},
      where: 'id = ?',
      whereArgs: [goalId],
    );
  }

  Future<int> updateGoalFeasibility(int goalId, double score, String note) async {
    final dbClient = await db;
    return await dbClient.update(
      'goals',
      {
        'feasibility_score': score,
        'feasibility_note': note,
      },
      where: 'id = ?',
      whereArgs: [goalId],
    );
  }

  Future<Goal?> fetchEmergencyGoal(int userId) async {
    final dbClient = await db;
    final List<Map<String, dynamic>> maps = await dbClient.query(
      'goals',
      where: 'user_id = ? AND type = ?',
      whereArgs: [userId, 'emergency_fund'],
      limit: 1,
    );
    if (maps.isNotEmpty) {
      return Goal.fromMap(maps.first);
    }
    return null;
  }

  Future<int> ensureEmergencyGoalExists(int userId, {double? defaultTarget}) async {
    final emergencyGoal = await fetchEmergencyGoal(userId);
    if (emergencyGoal != null && emergencyGoal.id != null) {
      return emergencyGoal.id!;
    }

    final target = defaultTarget ?? 50000.0;
    final goal = Goal(
      userId: userId,
      name: 'Emergency Fund',
      type: 'emergency_fund',
      targetAmount: target,
      savedAmount: 0.0,
      monthlyContribution: 0.0,
      priority: 1,
      status: 'active',
      deadline: null,
      createdAt: DateTime.now(),
    );
    return await insertGoal(goal);
  }

  Future<void> updateMonthlyContributionBulk(Map<int, double> goalIdToAmount) async {
    final dbClient = await db;
    await dbClient.transaction((txn) async {
      for (var entry in goalIdToAmount.entries) {
        await txn.update(
          'goals',
          {'monthly_contribution': entry.value},
          where: 'id = ?',
          whereArgs: [entry.key],
        );
      }
    });
  }
}

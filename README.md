# Personal Finance Management System - Morpheus

An AI-powered, secure, and scalable **Personal Finance Management** platform designed to help users track spending, manage budgets, detect anomalies, plan financial goals, and determine investment readiness — all with enterprise-grade security.

## 🎯 Key Features

- **Automated Transaction Categorization** - AI-powered merchant detection and category classification
- **Real-Time Anomaly Detection** - Detects suspicious spending patterns instantly
- **Smart Goal Planning** - Optimizes financial goals based on user behavior
- **Expense Tracking** - Beautiful dashboard with category breakdown and filters
- **Behavioral Analytics** - ML-powered insights into spending patterns
- **Investment Readiness** - Determines financial readiness for investment

## 🛠️ Tech Stack

**Frontend:**
- Flutter (Mobile & Web)
- GoRouter (Navigation)
- fl_chart (Data Visualization)

**Backend:**
- FastAPI + Uvicorn
- Supabase (PostgreSQL + Authentication)
- Machine Learning (IsolationForest, TF-IDF, SentenceTransformer, SVC)

**Security:**
- JWT Authentication
- Supabase Row-Level Security
- Encrypted Data Storage

---

## 🚀 Quick Start

### Prerequisites
- Flutter 3.9.2+
- Python 3.9+
- Android Device with USB Debugging enabled (for physical device testing)

### Setup Backend

1. **Navigate to backend:**
   ```bash
   cd Morpheus
   ```

2. **Create virtual environment:**
   ```bash
   python -m venv .venv
   .venv\Scripts\activate    # Windows
   source .venv/bin/activate # Mac/Linux
   ```

3. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

4. **Run migrations:**
   ```bash
   alembic upgrade head
   ```

5. **Start server:**
   ```bash
   uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
   ```

### Setup Flutter App

1. **Install dependencies:**
   ```bash
   flutter pub get
   ```

2. **For USB Physical Device Testing:**
   ```bash
   # Enable USB Debugging on device (Settings → Developer Options)
   adb devices                    # Verify connection
   adb reverse tcp:8000 tcp:8000 # Create USB tunnel
   flutter run -d <device-id>
   ```

3. **For Emulator:**
   ```bash
   flutter run -d emulator-5554
   ```

---

## 📁 Project Structure

```
lib/
├── main.dart                 # App entry point
├── app_router.dart          # Navigation routes
├── dashboard.dart           # Home screen
├── expenses.dart            # Expense tracking with filters
├── insights.dart            # Anomaly detection & analytics
├── goals.dart               # Financial goals
├── profile.dart             # User profile
├── signup.dart              # Authentication
└── services/
    └── api_service.dart     # API communication

Morpheus/
├── app/
│   ├── main.py             # FastAPI app
│   ├── models.py           # Database models
│   ├── schemas.py          # Request/response schemas
│   └── routers/            # API endpoints
├── ml_models/              # ML models & training
├── migrations/             # Database migrations
└── requirements.txt        # Python dependencies
```

---

## ✨ Core Features Explained

### 1. **Smart Categorization**
- Uses sentence embeddings and machine learning
- Learns from user corrections
- 95%+ accuracy for common merchants
- Confidence scoring for uncertain cases

### 2. **Anomaly Detection**
- Multi-factor scoring system
- Amount deviation analysis
- Frequency pattern detection
- Real-time alerts
- Expandable anomaly list in Insights

### 3. **Category Breakdown**
- Visual pie chart showing expense distribution
- Top 3 categories with amounts
- Monthly tracking
- Appears at top of Expenses screen

### 4. **Expense Filtering**
- **Category Filter:** All, Food, Transport, Shopping
- **Time Period Filter:** Daily, Weekly, This Month
- Real-time updates as user changes filters
- Filtered data displayed below category breakdown

### 5. **Merchant Name Display**
- Shows merchant/merchant ID instead of raw transaction
- Extracted from transaction description
- Cleaner, user-friendly interface

---

## 🔐 Security Features

- **JWT Authentication** via Supabase
- **Encrypted Data Storage** at rest
- **TLS Encryption** in transit
- **Row-Level Security** in PostgreSQL
- **Environment-based Configuration** (no hardcoded credentials)

---

## 📱 UI/UX Highlights

### Expenses Screen
- ✅ Category breakdown pie chart at top
- ✅ Functional category filter chips
- ✅ Dropdown time period selector (Daily/Weekly/Monthly)
- ✅ Merchant names instead of "Transaction"
- ✅ Anomaly alert banner with count overview

### Insights Screen
- ✅ Clickable anomaly summary card
- ✅ Shows "X Anomalies Detected Out of Y transactions"
- ✅ Expands to full list only when clicked
- ✅ Behavioral patterns & spending trends
- ✅ Investment readiness scoring

### Dashboard
- ✅ Financial overview
- ✅ Quick action buttons
- ✅ Account summary
- ✅ Goal progress tracking

---

## 🔧 Configuration

### API Host Configuration (main.dart)

**For Android Device (USB with adb reverse):**
```dart
ApiService.setApiHost('localhost:8000');
```

**For Emulator:**
```dart
ApiService.setApiHost('localhost:8000');
```

**For WiFi Network:**
```dart
ApiService.setApiHost('192.168.x.x:8000'); // Your laptop IP
```

### Backend Configuration (Morpheus/app/main.py)

Backend runs on:
- Host: `127.0.0.1` (localhost only)
- Port: `8000`
- Reload: `--reload` (development)

---

## 🧪 Testing

### Desktop Testing
```bash
dart analyze lib/           # Code analysis
flutter test               # Unit tests
```

### Device Testing
```bash
# Physical Android Device
adb reverse tcp:8000 tcp:8000
flutter run -d <device-id>

# Emulator
flutter run -d emulator-5554
```

---

## 📊 Database Schema

Key Tables:
- `users` - User accounts
- `transactions` - User transactions
- `categories` - Expense categories
- `anomalies` - Detected anomalies
- `goals` - Financial goals
- `user_patterns` - Behavioral data

---

## 🚨 Troubleshooting

### API Timeout Issues
- Ensure backend is running: `uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload`
- For USB device: `adb reverse tcp:8000 tcp:8000`
- Check network connectivity

### Database Errors
- Ensure migrations are run: `alembic upgrade head`
- Check Supabase connection credentials in environment variables

### UI Issues
- Hot reload: Press `R` in terminal
- Full restart: Press `Shift + R`
- Rebuild: `flutter clean && flutter pub get && flutter run`

---

## 📚 ML Models

All ML models are stored as joblib files in `Morpheus/ml_models/`:

- **IsolationForest** - Anomaly detection
- **TF-IDF Vectorizer** - Text feature extraction
- **SentenceTransformer** - Semantic embeddings
- **SVC Classifier** - Transaction categorization

Models are loaded at startup and predictions run asynchronously.

---

## 🔄 Development Workflow

1. **During Development:**
   ```bash
   # Terminal 1: Backend
   cd Morpheus && uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
   
   # Terminal 2: Flutter (USB device)
   adb reverse tcp:8000 tcp:8000
   flutter run -d <device-id>
   ```

2. **Making Changes:**
   - Edit Flutter code → Hot reload (R)
   - Edit Backend code → Auto-reloads (--reload flag)
   - Commit frequently: `git add . && git commit -m "message"`

3. **Testing Changes:**
   - Transactions screen → Verify category breakdown displays
   - Apply filters → Check Daily/Weekly/Month filtering
   - Insights → Click anomaly card to expand/collapse
   - Add transaction → Verify merchant name shows correctly

---

## 🎓 Key Learning Points

### Flutter
- State management with `setState()`
- Mounted checks for safe async operations
- GoRouter for navigation
- FL Chart for data visualization

### FastAPI
- Async request handling
- Middleware for authentication
- CORS configuration
- OpenAPI documentation

### ML/Data Science
- Feature engineering from transaction data
- Real-time anomaly detection
- Behavioral pattern learning
- Confidence scoring

---

## 📝 Notes

- All user IDs currently hardcoded as `1` - Update with actual auth in production
- Account IDs hardcoded as `1` - Link to actual user accounts
- Supabase credentials in `main.dart` - Move to environment variables
- ML models run asynchronously - No real-time blocking of UI

---

## 🤝 Contributing

When building new features:
1. Ensure all async operations use `if (mounted)` checks
2. Add proper error handling and user feedback
3. Test on both emulator and physical device
4. Update this README for new features

---

## 📞 Support & Debugging

- **Flutter Logs:** Run with `flutter run -v` for verbose output
- **Backend Logs:** Check Uvicorn console output
- **Database Queries:** View in Supabase dashboard
- **Android Logs:** `adb logcat | grep flutter`

---

## 📄 License

Currently under internal development. License will be defined before public release.

---

**Built with ❤️ by Team Error404**


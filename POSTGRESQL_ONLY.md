# AutoTaskTracker - PostgreSQL Architecture

**AutoTaskTracker is now PostgreSQL-only.** SQLite support has been completely removed after successful data migration.

## 🏗️ Architecture Overview

### **Database Backend**
- **PostgreSQL**: Single, production-ready database backend
- **Connection**: localhost:5433/autotasktracker  
- **Pool Management**: ThreadedConnectionPool with lazy initialization
- **Schema**: Pensieve-compatible entities and metadata_entries tables

### **Core Components**
- `autotasktracker/core/database.py`: PostgreSQL-only DatabaseManager
- `autotasktracker/config.py`: Simplified PostgreSQL configuration
- `autotasktracker/dashboards/`: All dashboards use PostgreSQL

## 🚀 Quick Start

### **Database Connection**
```bash
# Set PostgreSQL connection (if different from default)
export AUTOTASK_DATABASE_URL=postgresql://postgres:password@localhost:5433/autotasktracker
```

### **Launch Commands**
```bash
# Main dashboards
python autotasktracker.py dashboard        # Task Board
python autotasktracker.py analytics        # Analytics
python autotasktracker.py timetracker      # Time Tracker

# Alternative launcher
python autotask.py dashboard               # Task Board
python autotask.py analytics               # Analytics  
python autotask.py timetracker             # Time Tracker
```

### **Database Management**
```bash
python db_manager.py status               # Connection status
python db_manager.py test                 # Test connection
python db_manager.py stats                # Database statistics
python autotask.py test                   # Quick connection test
```

## 📊 Current Data

**Successfully migrated from SQLite:**
- **6,606 entities** (screenshots)
- **54,245 metadata entries** (OCR, window data, etc.)
- **1,783 screenshots with OCR data**
- **Complete file paths and timestamps**

## 🔧 Configuration

### **Environment Variables**
```bash
AUTOTASK_DATABASE_URL=postgresql://postgres:password@localhost:5433/autotasktracker
AUTOTASK_POSTGRESQL_URL=postgresql://postgres:password@localhost:5433/autotasktracker
```

### **Default Configuration**
- **Host**: localhost
- **Port**: 5433  
- **Database**: autotasktracker
- **User**: postgres
- **Connection Pool**: 1-10 connections

## 💻 Development

### **Database Manager Usage**
```python
from autotasktracker.core.database import DatabaseManager

# PostgreSQL-only manager
db = DatabaseManager()

# Get connection
with db.get_connection() as conn:
    # Use PostgreSQL connection
    pass

# Query helpers
entities = db.get_entity_count()
metadata = db.get_metadata_count()
tasks_df = db.fetch_tasks(limit=100)
```

### **Configuration Usage**
```python
from autotasktracker.config import get_config

config = get_config()
db_url = config.get_database_url()      # PostgreSQL URL
backend = config.get_database_backend() # Returns "postgresql"
connected = config.test_database_connection()
```

## 🗂️ File Structure

```
autotasktracker/
├── core/
│   └── database.py           # PostgreSQL-only DatabaseManager
├── config.py                 # Simplified PostgreSQL configuration
├── dashboards/               # All dashboards use PostgreSQL
│   ├── task_board.py         # Main dashboard
│   ├── analytics.py          # Analytics dashboard
│   ├── timetracker.py        # Time tracker
│   └── components/           # UI components
└── pensieve/                 # Pensieve integration
```

## 🚫 Removed Components

**The following SQLite-related components have been removed:**
- SQLite imports and dependencies
- Multi-backend configuration (DATABASE_BACKEND, SQLITE_PATH)
- Backend switching functionality (`switch_database_backend()`)
- SimpleDatabaseManager (SQLite support)
- Migration tools (`migrate_data.py`)
- Temporary PostgreSQL dashboards (`postgres_*.py`)
- Adaptive dashboard (`adaptive_task_board.py`)

## ✅ Benefits of PostgreSQL-Only Architecture

1. **Simplified Codebase**: No dual-backend complexity
2. **Production Ready**: Robust PostgreSQL connection pooling
3. **Better Performance**: Optimized for PostgreSQL features
4. **Reduced Dependencies**: No SQLite imports or fallbacks
5. **Cleaner Configuration**: Single database backend
6. **Maintainability**: Less code paths to test and maintain

---

**AutoTaskTracker is now fully PostgreSQL-native with simplified, production-ready architecture.**
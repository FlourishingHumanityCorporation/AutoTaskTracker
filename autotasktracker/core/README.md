# 🏗️ Core Module Documentation

The core module provides the foundational components that all other AutoTaskTracker modules depend on.

## 📁 Module Contents

```
autotasktracker/core/
├── __init__.py                # Module initialization
├── database.py               # Database connection and management
├── task_extractor.py         # Basic task extraction logic
├── categorizer.py            # Activity categorization
└── vlm_integration.py        # [LEGACY] VLM integration (moved to ai/)
```

## 🔗 Component Relationships

```
DatabaseManager  ←──── TaskExtractor  ←──── ActivityCategorizer
      ↑                      ↑                      ↑
      │                      │                      │
   SQLite DB            Window Titles          Task + Context
      │                      │                      │
      └── Memos/Pensieve     └── Screenshots       └── Categories
```

## 📊 database.py

### **Purpose**
Manages connections to the Memos/Pensieve SQLite database and provides data access methods.

### **Key Class: DatabaseManager**

#### **Initialization**
```python
from autotasktracker.core import DatabaseManager

# Uses default database path
db_manager = DatabaseManager()

# Or specify custom path
db_manager = DatabaseManager(db_path="/custom/path/database.db")
```

#### **Core Methods**
```python
# Get database connection (context manager)
with db_manager.get_connection() as conn:
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM entities LIMIT 5")
    results = cursor.fetchall()

# Get database path
path = db_manager.db_path
```

#### **Database Schema Context**
The DatabaseManager connects to a Memos/Pensieve database with these key tables:

- **`entities`**: Screenshot files and metadata
  - `id`, `filepath`, `filename`, `created_at`, `file_type_group`
  
- **`metadata_entries`**: AI processing results
  - `entity_id`, `key`, `value`, `source_type`, `data_type`
  - Keys: `'ocr_result'`, `'vlm_result'`, `'active_window'`, `'embedding'`

#### **Usage Patterns**
```python
# Load recent screenshots with metadata
query = """
SELECT e.*, me.value as ocr_text 
FROM entities e 
LEFT JOIN metadata_entries me ON e.id = me.entity_id 
WHERE e.file_type_group = 'image' 
AND me.key = 'ocr_result'
ORDER BY e.created_at DESC 
LIMIT 10
"""

with db_manager.get_connection() as conn:
    df = pd.read_sql_query(query, conn)
```

---

## 🎯 task_extractor.py

### **Purpose**
Extracts human-readable task names from window titles using pattern matching.

### **Key Class: TaskExtractor**

#### **Initialization**
```python
from autotasktracker.core import TaskExtractor

extractor = TaskExtractor()
```

#### **Core Method**
```python
# Extract task from window title
task = extractor.extract_task("Claude Code - VS Code")
# Returns: "Claude Code"

task = extractor.extract_task("AutoTaskTracker — ✳ Core Methods — claude")  
# Returns: "AI Coding: AutoTaskTracker"
```

#### **Pattern Matching Logic**
The TaskExtractor uses several strategies:

1. **Application-specific patterns**:
   - VS Code: Extracts project/file names
   - Web browsers: Extracts page titles
   - Terminal: Extracts command contexts

2. **Keyword-based enhancement**:
   - Detects coding contexts ("claude", "github", "python")
   - Identifies productivity tools ("notion", "slack", "zoom")
   - Recognizes development activities

3. **Fallback handling**:
   - Returns cleaned window title if no pattern matches
   - Handles edge cases and empty titles

#### **Example Patterns**
```python
# Coding contexts
"VS Code - project.py" → "Python Development"
"GitHub - username/repo" → "GitHub: repo"
"Claude Code" → "Claude Code"

# Productivity contexts  
"Slack - #channel" → "Slack Communication"
"Zoom Meeting" → "Video Conference"
"Notion - Page Title" → "Notion: Page Title"

# Fallback
"Unknown Application" → "Unknown Application"
```

---

## 🏷️ categorizer.py

### **Purpose**
Classifies activities into standardized categories with emoji icons.

### **Key Class: ActivityCategorizer**

#### **Static Method Usage**
```python
from autotasktracker.core import ActivityCategorizer

# Categorize with window title only
category = ActivityCategorizer.categorize("VS Code - main.py", "")
# Returns: "🧑‍💻 Coding"

# Categorize with additional OCR context
category = ActivityCategorizer.categorize(
    window_title="Chrome - Gmail", 
    ocr_text="Compose message Send"
)
# Returns: "📧 Communication"
```

#### **Category System**
The categorizer uses a hierarchical keyword-based system:

1. **Primary Categories** (with emojis):
   - 🧑‍💻 **Coding**: Development, programming, version control
   - 📧 **Communication**: Email, chat, messaging, video calls
   - 📚 **Research**: Reading, documentation, learning
   - 📊 **Productivity**: Task management, planning, organization
   - 🎨 **Design**: Graphics, UI/UX, creative tools
   - 🤖 **AI Tools**: AI assistants, automation, ML tools
   - 🌐 **Web Browsing**: General web activities
   - ⚙️ **System**: OS, settings, maintenance
   - 🎮 **Entertainment**: Games, media, leisure
   - 📄 **Documents**: Word processing, spreadsheets

2. **Keyword Mapping**:
   ```python
   CODING_KEYWORDS = ["code", "github", "python", "javascript", "development"]
   COMMUNICATION_KEYWORDS = ["slack", "zoom", "email", "teams", "discord"] 
   AI_KEYWORDS = ["claude", "chatgpt", "copilot", "openai"]
   # ... etc
   ```

3. **OCR Enhancement**:
   - Uses OCR text to provide additional context
   - Helps distinguish similar applications used for different purposes
   - Improves accuracy for ambiguous window titles

#### **Classification Logic**
```python
def categorize(window_title: str, ocr_text: str = "") -> str:
    # 1. Combine window title and OCR text
    combined_text = f"{window_title} {ocr_text}".lower()
    
    # 2. Check keywords in priority order
    if any(keyword in combined_text for keyword in CODING_KEYWORDS):
        return "🧑‍💻 Coding"
    elif any(keyword in combined_text for keyword in AI_KEYWORDS):
        return "🤖 AI Tools"
    # ... continue through categories
    
    # 3. Default fallback
    return "🌐 Web Browsing"
```

---

## 🔗 Module Integration

### **Typical Usage Pattern**
```python
from autotasktracker.core import DatabaseManager, TaskExtractor, ActivityCategorizer

# Initialize components
db_manager = DatabaseManager()
task_extractor = TaskExtractor()

# Load screenshot data
with db_manager.get_connection() as conn:
    cursor = conn.cursor()
    cursor.execute("""
        SELECT me_window.value as window_title, 
               me_ocr.value as ocr_text
        FROM metadata_entries me_window 
        LEFT JOIN metadata_entries me_ocr ON me_window.entity_id = me_ocr.entity_id
        WHERE me_window.key = 'active_window' 
        AND me_ocr.key = 'ocr_result'
        LIMIT 1
    """)
    row = cursor.fetchone()

# Process data
if row:
    window_title, ocr_text = row
    
    # Extract task
    task = task_extractor.extract_task(window_title)
    
    # Categorize activity  
    category = ActivityCategorizer.categorize(window_title, ocr_text or "")
    
    print(f"Task: {task}")
    print(f"Category: {category}")
```

### **Dependencies**
- **External**: SQLite database (Memos/Pensieve)
- **Python libraries**: `sqlite3`, `os`, `re` (standard library)
- **Internal**: None (this is the foundation module)

### **Used By**
- `autotasktracker.ai.*` - AI enhancement modules
- `autotasktracker.dashboards.*` - All dashboard interfaces
- `autotasktracker.comparison.*` - Pipeline comparison tools

## 🎯 Key Design Principles

1. **Simplicity**: Core functionality with minimal dependencies
2. **Reliability**: Robust pattern matching with fallbacks
3. **Extensibility**: Easy to add new patterns and categories
4. **Performance**: Fast processing suitable for real-time use
5. **Independence**: No AI dependencies required for basic functionality

This core module provides the stable foundation that enables all advanced AutoTaskTracker features while remaining simple and reliable on its own.
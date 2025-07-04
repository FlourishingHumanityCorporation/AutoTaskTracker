# AutoTaskTracker - Core Methods Detailed Implementation

## Table of Contents
1. [DatabaseManager Core Methods](#databasemanager-core-methods)
2. [TaskExtractor Implementation](#taskextractor-implementation)
3. [ActivityCategorizer Logic](#activitycategorizer-logic)
4. [AI Features Implementation](#ai-features-implementation)
5. [Data Flow Analysis](#data-flow-analysis)
6. [Performance Considerations](#performance-considerations)

## DatabaseManager Core Methods

### 1. Connection Management (`get_connection`)

```python
@contextmanager
def get_connection(self, readonly: bool = True):
    conn = None
    try:
        if readonly:
            conn = sqlite3.connect(f'file:{self.db_path}?mode=ro', uri=True)
        else:
            conn = sqlite3.connect(self.db_path)
        
        conn.row_factory = sqlite3.Row
        yield conn
    except sqlite3.OperationalError as e:
        logger.error(f"Database connection error: {e}")
        raise
    finally:
        if conn:
            conn.close()
```

**How it works:**
1. **Context Manager Pattern**: Uses `@contextmanager` decorator for automatic resource cleanup
2. **Read-Only Safety**: Default `readonly=True` prevents accidental data modification
3. **URI Mode**: Uses SQLite URI syntax for read-only connections (`file:path?mode=ro`)
4. **Row Factory**: Sets `sqlite3.Row` for dictionary-like access to query results
5. **Error Handling**: Catches connection errors and logs them before re-raising
6. **Automatic Cleanup**: `finally` block ensures connections are always closed

**Data Flow:**
```
Request → URI Construction → Connection → Row Factory Setup → Yield → Cleanup
```

### 2. Task Fetching (`fetch_tasks`)

```python
def fetch_tasks(self, start_date=None, end_date=None, limit=100, offset=0) -> pd.DataFrame:
    query = """
    SELECT
    # ... (truncated - see source files for full implementation)
```

**How it works:**
1. **Base Query Construction**: Joins entities with metadata_entries for OCR and window data
2. **Dynamic Filtering**: Conditionally adds WHERE clauses based on parameters
3. **Parameter Binding**: Uses parameterized queries to prevent SQL injection
4. **CRITICAL TIMEZONE CHANGE**: Now performs direct UTC-to-UTC comparison in WHERE clauses, but still converts to localtime in SELECT for display
5. **Pagination**: Implements LIMIT/OFFSET for large datasets
6. **Error Recovery**: Returns empty DataFrame on database errors
7. **Pandas Integration**: Uses `pd.read_sql_query()` for direct DataFrame creation

**Important Implementation Detail:**
The method has been updated to fix timezone handling inconsistencies:
- **WHERE clauses** now compare `e.created_at` (UTC) directly with UTC parameters
- **SELECT clause** still converts to localtime for display: `datetime(e.created_at, 'localtime')`
- This prevents timezone double-conversion bugs that could cause missing or duplicate results

**Query Evolution:**
```sql
-- Base query
SELECT e.id, ... FROM entities e LEFT JOIN metadata_entries ...

-- With date filter
... WHERE e.file_type_group = 'image' AND datetime(e.created_at, 'localtime') >= ?

-- With pagination
... ORDER BY e.created_at DESC LIMIT ? OFFSET ?
```

### 3. Time-Based Filtering (`fetch_tasks_by_time_filter`)

```python
def fetch_tasks_by_time_filter(self, time_filter: str, limit: int = 100) -> pd.DataFrame:
    now = datetime.now()
    
    time_filters = {
        "Last 15 Minutes": now - timedelta(minutes=15),
        "Last Hour": now - timedelta(hours=1),
        "Today": now.replace(hour=0, minute=0, second=0, microsecond=0),
        "Last 24 Hours": now - timedelta(days=1),
        "Last 7 Days": now - timedelta(days=7),
        "All Time": datetime(2000, 1, 1)
    }
    
    start_date = time_filters.get(time_filter, datetime(2000, 1, 1))
    return self.fetch_tasks(start_date=start_date, limit=limit)
```

**How it works:**
1. **Predefined Filters**: Maps human-readable strings to datetime calculations
2. **Dynamic Calculation**: Calculates relative times based on current time
3. **Special Cases**: 
   - "Today" uses `replace()` to get midnight of current day
   - "All Time" uses arbitrary old date (2000-01-01)
4. **Delegation Pattern**: Reuses `fetch_tasks()` method for actual query execution
5. **Default Fallback**: Uses "All Time" if invalid filter provided

### 4. Activity Summary (`get_activity_summary`)

```python
def get_activity_summary(self, date: Optional[datetime] = None) -> Dict[str, Any]:
    if date is None:
        date = datetime.now()
    # ... (truncated - see source files)
```

**How it works:**
1. **Default Date**: Uses current date if none provided
2. **Composite Data**: Combines count and time range information
3. **Aggregation Query**: Uses MIN/MAX to find activity span
4. **Date Filtering**: Uses SQLite's `date()` function for date-only comparison
5. **Duration Calculation**: Computes hours using `total_seconds() / 3600`
6. **Safe Division**: Uses `max(duration_hours, 1)` to prevent division by zero
7. **Robust Error Handling**: Returns partial data even if time range query fails

## TaskExtractor Implementation

### 1. Main Extraction Logic (`extract_task`)

```python
def extract_task(self, window_title: str, ocr_text: Optional[str] = None) -> Optional[str]:
    if not window_title:
        return None
    # ... (truncated - see source files)
```

**How it works:**
1. **Input Validation**: Early return if no window title provided
2. **Data Cleaning**: Strips whitespace from input
3. **UPDATED JSON Handling**: Attempts to parse JSON-formatted window data from Pensieve with specific exception handling for `(json.JSONDecodeError, TypeError, KeyError)`
4. **Pattern Matching**: Iterates through application-specific regex patterns
5. **Case Sensitivity**: Uses case-insensitive matching for both detection and extraction
6. **Quality Check**: Ensures extracted task differs from original title
7. **Fallback Strategy**: Uses generic extraction if no patterns match

**Pattern Matching Flow:**
```
Window Title → JSON Parse → App Detection → Pattern Match → Extract → Validate → Return
```

### 2. Terminal Task Extraction (`_extract_terminal_task`)

```python
def _extract_terminal_task(self, match) -> str:
    parts = match.groups()
    if len(parts) >= 2 and parts[1]:
    # ... (truncated - see source files)
```

**How it works:**
1. **Group Extraction**: Uses regex match groups to separate directory and command
2. **Hierarchical Detection**: Checks for specific tools in priority order
3. **Git Detection**: Special handling for version control operations
4. **Tool Recognition**: Recognizes common development tools (npm, pip, cargo, etc.)
5. **Path Recognition**: Identifies directory navigation patterns
6. **Fallback Naming**: Provides meaningful default for unrecognized commands

**Decision Tree:**
```
Terminal Match → Git? → Tool Match? → Path Pattern? → Generic Terminal
```

### 3. Browser Task Extraction (`_extract_browser_task`)

```python
def _extract_browser_task(self, match) -> str:
    page_title = match.group(1).strip() if match.group(1) else ""
    
    # ... (truncated - see source files)
```

**How it works:**
1. **Safe Extraction**: Handles cases where regex groups might be None
2. **Domain-Specific Logic**: Uses specialized extractors for known websites
3. **Title Cleaning**: Removes common browser/site suffixes
4. **Length Management**: Truncates long titles with ellipsis
5. **Readable Format**: Prefixes with "Reading:" for clarity

### 4. GitHub-Specific Extraction (`_extract_github_task`)

```python
def _extract_github_task(self, title: str) -> str:
    if '/pull/' in title:
        pr_match = re.search(r'#(\d+)', title)
        if pr_match:
            return f"Reviewing PR #{pr_match.group(1)}"
        return "Reviewing GitHub PR"
    elif '/issues/' in title:
        return "GitHub: Issue tracking"
    elif '/commits/' in title:
        return "GitHub: Reviewing commits"
    elif re.search(r'[\w-]+/[\w-]+', title):
        repo_match = re.search(r'([\w-]+/[\w-]+)', title)
        if repo_match:
            return f"GitHub: {repo_match.group(1)}"
    return "Browsing GitHub"
```

**How it works:**
1. **URL Pattern Recognition**: Detects GitHub sections by URL fragments
2. **PR Number Extraction**: Uses regex to extract pull request numbers
3. **Activity Classification**: Maps URL patterns to specific activities
4. **Repository Identification**: Extracts owner/repo format when possible
5. **Hierarchical Matching**: Checks specific patterns before generic ones

## ActivityCategorizer Logic

### 1. Smart Categorization (`categorize`)

```python
@classmethod
def categorize(cls, window_title: Optional[str], ocr_text: Optional[str] = None) -> str:
    if not window_title:
    # ... (truncated - see source files)
```

**How it works:**
1. **Null Safety**: Returns default category for empty input
2. **Case Normalization**: Converts to lowercase for consistent matching
3. **Priority-Based Classification**: 
   - File extensions (highest priority)
   - Development indicators
   - Context-aware AI tool classification
   - General keyword matching
4. **Overlap Resolution**: Specific patterns override general ones
5. **Context Awareness**: AI tools categorized as coding when in development context

**Classification Hierarchy:**
```
File Extensions → Development → AI Context → General Keywords → Default
```

### 2. Window Title Extraction (`extract_window_title`)

```python
def extract_window_title(active_window_data: str) -> Optional[str]:
    if not active_window_data:
        return None
    # ... (truncated - see source files)
```

**How it works:**
1. **Flexible Input**: Handles both string and dict inputs
2. **JSON Parsing**: Attempts to parse JSON-formatted window data
3. **Safe Extraction**: Checks for dict type and 'title' key existence
4. **Graceful Fallback**: Returns string representation if JSON parsing fails
5. **Error Tolerance**: Catches JSON and type errors without crashing

## AI Features Implementation

### 1. Semantic Search (`semantic_search`)

```python
def semantic_search(self, query_entity_id: int, limit: int = 10, 
                   similarity_threshold: float = 0.7,
                   time_window_hours: Optional[int] = None) -> List[Dict]:
    # ... (truncated - see source files)
```

**How it works:**
1. **Embedding Validation**: Ensures query entity has an embedding
2. **Comprehensive Query**: Joins all relevant metadata tables
3. **Self-Exclusion**: Excludes the query entity from results (`e.id != ?`)
4. **Time Filtering**: Optional time window for recent results
5. **In-Memory Processing**: Loads candidates and calculates similarity in Python
6. **Threshold Filtering**: Only returns results above similarity threshold
7. **Ranking**: Sorts results by similarity score in descending order
8. **Limit Enforcement**: Returns top N results after ranking

**Process Flow:**
```
Query Entity → Get Embedding → Database Query → Parse Embeddings → Calculate Similarity → Filter → Sort → Limit
```

### 2. Cosine Similarity Calculation (`cosine_similarity`)

```python
def cosine_similarity(self, embedding1: np.ndarray, embedding2: np.ndarray) -> float:
    # Normalize embeddings
    norm1 = np.linalg.norm(embedding1)
    norm2 = np.linalg.norm(embedding2)
    
    if norm1 == 0 or norm2 == 0:
        return 0.0
    
    # Calculate cosine similarity
    return np.dot(embedding1, embedding2) / (norm1 * norm2)
```

**How it works:**
1. **Vector Normalization**: Calculates L2 norm of both vectors
2. **Zero Vector Handling**: Returns 0.0 for zero-length vectors
3. **Dot Product**: Computes dot product of normalized vectors
4. **Mathematical Formula**: Implements cosine similarity: cos(θ) = (A·B)/(||A||×||B||)
5. **Range**: Returns values between -1 (opposite) to 1 (identical)

**Mathematical Background:**
```
Cosine Similarity = (A · B) / (||A|| × ||B||)
where A · B is dot product and ||A|| is vector magnitude
```

### 3. Task Grouping (`find_similar_task_groups`)

```python
def find_similar_task_groups(self, min_group_size: int = 3,
                           similarity_threshold: float = 0.8,
                           time_window_hours: int = 24) -> List[List[Dict]]:
    # ... (truncated - see source files)
```

**How it works:**
1. **Batch Processing**: Loads all embeddings in time window
2. **Data Validation**: Filters out entities without valid embeddings
3. **Matrix Operations**: Uses NumPy for efficient similarity calculations
4. **Batch Normalization**: Normalizes all embeddings at once
5. **Similarity Matrix**: Computes pairwise similarities using matrix multiplication
6. **Greedy Grouping**: Iteratively forms groups while tracking used entities
7. **Size Filtering**: Only creates groups meeting minimum size requirement
8. **Anti-Overlap**: Ensures each entity appears in at most one group

**Matrix Computation:**
```
Embeddings (n×768) → Normalize → Similarity Matrix (n×n) → Group Formation
```

## Data Flow Analysis

### Overall System Flow

```
Screenshots → Pensieve → SQLite Database → AutoTaskTracker → Dashboards
    ↓             ↓           ↓                ↓              ↓
Capture        OCR/VLM    Metadata        Analysis       Visualization
```

### Core Method Interaction

```
DatabaseManager.fetch_tasks() / fetch_tasks_with_ai()
    ↓
TaskExtractor.extract_task() → AIEnhancedTaskExtractor.extract_enhanced_task()
    ↓
ActivityCategorizer.categorize()
    ↓
Dashboard Display (with AI confidence indicators)
```

### AI Enhancement Flow

```
Base Task → OCR Enhancement → VLM Analysis → Embedding Search → Enhanced Task
     ↓           ↓                ↓              ↓               ↓
Window Title → Quality Score → Visual Context → Similar Tasks → Confidence Score
```

### Dashboard Integration Pattern

```python
# New pattern with AI features
if AI_FEATURES_AVAILABLE and use_ai_features:
    tasks_df = db_manager.fetch_tasks_with_ai()
    ai_extractor = AIEnhancedTaskExtractor(db_manager.db_path)
    enhanced_task = ai_extractor.extract_enhanced_task(...)
    # Display with confidence indicators and similar tasks
else:
    tasks_df = db_manager.fetch_tasks_by_time_filter()
    # Standard display
```

## Performance Considerations

### Database Optimization
- **Connection Pooling**: Context managers ensure proper cleanup
- **Read-Only Connections**: Default to read-only for safety and performance
- **Parameterized Queries**: Prevent SQL injection and enable query plan caching
- **Pagination**: LIMIT/OFFSET for large datasets
- **Indexing**: Relies on Pensieve's database indexes

### Memory Management
- **Streaming Results**: Uses pandas DataFrame for efficient data handling
- **Limited Embeddings**: Processes embeddings in batches
- **Connection Cleanup**: Automatic resource management with context managers

### AI Processing
- **Lazy Loading**: AI features loaded only when needed
- **Threshold Filtering**: Reduces computation by filtering early
- **Vectorized Operations**: NumPy for efficient similarity calculations
- **Caching**: Results cached at application level (Streamlit)

### Error Handling Strategy
- **Graceful Degradation**: Methods return safe defaults on errors
- **Logging**: Comprehensive error logging for debugging
- **Fallback Modes**: Generic extraction when specific patterns fail
- **Input Validation**: Early validation prevents downstream errors

---

This detailed documentation provides a complete understanding of how each core method works, their implementation details, data flow patterns, and performance characteristics. The methods are designed for reliability, maintainability, and extensibility while handling real-world edge cases gracefully.
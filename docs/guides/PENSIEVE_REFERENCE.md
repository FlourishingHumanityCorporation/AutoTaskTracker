# Pensieve Reference Guide

## Overview

**Pensieve** (also known as **memos**) is an open-source screenshot capture and processing system designed for passive data collection and analysis. It provides automated screenshot capture, OCR text extraction, and a flexible metadata storage system that serves as the foundation for AI-powered productivity tools.

## Core Functionality

### Screenshot Capture System
- **Automated Capture**: Continuous screenshot capture at configurable intervals
- **Window Detection**: Captures active window titles and application context
- **Privacy Controls**: Configurable capture rules and exclusion patterns
- **Cross-Platform**: Supports macOS, Linux, and Windows

### OCR Processing
- **Built-in OCR Engine**: Tesseract-based text extraction from screenshots
- **Plugin Architecture**: `builtin_ocr` plugin for extensible OCR processing
- **Text Indexing**: Full-text search capabilities across captured content
- **Language Support**: Multi-language OCR recognition

### Data Storage
- **SQLite Backend**: Default lightweight database storage (`~/.memos/database.db`)
- **PostgreSQL Support**: Enterprise-scale backend for large datasets
- **Metadata System**: Flexible key-value metadata storage via `metadata_entries` table
- **File Management**: Organized screenshot storage with automatic cleanup

## Architecture

### Core Components

**Database Schema**:
```sql
-- Core entities table
entities (
    id INTEGER PRIMARY KEY,
    filepath TEXT,
    created_at TIMESTAMP,
    updated_at TIMESTAMP
)

-- Extensible metadata system
metadata_entries (
    id INTEGER PRIMARY KEY,
    entity_id INTEGER,
    key TEXT,
    value TEXT,
    created_at TIMESTAMP
)
```

**File System Structure**:
```
~/.memos/
├── database.db          # SQLite database
├── screenshots/         # Screenshot files
├── config/             # Configuration files
└── plugins/            # Plugin directory
```

### Service Architecture

**Background Services**:
- Screenshot capture daemon
- OCR processing queue
- File cleanup scheduler
- Web API server (port 8839)

**Plugin System**:
- `builtin_ocr` - Text extraction
- `builtin_vlm` - Visual language model processing
- Custom plugin support for extensibility

## Command Line Interface

### Basic Commands
```bash
# Initialize Pensieve
memos init

# Service management
memos start          # Start background services
memos stop           # Stop all services
memos ps             # Check service status
memos enable         # Enable automatic startup
memos disable        # Disable automatic startup

# Data operations
memos scan           # Scan for new screenshots
memos reindex        # Rebuild search index
memos config         # View/edit configuration
```

### Advanced Commands
```bash
# Data management
memos export         # Export captured data
memos import         # Import data from backup
memos cleanup        # Remove old files
memos tag            # Tag management

# API server
memos serve          # Start REST API server
```

## REST API

### Base URL
```
http://localhost:8839/api/
```

### Core Endpoints
```http
GET /api/screenshots              # List recent screenshots
GET /api/screenshots/{id}         # Get screenshot details
GET /api/metadata/{id}/{key}      # Get metadata value
POST /api/metadata/{id}           # Store metadata
GET /api/search?q={query}         # Search screenshots
GET /api/health                   # Service health check
```

### Response Format
```json
{
  "status": "success",
  "data": {
    "id": 12345,
    "filepath": "/path/to/screenshot.png",
    "created_at": "2025-01-05T10:30:00Z",
    "metadata": {
      "ocr_result": "extracted text",
      "active_window": "Application Name"
    }
  }
}
```

## Configuration

### Core Settings
```yaml
# ~/.memos/config.yaml
capture:
  interval: 30              # Screenshot interval (seconds)
  enabled: true             # Enable/disable capture
  
ocr:
  enabled: true             # Enable OCR processing
  language: "eng"           # OCR language
  
storage:
  retention_days: 90        # File retention period
  max_storage_gb: 10        # Storage limit
  
api:
  port: 8839               # API server port
  enabled: true            # Enable API server
```

### Privacy Controls
```yaml
privacy:
  exclude_apps:            # Applications to exclude
    - "1Password"
    - "Keychain Access"
  exclude_patterns:        # Text patterns to exclude
    - "password"
    - "ssn:"
  blur_sensitive: true     # Blur sensitive content
```

## Plugin Development

### Plugin Structure
```python
# Example plugin
class CustomPlugin:
    def __init__(self):
        self.name = "custom_processor"
        
    def process(self, entity_id: int, filepath: str) -> dict:
        """Process screenshot and return metadata"""
        # Custom processing logic
        return {
            "custom_key": "processed_value"
        }
        
    def configure(self, config: dict):
        """Plugin configuration"""
        pass
```

### Plugin Registration
```bash
# Install plugin
memos plugin install /path/to/plugin.py

# Enable plugin
memos plugin enable custom_processor

# List plugins
memos plugin list
```

## Use Cases

### Productivity Tracking
- Automatic time tracking from window titles
- Task extraction from captured content
- Activity pattern analysis
- Focus time measurement

### Research and Knowledge Management
- Automatic capture of research content
- Full-text search across browsing history
- Reference material organization
- Knowledge graph construction

### Security and Compliance
- User activity monitoring
- Data loss prevention
- Compliance reporting
- Incident investigation

### AI and Machine Learning
- Training data collection for productivity AI
- Screenshot-based behavior analysis
- Workflow optimization
- Automated task classification

## Performance and Scaling

### Storage Requirements
- **SQLite Mode**: < 100K screenshots (< 1GB)
- **PostgreSQL Mode**: < 1M screenshots (< 100GB)
- **Enterprise Mode**: Unlimited with proper infrastructure

### Processing Performance
- **OCR Speed**: ~1 second per screenshot
- **Search Performance**: Sub-second full-text search
- **API Response**: < 100ms for standard queries
- **Batch Processing**: 1000+ screenshots/hour

### Optimization Tips
```bash
# Enable WAL mode for better concurrency
memos config set database.journal_mode WAL

# Increase cache size for better performance
memos config set database.cache_size 10000

# Enable memory-mapped I/O
memos config set database.mmap_size 268435456
```

## Security and Privacy

### Data Protection
- **Local Storage**: All data remains on local machine
- **Encryption**: Optional at-rest encryption
- **Access Control**: File-system level permissions
- **Network Isolation**: No cloud services required

### Privacy Features
- **Content Filtering**: Exclude sensitive applications
- **Pattern Matching**: Filter sensitive text patterns
- **Selective Capture**: Configurable capture rules
- **Data Retention**: Automatic cleanup policies

## Integration Patterns

### Direct Database Access
```python
import sqlite3

conn = sqlite3.connect("~/.memos/database.db")
cursor = conn.cursor()
cursor.execute("SELECT * FROM entities LIMIT 10")
results = cursor.fetchall()
```

### REST API Integration
```python
import requests

# Get recent screenshots
response = requests.get("http://localhost:8839/api/screenshots")
screenshots = response.json()["data"]

# Search content
response = requests.get("http://localhost:8839/api/search?q=python")
results = response.json()["data"]
```

### Plugin Integration
```python
# Custom processing via plugin
from memos.plugins import register_plugin

@register_plugin("task_extractor")
def extract_tasks(entity_id, filepath):
    # Custom task extraction logic
    return {"tasks": extracted_tasks}
```

## Troubleshooting

### Common Issues

**Service Not Starting**:
```bash
# Check service status
memos ps

# Check logs
tail -f ~/.memos/logs/service.log

# Restart services
memos stop && memos start
```

**OCR Not Working**:
```bash
# Install Tesseract
brew install tesseract  # macOS
sudo apt install tesseract-ocr  # Ubuntu

# Test OCR
memos scan --test-ocr
```

**Database Issues**:
```bash
# Check database integrity
memos config database.integrity_check

# Rebuild index
memos reindex

# Backup database
cp ~/.memos/database.db ~/.memos/database.backup.db
```

### Performance Issues
```bash
# Clean old files
memos cleanup --days 30

# Optimize database
memos config database.vacuum

# Check disk usage
du -sh ~/.memos/
```

## External Resources

- **Official Repository**: [github.com/arkohut/memos](https://github.com/arkohut/memos)
- **Documentation**: Official docs and API reference
- **Community**: User forums and plugin sharing
- **Support**: Issue tracking and bug reports

## Version Information

This reference covers Pensieve/memos core functionality. Specific version features and API changes should be verified against the official documentation for your installed version.

---

*This document serves as a general reference for understanding Pensieve/memos as a standalone system, independent of any specific integration or application built on top of it.*
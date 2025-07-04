# Pensieve/memos Deep Integration Plan

## Executive Summary

AutoTaskTracker currently uses only ~20% of Pensieve's capabilities, primarily treating it as a passive SQLite database. This plan outlines a phased approach to leverage Pensieve's full feature set, reducing code duplication and improving maintainability.

## Current State Analysis

### What We Use
- Direct SQLite database access (`~/.memos/database.db`)
- Basic service commands (`memos start/stop/ps`)
- OCR text from `metadata_entries` table
- Screenshot metadata from `entities` table

### What We Don't Use
- REST API (`http://localhost:8839/api/*`)
- Plugin system
- Configuration management
- Advanced search capabilities
- PostgreSQL/pgvector support
- Web interface integration
- Processing pipeline hooks

### Duplicate Implementations
1. OCR enhancement (vs memos OCR plugins)
2. VLM processing (vs memos VLM plugins)
3. Embedding search (vs memos semantic search)
4. Screenshot caching (vs memos optimization)

## Integration Phases

### Phase 1: Configuration Synchronization (Week 1-2)

**Goal**: Read and respect memos configuration settings

**Implementation**:
```python
# autotasktracker/core/memos_config.py
import yaml
import os
from typing import Dict, Any

class MemosConfig:
    def __init__(self):
        self.config_path = os.path.expanduser('~/.memos/config.yaml')
        self._config = self._load_config()
    
    def _load_config(self) -> Dict[str, Any]:
        with open(self.config_path) as f:
            return yaml.safe_load(f)
    
    @property
    def screenshot_interval(self) -> int:
        return self._config.get('record_interval', 4)
    
    @property
    def vlm_endpoint(self) -> str:
        return self._config['vlm']['endpoint']
    
    @property
    def embedding_model(self) -> str:
        return self._config['embedding']['model']
```

**Tasks**:
- [ ] Create `memos_config.py` module
- [ ] Update `DatabaseManager` to use memos settings
- [ ] Sync processing intervals with memos config
- [ ] Update time tracking to use actual screenshot interval

### Phase 2: API Migration (Week 3-4)

**Goal**: Replace direct database access with REST API

**Architecture**:
```python
# autotasktracker/core/memos_client.py
from typing import List, Dict, Optional
import requests
from datetime import datetime

class MemosAPIClient:
    def __init__(self, base_url: str = 'http://localhost:8839'):
        self.base_url = base_url
        self.session = requests.Session()
    
    def get_frames(self, 
                   start_date: Optional[datetime] = None,
                   end_date: Optional[datetime] = None,
                   limit: int = 100) -> List[Dict]:
        """Get frames with metadata via API"""
        params = {
            'limit': limit,
            'include_metadata': True
        }
        if start_date:
            params['start_date'] = start_date.isoformat()
        if end_date:
            params['end_date'] = end_date.isoformat()
            
        response = self.session.get(
            f'{self.base_url}/api/frames',
            params=params
        )
        response.raise_for_status()
        return response.json()
    
    def search(self, 
               query: str,
               search_type: str = 'semantic',
               limit: int = 50) -> List[Dict]:
        """Use memos search capabilities"""
        response = self.session.post(
            f'{self.base_url}/api/search',
            json={
                'query': query,
                'type': search_type,
                'limit': limit
            }
        )
        response.raise_for_status()
        return response.json()
```

**Migration Strategy**:
1. Create API client alongside existing database code
2. Add feature flag for API vs database mode
3. Implement API methods matching current database queries
4. Gradually migrate each dashboard to use API
5. Remove direct database access once stable

### Phase 3: Plugin Development (Week 5-6)

**Goal**: Create AutoTaskTracker as a memos plugin

**Plugin Structure**:
```yaml
# ~/.memos/plugins/autotasktracker/plugin.yaml
name: autotasktracker
version: 1.0.0
description: AI-powered task extraction from screenshots
processors:
  - name: task_extractor
    type: metadata
    config:
      model: gpt-4
      categories:
        - Development
        - Communication
        - Research
  - name: task_aggregator
    type: post_processor
    schedule: "*/5 * * * *"
```

**Implementation**:
```python
# ~/.memos/plugins/autotasktracker/task_extractor.py
from memos.plugin import MetadataProcessor
from autotasktracker.ai import AITaskExtractor

class TaskExtractorPlugin(MetadataProcessor):
    def process(self, frame_data: dict) -> dict:
        """Extract tasks from frame data"""
        ocr_text = frame_data.get('metadata', {}).get('ocr_result', '')
        window_title = frame_data.get('metadata', {}).get('active_window', '')
        
        extractor = AITaskExtractor()
        tasks = extractor.extract_from_context(
            text=ocr_text,
            window_title=window_title
        )
        
        return {
            'tasks': tasks,
            'task_count': len(tasks),
            'categories': list(set(t['category'] for t in tasks))
        }
```

### Phase 4: Advanced Features (Week 7-8)

**Goal**: Leverage memos advanced capabilities

**Features to Implement**:

1. **Semantic Search Integration**
```python
# Use memos semantic search instead of custom implementation
def search_tasks(query: str) -> List[Task]:
    results = memos_client.search(
        query=query,
        search_type='semantic',
        filters={'metadata.tasks': {'$exists': True}}
    )
    return [Task.from_memos(r) for r in results]
```

2. **PostgreSQL/pgvector Support**
```python
# Add configuration for PostgreSQL
if memos_config.database_type == 'postgresql':
    connection_string = memos_config.database_url
    # Use pgvector for similarity search
```

3. **Web Interface Integration**
```python
# Add links to memos web interface
def get_screenshot_url(entity_id: str) -> str:
    return f"http://localhost:8839/frames/{entity_id}"
```

## Implementation Timeline

### Week 1-2: Configuration Phase
- Create memos configuration reader
- Update time tracking to use real intervals
- Add configuration documentation

### Week 3-4: API Migration
- Implement API client
- Add backwards compatibility layer
- Migrate one dashboard as proof of concept

### Week 5-6: Plugin Architecture
- Develop task extraction plugin
- Create plugin configuration
- Test plugin integration

### Week 7-8: Advanced Features
- Enable semantic search via API
- Add PostgreSQL support
- Integrate web interface links

## Testing Strategy

### Unit Tests
```python
# tests/unit/test_memos_integration.py
def test_memos_config_loading():
    config = MemosConfig()
    assert config.screenshot_interval > 0

def test_api_client_frames():
    client = MemosAPIClient()
    frames = client.get_frames(limit=10)
    assert len(frames) <= 10
```

### Integration Tests
```python
# tests/integration/test_memos_api.py
def test_api_vs_database_consistency():
    # Compare API results with direct DB queries
    api_frames = memos_client.get_frames()
    db_frames = database_manager.get_screenshots()
    assert len(api_frames) == len(db_frames)
```

## Backwards Compatibility

### Feature Flags
```python
# autotasktracker/config.py
MEMOS_INTEGRATION_MODE = os.getenv('MEMOS_MODE', 'database')  # 'database' or 'api'
USE_MEMOS_PLUGINS = os.getenv('USE_MEMOS_PLUGINS', 'false').lower() == 'true'
```

### Gradual Migration
1. Run both database and API in parallel
2. Compare results for consistency
3. Switch to API when confidence is high
4. Keep database fallback for 2 releases

## Success Metrics

1. **Code Reduction**: Remove 40% of duplicate code
2. **Performance**: API latency < 50ms for most queries
3. **Feature Coverage**: Use 80%+ of memos capabilities
4. **Maintainability**: Single source of truth for screenshot data
5. **User Experience**: No breaking changes during migration

## Risk Mitigation

### Risks
1. API performance vs direct database
2. Breaking changes in memos updates
3. Plugin API stability
4. User data migration

### Mitigations
1. Implement caching layer for API responses
2. Pin memos version during migration
3. Extensive testing before plugin deployment
4. Automated backup before migration

## Documentation Updates

### CLAUDE.md Additions
```markdown
## Pensieve/memos Integration

### Configuration
AutoTaskTracker now reads memos configuration from `~/.memos/config.yaml`

### API Usage
Use MemosAPIClient for all screenshot data access:
```python
from autotasktracker.core.memos_client import MemosAPIClient
client = MemosAPIClient()
frames = client.get_frames(limit=100)
```

### Plugin Development
AutoTaskTracker plugins go in `~/.memos/plugins/autotasktracker/`
```

## Next Steps

1. Review and approve this plan
2. Create implementation issues/tickets
3. Set up testing environment
4. Begin Phase 1 implementation
5. Weekly progress reviews

## Conclusion

This phased approach will transform AutoTaskTracker from a passive consumer of memos data to a fully integrated component of the memos ecosystem. The migration preserves backwards compatibility while unlocking significant new capabilities and reducing maintenance burden.
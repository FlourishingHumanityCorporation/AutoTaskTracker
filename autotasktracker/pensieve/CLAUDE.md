# Pensieve Integration Module Context

**Focus**: Pensieve/memos integration and API client management

## Module-Specific Rules

- **API-first approach**: Prefer Pensieve APIs over direct database access
- **Graceful fallback**: Always provide SQLite fallback when API unavailable
- **Health monitoring**: Continuously monitor Pensieve service health
- **Connection pooling**: Use proper connection management
- **Error handling**: Distinguish between temporary and permanent failures

## Integration Architecture

**Core Integration:**
- `api_client.py` - Primary Pensieve API client with health checks
- `config_reader.py` - Read Pensieve configuration and settings
- `health_monitor.py` - Service health monitoring and reporting

**Advanced Features:**
- `webhook_client.py` - Real-time event processing via webhooks
- `search_coordinator.py` - Unified search across multiple methods
- `migration_automation.py` - PostgreSQL migration management
- `performance_optimizer.py` - Automated performance tuning

## API Integration Patterns

```python
# ✅ Correct: API-first with fallback
class PensieveAPIClient:
    def get_entities(self, limit=100):
        try:
            # Try API first
            if self.is_healthy():
                return self._fetch_via_api(limit)
        except PensieveAPIError as e:
            logger.warning(f"API failed: {e}, falling back to SQLite")
        
        # Fallback to direct database
        return self._fetch_via_sqlite(limit)
    
    def is_healthy(self):
        # Cache health checks to avoid overhead
        if self._last_health_check and time.time() - self._last_health_check < 30:
            return self._api_healthy
        
        try:
            response = requests.get(f"{self.base_url}/health", timeout=2)
            self._api_healthy = response.status_code == 200
        except Exception:
            self._api_healthy = False
        
        self._last_health_check = time.time()
        return self._api_healthy
```

## Service Discovery

- **Auto-detection**: Automatically detect Pensieve service availability
- **Configuration sync**: Keep AutoTaskTracker config in sync with Pensieve
- **Endpoint discovery**: Dynamically discover available API endpoints
- **Version compatibility**: Handle API version differences gracefully

## Performance Optimization

- **Connection caching**: Reuse HTTP connections where possible
- **Request batching**: Batch multiple requests when supported
- **Async operations**: Use async patterns for non-blocking operations
- **Memory efficiency**: Stream large datasets instead of loading all at once

## Error Recovery Patterns

```python
# ✅ Correct: Resilient error handling
@retry(max_attempts=3, backoff=exponential_backoff)
def pensieve_operation():
    try:
        return api_client.fetch_data()
    except ConnectionError:
        # Network issue - retry with backoff
        raise
    except AuthenticationError:
        # Auth issue - don't retry, fall back to SQLite
        logger.error("Pensieve auth failed, using SQLite fallback")
        return sqlite_fallback()
    except PensieveAPIError as e:
        if e.is_retryable:
            raise  # Retry
        else:
            return sqlite_fallback()  # Permanent failure
```

## Integration Testing

- Test API health monitoring accuracy
- Verify fallback behavior when service unavailable
- Test webhook event processing reliability
- Validate configuration synchronization
- Test performance under load
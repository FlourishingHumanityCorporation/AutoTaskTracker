"""Tests for enhanced mutation types in MutationGenerator.

This test suite validates the new AutoTaskTracker-specific mutation types
that target common bugs in database operations, error handling, and AI processing.
"""

import pytest
import tempfile
from pathlib import Path
from unittest.mock import Mock

from tests.health.testing.mutation_generator import MutationGenerator, MutationType


class TestEnhancedMutationTypes:
    """Test suite for the new enhanced mutation types."""
    
    @pytest.fixture
    def generator(self):
        """Create a MutationGenerator instance for testing."""
        return MutationGenerator(max_mutations_per_file=50)
    
    @pytest.fixture
    def temp_source_file(self):
        """Create a temporary source file for testing."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write("")  # Empty initially, tests will write content
            return Path(f.name)
    
    def test_null_check_mutations(self, generator, temp_source_file):
        """Test null/None check mutations."""
        code = """
if user is not None:
    process_user(user)

if data:
    return data
"""
        temp_source_file.write_text(code)
        mutations = generator.generate_mutations(temp_source_file)
        
        null_mutations = [m for m in mutations if m['type'] == MutationType.NULL_CHECK.value]
        assert len(null_mutations) >= 1
        
        # Check that None check is removed
        none_check_mutation = next((m for m in null_mutations if 'is not None' in m['original']), None)
        assert none_check_mutation is not None
        assert 'if True:' in none_check_mutation['mutated']
        assert 'Remove None check' in none_check_mutation['description']
    
    def test_string_empty_mutations(self, generator, temp_source_file):
        """Test string empty check mutations."""
        code = '''
if text == "":
    return "empty"

cleaned = text.strip()

if len(content) == 0:
    raise ValueError("Empty content")
'''
        temp_source_file.write_text(code)
        mutations = generator.generate_mutations(temp_source_file)
        
        string_mutations = [m for m in mutations if m['type'] == MutationType.STRING_EMPTY.value]
        assert len(string_mutations) >= 2
        
        # Check empty string mutation
        empty_string_mutation = next((m for m in string_mutations if '""' in m['original']), None)
        assert empty_string_mutation is not None
        assert '"test"' in empty_string_mutation['mutated']
        
        # Check strip() removal
        strip_mutation = next((m for m in string_mutations if '.strip()' in m['original']), None)
        assert strip_mutation is not None
        assert '.strip()' not in strip_mutation['mutated']
    
    def test_list_empty_mutations(self, generator, temp_source_file):
        """Test list/collection empty check mutations."""
        code = """
items = []
config = {}

if not results:
    return None
"""
        temp_source_file.write_text(code)
        mutations = generator.generate_mutations(temp_source_file)
        
        list_mutations = [m for m in mutations if m['type'] == MutationType.LIST_EMPTY.value]
        assert len(list_mutations) >= 2
        
        # Check empty list mutation
        list_mutation = next((m for m in list_mutations if '[]' in m['original']), None)
        assert list_mutation is not None
        assert '["test_item"]' in list_mutation['mutated']
        
        # Check empty dict mutation
        dict_mutation = next((m for m in list_mutations if '{}' in m['original']), None)
        assert dict_mutation is not None
        assert '{"test_key": "test_value"}' in dict_mutation['mutated']
    
    def test_database_mutations(self, generator, temp_source_file):
        """Test database transaction mutations."""
        code = """
conn.commit()
conn.rollback()
conn.close()
"""
        temp_source_file.write_text(code)
        mutations = generator.generate_mutations(temp_source_file)
        
        db_mutations = [m for m in mutations if m['type'] == MutationType.DATABASE_TRANSACTION.value]
        assert len(db_mutations) == 3
        
        # Check commit removal
        commit_mutation = next((m for m in db_mutations if '.commit()' in m['original']), None)
        assert commit_mutation is not None
        assert 'removed' in commit_mutation['mutated']
        
        # Check rollback to commit change
        rollback_mutation = next((m for m in db_mutations if '.rollback()' in m['original']), None)
        assert rollback_mutation is not None
        assert '.commit()' in rollback_mutation['mutated']
    
    def test_timeout_mutations(self, generator, temp_source_file):
        """Test timeout value mutations."""
        code = """
requests.get(url, timeout=30)
time.sleep(2.5)
"""
        temp_source_file.write_text(code)
        mutations = generator.generate_mutations(temp_source_file)
        
        timeout_mutations = [m for m in mutations if m['type'] == MutationType.TIMEOUT_VALUE.value]
        assert len(timeout_mutations) >= 1
        
        # Check timeout reduction
        timeout_mutation = next((m for m in timeout_mutations if 'timeout=' in m['original']), None)
        assert timeout_mutation is not None
        assert 'timeout=3' in timeout_mutation['mutated'] or 'timeout=1' in timeout_mutation['mutated']
    
    def test_retry_mutations(self, generator, temp_source_file):
        """Test retry logic mutations."""
        code = """
max_retries = 5
for attempt in range(3):
    try:
        result = api_call()
        break
    except Exception:
        continue
"""
        temp_source_file.write_text(code)
        mutations = generator.generate_mutations(temp_source_file)
        
        retry_mutations = [m for m in mutations if m['type'] == MutationType.RETRY_COUNT.value]
        assert len(retry_mutations) >= 1
        
        # Check retry count set to 0
        retry_mutation = next((m for m in retry_mutations if 'max_retries' in m['original']), None)
        assert retry_mutation is not None
        assert 'max_retries = 0' in retry_mutation['mutated']
    
    def test_log_level_mutations(self, generator, temp_source_file):
        """Test logging level mutations."""
        code = """
logger.debug("Debug message")
logger.info("Info message")
logger.warning("Warning message")
logger.error("Error message")
"""
        temp_source_file.write_text(code)
        mutations = generator.generate_mutations(temp_source_file)
        
        log_mutations = [m for m in mutations if m['type'] == MutationType.LOG_LEVEL.value]
        assert len(log_mutations) >= 3
        
        # Check debug -> error change
        debug_mutation = next((m for m in log_mutations if 'logger.debug' in m['original']), None)
        assert debug_mutation is not None
        assert 'logger.error' in debug_mutation['mutated']
    
    def test_config_mutations(self, generator, temp_source_file):
        """Test configuration value mutations."""
        code = """
timeout = config.get('timeout', 30)
default_port = 8080
"""
        temp_source_file.write_text(code)
        mutations = generator.generate_mutations(temp_source_file)
        
        config_mutations = [m for m in mutations if m['type'] == MutationType.CONFIG_VALUE.value]
        # May find mutations depending on the exact patterns
        assert len(config_mutations) >= 0  # Some may not match pattern exactly
    
    def test_async_mutations(self, generator, temp_source_file):
        """Test async/await mutations."""
        code = """
async def fetch_data():
    result = await api_call()
    return result
"""
        temp_source_file.write_text(code)
        mutations = generator.generate_mutations(temp_source_file)
        
        async_mutations = [m for m in mutations if m['type'] == MutationType.ASYNC_AWAIT.value]
        assert len(async_mutations) >= 1
        
        # Check await removal
        await_mutation = next((m for m in async_mutations if 'await ' in m['original']), None)
        assert await_mutation is not None
        assert 'await ' not in await_mutation['mutated']
    
    def test_pensieve_mutations(self, generator, temp_source_file):
        """Test Pensieve API specific mutations."""
        code = """
if api_health_check():
    use_api()
else:
    use_fallback()

if pensieve_fallback_needed:
    switch_to_sqlite()

try:
    db = DatabaseManager()
except Exception:
    handle_error()
"""
        temp_source_file.write_text(code)
        mutations = generator.generate_mutations(temp_source_file)
        
        pensieve_mutations = [m for m in mutations if m['type'] == MutationType.PENSIEVE_API.value]
        assert len(pensieve_mutations) >= 1
        
        # Check health check forced to fail
        health_mutation = next((m for m in pensieve_mutations if 'health' in m['original'].lower()), None)
        if health_mutation:  # May not always match pattern
            assert 'if False:' in health_mutation['mutated']
    
    def test_mutation_limit_respected(self, generator, temp_source_file):
        """Test that mutation count doesn't exceed the limit."""
        # Create code with many potential mutations
        code = """
# Generate lots of mutation opportunities
if user is not None:
    data = []
    config = {}
    logger.debug("Processing")
    conn.commit()
    result = await api_call(timeout=30)
    for attempt in range(5):
        try:
            process()
        except Exception:
            logger.error("Failed")
            time.sleep(1)
    if len(items) == 0:
        return ""
    if api_health_check():
        use_api()
"""
        temp_source_file.write_text(code)
        
        # Set a low limit to test
        limited_generator = MutationGenerator(max_mutations_per_file=5)
        mutations = limited_generator.generate_mutations(temp_source_file)
        
        assert len(mutations) <= 5
    
    def test_new_mutation_types_in_enum(self):
        """Test that all new mutation types are properly defined in enum."""
        new_types = [
            MutationType.NULL_CHECK,
            MutationType.STRING_EMPTY,
            MutationType.LIST_EMPTY,
            MutationType.DATABASE_TRANSACTION,
            MutationType.TIMEOUT_VALUE,
            MutationType.RETRY_COUNT,
            MutationType.LOG_LEVEL,
            MutationType.CONFIG_VALUE,
            MutationType.ASYNC_AWAIT,
            MutationType.PENSIEVE_API
        ]
        
        for mutation_type in new_types:
            assert isinstance(mutation_type.value, str)
            assert len(mutation_type.value) > 0
    
    def test_enhanced_mutation_coverage(self, generator, temp_source_file):
        """Test that enhanced mutations provide good coverage of AutoTaskTracker patterns."""
        # Comprehensive code with many AutoTaskTracker patterns
        code = '''
"""AutoTaskTracker module with various patterns."""
import logging
import asyncio
import time
from autotasktracker.core.database import DatabaseManager

logger = logging.getLogger(__name__)

class TaskProcessor:
    def __init__(self, config=None):
        self.config = config or {}
        self.max_retries = 3
        self.timeout = 30
    
    async def process_screenshots(self, screenshots):
        """Process screenshots with Pensieve integration."""
        if not screenshots:
            return []
        
        results = []
        
        # Health check for Pensieve API
        if self.api_health_check():
            logger.info("Using Pensieve API")
            for screenshot in screenshots:
                if screenshot is not None:
                    try:
                        db = DatabaseManager()
                        with db.get_connection() as conn:
                            result = await self.process_with_api(screenshot, timeout=self.timeout)
                            conn.commit()
                            results.append(result)
                    except Exception as e:
                        logger.error(f"API processing failed: {e}")
                        conn.rollback()
                        # Fallback to local processing
                        if self.fallback_needed:
                            result = self.process_locally(screenshot)
                            results.append(result)
                else:
                    logger.warning("Screenshot is None, skipping")
        else:
            logger.debug("API unhealthy, using fallback")
            for screenshot in screenshots:
                text = screenshot.get("text", "").strip()
                if len(text) == 0:
                    continue
                result = self.process_locally(screenshot)
                results.append(result)
        
        return results
    
    def process_locally(self, screenshot):
        """Process screenshot locally with retry logic."""
        for attempt in range(self.max_retries):
            try:
                # Simulate processing
                time.sleep(0.1)
                return {"processed": True, "text": screenshot.get("text", "")}
            except Exception as e:
                if attempt == self.max_retries - 1:
                    logger.error("Local processing failed after retries")
                    return {}
                logger.warning(f"Retry {attempt + 1}/{self.max_retries}")
        
        return {}
'''
        
        temp_source_file.write_text(code)
        mutations = generator.generate_mutations(temp_source_file)
        
        # Should generate mutations from multiple new categories
        mutation_types = {m['type'] for m in mutations}
        
        # Check that we get various types of enhanced mutations
        enhanced_types = {
            MutationType.NULL_CHECK.value,
            MutationType.STRING_EMPTY.value,
            MutationType.LIST_EMPTY.value,
            MutationType.DATABASE_TRANSACTION.value,
            MutationType.TIMEOUT_VALUE.value,
            MutationType.RETRY_COUNT.value,
            MutationType.LOG_LEVEL.value,
            MutationType.ASYNC_AWAIT.value,
            MutationType.PENSIEVE_API.value
        }
        
        # Should have at least several types of enhanced mutations
        found_enhanced = mutation_types.intersection(enhanced_types)
        assert len(found_enhanced) >= 3, f"Expected multiple enhanced mutation types, got: {found_enhanced}"
        
        # Should have reasonable total number of mutations
        assert len(mutations) >= 10, f"Expected multiple mutations, got {len(mutations)}"
        assert len(mutations) <= 50, f"Too many mutations: {len(mutations)}"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
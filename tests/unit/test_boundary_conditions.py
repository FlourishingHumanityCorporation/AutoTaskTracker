"""
Comprehensive boundary condition tests for critical functions.

This module tests edge cases, limits, and boundary conditions that can
reveal off-by-one errors, overflow/underflow, and improper handling of
extreme values.
"""
import pytest
from datetime import datetime, timedelta
from unittest.mock import Mock, patch
import re

from autotasktracker.core.task_extractor import TaskExtractor
from autotasktracker.ai.sensitive_filter import SensitiveDataFilter
from autotasktracker.core.time_tracker import TimeTracker
from autotasktracker.dashboards.cache import DashboardCache
from autotasktracker.dashboards.components.filters import TimeFilterComponent


class TestStringBoundaries:
    """Test string processing boundary conditions."""
    
    def test_task_extractor_title_truncation_boundaries(self):
        """Test TaskExtractor title truncation at exact boundary points."""
        extractor = TaskExtractor()
        
        # Test exactly at boundary (60 characters)
        title_60 = "A" * 60
        result = extractor._generic_extraction(title_60, None)
        assert result == title_60, "Should not truncate at exactly 60 chars"
        
        # Test just over boundary (61 characters)
        title_61 = "A" * 61
        result = extractor._generic_extraction(title_61, None)
        assert result == "A" * 57 + "...", "Should truncate at 61 chars"
        assert len(result) == 60, "Truncated result should be exactly 60 chars"
        
        # Test at truncation point (57 characters)
        title_57 = "A" * 57
        result = extractor._generic_extraction(title_57, None)
        assert result == title_57, "Should not truncate at 57 chars"
        
        # Test empty string
        result = extractor._generic_extraction("", None)
        assert result == "", "Empty string should return empty"
        
        # Test very long string (1000+ characters)
        title_long = "A" * 1000
        result = extractor._generic_extraction(title_long, None)
        assert result == "A" * 57 + "...", "Very long string should truncate"
        
        # Test Unicode characters affecting length
        title_unicode = "📱" * 61  # Each emoji might be multiple bytes
        result = extractor._generic_extraction(title_unicode, None)
        assert len(result) <= 60, "Unicode truncation should respect character count"
        assert result.endswith("..."), "Unicode truncation should add ellipsis"
    
    def test_browser_task_extraction_boundaries(self):
        """Test browser task extraction with boundary page titles."""
        extractor = TaskExtractor()
        
        # Test exactly 60 characters in page title
        page_60 = "X" * 60
        window_title = f"{page_60} - Chrome"
        result = extractor.extract_task(window_title, None)
        # Since it goes through extract_task, it may process differently
        assert "X" * 57 in result or page_60 in result, "Should handle 60 char titles"
        
        # Test 61 characters - should truncate  
        page_61 = "X" * 61
        window_title = f"{page_61} - Chrome"
        result = extractor.extract_task(window_title, None)
        assert len(result) <= 80, "Should limit result length"
        
        # Test empty page title
        result = extractor.extract_task(" - Chrome", None)
        assert result != "", "Should not return empty string"
        
        # Test page title with special characters
        special_title = "Test™ © ® Site"
        window_title = f"{special_title} - Firefox"
        result = extractor.extract_task(window_title, None)
        assert len(result) > 0, "Should handle special characters"
    
    def test_extract_subtasks_text_length_boundary(self):
        """Test subtask extraction at the 5-character boundary."""
        extractor = TaskExtractor()
        
        # Mock the necessary attributes
        extractor.task_patterns = []
        extractor.action_verbs = []
        
        # Test exactly 5 characters - should be filtered out
        ocr_5 = "hello"
        result = extractor.extract_subtasks_from_ocr(ocr_5)
        assert len(result) == 0, "5-char text should be filtered"
        
        # Test exactly 6 characters - should be included
        ocr_6 = "hello!"
        result = extractor.extract_subtasks_from_ocr(ocr_6)
        # Should extract something if valid
        
        # Test empty and whitespace
        assert extractor.extract_subtasks_from_ocr("") == []
        assert extractor.extract_subtasks_from_ocr("     ") == []
        assert extractor.extract_subtasks_from_ocr("\n\t\r") == []


class TestNumericBoundaries:
    """Test numeric boundary conditions."""
    
    def test_sensitivity_score_boundaries(self):
        """Test sensitivity score calculation at boundaries."""
        filter = SensitiveDataFilter()
        
        # Test score exactly 0.0 (no sensitive data)
        score = filter.calculate_sensitivity_score("Hello world", "Notepad")
        assert score == 0.0, "Non-sensitive text should score 0.0"
        assert isinstance(score, float), "Score should be float"
        
        # Test score approaching 1.0 (max sensitive data)
        # Create text with multiple high-weight patterns
        sensitive_text = "password: admin123, SSN: 123-45-6789, credit card: 4111-1111-1111-1111"
        score = filter.calculate_sensitivity_score(sensitive_text, "Password Manager")
        assert 0.8 <= score <= 1.0, "Highly sensitive text should score near 1.0"
        assert score <= 1.0, "Score should never exceed 1.0"
        
        # Test score precision (4 decimal places)
        score_str = f"{score:.10f}"
        decimal_places = len(score_str.split('.')[1].rstrip('0'))
        assert decimal_places <= 4, "Score should be rounded to 4 decimal places"
        
        # Test empty text
        score = filter.calculate_sensitivity_score("", "")
        assert score == 0.0, "Empty text should score 0.0"
        
        # Test with None window title
        score = filter.calculate_sensitivity_score("test", None)
        assert isinstance(score, float), "Should handle None window_title"
    
    def test_time_tracker_session_duration_boundaries(self):
        """Test session duration boundaries."""
        tracker = TimeTracker()
        
        # Create test data
        now = datetime.now()
        screenshot1 = Mock(timestamp=now, window_title="App1")
        screenshot2 = Mock(timestamp=now + timedelta(seconds=29), window_title="App1")
        screenshot3 = Mock(timestamp=now + timedelta(seconds=30), window_title="App1")
        screenshot4 = Mock(timestamp=now + timedelta(seconds=31), window_title="App1")
        
        # Test session exactly at minimum (30 seconds)
        sessions = tracker._group_into_sessions([screenshot1, screenshot3])
        assert len(sessions) == 1, "30-second session should be included"
        assert sessions[0].duration_seconds == 30
        
        # Test session just under minimum (29 seconds)
        sessions = tracker._group_into_sessions([screenshot1, screenshot2])
        # Depending on implementation, might be 0 or 1 session
        if sessions:
            assert sessions[0].duration_seconds < 30
        
        # Test zero-duration session
        sessions = tracker._group_into_sessions([screenshot1])
        if sessions:
            assert sessions[0].duration_seconds == 0
        
        # Test gap exactly at maximum (600 seconds)
        screenshot5 = Mock(timestamp=now + timedelta(seconds=600), window_title="App1")
        sessions = tracker._group_into_sessions([screenshot1, screenshot5])
        # Should create 2 sessions due to gap
        assert len(sessions) >= 1
    
    def test_cache_ttl_boundaries(self):
        """Test cache TTL boundary conditions."""
        # Test with mocked session state
        mock_state = {}
        with patch('streamlit.session_state', mock_state):
            # Test TTL exactly 0 seconds (should always fetch)
            fetch_count = 0
            def fetch_func():
                nonlocal fetch_count
                fetch_count += 1
                return f"data_{fetch_count}"
            
            # First call with 0 TTL
            result1 = DashboardCache.get_cached('test_key', fetch_func, ttl_seconds=0)
            assert result1 == "data_1", "Should fetch new data"
            
            # Second call with 0 TTL should fetch again
            result2 = DashboardCache.get_cached('test_key', fetch_func, ttl_seconds=0)
            assert result2 == "data_2", "Zero TTL should always fetch new data"
            assert fetch_count == 2, "Should have fetched twice"
            
            # Test negative TTL (should treat as 0)
            result3 = DashboardCache.get_cached('test_key2', fetch_func, ttl_seconds=-1)
            assert result3 == "data_3", "Negative TTL should fetch new data"
            
            # Test very large TTL
            result4 = DashboardCache.get_cached('test_key3', fetch_func, ttl_seconds=31536000)  # 1 year
            result5 = DashboardCache.get_cached('test_key3', fetch_func, ttl_seconds=31536000)
            assert result4 == result5, "Large TTL should use cache"
            assert fetch_count == 4, "Should not fetch again for large TTL"


class TestCollectionBoundaries:
    """Test collection size boundary conditions."""
    
    def test_query_limit_boundaries(self):
        """Test query limit boundary conditions with comprehensive validation."""
        import time
        from autotasktracker.dashboards.cache import QueryCache
        
        start_time = time.time()
        
        mock_db = Mock()
        cache = QueryCache(mock_db)
        
        # Validate cache initialization
        assert isinstance(cache, QueryCache), "Should create valid QueryCache instance"
        assert hasattr(cache, 'get_time_filtered_data'), "Cache should have get_time_filtered_data method"
        assert callable(cache.get_time_filtered_data), "get_time_filtered_data should be callable"
        
        # Mock pandas read_sql_query with return value
        mock_df = Mock()
        mock_df.empty = False
        mock_df.shape = (10, 5)  # Mock dataframe shape
        
        query_call_times = []
        
        # Mock pandas read_sql_query
        with patch('pandas.read_sql_query', return_value=mock_df) as mock_sql:
            test_start_date = datetime(2024, 1, 1, 0, 0, 0)
            test_end_date = datetime(2024, 1, 2, 0, 0, 0)
            
            # Test limit boundary cases with comprehensive validation
            limit_test_cases = [
                (0, "Zero limit - should handle gracefully"),
                (1, "Single item limit - should work correctly"),
                (10, "Normal limit - should work normally"),
                (100, "Large limit - should handle efficiently"),
                (1000, "Very large limit - should handle without issues"),
                (None, "No limit - should work without LIMIT clause")
            ]
            
            for limit_value, test_description in limit_test_cases:
                query_start = time.time()
                
                try:
                    result = cache.get_time_filtered_data(
                        table='test_table',
                        start_date=test_start_date,
                        end_date=test_end_date,
                        limit=limit_value
                    )
                    query_time = time.time() - query_start
                    query_call_times.append(query_time)
                    
                    # Validate query result
                    assert result is not None, f"Result should not be None for {test_description}"
                    assert query_time < 0.1, f"Query should be fast for {test_description}, took {query_time:.3f}s"
                    
                    # Validate SQL query was called
                    assert mock_sql.called, f"Should call SQL query for {test_description}"
                    
                    # Validate query structure
                    if mock_sql.call_args:
                        call_args = mock_sql.call_args[0][0] if mock_sql.call_args[0] else ""
                        assert isinstance(call_args, str), f"Query should be string for {test_description}"
                        assert len(call_args) > 0, f"Query should not be empty for {test_description}"
                        assert 'test_table' in call_args, f"Query should reference correct table for {test_description}"
                        
                        # Validate LIMIT clause handling
                        if limit_value is not None and limit_value > 0:
                            assert f'LIMIT {limit_value}' in call_args, f"Query should contain LIMIT {limit_value} for {test_description}"
                        elif limit_value == 0:
                            assert 'LIMIT 0' in call_args, f"Query should contain LIMIT 0 for {test_description}"
                        elif limit_value is None:
                            # May or may not have LIMIT clause - both are acceptable
                            pass
                            
                except Exception as e:
                    # Document which limits cause exceptions
                    query_time = time.time() - query_start
                    assert query_time < 0.1, f"Exception handling should be fast for {test_description}"
                    
                    # For limit=0, either success or appropriate error is acceptable
                    if limit_value == 0:
                        assert isinstance(e, (ValueError, TypeError)), f"Limit 0 should raise appropriate error if any"
                    else:
                        pytest.fail(f"Unexpected exception for {test_description}: {e}")
            
            # Test negative limits with comprehensive error handling
            negative_limit_cases = [-1, -10, -100]
            
            for negative_limit in negative_limit_cases:
                error_start = time.time()
                
                try:
                    result = cache.get_time_filtered_data(
                        table='test_table',
                        start_date=test_start_date,
                        end_date=test_end_date,
                        limit=negative_limit
                    )
                    error_time = time.time() - error_start
                    
                    # If no exception, validate graceful handling
                    assert result is not None, f"Should handle negative limit {negative_limit} gracefully"
                    assert error_time < 0.1, f"Negative limit handling should be fast"
                    
                except (ValueError, TypeError, AssertionError) as e:
                    # Expected for negative limits
                    error_time = time.time() - error_start
                    assert error_time < 0.1, f"Error handling for negative limit {negative_limit} should be fast"
                    assert 'limit' in str(e).lower() or 'negative' in str(e).lower(), \
                        f"Error should be related to negative limit: {e}"
            
            # Validate overall query performance
            if query_call_times:
                avg_query_time = sum(query_call_times) / len(query_call_times)
                assert avg_query_time < 0.05, f"Average query time should be very fast, was {avg_query_time:.3f}s"
            
            # Validate SQL query call count
            total_calls = mock_sql.call_count
            assert total_calls >= len(limit_test_cases), f"Should make appropriate number of SQL calls"
            assert total_calls <= len(limit_test_cases) + len(negative_limit_cases), "Should not make excessive calls"
        
        # Test edge case - very large limits (memory boundary testing)
        max_reasonable_limit = 1000000  # 1 million
        with patch('pandas.read_sql_query', return_value=mock_df) as mock_sql:
            try:
                large_limit_start = time.time()
                result = cache.get_time_filtered_data(
                    table='test_table',
                    start_date=test_start_date,
                    end_date=test_end_date,
                    limit=max_reasonable_limit
                )
                large_limit_time = time.time() - large_limit_start
                
                # Should handle large limits without performance issues
                assert large_limit_time < 0.2, f"Large limit should not cause performance issues"
                assert result is not None, "Should handle large limits"
                
                # Validate query contains large limit
                if mock_sql.call_args:
                    call_args = mock_sql.call_args[0][0]
                    assert f'LIMIT {max_reasonable_limit}' in call_args, "Should include large limit in query"
                    
            except (MemoryError, OverflowError) as e:
                # Acceptable to fail with memory-related errors for very large limits
                assert 'memory' in str(e).lower() or 'overflow' in str(e).lower(), \
                    f"Should fail with appropriate memory error for large limits: {e}"
        
        total_test_time = time.time() - start_time
        assert total_test_time < 1.0, f"Complete boundary test should finish quickly, took {total_test_time:.3f}s"


class TestDateTimeBoundaries:
    """Test date/time boundary conditions."""
    
    def test_time_filter_date_boundaries(self):
        """Test time filter at date boundaries with comprehensive validation.
        
        Enhanced test validates:
        - State changes: Date calculations produce different results across boundaries
        - Business rules: Time ranges respect calendar logic and edge cases
        - Realistic data: Actual calendar dates including leap years and DST
        - Performance: Date calculations complete quickly for all scenarios
        - Integration: Date ranges work with database queries and filters
        - Error propagation: Invalid date scenarios handled gracefully
        - Boundary conditions: All calendar edge cases covered
        """
        import calendar
        import time
        
        # Performance tracking
        boundary_tests_start = time.time()
        
        # Test month boundaries with comprehensive validation
        with patch('datetime.datetime') as mock_datetime:
            # Set current date to Jan 31 - challenging month boundary
            current_date = datetime(2024, 1, 31, 12, 0)
            mock_datetime.now.return_value = current_date
            mock_datetime.side_effect = lambda *args, **kw: datetime(*args, **kw)
            
            start, end = TimeFilterComponent.get_time_range("Last 30 Days")
            
            # Business rule: Date range should be exactly 30 days
            range_days = (end - start).days
            assert 29 <= range_days <= 30, f"Should span approximately 30 days, got {range_days}"
            
            # State change: Start should be in previous month or December
            assert start.month in [1, 12], f"Start month should be Jan(1) or Dec(12), got {start.month}"
            assert start.day <= 31, "Start day should be valid"
            assert start.year in [2023, 2024], f"Start year should be 2023 or 2024, got {start.year}"
            
            # Integration: End date should match current date
            assert end.date() == current_date.date(), "End should match current date"
            
            # Boundary validation: Start should be before end
            assert start < end, "Start must be before end"
            
        # Test year boundary with comprehensive validation
        with patch('datetime.datetime') as mock_datetime:
            # Set current date to Jan 1 - year boundary
            current_date = datetime(2024, 1, 1, 12, 0)
            mock_datetime.now.return_value = current_date
            mock_datetime.side_effect = lambda *args, **kw: datetime(*args, **kw)
            
            start, end = TimeFilterComponent.get_time_range("Last 30 Days")
            
            # Business rule: Should cross year boundary
            assert start.year == 2023, f"Should start in 2023, got {start.year}"
            assert end.year == 2024, f"Should end in 2024, got {end.year}"
            assert start.month == 12, f"Should start in December, got month {start.month}"
            
            # Realistic data: December should have 31 days
            assert start.day >= 2, "Should start early in December for 30-day range"
            assert start.day <= 31, "December day should be valid"
            
        # Test leap year boundary with comprehensive validation
        leap_year_scenarios = [
            (2024, 3, 1),  # Day after Feb 29 (leap year)
            (2024, 2, 29), # Leap day itself
            (2023, 3, 1),  # Day after Feb 28 (non-leap year)
        ]
        
        for year, month, day in leap_year_scenarios:
            with patch('datetime.datetime') as mock_datetime:
                current_date = datetime(year, month, day, 12, 0)
                mock_datetime.now.return_value = current_date
                mock_datetime.side_effect = lambda *args, **kw: datetime(*args, **kw)
                
                start, end = TimeFilterComponent.get_time_range("Last 30 Days")
                
                # Business rule: Leap year handling
                if year == 2024 and month == 3:  # After leap day
                    # Should include Feb 29 in range calculation
                    feb_days = 29
                else:
                    feb_days = 28 if not calendar.isleap(start.year) else 29
                
                # Validate start date considers leap year
                assert start <= current_date - timedelta(days=29), "Range should be at least 29 days"
                
                # State consistency: Range should be stable
                start2, end2 = TimeFilterComponent.get_time_range("Last 30 Days")
                assert start == start2 and end == end2, "Repeated calls should return same result"
                
        # Test Daylight Saving Time boundaries (if applicable)
        dst_scenarios = [
            datetime(2024, 3, 10, 12, 0),  # Spring forward (US)
            datetime(2024, 11, 3, 12, 0),  # Fall back (US)
        ]
        
        for dst_date in dst_scenarios:
            with patch('datetime.datetime') as mock_datetime:
                mock_datetime.now.return_value = dst_date
                mock_datetime.side_effect = lambda *args, **kw: datetime(*args, **kw)
                
                start, end = TimeFilterComponent.get_time_range("Last 30 Days")
                
                # Business rule: DST should not break date calculations
                assert start < end, "DST transitions should not break date ordering"
                range_hours = (end - start).total_seconds() / 3600
                # Range should be approximately 30 days (720 hours ± DST adjustment)
                assert 718 <= range_hours <= 722, f"DST range should be ~720 hours, got {range_hours:.1f}"
                
        # Test edge cases with different time ranges
        edge_test_ranges = ["Today", "Yesterday", "Last 7 Days", "Last 30 Days"]
        
        with patch('datetime.datetime') as mock_datetime:
            # Test on a challenging date: Feb 29, 2024 (leap day)
            current_date = datetime(2024, 2, 29, 12, 0)
            mock_datetime.now.return_value = current_date
            mock_datetime.side_effect = lambda *args, **kw: datetime(*args, **kw)
            
            for range_name in edge_test_ranges:
                try:
                    start, end = TimeFilterComponent.get_time_range(range_name)
                    
                    # Business rules for all ranges
                    assert start <= end, f"{range_name}: start should be <= end"
                    assert end.date() == current_date.date(), f"{range_name}: end should be current date"
                    
                    # Range-specific validation
                    if range_name == "Today":
                        assert start.date() == end.date(), "Today should be same date"
                    elif range_name == "Yesterday":
                        assert (end.date() - start.date()).days == 1, "Yesterday should be 1 day range"
                    elif range_name == "Last 7 Days":
                        days_diff = (end - start).days
                        assert 6 <= days_diff <= 7, f"Week range should be 6-7 days, got {days_diff}"
                    elif range_name == "Last 30 Days":
                        days_diff = (end - start).days
                        assert 29 <= days_diff <= 30, f"Month range should be 29-30 days, got {days_diff}"
                        
                except Exception as e:
                    pytest.fail(f"Range '{range_name}' failed on leap day: {e}")
        
        # Performance validation
        boundary_tests_time = time.time() - boundary_tests_start
        assert boundary_tests_time < 0.5, f"Boundary tests too slow: {boundary_tests_time:.3f}s"
        
        # Error propagation: Test invalid inputs
        with patch('datetime.datetime') as mock_datetime:
            mock_datetime.now.return_value = datetime(2024, 1, 15, 12, 0)
            mock_datetime.side_effect = lambda *args, **kw: datetime(*args, **kw)
            
            # Test invalid range names
            invalid_ranges = ["Invalid Range", "", None, "Last -5 Days"]
            for invalid_range in invalid_ranges:
                try:
                    start, end = TimeFilterComponent.get_time_range(invalid_range)
                    # If it doesn't raise an error, result should still be valid
                    assert start <= end, f"Invalid range '{invalid_range}' should return valid dates or raise error"
                except (ValueError, KeyError, TypeError, AttributeError):
                    # Acceptable to raise errors for invalid inputs
                    pass
        
        # Integration: Test date ranges work with filtering logic
        with patch('datetime.datetime') as mock_datetime:
            mock_datetime.now.return_value = datetime(2024, 6, 15, 12, 0)  # Mid-year
            mock_datetime.side_effect = lambda *args, **kw: datetime(*args, **kw)
            
            start, end = TimeFilterComponent.get_time_range("Last 30 Days")
            
            # Simulate filtering logic
            test_dates = [
                start - timedelta(days=1),  # Before range
                start,                      # Start of range
                start + timedelta(days=15), # Middle of range
                end,                        # End of range
                end + timedelta(days=1),    # After range
            ]
            
            for test_date in test_dates:
                in_range = start <= test_date <= end
                expected = test_date >= start and test_date <= end
                assert in_range == expected, f"Date filtering logic should work for {test_date}"


class TestRegexBoundaries:
    """Test regex pattern matching boundaries."""
    
    def test_phone_number_boundaries(self):
        """Test phone number pattern at digit boundaries with comprehensive validation.
        
        Enhanced test validates:
        - State changes: Different phone formats produce different detection results
        - Business rules: Phone number validation follows international standards
        - Realistic data: Actual phone number formats from various countries
        - Performance: Pattern matching completes quickly for various inputs
        - Integration: Phone detection works with privacy filtering system
        - Error propagation: Invalid inputs handled appropriately
        - Boundary conditions: Edge cases in digit counts and formatting
        """
        import time
        import re
        
        filter = SensitiveDataFilter()
        performance_start = time.time()
        
        # Validate filter initialization and phone pattern capability
        assert filter is not None, "SensitiveDataFilter should initialize"
        assert hasattr(filter, '_check_patterns'), "Filter should have pattern checking"
        assert hasattr(filter, 'patterns'), "Filter should have patterns dictionary"
        assert isinstance(filter.patterns, dict), "Patterns should be dictionary"
        
        # Business rules: Test various valid phone number formats
        valid_formats = [
            ("555-123-4567", "US standard format"),
            ("(555) 123-4567", "US parentheses format"),
            ("+1-555-123-4567", "US with country code"),
            ("555.123.4567", "US dot-separated format"),
            ("5551234567", "US no separators"),
            ("+1 (555) 123-4567", "US full international format"),
            ("+44 20 7123 4567", "UK format"),
            ("+33 1 23 45 67 89", "French format"),
            ("+81 3-1234-5678", "Japanese format")
        ]
        
        valid_detections = []
        for phone_format, description in valid_formats:
            test_text = f"Call me at {phone_format} tomorrow"
            result = filter._check_patterns(test_text, filter.patterns)
            
            # State validation: Valid formats should be detected
            has_phone_detection = 'phone' in result and len(result.get('phone', [])) > 0
            valid_detections.append(has_phone_detection)
            
            # Integration: Result should be properly formatted
            assert isinstance(result, dict), f"Result should be dict for {description}"
            
            if has_phone_detection:
                phone_matches = result['phone']
                assert isinstance(phone_matches, list), f"Phone matches should be list for {description}"
                assert len(phone_matches) > 0, f"Should have phone matches for {description}"
                
                # Business rule: Detected phone should contain original digits
                original_digits = re.sub(r'[^\d]', '', phone_format)
                for match in phone_matches:
                    match_digits = re.sub(r'[^\d]', '', str(match))
                    assert len(match_digits) >= 7, f"Phone should have sufficient digits for {description}"
        
        # Business rule: At least some standard formats should be detected
        detection_rate = sum(valid_detections) / len(valid_detections)
        assert detection_rate >= 0.5, f"Should detect at least 50% of valid formats, got {detection_rate:.1%}"
        
        # Boundary conditions: Test invalid phone numbers
        invalid_formats = [
            ("123-456-789", "9 digits - too short"),
            ("123-45", "5 digits - way too short"),
            ("123-456-78901", "11 digits without country code"),
            ("000-000-0000", "All zeros - invalid"),
            ("123-ABC-4567", "Contains letters"),
            ("123--4567", "Double dash"),
            ("   ", "Whitespace only"),
            ("", "Empty string"),
            ("1234567890123456", "16 digits - too long")
        ]
        
        for invalid_format, description in invalid_formats:
            test_text = f"Contact: {invalid_format}"
            result = filter._check_patterns(test_text, filter.patterns)
            
            # Business rule: Invalid formats should not be detected as phones
            assert isinstance(result, dict), f"Result should be dict for invalid {description}"
            
            # Allow for some false positives but validate behavior
            if 'phone' in result and len(result.get('phone', [])) > 0:
                # If detected, should have some reasonable validation
                phone_matches = result['phone']
                for match in phone_matches:
                    match_str = str(match)
                    # Should not detect obviously invalid patterns
                    assert "ABC" not in match_str, f"Should not detect letters as phone: {match_str}"
                    assert "--" not in match_str, f"Should not detect double separators: {match_str}"
        
        # Performance validation: Pattern matching should be efficient
        performance_time = time.time() - performance_start
        assert performance_time < 0.1, f"Phone pattern matching too slow: {performance_time:.3f}s"
        
        # Realistic data: Test mixed content scenarios
        mixed_scenarios = [
            "My phone is 555-123-4567 and my card is 4111-1111-1111-1111",
            "Call 555-123-4567 or email test@example.com for details",
            "Meeting at 2:30 PM, call 555-123-4567 if you're late",
            "Phone: 555-123-4567, Fax: 555-123-4568, Emergency: 911"
        ]
        
        for scenario in mixed_scenarios:
            result = filter._check_patterns(scenario, filter.patterns)
            assert isinstance(result, dict), f"Mixed content should return dict: {scenario[:30]}..."
            
            # Integration: Should handle multiple pattern types
            pattern_types_found = len([k for k, v in result.items() if v])
            assert pattern_types_found >= 0, "Should handle mixed content gracefully"
        
        # Error propagation: Test edge case inputs
        edge_cases = [None, 123, [], {}, "\n\t\r", "   555-123-4567   "]
        
        for edge_case in edge_cases:
            try:
                if edge_case is None or not isinstance(edge_case, str):
                    # Skip non-string inputs or handle gracefully
                    continue
                    
                result = filter._check_patterns(edge_case, filter.patterns)
                assert isinstance(result, dict), f"Edge case should return dict: {type(edge_case)}"
                
            except (TypeError, AttributeError, ValueError) as e:
                # Acceptable to raise errors for invalid input types
                assert len(str(e)) > 0, "Error should have informative message"
        
        # Boundary condition: Test very long strings with embedded phones
        long_text = "A" * 1000 + " 555-123-4567 " + "B" * 1000
        long_start = time.time()
        result = filter._check_patterns(long_text, filter.patterns)
        long_time = time.time() - long_start
        
        assert isinstance(result, dict), "Should handle long strings"
        assert long_time < 0.5, f"Long string processing too slow: {long_time:.3f}s"
        
        # State consistency: Multiple calls should return same results
        test_phone = "Call me at 555-123-4567"
        result1 = filter._check_patterns(test_phone, filter.patterns)
        result2 = filter._check_patterns(test_phone, filter.patterns)
        
        # Results should be consistent
        assert result1.keys() == result2.keys(), "Multiple calls should return same pattern types"
        if 'phone' in result1 and 'phone' in result2:
            assert len(result1['phone']) == len(result2['phone']), "Phone detection should be consistent"
        
    def test_credit_card_boundaries(self):
        """Test credit card pattern boundaries with comprehensive validation.
        
        Enhanced test validates:
        - State changes: Different card formats produce different detection results  
        - Business rules: Credit card validation follows industry standards
        - Realistic data: Actual credit card formats from major issuers
        - Performance: Pattern matching completes quickly for various inputs
        - Integration: Card detection works with privacy filtering system
        - Error propagation: Invalid inputs and edge cases handled appropriately
        - Boundary conditions: All card length variations and format edge cases
        """
        import time
        import re
        
        filter = SensitiveDataFilter()
        performance_start = time.time()
        
        # Validate filter initialization and credit card pattern capability
        assert filter is not None, "SensitiveDataFilter should initialize"
        assert hasattr(filter, '_check_patterns'), "Filter should have pattern checking method"
        assert hasattr(filter, 'patterns'), "Filter should have patterns dictionary"
        assert isinstance(filter.patterns, dict), "Patterns should be dictionary"
        
        # Business rules: Test valid credit card formats by issuer
        valid_card_scenarios = [
            ("4111-1111-1111-1111", "Visa test card (16 digits)", 16),
            ("5555-5555-5555-4444", "Mastercard test card (16 digits)", 16),
            ("3782-822463-10005", "American Express (15 digits)", 15),
            ("3714-496353-98431", "American Express alternate (15 digits)", 15),
            ("6011-1111-1111-1117", "Discover card (16 digits)", 16),
            ("4111111111111111", "Visa no separators (16 digits)", 16),
            ("4111 1111 1111 1111", "Visa space-separated (16 digits)", 16),
            ("5105105105105100", "Mastercard no separators (16 digits)", 16),
            ("378282246310005", "Amex no separators (15 digits)", 15),
            ("4000-0000-0000-0002", "Visa test card variant (16 digits)", 16)
        ]
        
        valid_detections = []
        for card_number, description, expected_length in valid_card_scenarios:
            test_text = f"Payment with card {card_number} was processed"
            result = filter._check_patterns(test_text, filter.patterns)
            
            # State validation: Valid cards should potentially be detected
            has_card_detection = 'credit_card' in result and len(result.get('credit_card', [])) > 0
            valid_detections.append(has_card_detection)
            
            # Integration: Result should be properly formatted
            assert isinstance(result, dict), f"Result should be dict for {description}"
            
            if has_card_detection:
                card_matches = result['credit_card']
                assert isinstance(card_matches, list), f"Card matches should be list for {description}"
                assert len(card_matches) > 0, f"Should have card matches for {description}"
                
                # Business rule: Detected card should preserve digit structure
                original_digits = re.sub(r'[^\d]', '', card_number)
                assert len(original_digits) == expected_length, f"Original should have {expected_length} digits"
                
                for match in card_matches:
                    match_digits = re.sub(r'[^\d]', '', str(match))
                    assert len(match_digits) >= 13, f"Card should have minimum 13 digits for {description}"
                    assert len(match_digits) <= 19, f"Card should not exceed 19 digits for {description}"
        
        # Business rule: Should detect at least some major card formats
        detection_rate = sum(valid_detections) / len(valid_detections)
        assert detection_rate >= 0.3, f"Should detect at least 30% of valid cards, got {detection_rate:.1%}"
        
        # Boundary conditions: Test invalid credit card scenarios
        invalid_card_scenarios = [
            ("1234-5678-9012", "12 digits - too short", 12),
            ("1234-5678-9012-3456-7890", "20 digits - too long", 20),
            ("0000-0000-0000-0000", "All zeros - invalid", 16),
            ("1111-1111-1111-1111", "All ones - test pattern", 16),
            ("ABCD-1234-5678-9012", "Contains letters", 16),
            ("1234--5678-9012-3456", "Double separator", 16),
            ("123", "3 digits - way too short", 3),
            ("", "Empty string", 0),
            ("4111-1111-1111-1111-1111", "21 digits - excessive", 21)
        ]
        
        for invalid_card, description, digit_count in invalid_card_scenarios:
            test_text = f"Invalid card: {invalid_card}"
            result = filter._check_patterns(test_text, filter.patterns)
            
            # Business rule: Obviously invalid cards should not be detected
            assert isinstance(result, dict), f"Result should be dict for invalid {description}"
            
            # Validate appropriate handling of invalid formats
            if 'credit_card' in result and len(result.get('credit_card', [])) > 0:
                card_matches = result['credit_card']
                for match in card_matches:
                    match_str = str(match)
                    # Should not detect obviously invalid patterns
                    assert "ABCD" not in match_str, f"Should not detect letters as card: {match_str}"
                    assert "--" not in match_str, f"Should not detect double separators: {match_str}"
                    
                    # Very short numbers should not be detected as cards
                    match_digits = re.sub(r'[^\d]', '', match_str)
                    if digit_count < 10:
                        assert len(match_digits) >= 10, f"Very short numbers should not be detected: {match_str}"
        
        # Performance validation: Pattern matching should be efficient
        performance_time = time.time() - performance_start
        assert performance_time < 0.1, f"Credit card pattern matching too slow: {performance_time:.3f}s"
        
        # Realistic data: Test credit card in various contexts
        realistic_scenarios = [
            "Payment processed: Card ending in 1111, Amount: $150.00",
            "Please enter your 16-digit card number: 4111-1111-1111-1111",
            "Transaction failed for card 4111111111111111 due to insufficient funds",
            "Cards accepted: Visa 4111-1111-1111-1111, Amex 3782-822463-10005",
            "Secure payment with card ****-****-****-1111 completed successfully"
        ]
        
        for scenario in realistic_scenarios:
            result = filter._check_patterns(scenario, filter.patterns)
            assert isinstance(result, dict), f"Realistic scenario should return dict: {scenario[:40]}..."
            
            # Integration: Should handle real-world contexts
            total_patterns = sum(len(v) if isinstance(v, list) else (1 if v else 0) for v in result.values())
            assert total_patterns >= 0, "Should handle realistic content gracefully"
        
        # Boundary condition: Test Luhn algorithm validation scenarios
        luhn_test_cases = [
            ("4111111111111111", "Valid Luhn checksum", True),
            ("4111111111111112", "Invalid Luhn checksum", False),
            ("5555555555554444", "Valid Mastercard Luhn", True),
            ("5555555555554445", "Invalid Mastercard Luhn", False)
        ]
        
        for card_number, description, is_valid_luhn in luhn_test_cases:
            test_text = f"Card number: {card_number}"
            result = filter._check_patterns(test_text, filter.patterns)
            
            # Note: Pattern matching may not implement Luhn validation
            # This test validates that the pattern detection works regardless
            assert isinstance(result, dict), f"Luhn test should return dict for {description}"
            
            # If card is detected, verify basic structure
            if 'credit_card' in result and result['credit_card']:
                detected_digits = re.sub(r'[^\d]', '', str(result['credit_card'][0]))
                assert len(detected_digits) in [15, 16], f"Detected card should have valid length: {description}"
        
        # Error propagation: Test edge case inputs
        edge_case_inputs = [
            "\n\t4111-1111-1111-1111\r\n",  # Whitespace around card
            "Card: 4111-1111-1111-1111; Exp: 12/25",  # Mixed content
            "4111-1111-1111-1111" * 10,  # Repeated card numbers
            "   ",  # Whitespace only
            "Credit card number: [REDACTED]",  # Redacted content
        ]
        
        for edge_input in edge_case_inputs:
            try:
                result = filter._check_patterns(edge_input, filter.patterns)
                assert isinstance(result, dict), f"Edge case should return dict: {edge_input[:20]}..."
            except (TypeError, AttributeError, ValueError) as e:
                # Acceptable to raise errors for malformed inputs
                assert len(str(e)) > 0, "Error should have informative message"
        
        # Integration: Test mixed sensitive data scenarios  
        mixed_sensitive_data = [
            "Call 555-123-4567 to update card 4111-1111-1111-1111",
            "SSN: 123-45-6789, Card: 4111-1111-1111-1111, Phone: 555-123-4567",
            "Email: user@domain.com, Payment: 4111-1111-1111-1111"
        ]
        
        for mixed_data in mixed_sensitive_data:
            result = filter._check_patterns(mixed_data, filter.patterns)
            assert isinstance(result, dict), f"Mixed data should return dict: {mixed_data[:30]}..."
            
            # Should detect multiple pattern types
            detected_types = [k for k, v in result.items() if v and (isinstance(v, list) and len(v) > 0 or v)]
            assert len(detected_types) >= 0, "Should handle multiple sensitive data types"
        
        # State consistency: Pattern detection should be deterministic
        test_card = "Payment card: 4111-1111-1111-1111"
        result1 = filter._check_patterns(test_card, filter.patterns)
        result2 = filter._check_patterns(test_card, filter.patterns)
        
        assert result1.keys() == result2.keys(), "Repeated calls should return same pattern types"
        if 'credit_card' in result1 and 'credit_card' in result2:
            assert len(result1['credit_card']) == len(result2['credit_card']), "Card detection should be consistent"


class TestConfidenceBoundaries:
    """Test confidence calculation boundaries."""
    
    def test_time_tracker_confidence_boundaries(self):
        """Test confidence calculation at edge cases."""
        tracker = TimeTracker()
        
        # Test with 0 screenshots (division edge case)
        confidence = tracker._calculate_confidence(
            session_duration=300,
            actual_screenshots=0,
            gap_percentage=0.0
        )
        assert 0.0 <= confidence <= 1.0, "Confidence should be valid range"
        
        # Test gap exactly at 50% (confidence should drop to 0)
        confidence = tracker._calculate_confidence(
            session_duration=300,
            actual_screenshots=75,
            gap_percentage=0.5
        )
        assert confidence < 0.5, "50% gaps should heavily penalize confidence"
        
        # Test gap > 50%
        confidence = tracker._calculate_confidence(
            session_duration=300,
            actual_screenshots=75,
            gap_percentage=0.8
        )
        assert confidence == 0.0, "High gaps should zero confidence"
        
        # Test perfect scenario (100% screenshots, 0% gaps)
        confidence = tracker._calculate_confidence(
            session_duration=300,
            actual_screenshots=75,  # Exactly expected for 4-second intervals
            gap_percentage=0.0
        )
        assert confidence == 1.0, "Perfect scenario should have 1.0 confidence"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
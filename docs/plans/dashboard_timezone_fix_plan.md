# Dashboard Timezone and Display Fix Plan

## Problem Summary
The AutoTaskTracker dashboard is not displaying correct data due to timezone mismatches between data storage and retrieval. Screenshots from 19:32 PDT are stored with timestamps of 03:32 UTC the next day, causing queries for "today" to return no results.

## Current Status
- [x] Metrics query fixed (removed hardcoded `and False`)
- [x] Cache cleared multiple times
- [x] OCR metadata added to 29+ screenshots
- [x] Window titles cleaned (removed tuple format)
- [ ] Dashboard still shows "Unknown Activity" for everything
- [ ] Timestamps display wrong time (10:15 instead of 19:15)
- [ ] No data retrieved due to timezone mismatch

## Root Cause Analysis
1. **Primary Issue**: Database timestamps are 8 hours in the future
   - Local time: 2025-07-06 19:32 PDT (UTC-7)
   - Stored as: 2025-07-07 03:32 UTC (should be 2025-07-07 02:32 UTC)
   - Extra hour added somewhere in the pipeline

2. **Secondary Issues**:
   - Repository queries use local time without proper conversion
   - Display formatting doesn't handle timezone correctly
   - Metrics section showing deprecation warning instead of data

## Step-by-Step Fix Plan

### Phase 1: Diagnostic and Temporary Fixes
- [ ] **1.1 Create diagnostic script** to identify exact timezone offset
  ```python
  # Compare filesystem timestamps with database timestamps
  # Identify where the extra hour is being added
  ```

- [ ] **1.2 Create temporary query fix** 
  - [ ] Modify TaskRepository to query with expanded time range
  - [ ] Add timezone offset compensation in SQL queries
  - [ ] Test that data is returned correctly

- [ ] **1.3 Fix deprecation warning**
  - [ ] Update Streamlit column width parameter
  - [ ] Ensure metrics display properly

### Phase 2: Repository Query Fixes
- [ ] **2.1 Update TaskRepository.get_tasks_for_period()**
  - [ ] Add timezone-aware query logic
  - [ ] Handle both UTC and local time queries
  - [ ] Add logging to track query ranges

- [ ] **2.2 Update MetricsRepository.get_metrics_summary()**
  - [ ] Ensure PostgreSQL adapter is used (not SQLite fallback)
  - [ ] Add timezone handling for date ranges
  - [ ] Cache results with proper TTL

- [ ] **2.3 Create timezone-aware date filter**
  - [ ] Update get_date_filter_options() to handle UTC data
  - [ ] Ensure "Today" filter captures correct range

### Phase 3: Data Storage Fix (Long-term)
- [ ] **3.1 Identify where timestamps are set**
  - [ ] Check Pensieve screenshot capture code
  - [ ] Verify PostgreSQL timezone settings
  - [ ] Find where extra hour is added

- [ ] **3.2 Fix timestamp storage**
  - [ ] Ensure UTC timestamps are stored correctly
  - [ ] Update existing data if needed
  - [ ] Add validation to prevent future issues

- [ ] **3.3 Create data migration script**
  - [ ] Correct existing timestamps in database
  - [ ] Preserve data integrity
  - [ ] Add rollback capability

### Phase 4: Display and Formatting
- [ ] **4.1 Fix timestamp display**
  - [ ] Update format_timestamp() in components/filters.py
  - [ ] Ensure proper UTC to local conversion
  - [ ] Test with various timezones

- [ ] **4.2 Verify screenshot grouping**
  - [ ] Confirm window titles are used for grouping
  - [ ] Test that correct screenshot is shown
  - [ ] Validate task assignment logic

### Phase 5: Testing and Validation
- [ ] **5.1 Create comprehensive test suite**
  - [ ] Test timezone conversions
  - [ ] Verify data retrieval for different time ranges
  - [ ] Check display formatting

- [ ] **5.2 Manual testing checklist**
  - [ ] Dashboard shows correct metrics (6,770+ activities)
  - [ ] Tasks grouped by window title (Chrome, Terminal, etc.)
  - [ ] Timestamps show correct local time
  - [ ] Screenshots match their task groups

## Pre-Mortem Analysis

### Potential Failure Points

1. **Query Fix Breaks Historical Data**
   - **Risk**: Changing query logic might make old data inaccessible
   - **Mitigation**: 
     - [ ] Create versioned query methods
     - [ ] Test with data from different time periods
     - [ ] Add fallback logic for old data format

2. **Timezone Fix Causes Data Loss**
   - **Risk**: Updating timestamps might corrupt data
   - **Mitigation**:
     - [ ] Create full database backup before changes
     - [ ] Test migration on copy of data first
     - [ ] Implement changes in transaction with rollback

3. **Cache Invalidation Issues**
   - **Risk**: Old data persists despite fixes
   - **Mitigation**:
     - [ ] Add cache version key
     - [ ] Implement force-refresh parameter
     - [ ] Create cache monitoring tools

4. **PostgreSQL Connection Issues**
   - **Risk**: Fallback to SQLite gives wrong results
   - **Mitigation**:
     - [ ] Add connection retry logic
     - [ ] Log when fallback occurs
     - [ ] Alert user about connection issues

5. **Incomplete Metadata Processing**
   - **Risk**: New screenshots don't get window titles
   - **Mitigation**:
     - [ ] Set up automated OCR processing
     - [ ] Monitor metadata completeness
     - [ ] Create manual processing fallback

6. **Performance Degradation**
   - **Risk**: Timezone conversions slow down queries
   - **Mitigation**:
     - [ ] Add database indexes on timestamp columns
     - [ ] Implement query result caching
     - [ ] Monitor query performance

## Implementation Order

1. **Immediate (Today)**:
   - Diagnostic script to understand exact timezone issue
   - Temporary query fix to show data
   - Fix deprecation warning

2. **Short-term (This Week)**:
   - Update repository queries with timezone handling
   - Fix timestamp display formatting
   - Verify screenshot grouping works

3. **Long-term (Next Week)**:
   - Fix root cause of timestamp storage
   - Migrate existing data
   - Set up automated monitoring

## Success Criteria

- [ ] Dashboard displays 6,770+ total activities
- [ ] Tasks are grouped by window title (not "Unknown Activity")
- [ ] Timestamps show correct local time (19:xx not 10:xx)
- [ ] Screenshots match their associated tasks
- [ ] No deprecation warnings or errors
- [ ] Data updates in real-time as new screenshots are taken

## Rollback Plan

If fixes cause issues:
1. Restore database from backup
2. Revert code changes via git
3. Clear all caches
4. Restart all services
5. Document what went wrong for next attempt

## Monitoring

After implementation:
- [ ] Set up alerts for timezone mismatches
- [ ] Monitor query performance
- [ ] Track metadata processing success rate
- [ ] Log cache hit/miss ratios
- [ ] Create daily data integrity checks
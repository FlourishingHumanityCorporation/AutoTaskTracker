# VLM (Vision Language Model) Analysis for AutoTaskTracker

## Executive Summary

After analyzing the AutoTaskTracker codebase, I've identified several key areas where VLM capabilities from Pensieve could significantly improve task detection and provide better context for discovered activities.

## Current State Analysis

### 1. Current Task Extraction Logic

The project currently relies on:
- **Window titles**: Primary source for task identification
- **OCR text**: Secondary source for extracting text from screenshots
- **Pattern matching**: Application-specific rules to interpret window titles

### 2. Limitations of Current Approach

1. **Missing Visual Context**: Cannot understand what's happening in the screenshot beyond text
2. **Poor handling of visual-heavy applications**: Design tools, video editors, games
3. **No understanding of UI state**: Can't detect if user is actively working or idle
4. **Limited context for ambiguous windows**: Generic window titles like "Untitled" or "New Tab"
5. **No detection of visual tasks**: Drawing, designing, reviewing images/videos

### 3. Database Structure

- Pensieve is configured with VLM support but the `builtin_vlm` plugin is disabled
- No VLM data currently exists in the database (0 records with VLM keys)
- Database structure supports additional metadata through `metadata_entries` table

## VLM Integration Opportunities

### 1. Enhanced Task Detection

VLM descriptions could provide:

```python
# Example VLM description patterns that would improve task detection:

"A code editor showing a Python file with a function definition for data processing"
→ Task: "Implementing data processing function in Python"

"A Figma design interface with a mobile app mockup showing a login screen"
→ Task: "Designing mobile app login interface in Figma"

"A terminal window running pytest with green test results"
→ Task: "Running and passing Python unit tests"

"A browser showing Stack Overflow with a JavaScript error solution"
→ Task: "Researching JavaScript error solution on Stack Overflow"
```

### 2. Specific Improvements by Category

#### A. Coding Tasks
- **Current**: Only knows window title (e.g., "main.py - MyProject - VS Code")
- **With VLM**: Could identify:
  - What type of code is being written
  - Whether user is debugging (presence of breakpoints/debug panel)
  - If tests are running (test output visible)
  - Code review activities (diff views)

#### B. Design Work
- **Current**: Limited to app name (e.g., "Figma", "Photoshop")
- **With VLM**: Could identify:
  - Type of design (UI mockup, logo, illustration)
  - Design stage (wireframe vs high-fidelity)
  - Specific components being worked on

#### C. Communication
- **Current**: Just knows the app (e.g., "Slack", "Gmail")
- **With VLM**: Could identify:
  - Whether actively typing vs reading
  - Type of communication (code review, meeting planning, support)

#### D. Research/Browsing
- **Current**: Limited to page titles
- **With VLM**: Could identify:
  - Type of content being consumed (documentation, tutorial, article)
  - Whether user is actively reading or just has tab open

### 3. Handling Edge Cases

VLM would excel at:

1. **Screenshots without OCR text**: Images, videos, diagrams
2. **Multiple activities in one screenshot**: Split screen scenarios
3. **Context from UI elements**: Button states, progress bars, notifications
4. **Idle detection**: Screensaver, lock screen, away status

## Implementation Recommendations

### 1. Enable VLM Plugin

```yaml
# In ~/.memos/config.yaml
default_plugins:
- builtin_ocr
- builtin_vlm  # Uncomment this line
```

### 2. Update Task Extraction Logic

```python
# Enhanced task extraction with VLM
def extract_task_with_vlm(window_title, ocr_text, vlm_description):
    # First try existing extraction
    task = extract_task(window_title, ocr_text)
    
    # If generic or unclear, use VLM description
    if task in ["Activity Captured", "Web browsing", "Other"]:
        if vlm_description:
            # Parse VLM description for task context
            task = parse_vlm_for_task(vlm_description)
    
    return task
```

### 3. Update Database Queries

```python
# Add VLM data to task fetch queries
query = """
SELECT
    e.id,
    e.filepath,
    me.value as ocr_text,
    me2.value as active_window,
    me3.value as vlm_description  -- New
FROM entities e
LEFT JOIN metadata_entries me ON e.id = me.entity_id AND me.key = 'ocr_result'
LEFT JOIN metadata_entries me2 ON e.id = me2.entity_id AND me2.key = 'active_window'
LEFT JOIN metadata_entries me3 ON e.id = me3.entity_id AND me3.key = 'vlm_result'  -- New
"""
```

### 4. Enhance Categorization

```python
# Use VLM for better categorization
def categorize_with_vlm(window_title, ocr_text, vlm_description):
    # Check VLM description for visual cues
    if vlm_description:
        vlm_lower = vlm_description.lower()
        
        # Design indicators
        if any(term in vlm_lower for term in ['mockup', 'wireframe', 'design', 'layout', 'ui elements']):
            return '🎨 Design'
        
        # Coding indicators
        if any(term in vlm_lower for term in ['code editor', 'function', 'debugging', 'terminal']):
            return '🧑‍💻 Coding'
        
        # Meeting indicators
        if any(term in vlm_lower for term in ['video call', 'participants', 'screen share']):
            return '🎥 Meetings'
    
    # Fall back to existing categorization
    return categorize_activity(window_title, ocr_text)
```

## Performance Considerations

1. **VLM Processing Load**: 
   - VLM is more computationally intensive than OCR
   - Consider using sparsity settings to process every Nth screenshot
   - Could process during idle times

2. **Storage Impact**:
   - VLM descriptions add ~100-500 bytes per screenshot
   - Minimal impact compared to image storage

3. **Suggested Configuration**:
```yaml
vlm:
  enabled: true
  concurrency: 4  # Lower than OCR due to higher compute
  modelname: minicpm-v  # Efficient model
  prompt: "Describe what the user is doing in this screenshot. Focus on the application, content type, and user activity."
```

## Privacy Considerations

VLM descriptions could capture more sensitive information:
- Consider local-only VLM models
- Add filtering for sensitive content
- Allow users to disable VLM for specific applications

## Conclusion

Enabling VLM capabilities would significantly improve AutoTaskTracker's ability to:
1. Understand visual tasks beyond text
2. Provide better context for ambiguous activities  
3. Handle edge cases where OCR fails
4. Detect idle vs active states
5. Categorize activities more accurately

The implementation requires minimal changes to the existing codebase while providing substantial improvements in task detection quality.
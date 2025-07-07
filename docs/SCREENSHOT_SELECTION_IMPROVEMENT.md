# Screenshot Selection Improvement Plan

## Current Issue
When multiple tasks are grouped together (e.g., different activities in the same application), the dashboard was showing the screenshot from the first task in the group, which might not be representative of the current activity.

## Quick Fix Applied
Changed from using the first task's screenshot to using the last (most recent) task's screenshot:
```python
# Before: 
screenshot_path = group.tasks[0].screenshot_path if group.tasks else None

# After:
screenshot_path = group.tasks[-1].screenshot_path if group.tasks else None
```

## Future Improvements

### 1. Screenshot Carousel
Allow users to browse through all screenshots in a task group:
```python
# In TaskGroupComponent.render()
if show_screenshot and len(tasks) > 1:
    selected_index = st.select_slider(
        "Screenshot", 
        options=range(len(tasks)),
        format_func=lambda i: f"{tasks[i].timestamp.strftime('%H:%M:%S')}"
    )
    screenshot_path = tasks[selected_index].screenshot_path
```

### 2. Smart Screenshot Selection
Select the most relevant screenshot based on:
- Task with the longest duration
- Task with the most AI-detected content
- Task that best matches the group title
- Middle task (median time) for better representation

### 3. Thumbnail Grid
Show multiple screenshots as thumbnails:
```python
if show_screenshot and len(tasks) > 1:
    cols = st.columns(min(4, len(tasks)))
    for i, (col, task) in enumerate(zip(cols, tasks[:4])):
        with col:
            if task.screenshot_path and os.path.exists(task.screenshot_path):
                img = Image.open(task.screenshot_path)
                img.thumbnail((100, 100))
                st.image(img, caption=task.timestamp.strftime('%H:%M'))
```

### 4. Context-Aware Selection
Match screenshot to the specific task being highlighted:
- When hovering over a task, show its screenshot
- When expanding task details, show the relevant screenshot
- Use AI to detect which screenshot best represents the task content

## Implementation Priority
1. ✅ Quick fix: Use most recent screenshot (DONE)
2. Screenshot carousel for easy browsing
3. Smart selection based on relevance
4. Thumbnail grid for overview
5. Context-aware dynamic selection
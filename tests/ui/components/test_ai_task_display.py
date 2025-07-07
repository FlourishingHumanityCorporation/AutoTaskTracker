"""Test cases for AI Task Display component.

This module contains unit and integration tests for the AI task display
functionality, including processing of real screenshots from the database.
"""

import os
import json
import pytest
from pathlib import Path
from typing import Dict, List, Any, Optional, Union
from unittest.mock import patch, MagicMock
import inspect
import logging
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import MagicMock, patch, call

import numpy as np
from PIL import Image, ImageDraw

# Add the project root to the Python path
import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

# Import test utilities
try:
    from tests.conftest import TEST_DATA_DIR
except ImportError:
    # Fallback if TEST_DATA_DIR is not defined in conftest
    TEST_DATA_DIR = Path(__file__).parent.parent.parent / "test_data"
    TEST_DATA_DIR.mkdir(exist_ok=True)

# Import the components to test
from autotasktracker.dashboards.components.ai_task_display import AITaskDisplay
from autotasktracker.core.database import DatabaseManager
from autotasktracker.core import TaskExtractor, DatabaseManager
from autotasktracker.ai import VLMTaskExtractor, OCREnhancer, AIEnhancedTaskExtractor
from autotasktracker.ai.vlm_processor import SmartVLMProcessor
from autotasktracker.core.task_extractor import TaskExtractor
from autotasktracker.ai.ocr_enhancement import OCREnhancer
from autotasktracker.ai.vlm_processor import SmartVLMProcessor
from autotasktracker.config import get_config

# Test configuration
TEST_SCREENSHOT_DIR = Path("/Users/paulrohde/AutoTaskTracker.memos/screenshots")
TEST_SCREENSHOT_LIMIT = 3  # Number of test screenshots to use

@pytest.fixture(scope="module")
def test_config():
    """Fixture to provide test configuration."""
    return get_config()


@pytest.fixture(scope="module")
def test_screenshots() -> List[Dict[str, Any]]:
    """Fixture to provide test screenshots with metadata."""
    return _get_recent_screenshots(limit=TEST_SCREENSHOT_LIMIT)


def _get_recent_screenshots(limit: int = 3) -> List[Dict[str, Any]]:
    """
    Get the most recent screenshots with metadata from the database.
    
    Args:
        limit: Maximum number of screenshots to return
        
    Returns:
        List of dictionaries containing screenshot metadata and paths
    """
    try:
        config = get_config()
        db_path = config.get_db_path()
        screenshots_dir = Path(config.get_screenshots_path())
        
        # If no database exists, return an empty list
        if not os.path.exists(db_path):
            return []
            
        # If no screenshots directory exists, return an empty list
        if not screenshots_dir.exists():
            return []
        
        # Initialize database connection
        db = DatabaseManager(db_path)
        
        # Query for recent screenshots with metadata
        query = """
        SELECT 
            e.id,
            e.filepath,
            e.created_at,
            me.value as active_window,
            (SELECT value FROM metadata_entries WHERE entity_id = e.id AND key = 'ocr_result' LIMIT 1) as ocr_result,
            (SELECT value FROM metadata_entries WHERE entity_id = e.id AND key = 'minicpm_v_result' LIMIT 1) as vlm_result
        FROM entities e
        LEFT JOIN metadata_entries me ON e.id = me.entity_id AND me.key = 'active_window'
        WHERE e.file_type = 'image/png'
        ORDER BY e.created_at DESC
        LIMIT ?
        """
        
        with db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, (limit,))
            rows = cursor.fetchall()
        
        # Process results
        screenshots = []
        for row in rows:
            try:
                # Convert filepath to absolute path if it's relative
                if row['filepath'] and not os.path.isabs(row['filepath']):
                    screenshot_path = os.path.join(screenshots_dir, row['filepath'])
                else:
                    screenshot_path = row['filepath']
                
                # Only include if file exists
                if os.path.exists(screenshot_path):
                    screenshots.append({
                        'id': row['id'],
                        'filepath': screenshot_path,
                        'created_at': row['created_at'],
                        'active_window': row['active_window'],
                        'ocr_result': row['ocr_result'],
                        'vlm_result': row['vlm_result']
                    })
            except Exception as e:
                st.error(f"Error processing screenshot {row.get('id')}: {e}")
        
        return screenshots
        
    except Exception as e:
        st.error(f"Error getting screenshots from database: {e}")
        return []

def _process_screenshot(screenshot_path: str, screenshot_metadata: Dict[str, Any]) -> Dict[str, Any]:
    """
    Process a single screenshot using the AI pipeline.
    
    Args:
        screenshot_path: Path to the screenshot image
        screenshot_metadata: Metadata from the database
        
    Returns:
        Dictionary with processed task data
    """
    try:
        # Initialize AI components
        task_extractor = TaskExtractor()
        vlm_processor = SmartVLMProcessor()
        ocr_enhancer = OCREnhancer()
        
        # Basic task extraction from window title
        window_title = screenshot_metadata.get('active_window', '')
        ocr_text = screenshot_metadata.get('ocr_result', '')
        
        # Process with VLM if not already done
        vlm_result = None
        if not screenshot_metadata.get('vlm_result'):
            vlm_result = vlm_processor.process_image(
                screenshot_path,
                window_title=window_title,
                ocr_text=ocr_text,
                entity_id=screenshot_metadata.get('id')
            )
        else:
            try:
                vlm_result = json.loads(screenshot_metadata['vlm_result'])
            except (json.JSONDecodeError, TypeError):
                vlm_result = None
        
        # Enhance OCR text if available
        ocr_enhancement = None
        if ocr_text:
            ocr_enhancement = ocr_enhancer.enhance_task_with_ocr(ocr_text, window_title)
        
        # Extract basic task info
        task_info = task_extractor.extract_task(window_title, ocr_text)
        
        # Prepare the task data structure
        task_data = {
            "id": f"screenshot_{screenshot_metadata.get('id', str(hash(screenshot_path)))}",
            "title": task_info.get('task', 'Untitled Task'),
            "timestamp": screenshot_metadata.get('created_at', None),
            "ocr_text": ocr_text,
            "screenshot_path": screenshot_path,
            "metadata": {
                "minicpm_v_result": vlm_result,
                "ocr_enhancement": ocr_enhancement,
                "window_title": window_title,
                "processing_time": 0.0
            },
            "tasks": []
        }
        
        # Add VLM-extracted tasks if available
        if vlm_result and 'subtasks' in vlm_result:
            for i, subtask in enumerate(vlm_result['subtasks'][:5]):  # Limit to 5 subtasks
                task_data["tasks"].append({
                    "id": f"subtask_{i+1}_{task_data['id']}",
                    "title": subtask.get('title', f"Task {i+1}"),
                    "status": subtask.get('status', 'pending'),
                    "priority": subtask.get('priority', 'medium'),
                    "due_date": subtask.get('due'),
                    "assignee": subtask.get('assignee'),
                    "confidence": float(vlm_result.get('confidence', 0.8))
                })
        
        return task_data
        
    except Exception as e:
        pytest.fail(f"Error processing screenshot {screenshot_path}: {e}")

def _load_image(image_path: Union[str, Image.Image]) -> Optional[Image.Image]:
    """Load an image from a path or return it if already an Image object.
    
    Args:
        image_path: Path to the image or Image object
        
    Returns:
        Loaded PIL Image or None if loading failed
    """
    try:
        if isinstance(image_path, str):
            if not os.path.exists(image_path):
                return None
            return Image.open(image_path)
        return image_path
    except Exception as e:
        pytest.fail(f"Error loading image: {e}")
        return None

def test_ai_task_display_init():
    """Test initialization of AITaskDisplay component."""
    # The AITaskDisplay is a class with static methods, so we don't need to instantiate it
    assert hasattr(AITaskDisplay, 'render_task_with_ai_insights')
    assert callable(AITaskDisplay.render_task_with_ai_insights)


def test_process_screenshot_with_real_data(test_screenshots):
    """Test processing of real screenshots from the database."""
    if not test_screenshots:
        pytest.skip("No screenshots found in the database")
    
    for screenshot in test_screenshots:
        task_data = _process_screenshot(
            screenshot['filepath'],
            {
                'id': screenshot['id'],
                'active_window': screenshot.get('active_window', ''),
                'ocr_result': screenshot.get('ocr_result', ''),
                'vlm_result': screenshot.get('vlm_result', ''),
                'created_at': screenshot.get('created_at', '')
            }
        )
        
        assert isinstance(task_data, dict)
        assert 'id' in task_data
        assert 'title' in task_data
        assert 'metadata' in task_data
        assert 'tasks' in task_data


def test_ai_task_display_render(test_screenshots, caplog):
    """Test rendering of AITaskDisplay with test data."""
    # Enable debug logging for this test
    caplog.set_level(logging.DEBUG)
    
    # Create test task data with all fields that the component expects
    task_data = {
        'title': 'Test Task',
        'status': 'pending',
        'timestamp': '2023-01-01T12:00:00',
        'metadata': {
            'processing_status': 'completed',
            'confidence': 0.9,
            'source': 'test',
            'tasks': [
                {'title': 'Subtask 1', 'status': 'pending'},
                {'title': 'Subtask 2', 'status': 'completed'}
            ],
            'vlm_result': {
                'confidence': 0.9,
                'extracted_tasks': ['Task 1', 'Task 2']
            }
        }
    }
    
    # Create a mock for the Streamlit module
    mock_st = MagicMock()
    
    # Mock the container context manager
    mock_container = MagicMock()
    mock_container_context = MagicMock()
    mock_container_context.__enter__.return_value = mock_container
    mock_container_context.__exit__.return_value = False
    mock_st.container.return_value = mock_container_context
    
    # Create a function to track calls to st.columns
    def track_columns_call(*args, **kwargs):
        logging.debug(f"st.columns called with args: {args}, kwargs: {kwargs}")
        mock_col1 = MagicMock()
        mock_col2 = MagicMock()
        return [mock_col1, mock_col2]
    
    # Set up the columns mock
    mock_st.columns.side_effect = track_columns_call
    
    # Create a simple mock for Streamlit with the methods we know are used
    mock_st = MagicMock()
    
    # Set up the container context manager
    mock_container = MagicMock()
    mock_container_context = MagicMock()
    mock_container_context.__enter__.return_value = mock_container
    mock_container_context.__exit__.return_value = False
    mock_st.container.return_value = mock_container_context
    
    # Set up the columns mock
    mock_col1 = MagicMock()
    mock_col2 = MagicMock()
    mock_st.columns.return_value = [mock_col1, mock_col2]
    
    # Set up the expander mock
    mock_expander = MagicMock()
    mock_st.expander.return_value = mock_expander
    
    # Set up other Streamlit methods that might be called
    mock_st.write = MagicMock()
    mock_st.markdown = MagicMock()
    mock_st.caption = MagicMock()
    mock_st.warning = MagicMock()
    mock_st.error = MagicMock()
    mock_st.info = MagicMock()
    mock_st.success = MagicMock()
    
    # Set up the expander's context manager
    mock_expander.__enter__.return_value = MagicMock()
    mock_expander.__exit__.return_value = False
    
    # Patch the streamlit module in the AITaskDisplay module
    with patch('autotasktracker.dashboards.components.ai_task_display.st', mock_st):
        logging.debug("About to call render_task_with_ai_insights")
        # Call the render method
        AITaskDisplay.render_task_with_ai_insights(task_data)
        logging.debug("Finished calling render_task_with_ai_insights")
        
        # Log all calls to the mock
        logging.debug("All calls to mock_st:")
        for call in mock_st.method_calls:
            logging.debug(f"  - {call}")
        
        # Verify the streamlit methods were called
        try:
            mock_st.container.assert_called_once()
            logging.debug("✅ mock_st.container was called once")
            
            # Verify columns were used to write content
            if mock_st.columns.called:
                logging.debug("✅ mock_st.columns was called")
                logging.debug(f"  - Call args: {mock_st.columns.call_args}")
            else:
                logging.error("❌ mock_st.columns was not called")
            
            # Check if any write or markdown calls were made
            for call in mock_st.method_calls:
                if call[0] in ('write', 'markdown'):
                    logging.debug(f"✅ Found {call[0]} call: {call}")
            
            # If we get here, the test passed
            logging.info("✅ All assertions passed")
            
        except AssertionError as e:
            logging.error(f"❌ Assertion failed: {e}")
            # Log the actual calls for debugging
            logging.error("Actual calls to mock_st:")
            for i, call in enumerate(mock_st.method_calls, 1):
                logging.error(f"  {i}. {call}")
            raise
    
    # If there are real screenshots, test with real data too
    if test_screenshots:
        # Process the first test screenshot
        screenshot = test_screenshots[0]
        real_task_data = _process_screenshot(
            screenshot['filepath'],
            {
                'id': screenshot['id'],
                'active_window': screenshot.get('active_window', ''),
                'ocr_result': screenshot.get('ocr_result', ''),
                'vlm_result': screenshot.get('vlm_result', ''),
                'created_at': screenshot.get('created_at', '')
            }
        )
        
        # Create a new set of mocks for the real data test
        mock_col1_real = MagicMock()
        mock_col2_real = MagicMock()
        mock_columns_real = MagicMock(return_value=[mock_col1_real, mock_col2_real])
        mock_container_real = MagicMock()
        mock_container_real.__enter__.return_value = None
        mock_container_real.columns.side_effect = mock_columns_real
        mock_st_real = MagicMock()
        mock_st_real.container.return_value = mock_container_real
        
        # Test rendering with real data
        with patch('autotasktracker.dashboards.components.ai_task_display.st', mock_st_real):
            AITaskDisplay.render_task_with_ai_insights(real_task_data)
            mock_st_real.container.assert_called_once()
            mock_container_real.columns.assert_called_once_with([1, 12])


def test_image_loading():
    """Test image loading functionality."""
    # Test with a non-existent path
    assert _load_image("/non/existent/path.jpg") is None
    
    # Create a test image if it doesn't exist
    test_image_path = TEST_DATA_DIR / "test_screenshot.png"
    if not test_image_path.exists():
        # Create a small test image
        img = Image.new('RGB', (100, 100), color='red')
        img.save(test_image_path)
    
    # Test with the valid image
    image = _load_image(str(test_image_path))
    assert isinstance(image, Image.Image)


@patch('autotasktracker.ai.vlm_processor.SmartVLMProcessor.process_image')
def test_vlm_processing(mock_process_image, test_screenshots):
    """Test VLM processing with mocked VLM processor."""
    if not test_screenshots:
        pytest.skip("No screenshots found in the database")
    
    # Setup mock
    mock_process_image.return_value = {
        'subtasks': [
            {'title': 'Test Subtask 1', 'status': 'pending'},
            {'title': 'Test Subtask 2', 'status': 'in_progress'}
        ],
        'confidence': 0.9
    }
    
    # Process a screenshot with the mocked VLM
    screenshot = test_screenshots[0]
    task_data = _process_screenshot(
        screenshot['filepath'],
        {
            'id': screenshot['id'],
            'active_window': 'Test Window',
            'ocr_result': 'Test OCR text',
            'vlm_result': None,
            'created_at': '2023-01-01T12:00:00'
        }
    )
    
    # Verify VLM was called and processed the result
    assert mock_process_image.called
    assert len(task_data.get('tasks', [])) > 0


def main():
    """Run the AI task display test dashboard with real-time processing."""
    st.set_page_config(
        page_title="AI Task Display - Real-time Processing",
        page_icon="🤖",
        layout="wide"
    )
    
    st.title("AI Task Display with Real-time Processing")
    
    # Sidebar controls
    with st.sidebar:
        st.header("Processing Options")
        use_ai_display = st.checkbox("Use AI-Enhanced View", value=True)
        show_raw = st.checkbox("Show Raw Data", value=False)
        show_screenshots = st.checkbox("Show Screenshots", value=True)
        process_new = st.checkbox("Process New Screenshots", value=True, 
                                help="Process new screenshots that haven't been analyzed yet")
        
        st.markdown("---")
        st.subheader("AI Settings")
        vlm_enabled = st.checkbox("Enable VLM Processing", value=True)
        ocr_enhancement = st.checkbox("Enable OCR Enhancement", value=True)
        
        st.markdown("---")
        st.subheader("Screenshot Info")
    
    # Get recent screenshots
    screenshots = get_recent_screenshots(limit=5)
    
    if not screenshots:
        st.warning("No screenshots found in the database.")
        st.info("To use this dashboard:")
        st.info("1. Make sure AutoTaskTracker is running")
        st.info("2. Take some screenshots using the AutoTaskTracker hotkey")
        st.info("3. Refresh this page to see the results")
        return
    
    with st.sidebar:
        st.info(f"Found {len(screenshots)} recent screenshots")
        st.caption(f"Latest: {os.path.basename(screenshots[0].get('filepath', 'No path'))}")
    
    # Process screenshots
    tasks = []
    with st.spinner(f"Processing {len(screenshots)} screenshots..."):
        progress_bar = st.progress(0)
        for i, screenshot in enumerate(screenshots):
            task = process_screenshot(
                screenshot['filepath'],
                screenshot_metadata={
                    'id': screenshot['id'],
                    'active_window': screenshot['active_window'],
                    'ocr_result': screenshot['ocr_result'],
                    'vlm_result': screenshot['vlm_result'],
                    'created_at': screenshot['created_at']
                }
            )
            if task:
                tasks.append(task)
            progress_bar.progress((i + 1) / len(screenshots))
        progress_bar.empty()
    
    if not tasks:
        st.error("No tasks could be extracted from the screenshots.")
        return
    
    # Group tasks by date for display
    tasks_by_date = {}
    for task in tasks:
        # Parse the timestamp
        try:
            if 'timestamp' in task:
                if isinstance(task['timestamp'], str):
                    task_date = datetime.fromisoformat(task['timestamp']).date()
                else:
                    task_date = task['timestamp'].date()
                
                if task_date not in tasks_by_date:
                    tasks_by_date[task_date] = []
                tasks_by_date[task_date].append(task)
        except Exception as e:
            st.error(f"Error processing task date: {e}")
    
    # Sort dates in descending order
    sorted_dates = sorted(tasks_by_date.keys(), reverse=True)
    
    # Display tasks grouped by date
    for date in sorted_dates:
        st.header(date.strftime("%A, %B %d, %Y"))
        
        for task in tasks_by_date[date]:
            # Create a card for each task
            with st.container():
                # Display the task header with timestamp and status
                col1, col2 = st.columns([1, 5])
                
                with col1:
                    # Show a thumbnail of the screenshot
                    if show_screenshots and task.get("screenshot_path"):
                        img = display_screenshot(
                            task["screenshot_path"],
                            caption=None,
                            use_column_width=True,
                            max_width=300
                        )
                
                with col2:
                    # Show task title and metadata
                    st.subheader(task["title"])
                    
                    # Show processing status
                    if 'metadata' in task and task['metadata'].get('minicpm_v_result'):
                        vlm_data = task['metadata']['minicpm_v_result']
                        if isinstance(vlm_data, dict):
                            confidence = vlm_data.get('confidence', 0) * 100
                            st.caption(f"Confidence: {confidence:.1f}% | "
                                     f"Processed: {task['timestamp'][11:19]}")
                    
                    # Show the main content
                    if use_ai_display:
                        # Use the AI-enhanced display component
                        AITaskDisplay.render_task(task)
                    else:
                        # Fallback to basic display
                        if task.get("tasks"):
                            st.subheader("Subtasks")
                            for subtask in task["tasks"][:5]:  # Limit to 5 subtasks
                                status_emoji = {
                                    "completed": "✅",
                                    "in_progress": "🔄",
                                    "pending": "⬜"
                                }.get(subtask.get("status", "pending"), "⬜")
                                
                                # Create a nice task card
                                with st.container():
                                    st.markdown(
                                        f"""
                                        <div style="
                                            border-left: 4px solid #4CAF50;
                                            padding: 0.5em 1em;
                                            margin: 0.5em 0;
                                            background: rgba(76, 175, 80, 0.05);
                                            border-radius: 0 8px 8px 0;
                                        ">
                                            <div style="display: flex; align-items: center;">
                                                <span style="font-size: 1.2em; margin-right: 0.5em;">
                                                    {status_emoji}
                                                </span>
                                                <div>
                                                    <strong>{subtask.get('title', 'Untitled')}</strong>
                                                    <div style="font-size: 0.8em; color: #666;">
                                                        {f"Priority: {subtask.get('priority', 'medium').title()}" if subtask.get('priority') else ''}
                                                        {f" | Due: {subtask.get('due_date', 'No due date')}" if subtask.get('due_date') else ''}
                                                        {f" | Assignee: {subtask.get('assignee')}" if subtask.get('assignee') else ''}
                                                    </div>
                                                </div>
                                            </div>
                                        </div>
                                        """,
                                        unsafe_allow_html=True
                                    )
                        
                        # Show OCR text in an expander
                        if task.get("ocr_text"):
                            with st.expander("View Extracted Text", expanded=False):
                                st.text_area("OCR Text", task["ocr_text"], height=200)
                
                # Raw data view
                if show_raw:
                    with st.expander("View Raw Data", expanded=False):
                        st.json({
                            k: v for k, v in task.items() 
                            if k not in ['screenshot_path', 'ocr_text']
                        })
                
                st.markdown("---")  # Divider between tasks

if __name__ == "__main__":
    # Run pytest with the current file
    import sys
    import pytest
    sys.exit(pytest.main(["-v", __file__]))

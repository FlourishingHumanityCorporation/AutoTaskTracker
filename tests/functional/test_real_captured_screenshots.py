#!/usr/bin/env python3
"""
Real captured screenshot tests using actual AutoTaskTracker screenshot data.
These tests validate extraction on REAL screenshots captured by the system.
"""

import json
import os
import sqlite3
import sys
import subprocess
from pathlib import Path
from typing import Any, Dict, List, Optional
import random

import pytest

# Add the project root to Python path for imports
REPO_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(REPO_ROOT))

from autotasktracker.core.database import DatabaseManager
from autotasktracker.core.task_extractor import TaskExtractor


class TestRealCapturedScreenshots:
    """Test extraction functionality using real captured screenshots."""
    
    @pytest.fixture
    def real_db_path(self) -> Optional[str]:
        """Get the real memos database path if it exists."""
        memos_db = Path.home() / ".memos" / "database.db"
        if memos_db.exists():
            return str(memos_db)
        else:
            pytest.skip("Real memos database not found - need actual AutoTaskTracker usage data")
    
    def test_real_screenshot_database_contains_actual_data(self, real_db_path):
        """Test that we have real screenshot data to work with."""
        conn = sqlite3.connect(real_db_path)
        conn.row_factory = sqlite3.Row
        
        # Check that we have actual screenshot entities
        cursor = conn.execute("""
            SELECT COUNT(*) as count 
            FROM entities 
            WHERE file_type_group = 'image'
        """)
        image_count = cursor.fetchone()['count']
        
        assert image_count > 0, f"Should have captured screenshots, found {image_count}"
        assert image_count > 10, f"Should have meaningful amount of data, found {image_count}"
        
        # Check that we have window title metadata
        cursor = conn.execute("""
            SELECT COUNT(*) as count 
            FROM entities e
            JOIN metadata_entries m ON e.id = m.entity_id 
            WHERE e.file_type_group = 'image' 
            AND m.key = 'active_window'
            AND m.value IS NOT NULL
            AND LENGTH(m.value) > 0
        """)
        window_title_count = cursor.fetchone()['count']
        
        assert window_title_count > 0, "Should have captured window titles from real usage"
        
        coverage_ratio = window_title_count / image_count
        assert coverage_ratio > 0.5, f"Should have window titles for most screenshots, got {coverage_ratio:.2%}"
        
        conn.close()
        print(f"✅ Found {image_count} real screenshots with {window_title_count} window titles")
    
    def test_real_screenshot_files_exist_and_accessible(self, real_db_path):
        """Test that the actual screenshot files exist and are readable."""
        conn = sqlite3.connect(real_db_path)
        conn.row_factory = sqlite3.Row
        
        # Get a sample of recent screenshots
        cursor = conn.execute("""
            SELECT e.filepath, e.created_at, m.value as window_title
            FROM entities e
            LEFT JOIN metadata_entries m ON e.id = m.entity_id AND m.key = 'active_window'
            WHERE e.file_type_group = 'image'
            ORDER BY e.created_at DESC
            LIMIT 10
        """)
        
        screenshots = cursor.fetchall()
        conn.close()
        
        assert len(screenshots) > 0, "Should have recent screenshots"
        
        accessible_files = 0
        file_sizes = []
        
        for screenshot in screenshots:
            filepath = screenshot['filepath']
            if filepath and Path(filepath).exists():
                accessible_files += 1
                file_size = Path(filepath).stat().st_size
                file_sizes.append(file_size)
                
                # Validate file is reasonable size (not corrupted)
                assert file_size > 1000, f"Screenshot file {filepath} seems too small: {file_size} bytes"
                assert file_size < 50_000_000, f"Screenshot file {filepath} seems too large: {file_size} bytes"
        
        accessibility_ratio = accessible_files / len(screenshots)
        assert accessibility_ratio > 0.7, f"Should be able to access most screenshot files, got {accessibility_ratio:.2%}"
        
        avg_size = sum(file_sizes) / len(file_sizes) if file_sizes else 0
        print(f"✅ Found {accessible_files}/{len(screenshots)} accessible files, avg size: {avg_size:,.0f} bytes")
    
    def test_task_extraction_on_real_captured_screenshots(self, real_db_path):
        """Test task extraction on actual captured screenshots with real window titles."""
        conn = sqlite3.connect(real_db_path)
        conn.row_factory = sqlite3.Row
        
        # Get real window titles from recent captures
        cursor = conn.execute("""
            SELECT DISTINCT m.value as window_title, COUNT(*) as frequency
            FROM entities e
            JOIN metadata_entries m ON e.id = m.entity_id 
            WHERE e.file_type_group = 'image' 
            AND m.key = 'active_window'
            AND m.value IS NOT NULL
            AND LENGTH(m.value) > 5
            AND e.created_at > datetime('now', '-7 days')
            GROUP BY m.value
            ORDER BY frequency DESC
            LIMIT 20
        """)
        
        real_window_titles = cursor.fetchall()
        conn.close()
        
        assert len(real_window_titles) > 0, "Should have real window titles from recent usage"
        
        # Test task extraction on real window titles
        extractor = TaskExtractor()
        extraction_results = []
        
        for row in real_window_titles:
            window_title = row['window_title']
            frequency = row['frequency']
            
            try:
                # Extract task using the actual implementation
                extracted_task = extractor.extract_task(window_title)
                
                # Validate extraction result
                assert isinstance(extracted_task, str), f"Task extraction should return string, got {type(extracted_task)}"
                assert len(extracted_task.strip()) > 0, f"Should extract non-empty task from: {window_title}"
                
                extraction_results.append({
                    'window_title': window_title,
                    'extracted_task': extracted_task,
                    'frequency': frequency
                })
                
            except Exception as e:
                pytest.fail(f"Task extraction failed on real window title '{window_title}': {e}")
        
        # Validate that extraction produced meaningful results
        assert len(extraction_results) > 0, "Should successfully extract tasks from real window titles"
        
        # Check for variety in extracted tasks (not all "Unknown")
        unique_tasks = set(result['extracted_task'] for result in extraction_results)
        assert len(unique_tasks) > 1, f"Should extract variety of tasks, got: {unique_tasks}"
        
        # Check that we're not getting all "Unknown" tasks
        unknown_ratio = sum(1 for result in extraction_results 
                          if 'unknown' in result['extracted_task'].lower()) / len(extraction_results)
        assert unknown_ratio < 0.8, f"Too many unknown tasks ({unknown_ratio:.2%}), extraction may not be working well"
        
        print(f"✅ Successfully extracted tasks from {len(extraction_results)} real window titles")
        print(f"✅ Found {len(unique_tasks)} unique task types")
        print(f"✅ Unknown task ratio: {unknown_ratio:.2%}")
        
        # Show sample results
        for result in extraction_results[:5]:
            print(f"   '{result['window_title'][:60]}...' → '{result['extracted_task']}' (seen {result['frequency']}x)")
    
    def test_ocr_extraction_on_real_captured_screenshots(self, real_db_path):
        """Test OCR extraction on actual captured screenshot files."""
        conn = sqlite3.connect(real_db_path)
        conn.row_factory = sqlite3.Row
        
        # Get screenshots that have OCR data
        cursor = conn.execute("""
            SELECT e.filepath, e.id, m.value as ocr_text, m2.value as window_title
            FROM entities e
            JOIN metadata_entries m ON e.id = m.entity_id AND m.key = 'text'
            LEFT JOIN metadata_entries m2 ON e.id = m2.entity_id AND m2.key = 'active_window'
            WHERE e.file_type_group = 'image'
            AND m.value IS NOT NULL
            AND LENGTH(m.value) > 10
            ORDER BY e.created_at DESC
            LIMIT 10
        """)
        
        ocr_screenshots = cursor.fetchall()
        conn.close()
        
        if len(ocr_screenshots) == 0:
            pytest.skip("No screenshots with OCR data found - may need to run OCR processing first")
        
        ocr_results = []
        for screenshot in ocr_screenshots:
            filepath = screenshot['filepath']
            ocr_text = screenshot['ocr_text']
            window_title = screenshot['window_title']
            
            # Validate OCR data structure
            try:
                if ocr_text.startswith('['):
                    # OCR data is in list format
                    ocr_data = eval(ocr_text)  # Note: eval is safe here as this is test data we control
                    assert isinstance(ocr_data, list), "OCR data should be a list"
                    
                    if len(ocr_data) > 0:
                        # Extract text content
                        text_content = []
                        for item in ocr_data:
                            if isinstance(item, list) and len(item) >= 2:
                                text_content.append(str(item[1]))
                        
                        combined_text = " ".join(text_content).strip()
                        
                        ocr_results.append({
                            'filepath': filepath,
                            'window_title': window_title,
                            'text_regions': len(ocr_data),
                            'text_content': combined_text[:200] + "..." if len(combined_text) > 200 else combined_text
                        })
                
            except Exception as e:
                # OCR data might be in different format, that's okay for some entries
                pass
        
        if len(ocr_results) == 0:
            pytest.skip("No valid OCR data found in expected format")
        
        # Validate OCR results
        assert len(ocr_results) > 0, "Should have successfully parsed OCR data from real screenshots"
        
        # Check that OCR found meaningful text
        non_empty_ocr = [r for r in ocr_results if len(r['text_content'].strip()) > 0]
        assert len(non_empty_ocr) > 0, "Should have OCR results with actual text content"
        
        print(f"✅ Found OCR data in {len(ocr_results)} real screenshots")
        print(f"✅ {len(non_empty_ocr)} screenshots have meaningful text content")
        
        # Show sample OCR results
        for result in ocr_results[:3]:
            print(f"   File: {Path(result['filepath']).name}")
            print(f"   Window: {result['window_title'][:60]}...")
            print(f"   OCR Regions: {result['text_regions']}")
            print(f"   Sample Text: {result['text_content'][:100]}...")
            print()
    
    def test_ai_task_classification_on_real_data(self, real_db_path):
        """Test AI task classification on real captured data."""
        conn = sqlite3.connect(real_db_path)
        conn.row_factory = sqlite3.Row
        
        # Get screenshots with AI task classification
        cursor = conn.execute("""
            SELECT m.value as ai_task, m2.value as window_title, COUNT(*) as frequency
            FROM entities e
            JOIN metadata_entries m ON e.id = m.entity_id AND m.key = 'tasks'
            LEFT JOIN metadata_entries m2 ON e.id = m2.entity_id AND m2.key = 'active_window'
            WHERE e.file_type_group = 'image'
            AND m.value IS NOT NULL
            AND LENGTH(m.value) > 3
            GROUP BY m.value, m2.value
            ORDER BY frequency DESC
            LIMIT 15
        """)
        
        ai_classifications = cursor.fetchall()
        conn.close()
        
        if len(ai_classifications) == 0:
            pytest.skip("No AI task classifications found - may need to run AI processing first")
        
        # Validate AI classifications
        assert len(ai_classifications) > 0, "Should have AI task classifications from real data"
        
        # Check for variety in AI classifications
        unique_tasks = set(row['ai_task'] for row in ai_classifications)
        assert len(unique_tasks) > 1, f"Should have variety in AI classifications, got: {unique_tasks}"
        
        # Validate classification quality
        meaningful_classifications = []
        for row in ai_classifications:
            ai_task = row['ai_task']
            window_title = row['window_title'] or ""
            frequency = row['frequency']
            
            # Check that classification is meaningful (not just empty or generic)
            if len(ai_task.strip()) > 3 and 'unknown' not in ai_task.lower():
                meaningful_classifications.append({
                    'ai_task': ai_task,
                    'window_title': window_title,
                    'frequency': frequency
                })
        
        meaningful_ratio = len(meaningful_classifications) / len(ai_classifications)
        assert meaningful_ratio > 0.3, f"Should have meaningful AI classifications, got {meaningful_ratio:.2%}"
        
        print(f"✅ Found {len(ai_classifications)} AI task classifications")
        print(f"✅ {len(unique_tasks)} unique AI task types")
        print(f"✅ Meaningful classification ratio: {meaningful_ratio:.2%}")
        
        # Show sample AI classifications
        for result in meaningful_classifications[:5]:
            print(f"   AI Task: '{result['ai_task']}'")
            print(f"   Window: '{result['window_title'][:60]}...'")
            print(f"   Frequency: {result['frequency']}x")
            print()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
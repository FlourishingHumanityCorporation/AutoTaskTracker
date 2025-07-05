#!/usr/bin/env python3
"""
VLM (Visual Language Model) processor for AutoTaskTracker.
Analyzes screenshots using Ollama's minicpm-v model for richer task understanding.
"""
import sys
import os
import sqlite3
import logging
import requests
import json
import base64
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class VLMProcessor:
    """Process screenshots with Visual Language Model."""
    
    def __init__(self, model: str = "minicpm-v:latest", ollama_url: str = "http://localhost:11434"):
        self.db_path = os.path.expanduser("~/.memos/database.db")
        self.screenshots_dir = os.path.expanduser("~/.memos/screenshots")
        self.model = model
        self.ollama_url = ollama_url
        self.processed_count = 0
        
        # Test Ollama connection
        if not self._test_ollama_connection():
            logger.warning("Ollama not available. Make sure it's running: ollama serve")
    
    def _test_ollama_connection(self) -> bool:
        """Test if Ollama is running and model is available."""
        try:
            # Check if Ollama is running
            response = requests.get(f"{self.ollama_url}/api/tags")
            if response.status_code != 200:
                return False
            
            # Check if model is available
            models = response.json().get('models', [])
            model_names = [m['name'] for m in models]
            
            if self.model not in model_names:
                logger.error(f"Model {self.model} not found. Available: {model_names}")
                return False
            
            logger.info(f"Ollama connected with model {self.model}")
            return True
            
        except Exception as e:
            logger.error(f"Ollama connection failed: {e}")
            return False
    
    def get_unprocessed_screenshots(self, limit: int = 10) -> List[Dict]:
        """Get screenshots that haven't been VLM processed."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            # Find entities without VLM processing
            cursor.execute("""
                SELECT e.id, e.filepath, m_window.value as window_title, m_task.value as task
                FROM entities e
                LEFT JOIN metadata_entries m_window ON e.id = m_window.entity_id AND m_window.key = 'active_window'
                LEFT JOIN metadata_entries m_task ON e.id = m_task.entity_id AND m_task.key = 'tasks'
                LEFT JOIN metadata_entries m_vlm ON e.id = m_vlm.entity_id AND m_vlm.key = 'vlm_analysis'
                WHERE m_vlm.id IS NULL
                AND e.created_at > datetime('now', '-7 days')
                ORDER BY e.created_at DESC
                LIMIT ?
            """, (limit,))
            
            screenshots = []
            for row in cursor.fetchall():
                screenshots.append({
                    'id': row[0],
                    'filepath': row[1],
                    "active_window": row[2],
                    "tasks": row[3]
                })
            
            return screenshots
            
        finally:
            conn.close()
    
    def _encode_image(self, image_path: str) -> Optional[str]:
        """Encode image to base64."""
        try:
            # The filepath in database already includes the full path structure
            full_path = os.path.join(self.screenshots_dir, image_path)
            if not os.path.exists(full_path):
                # Try without screenshots dir prefix
                full_path = image_path
                if not os.path.exists(full_path):
                    logger.debug(f"Image not found at: {image_path}")
                    return None
            
            with open(full_path, 'rb') as f:
                return base64.b64encode(f.read()).decode('utf-8')
                
        except Exception as e:
            logger.error(f"Error encoding image {image_path}: {e}")
            return None
    
    def analyze_screenshot(self, screenshot: Dict) -> Optional[Dict]:
        """Analyze a screenshot with VLM."""
        image_base64 = self._encode_image(screenshot['filepath'])
        if not image_base64:
            logger.warning(f"Could not encode image: {screenshot['filepath']}")
            return None
        
        # Prepare prompt
        window_title = screenshot.get("active_window", 'Unknown')
        task = screenshot.get("tasks", 'Unknown task')
        
        prompt = f"""Analyze this screenshot and provide insights about the user's activity.
Context: Window title is "{window_title}", extracted task is "{task}".

Please identify:
1. What specific work is being done (be detailed)
2. Any visible progress indicators or status
3. Key UI elements or content visible
4. Suggested more specific task description
5. Any patterns or workflow indicators

Be concise but specific. Focus on actionable insights."""
        
        try:
            # Call Ollama API
            response = requests.post(
                f"{self.ollama_url}/api/generate",
                json={
                    "model": self.model,
                    "prompt": prompt,
                    "images": [image_base64],
                    "stream": False
                },
                timeout=30
            )
            
            if response.status_code != 200:
                logger.error(f"Ollama API error: {response.status_code}")
                return None
            
            result = response.json()
            analysis = result.get('response', '')
            
            if not analysis:
                return None
            
            # Structure the response
            return {
                'raw_analysis': analysis,
                'model': self.model,
                'timestamp': datetime.now().isoformat(),
                'confidence': 0.8  # Could be calculated based on response quality
            }
            
        except Exception as e:
            logger.error(f"VLM analysis failed: {e}")
            return None
    
    def save_vlm_analysis(self, entity_id: int, analysis: Dict) -> bool:
        """Save VLM analysis to database."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            # Save raw analysis
            cursor.execute("""
                INSERT INTO metadata_entries 
                (entity_id, key, value, source_type, data_type, created_at, updated_at)
                VALUES (?, 'vlm_analysis', ?, 'vlm_processor', 'json', datetime('now'), datetime('now'))
            """, (entity_id, json.dumps(analysis)))
            
            # Extract and save enhanced task if found
            if 'raw_analysis' in analysis:
                # Simple extraction - look for task-like descriptions
                lines = analysis['raw_analysis'].split('\n')
                for line in lines:
                    if "tasks" in line.lower() or 'working on' in line.lower():
                        enhanced_task = line.split(':', 1)[-1].strip()
                        if enhanced_task:
                            cursor.execute("""
                                INSERT INTO metadata_entries 
                                (entity_id, key, value, source_type, data_type, created_at, updated_at)
                                VALUES (?, 'vlm_task', ?, 'vlm_processor', 'text', datetime('now'), datetime('now'))
                            """, (entity_id, enhanced_task))
                            break
            
            conn.commit()
            return True
            
        except Exception as e:
            logger.error(f"Error saving VLM analysis: {e}")
            return False
        finally:
            conn.close()
    
    def process_batch(self, limit: int = 10) -> int:
        """Process a batch of screenshots."""
        screenshots = self.get_unprocessed_screenshots(limit)
        
        if not screenshots:
            logger.info("No unprocessed screenshots found")
            return 0
        
        logger.info(f"Processing {len(screenshots)} screenshots with VLM...")
        
        processed = 0
        for screenshot in screenshots:
            logger.info(f"Analyzing: {screenshot["tasks"]}")
            
            analysis = self.analyze_screenshot(screenshot)
            if analysis:
                if self.save_vlm_analysis(screenshot['id'], analysis):
                    processed += 1
                    self.processed_count += 1
                    logger.info(f"  ✓ Analysis saved")
                else:
                    logger.error(f"  ✗ Failed to save analysis")
            else:
                logger.warning(f"  ✗ Analysis failed")
        
        logger.info(f"Batch complete: {processed}/{len(screenshots)} processed")
        return processed
    
    def show_sample_results(self, limit: int = 5):
        """Show sample VLM analysis results."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute("""
                SELECT 
                    e.created_at,
                    m_task.value as task,
                    m_vlm.value as vlm_analysis
                FROM entities e
                JOIN metadata_entries m_task ON e.id = m_task.entity_id AND m_task.key = 'tasks'
                JOIN metadata_entries m_vlm ON e.id = m_vlm.entity_id AND m_vlm.key = 'vlm_analysis'
                ORDER BY e.created_at DESC
                LIMIT ?
            """, (limit,))
            
            results = cursor.fetchall()
            
            print(f"\n=== Sample VLM Analysis Results ({len(results)}) ===")
            for created_at, task, vlm_json in results:
                vlm_data = json.loads(vlm_json)
                print(f"\nTime: {created_at}")
                print(f"Task: {task}")
                print(f"VLM Analysis:")
                print(vlm_data.get('raw_analysis', 'No analysis')[:200] + "...")
                print("-" * 80)
                
        finally:
            conn.close()


def main():
    """Main entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(description='VLM processor for screenshots')
    parser.add_argument('--batch', type=int, default=10,
                        help='Number of screenshots to process (default: 10)')
    parser.add_argument('--sample', action='store_true',
                        help='Show sample results')
    parser.add_argument('--continuous', action='store_true',
                        help='Run continuously')
    
    args = parser.parse_args()
    
    processor = VLMProcessor()
    
    if args.sample:
        processor.show_sample_results()
    elif args.continuous:
        logger.info("Starting continuous VLM processing...")
        while True:
            processed = processor.process_batch(args.batch)
            if processed == 0:
                logger.info("No more screenshots to process. Waiting 60s...")
                import time
                time.sleep(60)
    else:
        processor.process_batch(args.batch)
        logger.info(f"Total processed: {processor.processed_count}")


if __name__ == "__main__":
    main()
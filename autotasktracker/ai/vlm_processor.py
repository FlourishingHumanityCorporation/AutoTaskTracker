"""
Smart VLM Processor with deduplication, caching, and optimized processing.
"""
import hashlib
import json
import logging
import time
import sys
import threading
from pathlib import Path
from typing import Dict, Optional, List, Tuple
from datetime import datetime, timedelta
from collections import OrderedDict, deque
import numpy as np
from PIL import Image
import imagehash
import requests
from autotasktracker.config import get_config
from autotasktracker.core.error_handler import (
    vlm_error_handler, measure_latency, get_error_handler, get_metrics, get_health_monitor
)
from autotasktracker.ai.sensitive_filter import get_sensitive_filter

logger = logging.getLogger(__name__)


class SmartVLMProcessor:
    """Intelligent VLM processor with caching and deduplication."""
    
    def __init__(self, db_path: str = None, cache_dir: str = None):
        """Initialize the smart VLM processor."""
        config = get_config()
        self.db_path = db_path or config.get_db_path()
        self.cache_dir = Path(cache_dir or config.get_vlm_cache_path())
        self.cache_dir.mkdir(exist_ok=True)
        self.vlm_model = config.vlm_model
        self.vlm_port = config.vlm_port
        
        # Initialize caches with memory management
        self.hash_cache = {}  # image_path -> perceptual_hash
        self.result_cache = {}  # hash -> vlm_result
        self.processing_times = []  # Track processing times
        
        # LRU cache for images with memory limits
        self.image_cache = OrderedDict()  # path -> base64 encoded image
        self.max_cache_size_mb = 100  # Maximum cache size in MB
        self.max_cache_items = 50  # Maximum number of cached items
        self.current_cache_size = 0  # Current cache size in bytes
        self.cache_lock = threading.Lock()  # Thread safety for cache operations
        
        # Load cache from disk
        self._load_cache()
        
        # Initialize connection session for better performance
        self.session = requests.Session()
        self.session.headers.update({'Content-Type': 'application/json'})
        
        # Rate limiting and circuit breaker
        self.rate_limiter = RateLimiter(max_requests=5, time_window=60)  # 5 req/min
        self.circuit_breaker = CircuitBreaker(
            failure_threshold=3,
            recovery_timeout=60,
            expected_exception=requests.RequestException
        )
        
        # Error handling, metrics, and privacy
        self.error_handler = get_error_handler()
        self.metrics = get_metrics()
        self.sensitive_filter = get_sensitive_filter()
        
        # Task-specific prompts
        self.task_prompts = {
            'IDE': "Analyze this IDE screenshot. Describe: 1) What file is being edited 2) Programming language 3) Any visible errors or debugging 4) Code structure visible 5) Project context from file tree",
            'Terminal': "Analyze this terminal screenshot. Describe: 1) Commands being run 2) Output or errors visible 3) Current directory 4) Task being performed",
            'Browser': "Analyze this browser screenshot. Describe: 1) Website/application 2) Content being viewed 3) User task (reading/searching/etc) 4) Any forms or interactions",
            'Meeting': "Analyze this video meeting screenshot. Describe: 1) Meeting platform 2) Number of participants 3) Shared screen content 4) Meeting context",
            'Document': "Analyze this document screenshot. Describe: 1) Document type 2) Content/topic 3) Editing or reading mode 4) Progress indicators",
            'Chat': "Analyze this chat screenshot. Describe: 1) Chat application 2) Conversation context 3) Active discussions 4) Work-related topics",
            'Default': "Describe this screenshot including: 1) Application type 2) Main activity 3) UI elements 4) Task context 5) Any progress indicators or status"
        }
        
    def _load_cache(self):
        """Load cache from disk."""
        cache_file = self.cache_dir / 'vlm_cache.json'
        if cache_file.exists():
            try:
                with open(cache_file, 'r') as f:
                    data = json.load(f)
                    self.result_cache = data.get('results', {})
                    logger.info(f"Loaded {len(self.result_cache)} cached VLM results")
            except Exception as e:
                logger.error(f"Failed to load cache: {e}")
    
    def _save_cache(self):
        """Save cache to disk."""
        cache_file = self.cache_dir / 'vlm_cache.json'
        try:
            with open(cache_file, 'w') as f:
                json.dump({
                    'results': self.result_cache,
                    'updated': datetime.now().isoformat()
                }, f)
        except Exception as e:
            logger.error(f"Failed to save cache: {e}")
    
    def get_image_hash(self, image_path: str) -> str:
        """Get perceptual hash of image for deduplication."""
        if image_path in self.hash_cache:
            return self.hash_cache[image_path]
        
        try:
            # Use perceptual hash for similarity detection
            img = Image.open(image_path)
            # Resize for consistent hashing
            img = img.resize((256, 256), Image.Resampling.LANCZOS)
            # Get multiple hash types for better matching
            dhash = str(imagehash.dhash(img))
            phash = str(imagehash.phash(img))
            combined_hash = f"{dhash}_{phash}"
            
            self.hash_cache[image_path] = combined_hash
            return combined_hash
        except Exception as e:
            logger.error(f"Failed to hash image {image_path}: {e}")
            # Fallback to file hash
            return hashlib.md5(Path(image_path).read_bytes()).hexdigest()
    
    def is_similar_to_recent(self, image_path: str, threshold: float = 0.95) -> bool:
        """Check if image is similar to recently processed images."""
        current_hash = self.get_image_hash(image_path)
        
        # Check against recent results
        for cached_hash in list(self.result_cache.keys())[-10:]:  # Last 10 processed
            if self._calculate_similarity(current_hash, cached_hash) > threshold:
                logger.debug(f"Image similar to recent: {image_path}")
                return True
        
        return False
    
    def _calculate_similarity(self, hash1: str, hash2: str) -> float:
        """Calculate similarity between two image hashes."""
        if hash1 == hash2:
            return 1.0
        
        try:
            # Split combined hashes
            dhash1, phash1 = hash1.split('_')
            dhash2, phash2 = hash2.split('_')
            
            # Calculate hamming distance
            d_dist = bin(int(dhash1, 16) ^ int(dhash2, 16)).count('1')
            p_dist = bin(int(phash1, 16) ^ int(phash2, 16)).count('1')
            
            # Convert to similarity (0-1)
            d_sim = 1 - (d_dist / 64)  # 64 bits in dhash
            p_sim = 1 - (p_dist / 64)  # 64 bits in phash
            
            return (d_sim + p_sim) / 2
        except (ValueError, IndexError) as e:
            logger.debug(f"Error calculating similarity: {e}")
            return 0.0
    
    def detect_application_type(self, window_title: str, ocr_text: str = None) -> str:
        """Detect application type for task-specific prompts."""
        window_lower = window_title.lower() if window_title else ""
        
        # IDE detection
        ide_keywords = ['code', 'pycharm', 'intellij', 'visual studio', 'sublime', 'atom', 'vim', 'emacs', 'neovim']
        if any(kw in window_lower for kw in ide_keywords):
            return 'IDE'
        
        # Terminal detection
        terminal_keywords = ['terminal', 'console', 'shell', 'iterm', 'powershell', 'cmd']
        if any(kw in window_lower for kw in terminal_keywords):
            return 'Terminal'
        
        # Browser detection
        browser_keywords = ['chrome', 'firefox', 'safari', 'edge', 'brave', 'opera']
        if any(kw in window_lower for kw in browser_keywords):
            return 'Browser'
        
        # Meeting detection
        meeting_keywords = ['zoom', 'teams', 'meet', 'skype', 'webex', 'slack huddle']
        if any(kw in window_lower for kw in meeting_keywords):
            return 'Meeting'
        
        # Document detection
        doc_keywords = ['word', 'docs', 'pages', 'writer', 'document', '.docx', '.pdf']
        if any(kw in window_lower for kw in doc_keywords):
            return 'Document'
        
        # Chat detection
        chat_keywords = ['slack', 'discord', 'telegram', 'whatsapp', 'messages']
        if any(kw in window_lower for kw in chat_keywords):
            return 'Chat'
        
        return 'Default'
    
    def should_process(self, image_path: str, window_title: str = None, entity_id: str = None, 
                      ocr_text: str = None) -> Tuple[bool, str]:
        """
        Determine if screenshot should be processed by VLM (without atomic locking).
        
        Note: This method only checks conditions, it does NOT insert processing flags.
        The atomic locking happens in process_image() when actually starting processing.
        
        Returns:
            Tuple of (should_process, reason)
        """
        # Check if already cached
        img_hash = self.get_image_hash(image_path)
        if img_hash in self.result_cache:
            return False, "cached"
        
        # Privacy/sensitivity check first
        should_process_privacy, sensitivity_score, scan_results = self.sensitive_filter.should_process_image(
            image_path, window_title, ocr_text
        )
        if not should_process_privacy:
            self.metrics.increment_counter('privacy_blocked')
            return False, "sensitive_content"
        
        # Check if already has VLM results (but don't insert processing flag yet)
        if entity_id and self._has_existing_vlm_results(entity_id):
            return False, "already_processed"
        
        # Check if similar to recent
        if self.is_similar_to_recent(image_path):
            return False, "similar_to_recent"
        
        # Skip static windows (no activity)
        static_windows = ['desktop', 'finder', 'explorer.exe']
        if window_title and any(sw in window_title.lower() for sw in static_windows):
            return False, "static_window"
        
        return True, "process"
    
    def _has_existing_vlm_results(self, entity_id: str) -> bool:
        """Check if entity already has VLM results (non-atomic check)."""
        from autotasktracker.core.database import DatabaseManager
        
        try:
            db = DatabaseManager()
            with db.get_connection() as conn:
                cursor = conn.cursor()
                
                # Check for existing VLM results (excluding processing flags)
                cursor.execute("""
                    SELECT 1 FROM metadata_entries 
                    WHERE entity_id = ? AND key IN ('minicpm_v_result', 'vlm_structured', 'vlm_description')
                    LIMIT 1
                """, (entity_id,))
                
                return cursor.fetchone() is not None
                
        except Exception as e:
            logger.error(f"Error checking existing VLM results: {e}")
            return True  # Be conservative - assume it exists if unsure
    
    def _try_acquire_processing_lock(self, entity_id: str) -> bool:
        """Atomically try to acquire processing lock for entity."""
        from autotasktracker.core.database import DatabaseManager
        
        try:
            db = DatabaseManager()
            with db.get_connection(readonly=False) as conn:
                cursor = conn.cursor()
                
                # Check for existing VLM results first
                cursor.execute("""
                    SELECT 1 FROM metadata_entries 
                    WHERE entity_id = ? AND key IN ('minicpm_v_result', 'vlm_structured', 'vlm_description')
                    LIMIT 1
                """, (entity_id,))
                
                if cursor.fetchone():
                    logger.debug(f"Entity {entity_id} already has VLM results")
                    return False
                
                # Check for existing processing flag
                cursor.execute("""
                    SELECT 1 FROM metadata_entries 
                    WHERE entity_id = ? AND key = 'vlm_processing'
                    LIMIT 1
                """, (entity_id,))
                
                if cursor.fetchone():
                    logger.debug(f"Entity {entity_id} already being processed")
                    return False
                
                # Atomically insert processing flag
                cursor.execute("""
                    INSERT INTO metadata_entries 
                    (entity_id, key, value, source_type, data_type, created_at, updated_at) 
                    VALUES (?, ?, ?, 'vlm', 'text', datetime('now'), datetime('now'))
                """, (entity_id, 'vlm_processing', 'in_progress'))
                
                conn.commit()
                logger.debug(f"Acquired processing lock for entity {entity_id}")
                return True
                    
        except Exception as e:
            logger.error(f"Error acquiring processing lock for {entity_id}: {e}")
            return False
    
    def _mark_processing_complete(self, entity_id: str, success: bool = True):
        """Mark processing as complete and remove processing flag."""
        from autotasktracker.core.database import DatabaseManager
        
        try:
            db = DatabaseManager()
            with db.get_connection(readonly=False) as conn:
                cursor = conn.cursor()
                
                if success:
                    # Remove processing flag
                    cursor.execute("""
                        DELETE FROM metadata_entries 
                        WHERE entity_id = ? AND key = 'vlm_processing'
                    """, (entity_id,))
                else:
                    # Update to failed status
                    cursor.execute("""
                        UPDATE metadata_entries 
                        SET value = 'failed', updated_at = datetime('now')
                        WHERE entity_id = ? AND key = 'vlm_processing'
                    """, (entity_id,))
                
                conn.commit()
                
        except Exception as e:
            logger.error(f"Error marking processing complete: {e}")
    
    def _save_vlm_result_to_db(self, entity_id: str, structured_result: Dict):
        """Save VLM result to database."""
        from autotasktracker.core.database import DatabaseManager
        import json
        
        try:
            db = DatabaseManager()
            with db.get_connection(readonly=False) as conn:
                cursor = conn.cursor()
                
                # Save structured VLM result
                cursor.execute("""
                    INSERT OR REPLACE INTO metadata_entries 
                    (entity_id, key, value, source_type, data_type, created_at, updated_at) 
                    VALUES (?, ?, ?, 'vlm', 'json', datetime('now'), datetime('now'))
                """, (entity_id, 'vlm_description', json.dumps(structured_result)))
                
                conn.commit()
                logger.debug(f"Saved VLM result to database for entity {entity_id}")
                
        except Exception as e:
            logger.error(f"Error saving VLM result to database for {entity_id}: {e}")
    
    def process_image(self, image_path: str, window_title: str = None, 
                     ocr_text: str = None, priority: str = "normal", entity_id: str = None) -> Dict:
        """
        Process image with VLM, using smart caching and prompts with race condition protection.
        
        Args:
            image_path: Path to screenshot
            window_title: Active window title
            ocr_text: OCR text if available
            priority: Processing priority (high/normal/low)
            entity_id: Database entity ID for atomic processing checks
            
        Returns:
            Structured VLM result
        """
        start_time = time.time()
        
        # Check if we should process (basic checks without locking)
        should_process, reason = self.should_process(image_path, window_title, entity_id, ocr_text)
        if not should_process:
            if reason == "cached":
                img_hash = self.get_image_hash(image_path)
                logger.debug(f"Returning cached result for {image_path}")
                return self.result_cache[img_hash]
            else:
                logger.debug(f"Skipping {image_path}: {reason}")
                return None
        
        # Atomically acquire processing lock to prevent race conditions
        if entity_id and not self._try_acquire_processing_lock(entity_id):
            logger.debug(f"Skipping {image_path}: could not acquire processing lock")
            return None
        
        try:
            # Detect application type
            app_type = self.detect_application_type(window_title, ocr_text)
            
            # Use privacy-safe prompt if sensitivity detected
            sensitivity_score = self.sensitive_filter.calculate_sensitivity_score(ocr_text or "", window_title)
            if sensitivity_score > 0.3:  # Use privacy-safe prompts for moderately sensitive content
                prompt = self.sensitive_filter.get_privacy_safe_prompt(app_type)
                self.metrics.increment_counter('privacy_safe_prompt_used')
            else:
                prompt = self.task_prompts[app_type]
            
            # Prepare VLM request
            result = self._call_vlm(image_path, prompt, priority)
            
            if result:
                # Structure the result
                structured_result = self._structure_vlm_result(result, app_type, window_title)
                
                # Cache the result
                img_hash = self.get_image_hash(image_path)
                self.result_cache[img_hash] = structured_result
                self._save_cache()
                
                # Save to database if entity_id provided
                if entity_id:
                    self._save_vlm_result_to_db(entity_id, structured_result)
                
                # Track processing time
                processing_time = time.time() - start_time
                self.processing_times.append(processing_time)
                logger.info(f"VLM processed {image_path} in {processing_time:.1f}s")
                
                # Mark processing as complete
                if entity_id:
                    self._mark_processing_complete(entity_id, success=True)
                
                return structured_result
            else:
                # Mark processing as failed
                if entity_id:
                    self._mark_processing_complete(entity_id, success=False)
                return None
                
        except Exception as e:
            # Mark processing as failed on exception
            if entity_id:
                self._mark_processing_complete(entity_id, success=False)
            logger.error(f"Error processing {image_path}: {e}")
            raise
    
    def _get_image_base64(self, image_path: str) -> str:
        """Get base64 encoded image with LRU caching and memory limits."""
        with self.cache_lock:
            # Check if already cached (and move to end for LRU)
            if image_path in self.image_cache:
                # Move to end (most recently used)
                self.image_cache.move_to_end(image_path)
                return self.image_cache[image_path]
        
        import base64
        from PIL import Image as PILImage
        
        # Resize image for faster processing
        try:
            with PILImage.open(image_path) as img:
                # Resize to max 768 pixels (reduced from 1024 for memory)
                max_size = 768
                if img.width > max_size or img.height > max_size:
                    img.thumbnail((max_size, max_size), PILImage.Resampling.LANCZOS)
                
                # Convert to RGB if necessary
                if img.mode != 'RGB':
                    img = img.convert('RGB')
                
                # Save to bytes with optimized quality
                import io
                buffer = io.BytesIO()
                img.save(buffer, format='JPEG', quality=75, optimize=True)
                image_bytes = buffer.getvalue()
        except Exception as e:
            logger.error(f"Failed to process image {image_path}: {e}")
            raise
        
        image_base64 = base64.b64encode(image_bytes).decode()
        image_size = len(image_base64)
        
        # Add to cache with memory management
        with self.cache_lock:
            self._manage_cache_memory(image_size)
            self.image_cache[image_path] = image_base64
            self.current_cache_size += image_size
        
        return image_base64
    
    def _manage_cache_memory(self, new_item_size: int):
        """Manage cache memory by evicting LRU items if needed."""
        max_size_bytes = self.max_cache_size_mb * 1024 * 1024
        
        # Remove oldest items if we would exceed memory limit or item limit
        while (len(self.image_cache) >= self.max_cache_items or 
               self.current_cache_size + new_item_size > max_size_bytes):
            
            if not self.image_cache:
                break
                
            # Remove oldest item (FIFO/LRU)
            oldest_path, oldest_data = self.image_cache.popitem(last=False)
            removed_size = len(oldest_data)
            self.current_cache_size -= removed_size
            
            logger.debug(f"Evicted cached image {oldest_path} ({removed_size/1024:.1f}KB)")
    
    def get_cache_stats(self) -> Dict:
        """Get cache statistics for monitoring."""
        with self.cache_lock:
            return {
                'image_cache_items': len(self.image_cache),
                'image_cache_size_mb': self.current_cache_size / (1024 * 1024),
                'image_cache_max_mb': self.max_cache_size_mb,
                'image_cache_usage_percent': (self.current_cache_size / (self.max_cache_size_mb * 1024 * 1024)) * 100,
                'result_cache_items': len(self.result_cache),
                'hash_cache_items': len(self.hash_cache)
            }
    
    def clear_caches(self):
        """Clear all caches to free memory."""
        with self.cache_lock:
            old_size = self.current_cache_size
            self.image_cache.clear()
            self.hash_cache.clear()
            self.result_cache.clear()
            self.current_cache_size = 0
            logger.info(f"Cleared all caches, freed {old_size/1024/1024:.1f}MB")
    
    def _call_vlm(self, image_path: str, prompt: str, priority: str = "normal") -> Optional[str]:
        """Call VLM API with improved error handling and longer timeouts."""
        max_retries = 2 if priority == "high" else 1
        timeout = 60 if priority == "high" else 45  # Increased timeout for VLM models
        
        # Apply rate limiting
        self.rate_limiter.wait_if_needed()
        
        def _make_request():
            try:
                # Get cached/resized image
                image_base64 = self._get_image_base64(image_path)
                logger.debug(f"Image base64 length: {len(image_base64)}")
                
                # Prepare request payload
                payload = {
                    'model': self.vlm_model,
                    'prompt': prompt,
                    'images': [image_base64],
                    'stream': False,  # Use non-streaming for reliability
                    'options': {
                        'temperature': 0.7,
                        'top_p': 0.9,
                        'num_predict': 300,
                        'num_ctx': 4096
                    }
                }
                
                logger.debug(f"Making VLM request to {self.vlm_model}")
                
                # Call Ollama API with session
                response = self.session.post(
                    f'http://localhost:{self.vlm_port}/api/generate',
                    json=payload,
                    timeout=timeout,
                    headers={'Content-Type': 'application/json'}
                )
                
                # Check response status
                response.raise_for_status()
                
                # Parse response
                result = response.json()
                logger.debug(f"VLM response keys: {list(result.keys())}")
                
                # Extract response text
                if 'response' in result:
                    full_response = result['response']
                    logger.debug(f"VLM response length: {len(full_response)}")
                    return full_response.strip()
                else:
                    logger.error(f"No 'response' key in VLM result: {result}")
                    return None
                    
            except requests.exceptions.Timeout as e:
                logger.error(f"VLM request timeout after {timeout}s: {e}")
                raise
            except requests.exceptions.ConnectionError as e:
                logger.error(f"VLM connection error: {e}")
                raise
            except requests.exceptions.HTTPError as e:
                logger.error(f"VLM HTTP error: {e}")
                raise
            except json.JSONDecodeError as e:
                logger.error(f"VLM JSON decode error: {e}")
                raise
            except Exception as e:
                logger.error(f"Unexpected VLM error: {e}")
                raise
        
        # Try with circuit breaker and retries
        for attempt in range(max_retries):
            try:
                result = self.circuit_breaker.call(_make_request)
                if result:
                    logger.info(f"VLM call successful on attempt {attempt + 1}")
                    return result
                else:
                    logger.warning(f"VLM returned empty response on attempt {attempt + 1}")
                    
            except (requests.Timeout, requests.ConnectionError) as e:
                logger.warning(f"VLM connection issue on attempt {attempt + 1}: {e}")
                if attempt < max_retries - 1:
                    wait_time = min(2 ** attempt, 10)  # Exponential backoff with cap
                    logger.info(f"Retrying in {wait_time} seconds...")
                    time.sleep(wait_time)
            except Exception as e:
                if "Circuit breaker is open" in str(e):
                    logger.error("VLM service unavailable due to circuit breaker")
                    break
                logger.error(f"VLM error on attempt {attempt + 1}: {e}")
                if attempt < max_retries - 1:
                    time.sleep(min(2 ** attempt, 5))
        
        return None
    
    def _structure_vlm_result(self, raw_result: str, app_type: str, window_title: str) -> Dict:
        """Structure VLM result into useful format."""
        # Extract key information from the VLM description
        task = self._extract_task_from_description(raw_result, app_type)
        category = self._map_app_to_category(app_type)
        
        structured = {
            'task': task,
            'category': category,
            'description': raw_result,
            'visual_context': raw_result,  # For compatibility
            'app_type': app_type,
            'window_title': window_title,
            'processed_at': datetime.now().isoformat(),
            'confidence': 0.8,  # Default confidence
            'ui_elements': self._extract_ui_elements(raw_result),
            'subtasks': self._extract_subtasks(raw_result),
        }
        
        return structured
    
    def _extract_task_from_description(self, description: str, app_type: str) -> str:
        """Extract a concise task description from VLM output."""
        if not description:
            return f"Using {app_type}"
            
        # Look for common task indicators
        desc_lower = description.lower()
        
        if 'coding' in desc_lower or 'programming' in desc_lower:
            return "Software Development"
        elif 'terminal' in desc_lower or 'command' in desc_lower:
            return "Command Line Operations"
        elif 'browsing' in desc_lower or 'website' in desc_lower:
            return "Web Browsing"
        elif 'meeting' in desc_lower or 'video call' in desc_lower:
            return "Video Conference"
        elif 'document' in desc_lower or 'writing' in desc_lower:
            return "Document Editing"
        else:
            # Extract first sentence as task
            sentences = description.split('.')
            if sentences:
                first_sentence = sentences[0].strip()
                if len(first_sentence) > 10:
                    return first_sentence
        
        return f"Working with {app_type}"
    
    def _map_app_to_category(self, app_type: str) -> str:
        """Map application type to category."""
        mapping = {
            'IDE': 'Development',
            'Terminal': 'Development', 
            'Browser': 'Research',
            'Meeting': 'Communication',
            'Document': 'Documentation',
            'Chat': 'Communication',
            'Default': 'General'
        }
        return mapping.get(app_type, 'General')
    
    def _extract_ui_elements(self, description: str) -> Dict:
        """Extract UI elements mentioned in description."""
        elements = {}
        desc_lower = description.lower()
        
        if 'button' in desc_lower:
            elements['buttons'] = True
        if 'menu' in desc_lower:
            elements['menus'] = True
        if 'tab' in desc_lower:
            elements['tabs'] = True
        if 'window' in desc_lower:
            elements['windows'] = True
        if 'dialog' in desc_lower:
            elements['dialogs'] = True
            
        return elements
    
    def _extract_subtasks(self, description: str) -> List[str]:
        """Extract subtasks from description."""
        subtasks = []
        
        # Look for numbered or bulleted lists
        lines = description.split('\n')
        for line in lines:
            line = line.strip()
            if line.startswith(('1.', '2.', '3.', '-', '•')):
                subtasks.append(line[2:].strip())
        
        # If no explicit lists, try to infer subtasks
        if not subtasks:
            desc_lower = description.lower()
            if 'editing' in desc_lower:
                subtasks.append('Code editing')
            if 'debugging' in desc_lower:
                subtasks.append('Debugging')
            if 'testing' in desc_lower:
                subtasks.append('Testing')
        
        return subtasks[:5]  # Limit to 5 subtasks


class RateLimiter:
    """Simple rate limiter for API calls."""
    
    def __init__(self, max_requests: int, time_window: int):
        self.max_requests = max_requests
        self.time_window = time_window
        self.requests = deque()
        self.lock = threading.Lock()
    
    def wait_if_needed(self):
        """Wait if rate limit would be exceeded."""
        with self.lock:
            now = time.time()
            
            # Remove old requests outside time window
            while self.requests and self.requests[0] <= now - self.time_window:
                self.requests.popleft()
            
            # Check if we need to wait
            if len(self.requests) >= self.max_requests:
                sleep_time = self.time_window - (now - self.requests[0])
                if sleep_time > 0:
                    logger.info(f"Rate limit reached, waiting {sleep_time:.1f}s")
                    time.sleep(sleep_time)
                    # Remove the old request after waiting
                    self.requests.popleft()
            
            # Record this request
            self.requests.append(now)
    
    def get_stats(self) -> Dict:
        """Get rate limiter statistics."""
        with self.lock:
            now = time.time()
            recent_requests = sum(1 for req_time in self.requests 
                                if req_time > now - self.time_window)
            return {
                'recent_requests': recent_requests,
                'max_requests': self.max_requests,
                'time_window': self.time_window,
                'requests_remaining': max(0, self.max_requests - recent_requests)
            }


class CircuitBreaker:
    """Circuit breaker pattern for API calls."""
    
    def __init__(self, failure_threshold: int, recovery_timeout: int, 
                 expected_exception: Exception = Exception):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.expected_exception = expected_exception
        
        self.failure_count = 0
        self.last_failure_time = None
        self.state = 'closed'  # closed, open, half-open
        self.lock = threading.Lock()
    
    def call(self, func, *args, **kwargs):
        """Execute function with circuit breaker protection."""
        with self.lock:
            if self.state == 'open':
                if time.time() - self.last_failure_time > self.recovery_timeout:
                    self.state = 'half-open'
                    logger.info("Circuit breaker entering half-open state")
                else:
                    raise Exception(f"Circuit breaker is open. Service unavailable.")
        
        try:
            result = func(*args, **kwargs)
            
            # Success - reset circuit breaker
            with self.lock:
                if self.state == 'half-open':
                    self.state = 'closed'
                    logger.info("Circuit breaker closed - service recovered")
                self.failure_count = 0
            
            return result
            
        except self.expected_exception as e:
            with self.lock:
                self.failure_count += 1
                self.last_failure_time = time.time()
                
                if self.failure_count >= self.failure_threshold:
                    self.state = 'open'
                    logger.error(f"Circuit breaker opened after {self.failure_count} failures")
                else:
                    logger.warning(f"Circuit breaker failure {self.failure_count}/{self.failure_threshold}")
            
            raise e
    
    def get_stats(self) -> Dict:
        """Get circuit breaker statistics."""
        with self.lock:
            return {
                'state': self.state,
                'failure_count': self.failure_count,
                'failure_threshold': self.failure_threshold,
                'last_failure_time': self.last_failure_time,
                'recovery_timeout': self.recovery_timeout
            }
    
    def _extract_ide_elements(self, text: str) -> Dict:
        """Extract IDE-specific elements from VLM text."""
        elements = {
            'file_name': None,
            'language': None,
            'errors_visible': False,
            'debugging': False
        }
        
        # Simple extraction logic (can be enhanced)
        text_lower = text.lower()
        
        # Language detection
        languages = ['python', 'javascript', 'java', 'typescript', 'go', 'rust']
        for lang in languages:
            if lang in text_lower:
                elements['language'] = lang
                break
        
        # Error detection
        if any(word in text_lower for word in ['error', 'exception', 'failed', 'syntax']):
            elements['errors_visible'] = True
        
        # Debug detection
        if any(word in text_lower for word in ['debug', 'breakpoint', 'step', 'watch']):
            elements['debugging'] = True
        
        return elements
    
    def _extract_terminal_elements(self, text: str) -> Dict:
        """Extract terminal-specific elements."""
        return {
            'commands': [],  # Could extract visible commands
            'has_error': 'error' in text.lower(),
            'has_output': len(text) > 100
        }
    
    def _extract_browser_elements(self, text: str) -> Dict:
        """Extract browser-specific elements."""
        return {
            'site_type': 'documentation' if 'docs' in text.lower() else 'general',
            'has_form': 'form' in text.lower() or 'input' in text.lower(),
            'reading_mode': 'article' in text.lower() or 'blog' in text.lower()
        }
    
    def _extract_coding_task(self, text: str) -> str:
        """Extract specific coding task from VLM description."""
        if 'debug' in text.lower():
            return "debugging"
        elif 'test' in text.lower():
            return "writing tests"
        elif 'refactor' in text.lower():
            return "refactoring"
        else:
            return "coding"
    
    def _extract_terminal_task(self, text: str) -> str:
        """Extract terminal task."""
        if 'git' in text.lower():
            return "version control"
        elif 'install' in text.lower() or 'pip' in text.lower():
            return "installing dependencies"
        elif 'test' in text.lower() or 'pytest' in text.lower():
            return "running tests"
        else:
            return "command execution"
    
    def _extract_browsing_task(self, text: str) -> str:
        """Extract browsing task."""
        if 'search' in text.lower():
            return "searching"
        elif 'docs' in text.lower() or 'documentation' in text.lower():
            return "reading documentation"
        elif 'stackoverflow' in text.lower():
            return "troubleshooting"
        else:
            return "browsing"
    
    def get_processing_stats(self) -> Dict:
        """Get processing statistics including memory usage."""
        cache_stats = self.get_cache_stats()
        
        base_stats = {
            'total_processed': len(self.processing_times),
            'cached_results': len(self.result_cache),
        }
        
        if self.processing_times:
            base_stats.update({
                'avg_processing_time': np.mean(self.processing_times),
                'max_processing_time': max(self.processing_times),
                'min_processing_time': min(self.processing_times),
                'cache_hit_rate': len(self.result_cache) / (len(self.result_cache) + len(self.processing_times)) if self.processing_times else 0
            })
        
        # Add memory stats
        base_stats.update(cache_stats)
        
        # Add system memory info if available
        try:
            import psutil
            process = psutil.Process()
            memory_info = process.memory_info()
            base_stats.update({
                'process_memory_mb': memory_info.rss / (1024 * 1024),
                'process_memory_percent': process.memory_percent()
            })
        except ImportError:
            pass
        
        # Add rate limiting and circuit breaker stats
        base_stats.update({
            'rate_limiter': self.rate_limiter.get_stats(),
            'circuit_breaker': self.circuit_breaker.get_stats()
        })
        
        return base_stats
    
    def batch_process(self, tasks: List[Dict], max_concurrent: int = 3) -> Dict[str, Dict]:
        """Process multiple images efficiently with concurrent processing and race condition protection."""
        import concurrent.futures
        from threading import Lock
        
        results = {}
        results_lock = Lock()
        
        # Filter out already processed
        to_process = []
        for task in tasks:
            path = task.get('filepath', task) if isinstance(task, dict) else task
            entity_id = task.get('entity_id') if isinstance(task, dict) else None
            window_title = task.get('window_title') if isinstance(task, dict) else None
            
            should_proc, reason = self.should_process(path, window_title, entity_id)
            if should_proc:
                to_process.append(task)
            elif reason == "cached":
                img_hash = self.get_image_hash(path)
                results[path] = self.result_cache[img_hash]
        
        logger.info(f"Batch processing {len(to_process)} images (skipped {len(tasks) - len(to_process)})")
        
        # Process concurrently
        def process_single(task):
            try:
                if isinstance(task, dict):
                    result = self.process_image(
                        task['filepath'],
                        task.get('window_title'),
                        task.get('ocr_text'),
                        task.get('priority', 'normal'),
                        task.get('entity_id')
                    )
                    path = task['filepath']
                else:
                    result = self.process_image(task)
                    path = task
                
                if result:
                    with results_lock:
                        results[path] = result
                return True
            except Exception as e:
                logger.error(f"Error processing {task}: {e}")
                return False
        
        # Use ThreadPoolExecutor for concurrent processing
        with concurrent.futures.ThreadPoolExecutor(max_workers=max_concurrent) as executor:
            futures = [executor.submit(process_single, task) for task in to_process]
            
            # Wait for completion with progress
            completed = 0
            for future in concurrent.futures.as_completed(futures):
                completed += 1
                if completed % 10 == 0:
                    logger.info(f"Batch progress: {completed}/{len(to_process)}")
        
        return results
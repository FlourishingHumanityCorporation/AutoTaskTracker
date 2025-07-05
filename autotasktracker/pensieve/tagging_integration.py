"""
Tagging system integration with Pensieve database via DatabaseManager.
Provides tagging functionality using the existing tags infrastructure.
"""

import logging
from typing import List, Dict, Any, Optional, Set
from datetime import datetime

from autotasktracker.core.database import DatabaseManager

logger = logging.getLogger(__name__)


class PensieveTagManager:
    """DatabaseManager-based integration for Pensieve tagging system."""
    
    def __init__(self, db_manager: Optional[DatabaseManager] = None):
        """Initialize tag manager with DatabaseManager instance."""
        self.db = db_manager if db_manager else DatabaseManager()
        
        # Verify database exists and has required tables
        self._verify_database()
    
    def _verify_database(self):
        """Verify database exists and has required tagging tables."""
        try:
            with self.db.get_connection() as conn:
                cursor = conn.cursor()
                
                # Check for required tables
                cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name IN ('tags', 'entity_tags')")
                tables = {row[0] for row in cursor.fetchall()}
                
                required_tables = {'tags', 'entity_tags'}
                missing_tables = required_tables - tables
                
                if missing_tables:
                    logger.warning(f"Missing tagging tables: {missing_tables}")
                else:
                    logger.debug("Tagging database tables verified")
                    
        except Exception as e:
            logger.error(f"Database verification failed: {e}")
    
    def get_entity_tags(self, entity_id: int) -> List[str]:
        """Get all tags for an entity.
        
        Args:
            entity_id: Entity ID
            
        Returns:
            List of tag names
        """
        try:
            with self.db.get_connection() as conn:
                cursor = conn.cursor()
                
                query = """
                SELECT t.name 
                FROM tags t
                JOIN entity_tags et ON t.id = et.tag_id
                WHERE et.entity_id = ?
                ORDER BY t.name
                """
                
                cursor.execute(query, (entity_id,))
                return [row[0] for row in cursor.fetchall()]
                
        except Exception as e:
            logger.error(f"Failed to get entity tags for {entity_id}: {e}")
            return []
    
    def add_entity_tag(self, entity_id: int, tag_name: str) -> bool:
        """Add a tag to an entity.
        
        Args:
            entity_id: Entity ID
            tag_name: Name of the tag
            
        Returns:
            True if successful, False otherwise
        """
        try:
            with self.db.get_connection() as conn:
                cursor = conn.cursor()
                
                # First, ensure tag exists
                tag_id = self._get_or_create_tag(cursor, tag_name)
                if tag_id is None:
                    return False
                
                # Check if relationship already exists
                cursor.execute(
                    "SELECT 1 FROM entity_tags WHERE entity_id = ? AND tag_id = ?",
                    (entity_id, tag_id)
                )
                
                if cursor.fetchone():
                    logger.debug(f"Tag '{tag_name}' already exists for entity {entity_id}")
                    return True
                
                # Add the relationship with required source field
                cursor.execute(
                    "INSERT INTO entity_tags (entity_id, tag_id, source, created_at, updated_at) VALUES (?, ?, ?, ?, ?)",
                    (entity_id, tag_id, 'autotask', datetime.now(), datetime.now())
                )
                
                conn.commit()
                logger.info(f"Added tag '{tag_name}' to entity {entity_id}")
                return True
                
        except Exception as e:
            logger.error(f"Failed to add tag '{tag_name}' to entity {entity_id}: {e}")
            return False
    
    def remove_entity_tag(self, entity_id: int, tag_name: str) -> bool:
        """Remove a tag from an entity.
        
        Args:
            entity_id: Entity ID
            tag_name: Name of the tag to remove
            
        Returns:
            True if successful, False otherwise
        """
        try:
            with self.db.get_connection() as conn:
                cursor = conn.cursor()
                
                # Get tag ID
                cursor.execute("SELECT id FROM tags WHERE name = ?", (tag_name,))
                result = cursor.fetchone()
                
                if not result:
                    logger.debug(f"Tag '{tag_name}' does not exist")
                    return True  # Consider this success
                
                tag_id = result[0]
                
                # Remove the relationship
                cursor.execute(
                    "DELETE FROM entity_tags WHERE entity_id = ? AND tag_id = ?",
                    (entity_id, tag_id)
                )
                
                rows_affected = cursor.rowcount
                conn.commit()
                
                if rows_affected > 0:
                    logger.info(f"Removed tag '{tag_name}' from entity {entity_id}")
                else:
                    logger.debug(f"Tag '{tag_name}' was not associated with entity {entity_id}")
                
                return True
                
        except Exception as e:
            logger.error(f"Failed to remove tag '{tag_name}' from entity {entity_id}: {e}")
            return False
    
    def search_entities_by_tags(self, tags: List[str], operator: str = "AND", limit: int = 100) -> List[Dict[str, Any]]:
        """Search entities by tags.
        
        Args:
            tags: List of tag names
            operator: "AND" or "OR" for tag matching
            limit: Maximum number of results
            
        Returns:
            List of entity dictionaries with metadata
        """
        if not tags:
            return []
        
        try:
            with self.db.get_connection() as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                
                if operator.upper() == "AND":
                    # All tags must be present
                    placeholders = ",".join("?" * len(tags))
                    query = f"""
                    SELECT e.*, GROUP_CONCAT(t.name, ',') as entity_tags
                    FROM entities e
                    JOIN entity_tags et ON e.id = et.entity_id
                    JOIN tags t ON et.tag_id = t.id
                    WHERE e.id IN (
                        SELECT entity_id
                        FROM entity_tags et2
                        JOIN tags t2 ON et2.tag_id = t2.id
                        WHERE t2.name IN ({placeholders})
                        GROUP BY entity_id
                        HAVING COUNT(DISTINCT t2.name) = ?
                    )
                    GROUP BY e.id
                    ORDER BY e.created_at DESC
                    LIMIT ?
                    """
                    params = tags + [len(tags), limit]
                    
                else:  # OR
                    # Any tag can be present
                    placeholders = ",".join("?" * len(tags))
                    query = f"""
                    SELECT DISTINCT e.*, GROUP_CONCAT(t.name, ',') as entity_tags
                    FROM entities e
                    JOIN entity_tags et ON e.id = et.entity_id
                    JOIN tags t ON et.tag_id = t.id
                    WHERE t.name IN ({placeholders})
                    GROUP BY e.id
                    ORDER BY e.created_at DESC
                    LIMIT ?
                    """
                    params = tags + [limit]
                
                cursor.execute(query, params)
                results = []
                
                for row in cursor.fetchall():
                    entity_dict = dict(row)
                    # Parse tags from GROUP_CONCAT result
                    if entity_dict['entity_tags']:
                        entity_dict['tags'] = entity_dict['entity_tags'].split(',')
                    else:
                        entity_dict['tags'] = []
                    del entity_dict['entity_tags']
                    
                    results.append(entity_dict)
                
                logger.info(f"Found {len(results)} entities with tags {tags} (operator: {operator})")
                return results
                
        except Exception as e:
            logger.error(f"Failed to search entities by tags {tags}: {e}")
            return []
    
    def get_all_tags(self) -> List[Dict[str, Any]]:
        """Get all available tags with usage counts.
        
        Returns:
            List of tag dictionaries with name and usage count
        """
        try:
            with self.db.get_connection() as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                
                query = """
                SELECT t.name, COUNT(et.entity_id) as usage_count
                FROM tags t
                LEFT JOIN entity_tags et ON t.id = et.tag_id
                GROUP BY t.id, t.name
                ORDER BY usage_count DESC, t.name
                """
                
                cursor.execute(query)
                return [dict(row) for row in cursor.fetchall()]
                
        except Exception as e:
            logger.error(f"Failed to get all tags: {e}")
            return []
    
    def get_popular_tags(self, limit: int = 20) -> List[str]:
        """Get most popular tags by usage.
        
        Args:
            limit: Maximum number of tags to return
            
        Returns:
            List of tag names ordered by popularity
        """
        all_tags = self.get_all_tags()
        return [tag['name'] for tag in all_tags[:limit] if tag['usage_count'] > 0]
    
    def auto_tag_entity(self, entity_id: int, metadata: Dict[str, Any]) -> List[str]:
        """Automatically suggest tags based on entity metadata.
        
        Args:
            entity_id: Entity ID
            metadata: Entity metadata including OCR text, VLM descriptions, etc.
            
        Returns:
            List of suggested tag names
        """
        suggested_tags = set()
        
        # Extract text content for analysis
        text_content = []
        if 'ocr_result' in metadata:
            text_content.append(str(metadata['ocr_result']).lower())
        if 'vlm_description' in metadata:
            text_content.append(str(metadata['vlm_description']).lower())
        if 'active_window' in metadata:
            text_content.append(str(metadata['active_window']).lower())
        
        combined_text = ' '.join(text_content)
        
        # Auto-tagging rules based on content analysis
        tagging_rules = {
            'coding': ['python', 'javascript', 'code', 'vscode', 'ide', 'github', 'programming'],
            'meeting': ['zoom', 'teams', 'meeting', 'video call', 'conference'],
            'document': ['word', 'google docs', 'document', 'writing', 'text editor'],
            'browser': ['chrome', 'firefox', 'safari', 'web', 'browser', 'website'],
            'terminal': ['terminal', 'command line', 'bash', 'shell', 'console'],
            'design': ['photoshop', 'figma', 'sketch', 'design', 'illustrator'],
            'data': ['excel', 'spreadsheet', 'data', 'csv', 'database'],
            'communication': ['slack', 'discord', 'chat', 'email', 'message'],
            'research': ['google', 'search', 'research', 'wikipedia', 'documentation']
        }
        
        for tag, keywords in tagging_rules.items():
            if any(keyword in combined_text for keyword in keywords):
                suggested_tags.add(tag)
        
        # Add specific application tags
        if 'active_window' in metadata:
            window_title = str(metadata['active_window']).lower()
            
            # Common applications
            app_mappings = {
                'visual studio code': 'vscode',
                'google chrome': 'chrome',
                'microsoft teams': 'teams',
                'adobe photoshop': 'photoshop',
                'microsoft excel': 'excel',
                'microsoft word': 'word'
            }
            
            for app_name, tag in app_mappings.items():
                if app_name in window_title:
                    suggested_tags.add(tag)
        
        return list(suggested_tags)
    
    def _get_or_create_tag(self, cursor: sqlite3.Cursor, tag_name: str) -> Optional[int]:
        """Get existing tag ID or create new tag.
        
        Args:
            cursor: Database cursor
            tag_name: Name of the tag
            
        Returns:
            Tag ID or None if failed
        """
        try:
            # Check if tag exists
            cursor.execute("SELECT id FROM tags WHERE name = ?", (tag_name,))
            result = cursor.fetchone()
            
            if result:
                return result[0]
            
            # Create new tag with required timestamps
            cursor.execute(
                "INSERT INTO tags (name, created_at, updated_at) VALUES (?, ?, ?)",
                (tag_name, datetime.now(), datetime.now())
            )
            
            return cursor.lastrowid
            
        except Exception as e:
            logger.error(f"Failed to get or create tag '{tag_name}': {e}")
            return None


# Singleton instance
_tag_manager: Optional[PensieveTagManager] = None


def get_tag_manager() -> PensieveTagManager:
    """Get singleton tag manager instance."""
    global _tag_manager
    if _tag_manager is None:
        _tag_manager = PensieveTagManager()
    return _tag_manager


def reset_tag_manager():
    """Reset singleton tag manager (useful for testing)."""
    global _tag_manager
    _tag_manager = None
"""Abstract interfaces for AutoTaskTracker.

Defines common interfaces for dependency injection and testing.
Enables swappable implementations and better testability.
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional, Union, Iterator
from pathlib import Path
import logging

logger = logging.getLogger(__name__)


class AbstractManager(ABC):
    """Abstract base class for all Manager classes."""
    
    @abstractmethod
    def initialize(self) -> bool:
        """Initialize the manager.
        
        Returns:
            True if initialization successful, False otherwise
        """
        pass
    
    @abstractmethod
    def cleanup(self) -> None:
        """Clean up resources."""
        pass
    
    @abstractmethod
    def get_status(self) -> Dict[str, Any]:
        """Get current status of the manager.
        
        Returns:
            Dictionary containing status information
        """
        pass


class AbstractDatabaseManager(AbstractManager):
    """Abstract interface for database managers."""
    
    @abstractmethod
    def get_connection(self):
        """Get database connection."""
        pass
    
    @abstractmethod
    def fetch_tasks(self, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """Fetch tasks from database.
        
        Args:
            limit: Optional limit on number of tasks
            
        Returns:
            List of task dictionaries
        """
        pass
    
    @abstractmethod
    def execute_query(self, query: str, params: Optional[tuple] = None) -> List[Dict[str, Any]]:
        """Execute database query.
        
        Args:
            query: SQL query string
            params: Optional query parameters
            
        Returns:
            Query results as list of dictionaries
        """
        pass


class AbstractAnalyzer(ABC):
    """Abstract base class for all Analyzer classes."""
    
    @abstractmethod
    def analyze(self, data: Any) -> Dict[str, Any]:
        """Analyze provided data.
        
        Args:
            data: Data to analyze
            
        Returns:
            Analysis results as dictionary
        """
        pass
    
    @abstractmethod
    def get_metrics(self) -> Dict[str, float]:
        """Get analysis metrics.
        
        Returns:
            Dictionary of metric name to value
        """
        pass


class AbstractPerformanceAnalyzer(AbstractAnalyzer):
    """Abstract interface for performance analyzers."""
    
    @abstractmethod
    def benchmark(self, func, *args, **kwargs) -> Dict[str, float]:
        """Benchmark function performance.
        
        Args:
            func: Function to benchmark
            *args: Function arguments
            **kwargs: Function keyword arguments
            
        Returns:
            Performance metrics
        """
        pass
    
    @abstractmethod
    def compare_performance(self, results1: Dict, results2: Dict) -> Dict[str, Any]:
        """Compare two performance results.
        
        Args:
            results1: First performance result
            results2: Second performance result
            
        Returns:
            Comparison analysis
        """
        pass


class AbstractProcessor(ABC):
    """Abstract base class for all Processor classes."""
    
    @abstractmethod
    def process(self, input_data: Any) -> Any:
        """Process input data.
        
        Args:
            input_data: Data to process
            
        Returns:
            Processed data
        """
        pass
    
    @abstractmethod
    def batch_process(self, input_list: List[Any]) -> List[Any]:
        """Process multiple inputs in batch.
        
        Args:
            input_list: List of inputs to process
            
        Returns:
            List of processed outputs
        """
        pass


class AbstractVLMProcessor(AbstractProcessor):
    """Abstract interface for Vision Language Model processors."""
    
    @abstractmethod
    def process_image(self, image_path: Union[str, Path]) -> Dict[str, Any]:
        """Process single image with VLM.
        
        Args:
            image_path: Path to image file
            
        Returns:
            VLM processing results
        """
        pass
    
    @abstractmethod
    def extract_tasks(self, image_path: Union[str, Path]) -> List[Dict[str, Any]]:
        """Extract tasks from image.
        
        Args:
            image_path: Path to image file
            
        Returns:
            List of extracted tasks
        """
        pass


class AbstractTaskExtractor(ABC):
    """Abstract interface for task extractors."""
    
    @abstractmethod
    def extract_from_text(self, text: str) -> List[Dict[str, Any]]:
        """Extract tasks from text.
        
        Args:
            text: Input text
            
        Returns:
            List of extracted tasks
        """
        pass
    
    @abstractmethod
    def extract_from_image(self, image_path: Union[str, Path]) -> List[Dict[str, Any]]:
        """Extract tasks from image.
        
        Args:
            image_path: Path to image file
            
        Returns:
            List of extracted tasks
        """
        pass


class AbstractSearchEngine(ABC):
    """Abstract interface for search engines."""
    
    @abstractmethod
    def search(self, query: str, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """Search for items matching query.
        
        Args:
            query: Search query
            limit: Optional result limit
            
        Returns:
            List of search results
        """
        pass
    
    @abstractmethod
    def index_document(self, doc_id: str, content: str, metadata: Optional[Dict] = None) -> bool:
        """Index document for search.
        
        Args:
            doc_id: Document identifier
            content: Document content
            metadata: Optional metadata
            
        Returns:
            True if indexing successful
        """
        pass


class AbstractEmbeddingsSearch(AbstractSearchEngine):
    """Abstract interface for embeddings-based search."""
    
    @abstractmethod
    def semantic_search(self, query: str, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """Perform semantic search using embeddings.
        
        Args:
            query: Search query
            limit: Optional result limit
            
        Returns:
            List of semantically similar results
        """
        pass
    
    @abstractmethod
    def generate_embeddings(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings for texts.
        
        Args:
            texts: List of texts to embed
            
        Returns:
            List of embedding vectors
        """
        pass


class AbstractAPIClient(ABC):
    """Abstract base class for API clients."""
    
    @abstractmethod
    def connect(self) -> bool:
        """Connect to the API.
        
        Returns:
            True if connection successful
        """
        pass
    
    @abstractmethod
    def disconnect(self) -> None:
        """Disconnect from the API."""
        pass
    
    @abstractmethod
    def is_connected(self) -> bool:
        """Check if connected to API.
        
        Returns:
            True if connected
        """
        pass
    
    @abstractmethod
    def make_request(self, endpoint: str, method: str = 'GET', **kwargs) -> Dict[str, Any]:
        """Make API request.
        
        Args:
            endpoint: API endpoint
            method: HTTP method
            **kwargs: Additional request parameters
            
        Returns:
            API response
        """
        pass


# Interface registry for dependency injection
INTERFACE_REGISTRY: Dict[str, type] = {
    'Manager': AbstractManager,
    'DatabaseManager': AbstractDatabaseManager,
    'Analyzer': AbstractAnalyzer,
    'PerformanceAnalyzer': AbstractPerformanceAnalyzer,
    'Processor': AbstractProcessor,
    'VLMProcessor': AbstractVLMProcessor,
    'TaskExtractor': AbstractTaskExtractor,
    'SearchEngine': AbstractSearchEngine,
    'EmbeddingsSearch': AbstractEmbeddingsSearch,
    'APIClient': AbstractAPIClient,
}


def get_interface(interface_name: str) -> type:
    """Get interface class by name.
    
    Args:
        interface_name: Name of interface
        
    Returns:
        Interface class
        
    Raises:
        ValueError: If interface not found
    """
    if interface_name not in INTERFACE_REGISTRY:
        available = ', '.join(INTERFACE_REGISTRY.keys())
        raise ValueError(f"Unknown interface '{interface_name}'. Available: {available}")
    
    return INTERFACE_REGISTRY[interface_name]


def register_interface(interface_name: str, interface_class: type) -> None:
    """Register custom interface.
    
    Args:
        interface_name: Name to register interface under
        interface_class: Interface class
    """
    INTERFACE_REGISTRY[interface_name] = interface_class
    logger.info(f"Registered interface {interface_name}")


def list_available_interfaces() -> List[str]:
    """Get list of available interface names.
    
    Returns:
        List of available interface names
    """
    return list(INTERFACE_REGISTRY.keys())
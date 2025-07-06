"""Base component interface for all dashboard components."""

from typing import Optional, Dict, Any, TypeVar, Generic
from abc import ABC, abstractmethod
import streamlit as st
import logging

logger = logging.getLogger(__name__)

T = TypeVar('T')

class BaseComponent(ABC, Generic[T]):
    """Base class for all dashboard components.
    
    Provides standard interface and common functionality for components.
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """Initialize component with optional configuration.
        
        Args:
            config: Component-specific configuration
        """
        self.config = self._merge_config(config)
        self._cache_key_prefix = self.__class__.__name__
    
    def _merge_config(self, config: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        """Merge provided config with defaults.
        
        Args:
            config: User-provided configuration
            
        Returns:
            Merged configuration
        """
        default_config = self.get_default_config()
        if config:
            default_config.update(config)
        return default_config
    
    @abstractmethod
    def render(self, data: T, **kwargs) -> None:
        """Render the component.
        
        Args:
            data: Component data
            **kwargs: Additional rendering options
        """
        pass
    
    @classmethod
    @abstractmethod
    def get_default_config(cls) -> Dict[str, Any]:
        """Get default configuration for component.
        
        Returns:
            Default configuration dictionary
        """
        pass
    
    def get_cache_key(self, suffix: str = "") -> str:
        """Generate cache key for component.
        
        Args:
            suffix: Optional suffix for cache key
            
        Returns:
            Cache key string
        """
        key = f"{self._cache_key_prefix}"
        if suffix:
            key += f"_{suffix}"
        return key
    
    def render_error_state(self, error: Exception) -> None:
        """Render error state for component.
        
        Args:
            error: Exception that occurred
        """
        st.error(f"Component error: {str(error)}")
        if st.session_state.get("debug_mode", False):
            st.exception(error)
    
    def render_empty_state(self, message: str = "No data available") -> None:
        """Render empty state for component.
        
        Args:
            message: Empty state message
        """
        st.info(message)
    
    def render_loading_state(self, message: str = "Loading...") -> None:
        """Render loading state for component.
        
        Args:
            message: Loading message
        """
        with st.spinner(message):
            pass


class StatelessComponent(BaseComponent[T]):
    """Base class for stateless components.
    
    These components don't maintain internal state between renders.
    """
    
    def __init__(self):
        """Initialize stateless component without config."""
        super().__init__(config=None)
    
    @classmethod
    def render_static(cls, data: T, config: Optional[Dict[str, Any]] = None, **kwargs) -> None:
        """Static method to render component without instantiation.
        
        Args:
            data: Component data
            config: Optional configuration
            **kwargs: Additional rendering options
        """
        component = cls()
        if config:
            component.config = component._merge_config(config)
        component.render(data, **kwargs)
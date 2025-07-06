"""Custom exceptions for AutoTaskTracker."""


class AutoTaskTrackerError(Exception):
    """Base exception for all AutoTaskTracker errors."""
    pass


class DatabaseError(AutoTaskTrackerError):
    """Raised when database operations fail."""
    pass


class ConfigurationError(AutoTaskTrackerError):
    """Raised when configuration is invalid or missing."""
    pass


class AIProcessingError(AutoTaskTrackerError):
    """Raised when AI processing fails."""
    pass


class TaskExtractionError(AIProcessingError):
    """Raised when task extraction from text fails."""
    pass


class EmbeddingError(AIProcessingError):
    """Raised when embedding generation fails."""
    pass


class VLMProcessingError(AIProcessingError):
    """Raised when Vision Language Model processing fails."""
    pass


class PensieveIntegrationError(AutoTaskTrackerError):
    """Raised when Pensieve integration fails."""
    pass


class CacheError(AutoTaskTrackerError):
    """Raised when cache operations fail."""
    pass


class ValidationError(AutoTaskTrackerError):
    """Raised when data validation fails."""
    pass
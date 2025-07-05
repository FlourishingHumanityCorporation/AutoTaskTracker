"""
Advanced Pensieve Configuration Integration.

This module provides deep integration between AutoTaskTracker's unified configuration
system and Pensieve, enabling real-time configuration synchronization, advanced
feature detection, and automatic optimization.
"""

import os
import logging
import time
import json
from typing import Dict, Any, Optional, List, Callable
from datetime import datetime, timedelta
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class PensieveFeature:
    """Represents a Pensieve feature with its capabilities."""
    name: str
    available: bool
    version: Optional[str] = None
    configuration: Dict[str, Any] = None
    last_checked: datetime = None


class PensieveConfigurationIntegrator:
    """Advanced Pensieve configuration integration with feature detection."""
    
    def __init__(self):
        self._features: Dict[str, PensieveFeature] = {}
        self._integration_callbacks: List[Callable] = []
        self._last_sync: datetime = datetime.min
        self._sync_interval = timedelta(minutes=5)
        self._pensieve_config = {}
        
    def register_integration_callback(self, callback: Callable):
        """Register a callback for configuration integration events."""
        self._integration_callbacks.append(callback)
        logger.debug(f"Registered integration callback: {callback.__name__}")
    
    def detect_pensieve_features(self) -> Dict[str, PensieveFeature]:
        """Detect available Pensieve features and their configurations."""
        try:
            from autotasktracker.pensieve.api_client import get_pensieve_client
            
            client = get_pensieve_client()
            if not client or not client.is_healthy():
                logger.warning("Pensieve client not available for feature detection")
                return {}
            
            features = {}
            
            # Detect core features
            features['ocr'] = self._detect_ocr_feature(client)
            features['vlm'] = self._detect_vlm_feature(client)
            features['postgresql'] = self._detect_postgresql_feature(client)
            features['vector_search'] = self._detect_vector_search_feature(client)
            features['webhooks'] = self._detect_webhook_feature(client)
            features['real_time_processing'] = self._detect_realtime_feature(client)
            
            self._features = features
            logger.info(f"Detected {len([f for f in features.values() if f.available])} available Pensieve features")
            
            return features
            
        except Exception as e:
            logger.error(f"Failed to detect Pensieve features: {e}")
            return {}
    
    def _detect_ocr_feature(self, client) -> PensieveFeature:
        """Detect OCR processing capabilities."""
        try:
            # Check if OCR endpoints are available
            health = client.get_health()
            ocr_available = health.get('plugins', {}).get('builtin_ocr', {}).get('enabled', False)
            
            return PensieveFeature(
                name="ocr",
                available=ocr_available,
                configuration={
                    'engine': 'tesseract',
                    'languages': ['eng'],
                    'confidence_threshold': 0.6
                },
                last_checked=datetime.now()
            )
        except Exception as e:
            logger.debug(f"OCR feature detection failed: {e}")
            return PensieveFeature(name="ocr", available=False)
    
    def _detect_vlm_feature(self, client) -> PensieveFeature:
        """Detect Vision-Language Model capabilities."""
        try:
            # Check if VLM endpoints are available
            health = client.get_health()
            vlm_available = health.get('plugins', {}).get('builtin_vlm', {}).get('enabled', False)
            
            return PensieveFeature(
                name="vlm",
                available=vlm_available,
                configuration={
                    'model': 'minicpm-v',
                    'timeout': 60,
                    'max_image_size': '2MB'
                },
                last_checked=datetime.now()
            )
        except Exception as e:
            logger.debug(f"VLM feature detection failed: {e}")
            return PensieveFeature(name="vlm", available=False)
    
    def _detect_postgresql_feature(self, client) -> PensieveFeature:
        """Detect PostgreSQL backend availability."""
        try:
            # Check database backend type
            health = client.get_health()
            db_type = health.get('database', {}).get('type', 'sqlite')
            
            return PensieveFeature(
                name="postgresql",
                available=(db_type == 'postgresql'),
                configuration={
                    'host': health.get('database', {}).get('host'),
                    'port': health.get('database', {}).get('port'),
                    'database': health.get('database', {}).get('name')
                },
                last_checked=datetime.now()
            )
        except Exception as e:
            logger.debug(f"PostgreSQL feature detection failed: {e}")
            return PensieveFeature(name="postgresql", available=False)
    
    def _detect_vector_search_feature(self, client) -> PensieveFeature:
        """Detect vector search capabilities."""
        try:
            # Check if vector search endpoints are available
            endpoints = client.discover_endpoints()
            vector_available = any('vector' in endpoint or 'embedding' in endpoint for endpoint in endpoints)
            
            return PensieveFeature(
                name="vector_search",
                available=vector_available,
                configuration={
                    'dimensions': 768,
                    'similarity_metric': 'cosine',
                    'index_type': 'hnsw'
                },
                last_checked=datetime.now()
            )
        except Exception as e:
            logger.debug(f"Vector search feature detection failed: {e}")
            return PensieveFeature(name="vector_search", available=False)
    
    def _detect_webhook_feature(self, client) -> PensieveFeature:
        """Detect webhook capabilities."""
        try:
            # Check if webhook endpoints are available
            endpoints = client.discover_endpoints()
            webhook_available = any('webhook' in endpoint for endpoint in endpoints)
            
            return PensieveFeature(
                name="webhooks",
                available=webhook_available,
                configuration={
                    'max_retries': 3,
                    'timeout': 30,
                    'events': ['entity_created', 'entity_updated', 'scan_completed']
                },
                last_checked=datetime.now()
            )
        except Exception as e:
            logger.debug(f"Webhook feature detection failed: {e}")
            return PensieveFeature(name="webhooks", available=False)
    
    def _detect_realtime_feature(self, client) -> PensieveFeature:
        """Detect real-time processing capabilities."""
        try:
            # Check if real-time endpoints are available
            endpoints = client.discover_endpoints()
            realtime_available = any('realtime' in endpoint or 'stream' in endpoint for endpoint in endpoints)
            
            return PensieveFeature(
                name="real_time_processing",
                available=realtime_available,
                configuration={
                    'websocket_url': 'ws://localhost:8839/ws',
                    'events': ['screenshot_captured', 'ocr_completed', 'vlm_processed']
                },
                last_checked=datetime.now()
            )
        except Exception as e:
            logger.debug(f"Real-time feature detection failed: {e}")
            return PensieveFeature(name="real_time_processing", available=False)
    
    def sync_configuration_with_pensieve(self) -> Dict[str, Any]:
        """Synchronize AutoTaskTracker configuration with Pensieve settings."""
        current_time = datetime.now()
        if current_time - self._last_sync < self._sync_interval:
            return self._pensieve_config
        
        try:
            from autotasktracker.pensieve.config_reader import get_pensieve_config
            from autotasktracker.config import get_config
            
            # Get configurations
            pensieve_config = get_pensieve_config()
            autotask_config = get_config()
            
            # Create synchronized configuration
            sync_config = {
                'database': {
                    'path': pensieve_config.database_path,
                    'type': 'postgresql' if self._features.get('postgresql', PensieveFeature('', False)).available else 'sqlite'
                },
                'processing': {
                    'ocr_enabled': self._features.get('ocr', PensieveFeature('', False)).available,
                    'vlm_enabled': self._features.get('vlm', PensieveFeature('', False)).available,
                    'realtime_enabled': self._features.get('real_time_processing', PensieveFeature('', False)).available
                },
                'features': {
                    'vector_search': self._features.get('vector_search', PensieveFeature('', False)).available,
                    'webhooks': self._features.get('webhooks', PensieveFeature('', False)).available
                },
                'ports': {
                    'memos': autotask_config.server.memos_port,
                    'task_board': autotask_config.server.task_board_port,
                    'analytics': autotask_config.server.analytics_port
                }
            }
            
            # Update feature flags based on Pensieve capabilities
            if hasattr(autotask_config, 'features'):
                autotask_config.features.enable_vlm_processing = sync_config['processing']['vlm_enabled']
                autotask_config.features.enable_real_time_processing = sync_config['processing']['realtime_enabled']
            
            self._pensieve_config = sync_config
            self._last_sync = current_time
            
            # Notify callbacks
            for callback in self._integration_callbacks:
                try:
                    callback(sync_config)
                except Exception as e:
                    logger.error(f"Integration callback failed: {e}")
            
            logger.info("Configuration synchronized with Pensieve")
            return sync_config
            
        except Exception as e:
            logger.error(f"Failed to sync configuration with Pensieve: {e}")
            return self._pensieve_config
    
    def optimize_autotask_for_pensieve(self) -> Dict[str, Any]:
        """Optimize AutoTaskTracker configuration based on detected Pensieve features."""
        features = self.detect_pensieve_features()
        optimizations = {}
        
        try:
            from autotasktracker.config import get_config
            config = get_config()
            
            # Database optimizations
            if features.get('postgresql', PensieveFeature('', False)).available:
                optimizations['database'] = {
                    'use_postgresql': True,
                    'connection_pool_size': 20,  # Higher for PostgreSQL
                    'query_timeout': 60
                }
                logger.info("Optimized for PostgreSQL backend")
            
            # Processing optimizations
            if features.get('ocr', PensieveFeature('', False)).available:
                optimizations['ocr'] = {
                    'use_pensieve_ocr': True,
                    'skip_local_ocr': True
                }
                logger.info("Optimized to use Pensieve OCR")
            
            if features.get('vlm', PensieveFeature('', False)).available:
                optimizations['vlm'] = {
                    'use_pensieve_vlm': True,
                    'batch_size': 10,  # Optimize for Pensieve VLM
                    'timeout': 90
                }
                logger.info("Optimized to use Pensieve VLM")
            
            # Vector search optimizations
            if features.get('vector_search', PensieveFeature('', False)).available:
                optimizations['embeddings'] = {
                    'use_pensieve_vectors': True,
                    'skip_local_embeddings': True
                }
                logger.info("Optimized to use Pensieve vector search")
            
            # Real-time optimizations
            if features.get('real_time_processing', PensieveFeature('', False)).available:
                optimizations['realtime'] = {
                    'enable_websocket': True,
                    'polling_interval': 0,  # Use push instead of poll
                    'buffer_size': 100
                }
                logger.info("Optimized for real-time processing")
            
            return optimizations
            
        except Exception as e:
            logger.error(f"Failed to optimize configuration: {e}")
            return {}
    
    def get_integration_status(self) -> Dict[str, Any]:
        """Get comprehensive integration status with Pensieve."""
        return {
            'features_detected': len(self._features),
            'features_available': len([f for f in self._features.values() if f.available]),
            'last_sync': self._last_sync.isoformat() if self._last_sync != datetime.min else None,
            'sync_interval_minutes': self._sync_interval.total_seconds() / 60,
            'callbacks_registered': len(self._integration_callbacks),
            'features': {
                name: {
                    'available': feature.available,
                    'version': feature.version,
                    'last_checked': feature.last_checked.isoformat() if feature.last_checked else None
                }
                for name, feature in self._features.items()
            }
        }


# Global integrator instance
_pensieve_integrator = None

def get_pensieve_integrator() -> PensieveConfigurationIntegrator:
    """Get the global Pensieve configuration integrator."""
    global _pensieve_integrator
    if _pensieve_integrator is None:
        _pensieve_integrator = PensieveConfigurationIntegrator()
    return _pensieve_integrator

def initialize_pensieve_integration() -> bool:
    """Initialize Pensieve integration with feature detection and optimization."""
    try:
        integrator = get_pensieve_integrator()
        
        # Detect features
        features = integrator.detect_pensieve_features()
        available_features = [name for name, feature in features.items() if feature.available]
        
        # Sync configuration
        sync_config = integrator.sync_configuration_with_pensieve()
        
        # Apply optimizations
        optimizations = integrator.optimize_autotask_for_pensieve()
        
        logger.info(f"Pensieve integration initialized: {len(available_features)} features available")
        logger.info(f"Available features: {', '.join(available_features)}")
        
        return True
        
    except Exception as e:
        logger.error(f"Failed to initialize Pensieve integration: {e}")
        return False
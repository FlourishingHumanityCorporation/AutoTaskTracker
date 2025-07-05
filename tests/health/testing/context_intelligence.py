"""Context-aware intelligence for testing system health validation.

This module provides intelligent, adaptive validation that considers:
- Module importance and criticality
- Code complexity and risk assessment  
- Historical patterns and trends
- Development context and priorities
"""

import logging
import os
import re
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Set
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)


class ModuleImportance(Enum):
    """Module importance levels for context-aware validation."""
    CRITICAL = "critical"      # Core functionality, high user impact
    IMPORTANT = "important"    # Key features, moderate impact
    STANDARD = "standard"      # Regular functionality
    EXPERIMENTAL = "experimental"  # New/experimental features
    INFRASTRUCTURE = "infrastructure"  # Testing/tooling infrastructure


class ValidationMode(Enum):
    """Validation execution modes for adaptive performance."""
    FAST = "fast"              # <30 seconds, essential checks only
    STANDARD = "standard"      # <2 minutes, comprehensive analysis
    COMPREHENSIVE = "comprehensive"  # <10 minutes, deep analysis


@dataclass
class ModuleContext:
    """Context information for a test module."""
    importance: ModuleImportance
    complexity_score: float  # 0.0 to 1.0
    risk_level: float       # 0.0 to 1.0
    is_critical_path: bool
    last_modified_days: int
    test_count: int
    assertion_requirements: Dict[str, int]  # Different requirements per importance


@dataclass
class ValidationConfig:
    """Configuration for context-aware validation."""
    mode: ValidationMode
    max_files_per_category: Dict[ModuleImportance, int]
    assertion_minimums: Dict[ModuleImportance, int]
    error_testing_requirements: Dict[ModuleImportance, bool]
    boundary_testing_requirements: Dict[ModuleImportance, bool]
    performance_thresholds: Dict[ModuleImportance, Dict[str, float]]


class TestingIntelligenceEngine:
    """Central intelligence engine for context-aware testing validation."""
    
    def __init__(self, project_root: Path):
        self.project_root = project_root
        self.test_dir = project_root / "tests"
        self._module_cache: Dict[str, ModuleContext] = {}
        self._load_configuration()
    
    def _load_configuration(self) -> None:
        """Load configuration based on environment and mode."""
        # Get mode from environment
        mode_str = os.getenv('VALIDATION_MODE', 'standard').lower()
        try:
            self.mode = ValidationMode(mode_str)
        except ValueError:
            self.mode = ValidationMode.STANDARD
            logger.warning(f"Unknown validation mode '{mode_str}', using standard")
        
        # Configure validation parameters based on mode
        self.config = self._create_validation_config()
        logger.info(f"Testing Intelligence Engine initialized in {self.mode.value} mode")
    
    def _create_validation_config(self) -> ValidationConfig:
        """Create validation configuration based on current mode."""
        if self.mode == ValidationMode.FAST:
            return ValidationConfig(
                mode=self.mode,
                max_files_per_category={
                    ModuleImportance.CRITICAL: 10,
                    ModuleImportance.IMPORTANT: 5,
                    ModuleImportance.STANDARD: 3,
                    ModuleImportance.EXPERIMENTAL: 1,
                    ModuleImportance.INFRASTRUCTURE: 2,
                },
                assertion_minimums={
                    ModuleImportance.CRITICAL: 3,
                    ModuleImportance.IMPORTANT: 2,
                    ModuleImportance.STANDARD: 1,
                    ModuleImportance.EXPERIMENTAL: 1,
                    ModuleImportance.INFRASTRUCTURE: 1,
                },
                error_testing_requirements={
                    ModuleImportance.CRITICAL: True,
                    ModuleImportance.IMPORTANT: True,
                    ModuleImportance.STANDARD: False,
                    ModuleImportance.EXPERIMENTAL: False,
                    ModuleImportance.INFRASTRUCTURE: False,
                },
                boundary_testing_requirements={
                    ModuleImportance.CRITICAL: True,
                    ModuleImportance.IMPORTANT: False,
                    ModuleImportance.STANDARD: False,
                    ModuleImportance.EXPERIMENTAL: False,
                    ModuleImportance.INFRASTRUCTURE: False,
                },
                performance_thresholds={
                    ModuleImportance.CRITICAL: {"max_sleep": 0.1, "max_timeout": 5.0},
                    ModuleImportance.IMPORTANT: {"max_sleep": 0.5, "max_timeout": 10.0},
                    ModuleImportance.STANDARD: {"max_sleep": 1.0, "max_timeout": 30.0},
                    ModuleImportance.EXPERIMENTAL: {"max_sleep": 2.0, "max_timeout": 60.0},
                    ModuleImportance.INFRASTRUCTURE: {"max_sleep": 5.0, "max_timeout": 120.0},
                }
            )
        
        elif self.mode == ValidationMode.COMPREHENSIVE:
            return ValidationConfig(
                mode=self.mode,
                max_files_per_category={
                    ModuleImportance.CRITICAL: 100,
                    ModuleImportance.IMPORTANT: 50,
                    ModuleImportance.STANDARD: 30,
                    ModuleImportance.EXPERIMENTAL: 20,
                    ModuleImportance.INFRASTRUCTURE: 25,
                },
                assertion_minimums={
                    ModuleImportance.CRITICAL: 5,
                    ModuleImportance.IMPORTANT: 4,
                    ModuleImportance.STANDARD: 3,
                    ModuleImportance.EXPERIMENTAL: 2,
                    ModuleImportance.INFRASTRUCTURE: 2,
                },
                error_testing_requirements={
                    ModuleImportance.CRITICAL: True,
                    ModuleImportance.IMPORTANT: True,
                    ModuleImportance.STANDARD: True,
                    ModuleImportance.EXPERIMENTAL: True,
                    ModuleImportance.INFRASTRUCTURE: True,
                },
                boundary_testing_requirements={
                    ModuleImportance.CRITICAL: True,
                    ModuleImportance.IMPORTANT: True,
                    ModuleImportance.STANDARD: True,
                    ModuleImportance.EXPERIMENTAL: False,
                    ModuleImportance.INFRASTRUCTURE: True,
                },
                performance_thresholds={
                    ModuleImportance.CRITICAL: {"max_sleep": 0.0, "max_timeout": 1.0},
                    ModuleImportance.IMPORTANT: {"max_sleep": 0.1, "max_timeout": 5.0},
                    ModuleImportance.STANDARD: {"max_sleep": 0.5, "max_timeout": 10.0},
                    ModuleImportance.EXPERIMENTAL: {"max_sleep": 1.0, "max_timeout": 30.0},
                    ModuleImportance.INFRASTRUCTURE: {"max_sleep": 2.0, "max_timeout": 60.0},
                }
            )
        
        else:  # STANDARD mode
            return ValidationConfig(
                mode=self.mode,
                max_files_per_category={
                    ModuleImportance.CRITICAL: 25,
                    ModuleImportance.IMPORTANT: 15,
                    ModuleImportance.STANDARD: 10,
                    ModuleImportance.EXPERIMENTAL: 5,
                    ModuleImportance.INFRASTRUCTURE: 8,
                },
                assertion_minimums={
                    ModuleImportance.CRITICAL: 4,
                    ModuleImportance.IMPORTANT: 3,
                    ModuleImportance.STANDARD: 2,
                    ModuleImportance.EXPERIMENTAL: 1,
                    ModuleImportance.INFRASTRUCTURE: 2,
                },
                error_testing_requirements={
                    ModuleImportance.CRITICAL: True,
                    ModuleImportance.IMPORTANT: True,
                    ModuleImportance.STANDARD: True,
                    ModuleImportance.EXPERIMENTAL: False,
                    ModuleImportance.INFRASTRUCTURE: True,
                },
                boundary_testing_requirements={
                    ModuleImportance.CRITICAL: True,
                    ModuleImportance.IMPORTANT: True,
                    ModuleImportance.STANDARD: False,
                    ModuleImportance.EXPERIMENTAL: False,
                    ModuleImportance.INFRASTRUCTURE: False,
                },
                performance_thresholds={
                    ModuleImportance.CRITICAL: {"max_sleep": 0.1, "max_timeout": 2.0},
                    ModuleImportance.IMPORTANT: {"max_sleep": 0.3, "max_timeout": 5.0},
                    ModuleImportance.STANDARD: {"max_sleep": 1.0, "max_timeout": 15.0},
                    ModuleImportance.EXPERIMENTAL: {"max_sleep": 2.0, "max_timeout": 30.0},
                    ModuleImportance.INFRASTRUCTURE: {"max_sleep": 3.0, "max_timeout": 60.0},
                }
            )
    
    def analyze_module_context(self, test_file: Path) -> ModuleContext:
        """Analyze and return context information for a test module."""
        file_key = str(test_file)
        
        # Use cache if available
        if file_key in self._module_cache:
            return self._module_cache[file_key]
        
        # Analyze module
        context = self._analyze_module(test_file)
        self._module_cache[file_key] = context
        return context
    
    def _analyze_module(self, test_file: Path) -> ModuleContext:
        """Perform detailed analysis of a test module."""
        # Determine importance based on file path and content
        importance = self._determine_module_importance(test_file)
        
        # Calculate complexity score
        complexity_score = self._calculate_complexity_score(test_file)
        
        # Assess risk level
        risk_level = self._assess_risk_level(test_file, importance, complexity_score)
        
        # Check if it's on critical path
        is_critical_path = self._is_critical_path(test_file)
        
        # Get last modified time
        try:
            import time
            last_modified = test_file.stat().st_mtime
            last_modified_days = int((time.time() - last_modified) / (24 * 3600))
        except OSError:
            last_modified_days = 999  # Very old or inaccessible
        
        # Count tests
        test_count = self._count_tests(test_file)
        
        # Set assertion requirements based on importance
        assertion_requirements = {
            "minimum": self.config.assertion_minimums[importance],
            "error_testing": self.config.error_testing_requirements[importance],
            "boundary_testing": self.config.boundary_testing_requirements[importance],
        }
        
        return ModuleContext(
            importance=importance,
            complexity_score=complexity_score,
            risk_level=risk_level,
            is_critical_path=is_critical_path,
            last_modified_days=last_modified_days,
            test_count=test_count,
            assertion_requirements=assertion_requirements
        )
    
    def _determine_module_importance(self, test_file: Path) -> ModuleImportance:
        """Determine the importance level of a test module."""
        file_path = str(test_file).lower()
        file_name = test_file.name.lower()
        
        # Critical modules
        critical_patterns = [
            'critical', 'core', 'main', 'primary', 'essential',
            'database', 'auth', 'security', 'api',
            'pensieve_critical_path', 'basic_functionality'
        ]
        if any(pattern in file_path or pattern in file_name for pattern in critical_patterns):
            return ModuleImportance.CRITICAL
        
        # Infrastructure modules  
        infra_patterns = [
            'health', 'infrastructure', 'config', 'setup', 'util',
            'test_', 'conftest', 'fixture', 'helper'
        ]
        if any(pattern in file_path for pattern in infra_patterns):
            # But health tests that check critical functionality are important
            if 'codebase_health' in file_name or 'testing_system' in file_name:
                return ModuleImportance.IMPORTANT
            return ModuleImportance.INFRASTRUCTURE
        
        # Experimental modules
        experimental_patterns = [
            'experimental', 'prototype', 'test_new', 'draft',
            'sandbox', 'poc', 'trial'
        ]
        if any(pattern in file_path or pattern in file_name for pattern in experimental_patterns):
            return ModuleImportance.EXPERIMENTAL
        
        # Important modules
        important_patterns = [
            'integration', 'e2e', 'dashboard', 'ai', 'processing',
            'analysis', 'workflow', 'pipeline'
        ]
        if any(pattern in file_path or pattern in file_name for pattern in important_patterns):
            return ModuleImportance.IMPORTANT
        
        # Default to standard
        return ModuleImportance.STANDARD
    
    def _calculate_complexity_score(self, test_file: Path) -> float:
        """Calculate complexity score (0.0 to 1.0) based on code analysis."""
        try:
            content = test_file.read_text(encoding='utf-8', errors='ignore')
        except (OSError, UnicodeDecodeError):
            return 0.5  # Default complexity
        
        if not content:
            return 0.0
        
        # Count various complexity indicators
        lines = content.split('\n')
        line_count = len([line for line in lines if line.strip()])
        
        # Complexity factors
        factors = {
            'functions': len(re.findall(r'def \w+\(', content)),
            'classes': len(re.findall(r'class \w+', content)),
            'imports': len(re.findall(r'^import |^from .* import', content, re.MULTILINE)),
            'conditionals': len(re.findall(r'\bif\b|\belif\b|\belse\b', content)),
            'loops': len(re.findall(r'\bfor\b|\bwhile\b', content)),
            'exceptions': len(re.findall(r'\btry\b|\bexcept\b|\bfinally\b', content)),
            'assertions': len(re.findall(r'\bassert\b', content)),
            'mocks': len(re.findall(r'\bmock\b|\bMock\b|\bpatch\b', content, re.IGNORECASE)),
        }
        
        # Normalize factors
        if line_count == 0:
            return 0.0
        
        # Calculate weighted complexity score
        complexity_score = (
            factors['functions'] * 0.15 +
            factors['classes'] * 0.20 +
            factors['conditionals'] * 0.15 +
            factors['loops'] * 0.10 +
            factors['exceptions'] * 0.10 +
            factors['mocks'] * 0.10 +
            min(line_count / 100, 1.0) * 0.20  # File size factor
        ) / 10.0  # Normalize to 0-1 range
        
        return min(complexity_score, 1.0)
    
    def _assess_risk_level(self, test_file: Path, importance: ModuleImportance, 
                          complexity_score: float) -> float:
        """Assess risk level based on importance, complexity, and other factors."""
        # Base risk from importance
        importance_risk = {
            ModuleImportance.CRITICAL: 0.8,
            ModuleImportance.IMPORTANT: 0.6,
            ModuleImportance.STANDARD: 0.4,
            ModuleImportance.EXPERIMENTAL: 0.3,
            ModuleImportance.INFRASTRUCTURE: 0.2,
        }[importance]
        
        # Adjust for complexity
        complexity_risk = complexity_score * 0.5
        
        # Adjust for external dependencies
        try:
            content = test_file.read_text(encoding='utf-8', errors='ignore')
            external_deps = len(re.findall(r'requests\.|subprocess\.|socket\.|urllib\.', content))
            dependency_risk = min(external_deps * 0.1, 0.3)
        except (OSError, UnicodeDecodeError):
            dependency_risk = 0.0
        
        # Combine risk factors
        total_risk = min(importance_risk + complexity_risk + dependency_risk, 1.0)
        return total_risk
    
    def _is_critical_path(self, test_file: Path) -> bool:
        """Determine if test file is on critical execution path."""
        file_path = str(test_file).lower()
        
        critical_path_indicators = [
            'critical_path', 'end_to_end', 'e2e', 'main_flow',
            'user_journey', 'core_functionality', 'basic_functionality'
        ]
        
        return any(indicator in file_path for indicator in critical_path_indicators)
    
    def _count_tests(self, test_file: Path) -> int:
        """Count number of test functions in file."""
        try:
            content = test_file.read_text(encoding='utf-8', errors='ignore')
            return len(re.findall(r'def test_\w+\(', content))
        except (OSError, UnicodeDecodeError):
            return 0
    
    def get_smart_file_selection(self, all_test_files: List[Path]) -> List[Path]:
        """Select files for testing based on intelligence and current mode."""
        # Analyze all files and categorize by importance
        categorized_files: Dict[ModuleImportance, List[Tuple[Path, ModuleContext]]] = {
            importance: [] for importance in ModuleImportance
        }
        
        for test_file in all_test_files:
            context = self.analyze_module_context(test_file)
            categorized_files[context.importance].append((test_file, context))
        
        # Sort each category by priority (risk * recency)
        for importance in ModuleImportance:
            categorized_files[importance].sort(
                key=lambda x: (x[1].risk_level * (1.0 / max(x[1].last_modified_days, 1)), 
                              x[1].complexity_score),
                reverse=True
            )
        
        # Select files based on mode limits
        selected_files = []
        for importance in ModuleImportance:
            max_files = self.config.max_files_per_category[importance]
            selected = categorized_files[importance][:max_files]
            selected_files.extend([file_path for file_path, _ in selected])
        
        logger.info(f"Smart file selection: {len(selected_files)} files selected from {len(all_test_files)} total")
        self._log_selection_summary(categorized_files, selected_files)
        
        return selected_files
    
    def _log_selection_summary(self, categorized_files: Dict[ModuleImportance, List], 
                              selected_files: List[Path]) -> None:
        """Log summary of file selection for transparency."""
        logger.info(f"File selection summary (mode: {self.mode.value}):")
        for importance in ModuleImportance:
            total = len(categorized_files[importance])
            selected = len([f for f in selected_files 
                          if any(str(f) == str(file_path) for file_path, _ in categorized_files[importance])])
            logger.info(f"  {importance.value}: {selected}/{total} files selected")
    
    def get_context_aware_thresholds(self, test_file: Path) -> Dict[str, any]:
        """Get context-aware validation thresholds for a specific test file."""
        context = self.analyze_module_context(test_file)
        
        return {
            'minimum_assertions': context.assertion_requirements['minimum'],
            'requires_error_testing': context.assertion_requirements['error_testing'],
            'requires_boundary_testing': context.assertion_requirements['boundary_testing'],
            'max_sleep_time': self.config.performance_thresholds[context.importance]['max_sleep'],
            'max_timeout': self.config.performance_thresholds[context.importance]['max_timeout'],
            'importance_level': context.importance.value,
            'complexity_score': context.complexity_score,
            'risk_level': context.risk_level,
            'is_critical_path': context.is_critical_path,
        }
    
    def should_apply_strict_validation(self, test_file: Path) -> bool:
        """Determine if strict validation should be applied to this file."""
        context = self.analyze_module_context(test_file)
        
        # Always apply strict validation to critical and important modules
        if context.importance in [ModuleImportance.CRITICAL, ModuleImportance.IMPORTANT]:
            return True
        
        # Apply to high-risk standard modules
        if context.importance == ModuleImportance.STANDARD and context.risk_level > 0.6:
            return True
        
        # Apply to recent changes in any module (within 7 days)
        if context.last_modified_days <= 7:
            return True
        
        return False
    
    def get_intelligent_error_message(self, test_file: Path, test_function: str, 
                                    issue_type: str, details: str) -> str:
        """Generate intelligent, context-aware error message."""
        context = self.analyze_module_context(test_file)
        
        # Impact assessment
        impact_level = "🎯 High" if context.importance == ModuleImportance.CRITICAL else \
                      "⚠️ Medium" if context.importance == ModuleImportance.IMPORTANT else \
                      "📝 Low"
        
        # Priority based on context
        priority = "🚨 URGENT" if context.is_critical_path else \
                  "⏰ Soon" if context.risk_level > 0.7 else \
                  "📋 Standard"
        
        # Build intelligent message
        message = f"""
❌ {test_file.name}:{test_function} - {issue_type}
💡 Issue: {details}
📍 Context: {context.importance.value} module (complexity: {context.complexity_score:.2f})
{impact_level} Impact | {priority} Priority
"""
        
        # Add specific recommendations based on context
        if context.importance == ModuleImportance.CRITICAL:
            message += "🔧 Fix: Critical module requires comprehensive validation\n"
        elif context.is_critical_path:
            message += "🔧 Fix: Critical path requires error condition testing\n"
        
        # Add guidance based on issue type
        if "assertion" in issue_type.lower():
            min_assertions = context.assertion_requirements['minimum']
            message += f"📚 Guide: Add {min_assertions} meaningful assertions minimum\n"
        
        return message.strip()
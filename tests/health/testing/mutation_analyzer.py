"""Mutation analysis module - analyzes results and generates reports.

This module is responsible for analyzing mutation testing results and
generating effectiveness reports with recommendations.
"""

import logging
from pathlib import Path
from typing import List, Dict, Optional
from dataclasses import dataclass, field

from .mutation_executor import MutationResult

logger = logging.getLogger(__name__)


@dataclass
class TestEffectivenessReport:
    """Report on test effectiveness based on mutation testing."""
    test_file: Path
    source_file: Optional[Path]
    total_mutations: int
    caught_mutations: int
    effectiveness_percentage: float
    uncaught_mutations: List[Dict] = field(default_factory=list)
    recommendations: List[str] = field(default_factory=list)
    error: Optional[str] = None
    
    @property
    def is_effective(self) -> bool:
        """Check if tests are considered effective (>70% mutations caught)."""
        return self.effectiveness_percentage >= 70.0


class MutationAnalyzer:
    """Analyzes mutation testing results to measure test effectiveness."""
    
    def __init__(self):
        self.effectiveness_thresholds = {
            'excellent': 90.0,
            'good': 70.0,
            'moderate': 50.0,
            'poor': 30.0
        }
    
    def analyze_results(self, test_file: Path, source_file: Optional[Path], 
                       results: List[MutationResult]) -> TestEffectivenessReport:
        """Analyze mutation testing results to create effectiveness report.
        
        Args:
            test_file: Path to the test file
            source_file: Path to the source file (may be None)
            results: List of mutation results
            
        Returns:
            TestEffectivenessReport with analysis and recommendations
        """
        if not results:
            return self._create_empty_report(test_file, source_file, "No mutation results")
        
        # Calculate basic metrics
        total_mutations = len(results)
        caught_mutations = sum(1 for r in results if r.was_caught)
        effectiveness = (caught_mutations / total_mutations) * 100 if total_mutations > 0 else 0.0
        
        # Find uncaught mutations
        uncaught = []
        for result in results:
            if not result.was_caught:
                uncaught.append({
                    'type': result.mutation_type,
                    'line': result.line_number,
                    'original': result.original_code,
                    'mutated': result.mutated_code,
                    'file': str(result.file_path)
                })
        
        # Generate recommendations
        recommendations = self._generate_recommendations(results, effectiveness)
        
        return TestEffectivenessReport(
            test_file=test_file,
            source_file=source_file,
            total_mutations=total_mutations,
            caught_mutations=caught_mutations,
            effectiveness_percentage=effectiveness,
            uncaught_mutations=uncaught,
            recommendations=recommendations
        )
    
    def _generate_recommendations(self, results: List[MutationResult], effectiveness: float) -> List[str]:
        """Generate specific recommendations based on mutation testing results."""
        recommendations = []
        
        # Overall effectiveness recommendation
        if effectiveness >= self.effectiveness_thresholds['excellent']:
            recommendations.append("✅ Excellent test effectiveness! Keep up the good work.")
        elif effectiveness >= self.effectiveness_thresholds['good']:
            recommendations.append("👍 Good test effectiveness, but room for improvement.")
        elif effectiveness >= self.effectiveness_thresholds['moderate']:
            recommendations.append("⚠️ Moderate test effectiveness - significant gaps exist.")
        else:
            recommendations.append("❌ Poor test effectiveness - major improvements needed.")
        
        # Analyze patterns in uncaught mutations
        uncaught_by_type = {}
        for result in results:
            if not result.was_caught:
                mutation_type = result.mutation_type
                if mutation_type not in uncaught_by_type:
                    uncaught_by_type[mutation_type] = 0
                uncaught_by_type[mutation_type] += 1
        
        # Type-specific recommendations
        if 'off_by_one' in uncaught_by_type:
            recommendations.append(
                f"🔍 Add boundary tests: {uncaught_by_type['off_by_one']} off-by-one mutations missed. "
                "Test edge cases like n-1, n, n+1."
            )
        
        if 'boolean_flip' in uncaught_by_type:
            recommendations.append(
                f"🔍 Add boolean tests: {uncaught_by_type['boolean_flip']} boolean mutations missed. "
                "Test both True and False conditions."
            )
        
        if 'return_value' in uncaught_by_type:
            recommendations.append(
                f"🔍 Add return value tests: {uncaught_by_type['return_value']} return mutations missed. "
                "Verify actual return values, not just side effects."
            )
        
        if 'exception_handling' in uncaught_by_type:
            recommendations.append(
                f"🔍 Add error tests: {uncaught_by_type['exception_handling']} exception mutations missed. "
                "Test error conditions with pytest.raises()."
            )
        
        # Line coverage recommendation
        if len(results) < 5:
            recommendations.append(
                "📊 Low mutation coverage: Only tested a few code paths. "
                "Consider adding more comprehensive tests."
            )
        
        # High-level recommendation
        if effectiveness < self.effectiveness_thresholds['good']:
            recommendations.append(
                "💡 Focus on: Write tests that verify specific behaviors, not just code execution. "
                "Each test should fail if the implementation is wrong."
            )
        
        return recommendations
    
    def _create_empty_report(self, test_file: Path, source_file: Optional[Path], 
                           reason: str) -> TestEffectivenessReport:
        """Create an empty report when mutation testing cannot be performed."""
        return TestEffectivenessReport(
            test_file=test_file,
            source_file=source_file,
            total_mutations=0,
            caught_mutations=0,
            effectiveness_percentage=0.0,
            error=reason,
            recommendations=[f"⚠️ Could not perform mutation testing: {reason}"]
        )
    
    def get_effectiveness_rating(self, percentage: float) -> str:
        """Get human-readable effectiveness rating.
        
        Args:
            percentage: Effectiveness percentage (0-100)
            
        Returns:
            Rating string (excellent/good/moderate/poor/very poor)
        """
        if percentage >= self.effectiveness_thresholds['excellent']:
            return 'excellent'
        elif percentage >= self.effectiveness_thresholds['good']:
            return 'good'
        elif percentage >= self.effectiveness_thresholds['moderate']:
            return 'moderate'
        elif percentage >= self.effectiveness_thresholds['poor']:
            return 'poor'
        else:
            return 'very poor'
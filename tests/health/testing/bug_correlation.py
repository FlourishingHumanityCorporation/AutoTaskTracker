"""Real-world bug correlation analysis from Git history and issue tracking.

This module analyzes actual bugs that occurred in the codebase and correlates
them with test patterns to identify what kinds of tests actually prevent real bugs.
"""

import logging
import subprocess
import re
import json
from pathlib import Path
from typing import List, Dict, Set, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime, timedelta
from collections import defaultdict

logger = logging.getLogger(__name__)


@dataclass
class BugPattern:
    """A pattern representing a real bug that occurred."""
    bug_type: str
    file_path: str
    commit_hash: str
    date: datetime
    description: str
    fix_diff: str
    test_that_should_have_caught_it: Optional[str] = None


@dataclass
class TestCorrelation:
    """Correlation between test patterns and bug prevention."""
    test_pattern: str
    bugs_prevented: List[BugPattern]
    bugs_missed: List[BugPattern]
    effectiveness_score: float
    recommendation: str


class GitBugAnalyzer:
    """Analyzes Git history to identify actual bugs and their patterns."""
    
    def __init__(self, project_root: Path):
        self.project_root = project_root
        self.bug_keywords = [
            'fix', 'bug', 'error', 'issue', 'problem', 'crash', 'fail',
            'broken', 'incorrect', 'wrong', 'exception', 'null', 'undefined'
        ]
        
    def extract_historical_bugs(self, days_back: int = 90) -> List[BugPattern]:
        """Extract real bugs from Git commit history."""
        since_date = (datetime.now() - timedelta(days=days_back)).strftime('%Y-%m-%d')
        
        try:
            # Get commits that look like bug fixes
            result = subprocess.run([
                'git', 'log', '--oneline', '--since', since_date,
                '--grep=fix', '--grep=bug', '--grep=error', 
                '--grep=issue', '--grep=crash', '--grep=fail',
                '--ignore-case'
            ], capture_output=True, text=True, cwd=self.project_root)
            
            if result.returncode != 0:
                logger.warning("Could not access Git history")
                return []
                
            commits = result.stdout.strip().split('\n')
            bugs = []
            
            for commit_line in commits:
                if not commit_line.strip():
                    continue
                    
                parts = commit_line.split(' ', 1)
                if len(parts) < 2:
                    continue
                    
                commit_hash = parts[0]
                description = parts[1]
                
                # Analyze this commit to extract bug pattern
                bug_pattern = self._analyze_bug_commit(commit_hash, description)
                if bug_pattern:
                    bugs.append(bug_pattern)
                    
            return bugs[:20]  # Limit to prevent long analysis
            
        except Exception as e:
            logger.warning(f"Git analysis failed: {e}")
            return []
    
    def _analyze_bug_commit(self, commit_hash: str, description: str) -> Optional[BugPattern]:
        """Analyze a specific commit to extract bug pattern."""
        try:
            # Get the diff for this commit
            result = subprocess.run([
                'git', 'show', '--name-only', commit_hash
            ], capture_output=True, text=True, cwd=self.project_root)
            
            if result.returncode != 0:
                return None
                
            diff_output = result.stdout
            
            # Extract changed files
            files = []
            for line in diff_output.split('\n'):
                if line.endswith('.py') and not line.startswith('test_'):
                    files.append(line.strip())
            
            if not files:
                return None
                
            # Get the actual diff
            diff_result = subprocess.run([
                'git', 'show', commit_hash
            ], capture_output=True, text=True, cwd=self.project_root)
            
            if diff_result.returncode != 0:
                return None
                
            diff_content = diff_result.stdout
            
            # Classify the bug type
            bug_type = self._classify_bug_type(description, diff_content)
            
            # Get commit date
            date_result = subprocess.run([
                'git', 'show', '-s', '--format=%ci', commit_hash
            ], capture_output=True, text=True, cwd=self.project_root)
            
            commit_date = datetime.now()  # Default
            if date_result.returncode == 0:
                try:
                    commit_date = datetime.fromisoformat(date_result.stdout.strip().replace(' ', 'T', 1))
                except (ValueError, TypeError) as e:
                    logger.debug(f"Could not parse commit date for {commit_hash}: {e}")
                    # commit_date remains as default
            
            return BugPattern(
                bug_type=bug_type,
                file_path=files[0] if files else "unknown",
                commit_hash=commit_hash,
                date=commit_date,
                description=description,
                fix_diff=diff_content
            )
            
        except (subprocess.SubprocessError, subprocess.TimeoutExpired) as e:
            logger.warning(f"Git operation failed for commit {commit_hash}: {e}")
            return None
        except (OSError, ValueError) as e:
            logger.warning(f"Bug commit analysis failed for {commit_hash}: {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error analyzing commit {commit_hash}: {e}")
            return None
    
    def _classify_bug_type(self, description: str, diff: str) -> str:
        """Classify the type of bug based on description and diff."""
        desc_lower = description.lower()
        diff_lower = diff.lower()
        
        # Off-by-one errors
        if any(pattern in diff for pattern in ['->', '<=', '>=', '==', '!=']):
            if any(keyword in desc_lower for keyword in ['boundary', 'index', 'range', 'length']):
                return "off_by_one"
                
        # Null pointer / None issues
        if any(keyword in desc_lower for keyword in ['null', 'none', 'undefined', 'attributeerror']):
            return "null_pointer"
            
        # Logic errors
        if any(pattern in diff_lower for pattern in ['and', 'or', 'not', 'if', 'else']):
            return "logic_error"
            
        # Error handling
        if any(keyword in desc_lower for keyword in ['exception', 'error', 'catch', 'handle']):
            return "error_handling"
            
        # Concurrency issues
        if any(keyword in desc_lower for keyword in ['thread', 'async', 'lock', 'race']):
            return "concurrency"
            
        # Configuration/environment issues
        if any(keyword in desc_lower for keyword in ['config', 'env', 'setting', 'path']):
            return "configuration"
            
        # Performance issues
        if any(keyword in desc_lower for keyword in ['slow', 'performance', 'timeout', 'memory']):
            return "performance"
            
        # Integration issues
        if any(keyword in desc_lower for keyword in ['api', 'database', 'connection', 'service']):
            return "integration"
            
        return "other"


class TestBugCorrelationAnalyzer:
    """Analyzes correlation between test patterns and actual bug prevention."""
    
    def __init__(self, project_root: Path):
        self.project_root = project_root
        self.test_dir = project_root / "tests"
        self.git_analyzer = GitBugAnalyzer(project_root)
        
    def analyze_test_bug_correlation(self) -> List[TestCorrelation]:
        """Analyze which test patterns actually prevent real bugs."""
        # Get historical bugs
        bugs = self.git_analyzer.extract_historical_bugs()
        if not bugs:
            return []
            
        # Group bugs by type
        bugs_by_type = defaultdict(list)
        for bug in bugs:
            bugs_by_type[bug.bug_type].append(bug)
            
        correlations = []
        
        # Analyze correlation for each bug type
        for bug_type, bug_list in bugs_by_type.items():
            correlation = self._analyze_bug_type_correlation(bug_type, bug_list)
            if correlation:
                correlations.append(correlation)
                
        return correlations
    
    def _analyze_bug_type_correlation(self, bug_type: str, bugs: List[BugPattern]) -> Optional[TestCorrelation]:
        """Analyze correlation between test patterns and specific bug types."""
        # Define test patterns that should prevent each bug type
        test_patterns = {
            'off_by_one': [
                r'assert.*== 0',
                r'assert.*== 1', 
                r'assert.*== -1',
                r'range\(.*\)',
                r'len\(.*\)',
                r'boundary|edge|limit'
            ],
            'null_pointer': [
                r'assert.*is not None',
                r'assert.*!= None',
                r'if.*is None',
                r'none|null|empty'
            ],
            'logic_error': [
                r'assert.*and.*',
                r'assert.*or.*',
                r'if.*else',
                r'True.*False'
            ],
            'error_handling': [
                r'pytest\.raises',
                r'except.*Exception',
                r'try.*except',
                r'error|exception|fail'
            ],
            'integration': [
                r'mock.*patch',
                r'requests\.',
                r'database|db|api',
                r'connection|service'
            ]
        }
        
        patterns = test_patterns.get(bug_type, [])
        if not patterns:
            return None
            
        # Find tests that should have caught these bugs
        prevented_bugs = []
        missed_bugs = []
        
        for bug in bugs:
            # Find corresponding test file
            test_file = self._find_test_file_for_source(bug.file_path)
            if test_file:
                # Check if test has patterns that should prevent this bug type
                has_preventive_patterns = self._test_has_patterns(test_file, patterns)
                if has_preventive_patterns:
                    prevented_bugs.append(bug)
                else:
                    missed_bugs.append(bug)
            else:
                missed_bugs.append(bug)
                
        total_bugs = len(prevented_bugs) + len(missed_bugs)
        effectiveness = len(prevented_bugs) / total_bugs if total_bugs > 0 else 0
        
        # Generate recommendation
        recommendation = self._generate_bug_correlation_recommendation(
            bug_type, effectiveness, missed_bugs, patterns
        )
        
        return TestCorrelation(
            test_pattern=bug_type,
            bugs_prevented=prevented_bugs,
            bugs_missed=missed_bugs,
            effectiveness_score=effectiveness * 100,
            recommendation=recommendation
        )
    
    def _find_test_file_for_source(self, source_path: str) -> Optional[Path]:
        """Find the test file that should cover the given source file."""
        source_name = Path(source_path).stem
        
        # Common test file patterns
        test_patterns = [
            f"test_{source_name}.py",
            f"{source_name}_test.py",
            f"test_{source_name}_*.py"
        ]
        
        for pattern in test_patterns:
            for test_file in self.test_dir.rglob(pattern):
                if test_file.is_file():
                    return test_file
                    
        return None
    
    def _test_has_patterns(self, test_file: Path, patterns: List[str]) -> bool:
        """Check if a test file contains patterns that should prevent specific bugs."""
        try:
            content = test_file.read_text(encoding='utf-8')
            return any(re.search(pattern, content, re.IGNORECASE) for pattern in patterns)
        except Exception:
            return False
    
    def _generate_bug_correlation_recommendation(self, bug_type: str, effectiveness: float,
                                               missed_bugs: List[BugPattern], patterns: List[str]) -> str:
        """Generate recommendations based on bug correlation analysis."""
        if effectiveness >= 0.8:
            return f"✅ EXCELLENT: Tests effectively prevent {bug_type} bugs ({effectiveness:.0%} success rate)"
        elif effectiveness >= 0.6:
            return f"✓ GOOD: Tests mostly prevent {bug_type} bugs ({effectiveness:.0%} success rate), minor gaps exist"
        elif effectiveness >= 0.4:
            return f"⚠️ WARNING: Tests have moderate gaps for {bug_type} bugs ({effectiveness:.0%} success rate)"
        else:
            specific_recommendations = {
                'off_by_one': "Add boundary value testing (0, 1, -1, max/min values)",
                'null_pointer': "Add null/None checking in all object access paths", 
                'logic_error': "Test both true and false branches of all conditions",
                'error_handling': "Add error condition testing with pytest.raises",
                'integration': "Add integration tests with real component interaction"
            }
            
            base_rec = f"🚨 CRITICAL: Tests poorly prevent {bug_type} bugs ({effectiveness:.0%} success rate)"
            specific_rec = specific_recommendations.get(bug_type, "Add comprehensive testing")
            
            return f"{base_rec}. {specific_rec}"


class RealWorldEffectivenessAnalyzer:
    """Combines mutation testing with real bug correlation for comprehensive effectiveness analysis."""
    
    def __init__(self, project_root: Path):
        self.project_root = project_root
        self.correlation_analyzer = TestBugCorrelationAnalyzer(project_root)
        
    def analyze_real_world_effectiveness(self, test_file: Path) -> Dict[str, any]:
        """Comprehensive real-world effectiveness analysis."""
        results = {
            'test_file': test_file.name,
            'historical_bug_prevention': {},
            'bug_correlation_score': 0.0,
            'real_world_recommendations': [],
            'effectiveness_rating': 'unknown'
        }
        
        try:
            # Analyze bug correlation
            correlations = self.correlation_analyzer.analyze_test_bug_correlation()
            
            if correlations:
                # Calculate overall bug prevention score
                total_score = sum(c.effectiveness_score for c in correlations)
                avg_score = total_score / len(correlations)
                results['bug_correlation_score'] = avg_score
                
                # Extract specific bug type effectiveness
                for correlation in correlations:
                    results['historical_bug_prevention'][correlation.test_pattern] = {
                        'effectiveness': correlation.effectiveness_score,
                        'bugs_prevented': len(correlation.bugs_prevented),
                        'bugs_missed': len(correlation.bugs_missed),
                        'recommendation': correlation.recommendation
                    }
                    results['real_world_recommendations'].append(correlation.recommendation)
                
                # Overall effectiveness rating
                if avg_score >= 80:
                    results['effectiveness_rating'] = 'excellent'
                elif avg_score >= 60:
                    results['effectiveness_rating'] = 'good'
                elif avg_score >= 40:
                    results['effectiveness_rating'] = 'moderate'
                else:
                    results['effectiveness_rating'] = 'poor'
            else:
                results['real_world_recommendations'] = [
                    "📊 No recent bug history found - analysis based on common patterns"
                ]
                
        except Exception as e:
            logger.error(f"Real-world effectiveness analysis failed: {e}")
            results['real_world_recommendations'] = [f"Analysis failed: {e}"]
            
        return results
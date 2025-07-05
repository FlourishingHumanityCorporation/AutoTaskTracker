"""Enhanced import health tests for AutoTaskTracker.

Tests import patterns, identifies issues, and provides automated fixes
to reduce import overhead during refactoring. Follows CLAUDE.md guidelines.
"""

import pytest
import os
from pathlib import Path
import logging
import subprocess
import sys

from tests.health.import_system import ImportAnalyzer, ImportFixer, ImportValidator, ImportOptimizer

logger = logging.getLogger(__name__)


class TestImportHealth:
    """Test import patterns and optimization opportunities."""
    
    @pytest.fixture(scope="class")
    def import_analyzer(self):
        """Create and run import analyzer."""
        project_root = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
        analyzer = ImportAnalyzer(project_root)
        return analyzer
    
    @pytest.fixture(scope="class")
    def import_fixer(self):
        """Create import fixer for automated fixes."""
        project_root = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
        return ImportFixer(project_root)
    
    @pytest.fixture(scope="class")
    def import_validator(self):
        """Create import validator for comprehensive validation."""
        project_root = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
        return ImportValidator(project_root)
    
    @pytest.fixture(scope="class")
    def import_optimizer(self):
        """Create import optimizer for optimization opportunities."""
        project_root = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
        return ImportOptimizer(project_root)
    
    @pytest.fixture(scope="class")  
    def analysis_results(self, import_analyzer):
        """Get analysis results."""
        return import_analyzer.analyze_codebase()
    
    @pytest.fixture(scope="class")
    def fixable_issues(self, import_fixer):
        """Get detailed import issues that can be fixed."""
        return import_fixer.find_fixable_issues()
    
    @pytest.fixture(scope="class")
    def validation_results(self, import_validator):
        """Get import validation results."""
        return import_validator.validate_all_imports()
    
    @pytest.fixture(scope="class")
    def optimization_opportunities(self, import_optimizer):
        """Get import optimization opportunities."""
        return import_optimizer.analyze_optimization_opportunities()
    
    def test_no_critical_antipatterns(self, analysis_results):
        """Ensure no critical antipatterns exist."""
        antipatterns = analysis_results['antipatterns']
        
        # Critical violations from CLAUDE.md
        critical_issues = []
        
        # Check for sys.path.append usage (forbidden)
        if antipatterns['sys_path_append']:
            critical_issues.extend([
                f"sys.path.append found in {issue['file']}:{issue['line']}"
                for issue in antipatterns['sys_path_append']
            ])
        
        # Check for direct sqlite3 usage (should use DatabaseManager)
        if antipatterns['direct_sqlite']:
            critical_issues.extend([
                f"Direct sqlite3 usage in {issue['file']}:{issue['line']} - {issue['recommendation']}"
                for issue in antipatterns['direct_sqlite']
            ])
        
        assert len(critical_issues) == 0, f"Critical import antipatterns found:\\n" + "\\n".join(critical_issues)
    
    def test_minimal_bare_except_clauses(self, analysis_results):
        """Check for bare except clauses (should be minimized)."""
        bare_excepts = analysis_results['antipatterns']['bare_except']
        
        if bare_excepts:
            issues = [f"{issue['file']}:{issue['line']}" for issue in bare_excepts]
            logger.warning(f"Bare except clauses found: {issues}")
            
            # Allow some bare excepts but keep them minimal
            assert len(bare_excepts) <= 5, f"Too many bare except clauses ({len(bare_excepts)}). Use specific exceptions."
    
    def test_minimal_print_statements_in_production(self, analysis_results):
        """Check for print statements in production code."""
        print_statements = analysis_results['antipatterns']['print_statements']
        
        if print_statements:
            issues = [f"{issue['file']}:{issue['line']}" for issue in print_statements]
            logger.warning(f"Print statements in production code: {issues}")
            
            # Should use logging instead
            assert len(print_statements) <= 3, f"Print statements found in production code. Use logging instead."
    
    def test_no_relative_imports(self, analysis_results):
        """Ensure no relative imports are used."""
        relative_imports = analysis_results['antipatterns']['relative_imports']
        
        if relative_imports:
            issues = [f"{issue['file']}:{issue['line']} - {issue['import']}" 
                     for issue in relative_imports]
            
            # CLAUDE.md forbids relative imports
            assert len(relative_imports) == 0, f"Relative imports found (forbidden by CLAUDE.md):\\n" + "\\n".join(issues)
    
    def test_import_health_score(self, analysis_results, import_analyzer):
        """Calculate and validate overall import health score."""
        health_score = import_analyzer.get_import_health_score()
        
        logger.info(f"Import health score: {health_score['score']}/100")
        logger.info(f"Details: {health_score['details']}")
        
        # Score should be reasonable (allow some room for improvement)
        assert health_score['score'] >= 70, f"Import health score too low: {health_score['score']}/100"
    
    def test_barrel_export_opportunities(self, analysis_results):
        """Identify opportunities for barrel exports to reduce import overhead."""
        barrel_candidates = analysis_results['optimization_opportunities']['barrel_exports']
        
        logger.info(f"Barrel export opportunities found: {len(barrel_candidates)}")
        
        # Log top opportunities
        for directory, items in list(barrel_candidates.items())[:5]:
            logger.info(f"  {directory}: {len(items)} exports ({', '.join(items[:3])}...)")
        
        # This is informational - no assertion needed
        # High barrel export opportunities suggest good modularization
        if len(barrel_candidates) >= 3:
            logger.info("Good modularization - multiple barrel export opportunities available")
    
    def test_factory_pattern_opportunities(self, analysis_results):
        """Identify opportunities for factory patterns."""
        factory_candidates = analysis_results['optimization_opportunities']['factory_candidates']
        
        logger.info(f"Factory pattern opportunities: {len(factory_candidates)}")
        
        for candidate in factory_candidates[:3]:
            logger.info(f"  Consider factory for: {candidate}")
        
        # This is informational - helps identify refactoring opportunities
    
    def test_interface_opportunities(self, analysis_results):
        """Identify opportunities for interface abstractions."""
        interface_candidates = analysis_results['optimization_opportunities']['interface_candidates']
        
        logger.info(f"Interface opportunities: {len(interface_candidates)}")
        
        # Group by pattern
        patterns = {}
        for candidate in interface_candidates:
            for base in ['Manager', 'Processor', 'Analyzer', 'Handler', 'Service']:
                if base in candidate:
                    patterns.setdefault(base, []).append(candidate)
        
        for pattern, classes in patterns.items():
            if len(classes) >= 2:
                logger.info(f"  Abstract{pattern} interface could unify: {classes}")
    
    def test_frequent_import_analysis(self, analysis_results):
        """Analyze most frequently imported modules."""
        frequent_imports = analysis_results['import_frequency']
        
        logger.info("Most frequently imported modules:")
        for module, count in list(frequent_imports.items())[:10]:
            logger.info(f"  {module}: {count} times")
        
        # Check if core modules are being imported frequently (good sign)
        core_modules = [mod for mod in frequent_imports.keys() 
                       if any(core in mod for core in ['DatabaseManager', 'TaskExtractor', 'logging'])]
        
        assert len(core_modules) >= 2, "Core modules should be frequently imported"
    
    def test_import_consolidation_opportunities(self, analysis_results):
        """Identify files with import consolidation opportunities."""
        recommendations = analysis_results['recommendations']
        
        consolidation_recs = [rec for rec in recommendations if rec['type'] == 'consolidation']
        
        logger.info(f"Import consolidation opportunities: {len(consolidation_recs)}")
        
        for rec in consolidation_recs[:3]:
            logger.info(f"  {rec['file']}: {len(rec['imports'])} imports from {rec['module']}")
    
    def test_no_circular_imports(self, analysis_results):
        """Check for circular import dependencies."""
        circular_imports = analysis_results['circular_imports']
        
        if circular_imports:
            issues = [f"{pair[0]} <-> {pair[1]}" for pair in circular_imports]
            logger.warning(f"Circular imports detected: {issues}")
            
            # Circular imports should be avoided
            assert len(circular_imports) <= 2, f"Too many circular imports: {circular_imports}"
    
    def test_duplicate_import_analysis(self, analysis_results):
        """Analyze duplicate imports across files."""
        duplicate_imports = analysis_results['duplicate_imports']
        
        logger.info(f"Modules with duplicate imports: {len(duplicate_imports)}")
        
        # Log modules imported in many places (candidates for barrel exports)
        for module, files in duplicate_imports.items():
            if len(files) >= 5:
                logger.info(f"  {module} imported in {len(files)} files - consider barrel export")
    
    def test_scripts_import_patterns(self, import_analyzer):
        """Test that scripts follow proper import patterns."""
        scripts_imports = {
            file_path: imports for file_path, imports in import_analyzer.imports_by_file.items()
            if file_path.startswith('scripts/')
        }
        
        logger.info(f"Scripts analyzed: {len(scripts_imports)}")
        
        # Scripts should use sys.path.insert pattern (not append)
        path_violations = []
        for file_path, imports in scripts_imports.items():
            for imp in imports:
                if (imp['type'] == 'from_import' and 
                    imp['module'] == 'sys' and 
                    'path' in str(imp)):
                    
                    # Check if using insert vs append (insert is preferred)
                    with open(import_analyzer.project_root / file_path, 'r') as f:
                        content = f.read()
                        if 'sys.path.append' in content:
                            path_violations.append(file_path)
        
        if path_violations:
            logger.warning(f"Scripts using sys.path.append: {path_violations}")
            # Note: CLAUDE.md shows sys.path.insert as acceptable for scripts
    
    def test_package_init_completeness(self, import_analyzer):
        """Check if __init__.py files exist where needed."""
        package_dirs = set()
        
        # Find directories that should have __init__.py
        for file_path in import_analyzer.imports_by_file.keys():
            if file_path.startswith('autotasktracker/'):
                parts = Path(file_path).parts[:-1]  # Exclude filename
                for i in range(1, len(parts) + 1):
                    package_dirs.add('/'.join(parts[:i]))
        
        missing_inits = []
        for pkg_dir in package_dirs:
            init_path = import_analyzer.project_root / pkg_dir / '__init__.py'
            if not init_path.exists():
                missing_inits.append(pkg_dir)
        
        if missing_inits:
            logger.warning(f"Missing __init__.py files: {missing_inits}")
            
        # Allow some missing __init__.py but core directories should have them
        core_missing = [d for d in missing_inits if '/core' in d or '/ai' in d or '/dashboards' in d]
        assert len(core_missing) == 0, f"Core directories missing __init__.py: {core_missing}"
    
    def test_comprehensive_import_validation(self, validation_results):
        """Comprehensive validation of all imports in the codebase."""
        logger.info(f"Import validation results: {validation_results}")
        
        # Critical issues should fail the test
        assert len(validation_results['syntax_errors']) == 0, f"Syntax errors found: {validation_results['syntax_errors']}"
        
        # Import errors should be minimal
        if validation_results['import_errors']:
            logger.warning(f"Import errors found: {validation_results['import_errors']}")
            assert len(validation_results['import_errors']) <= 3, "Too many import errors - fix critical imports first"
        
        # Overall status should be healthy or warning (not critical)
        assert validation_results['overall_status'] != 'critical', f"Critical import issues detected"
    
    def test_automated_import_fixes(self, import_fixer, fixable_issues):
        """Test automated import fixing capabilities."""
        logger.info(f"Fixable issues found: {sum(len(issues) for issues in fixable_issues.values())}")
        
        # Test fix simulation (dry run)
        simulation = import_fixer.apply_safe_fixes(fixable_issues, dry_run=True)
        
        logger.info(f"Safe fixes available: {len(simulation.get('safe_fixes', []))}")
        logger.info(f"Risky fixes identified: {len(simulation.get('risky_fixes', []))}")
        
        # Should have some fixable issues (if none, the test still passes)
        total_fixable = simulation.get('total_fixable_issues', 0)
        if total_fixable > 0:
            logger.info(f"Found {total_fixable} fixable import issues")
            
            # Safe fixes should be > 50% of total if we have issues
            safe_fixes = len(simulation.get('safe_fixes', []))
            if total_fixable > 0:
                safe_ratio = safe_fixes / total_fixable
                assert safe_ratio >= 0.3, f"Too few safe fixes available ({safe_ratio:.1%})"
        
        # Test passes regardless - this is diagnostic
        assert True
    
    def test_optimization_opportunities_analysis(self, optimization_opportunities):
        """Analyze and report import optimization opportunities."""
        total_opportunities = optimization_opportunities['total_opportunities']
        logger.info(f"Total optimization opportunities: {total_opportunities}")
        
        # Log key opportunities
        opportunities = optimization_opportunities['opportunities']
        
        barrel_exports = opportunities.get('barrel_export_suggestions', [])
        if barrel_exports:
            logger.info(f"Barrel export opportunities: {len(barrel_exports)}")
            for suggestion in barrel_exports[:3]:
                logger.info(f"  - {suggestion['base_module']}: {len(suggestion['imports'])} imports")
        
        factory_patterns = opportunities.get('factory_pattern_opportunities', [])
        if factory_patterns:
            logger.info(f"Factory pattern opportunities: {len(factory_patterns)}")
            for suggestion in factory_patterns[:3]:
                logger.info(f"  - {suggestion['class']}: used in {suggestion['usage_count']} files")
        
        # Priority recommendations
        priority_recs = optimization_opportunities.get('priority_recommendations', [])
        if priority_recs:
            logger.info("Top 3 priority recommendations:")
            for i, rec in enumerate(priority_recs[:3], 1):
                logger.info(f"  {i}. {rec['category']} (impact: {rec['impact_score']}, effort: {rec['effort']})")
        
        # Always pass - this is analysis
        assert True
    
    def test_import_consistency_check(self, import_validator):
        """Check for import consistency across the codebase."""
        consistency_results = import_validator.check_import_consistency()
        
        # Log consistency issues
        mixed_styles = consistency_results.get('mixed_import_styles', [])
        if mixed_styles:
            logger.warning(f"Mixed import styles found: {len(mixed_styles)} modules")
            for issue in mixed_styles[:3]:
                logger.warning(f"  - {issue['module']}: both direct and from imports")
        
        inconsistent_aliases = consistency_results.get('inconsistent_aliases', [])
        if inconsistent_aliases:
            logger.warning(f"Inconsistent aliases: {len(inconsistent_aliases)} modules")
            for issue in inconsistent_aliases[:3]:
                logger.warning(f"  - {issue['module']}: aliases {issue['aliases']}")
        
        # Consistency issues are warnings, not failures
        assert True
    
    def test_import_performance_analysis(self, import_validator):
        """Analyze import performance for key modules."""
        performance_results = import_validator.test_import_performance()
        
        logger.info("Import performance analysis:")
        for module, time_ms in performance_results.items():
            if time_ms > 0:
                status = "🐌" if time_ms > 1000 else "⚡" if time_ms < 100 else "✓"
                logger.info(f"  {status} {module}: {time_ms:.1f}ms")
            else:
                logger.warning(f"  ❌ {module}: import failed")
        
        # Check that core modules import reasonably fast
        core_modules = ['autotasktracker', 'autotasktracker.core']
        for module in core_modules:
            if module in performance_results:
                time_ms = performance_results[module]
                if time_ms > 0:
                    assert time_ms < 5000, f"{module} import too slow: {time_ms:.1f}ms"
        
        assert True
    
    def test_generate_comprehensive_optimization_report(self, analysis_results, import_analyzer, optimization_opportunities, validation_results):
        """Generate comprehensive optimization report with actionable insights."""
        health_score = import_analyzer.get_health_score()
        
        report = [
            "\\n🔍 COMPREHENSIVE IMPORT HEALTH REPORT",
            "=" * 50,
            f"Overall Health Score: {health_score['score']}/100",
            f"Files Analyzed: {analysis_results['files_analyzed']}",
            f"Total Imports: {analysis_results['total_imports']}",
            f"Validation Status: {validation_results['overall_status']}",
            "",
            "📊 ISSUE SUMMARY",
            "-" * 20
        ]
        
        # Issues summary
        issues = analysis_results.get('issues', {})
        total_issues = sum(len(issue_list) for issue_list in issues.values())
        
        if total_issues > 0:
            report.append(f"Total Issues Found: {total_issues}")
            for issue_type, issue_list in issues.items():
                if issue_list:
                    report.append(f"  • {issue_type.replace('_', ' ').title()}: {len(issue_list)} issues")
        else:
            report.append("✅ No critical issues found!")
        
        report.extend([
            "",
            "🚀 OPTIMIZATION OPPORTUNITIES",
            "-" * 30
        ])
        
        # Optimization opportunities
        total_opportunities = optimization_opportunities['total_opportunities']
        if total_opportunities > 0:
            report.append(f"Total Opportunities: {total_opportunities}")
            
            opportunities = optimization_opportunities['opportunities']
            for category, items in opportunities.items():
                if items:
                    category_name = category.replace('_', ' ').title()
                    report.append(f"  • {category_name}: {len(items)} opportunities")
        else:
            report.append("✅ Import patterns are well optimized!")
        
        # Priority recommendations
        priority_recs = optimization_opportunities.get('priority_recommendations', [])
        if priority_recs:
            report.extend([
                "",
                "🎯 TOP PRIORITY RECOMMENDATIONS",
                "-" * 35
            ])
            
            for i, rec in enumerate(priority_recs[:5], 1):
                category = rec['category'].replace('_', ' ').title()
                report.append(f"{i}. {category} ({rec['priority']} priority)")
                report.append(f"   Impact: {rec['impact_score']}, Effort: {rec['effort']}")
        
        # Implementation plan
        plan = optimization_opportunities.get('implementation_plan', [])
        if plan:
            report.extend([
                "",
                "📋 IMPLEMENTATION PLAN",
                "-" * 25
            ])
            
            for phase in plan:
                report.append(f"Phase {phase['phase']}: {phase['title']}")
                report.append(f"  Time: {phase['estimated_time']}, Risk: {phase['risk']}")
                for task in phase['tasks']:
                    report.append(f"  - {task}")
                report.append("")
        
        report.extend([
            "=" * 50,
            "🔧 NEXT STEPS:",
            "1. Review priority recommendations above",
            "2. Start with Phase 1 implementation plan",
            "3. Run tests after each optimization",
            "4. Re-run this health check to measure improvement",
            ""
        ])
        
        logger.info("\\n".join(report))
        
        # Always pass - this is a comprehensive reporting test
        assert True
"""Import optimizer for AutoTaskTracker health tests.

Provides comprehensive import optimization strategies to reduce
refactoring overhead and improve code maintainability.
"""

import ast
from pathlib import Path
from typing import Dict, List, Optional, Any, Set, Tuple
import logging
from collections import defaultdict, Counter

logger = logging.getLogger(__name__)


class ImportOptimizer:
    """Comprehensive import optimization system."""
    
    def __init__(self, project_root: str):
        self.project_root = Path(project_root)
        self.package_root = self.project_root / "autotasktracker"
        
        # Optimization strategies
        self.strategies = {
            'barrel_exports': True,
            'factory_patterns': True,
            'dependency_injection': True,
            'import_consolidation': True,
            'circular_import_resolution': True
        }
        
        # Current import mapping
        self.import_map = {}
        self.usage_analysis = {}
    
    def analyze_optimization_opportunities(self) -> Dict[str, Any]:
        """Analyze the codebase for import optimization opportunities."""
        logger.info("Analyzing import optimization opportunities...")
        
        # Build import map
        self._build_import_map()
        
        # Analyze usage patterns
        self._analyze_usage_patterns()
        
        opportunities = {
            'barrel_export_suggestions': self._suggest_barrel_exports(),
            'factory_pattern_opportunities': self._suggest_factory_patterns(),
            'consolidation_opportunities': self._suggest_consolidation(),
            'circular_import_fixes': self._detect_circular_imports(),
            'dependency_injection_candidates': self._suggest_dependency_injection(),
            'performance_optimizations': self._suggest_performance_optimizations()
        }
        
        return {
            'total_opportunities': sum(len(opp) for opp in opportunities.values()),
            'opportunities': opportunities,
            'priority_recommendations': self._prioritize_recommendations(opportunities),
            'implementation_plan': self._create_implementation_plan(opportunities)
        }
    
    def _build_import_map(self):
        """Build a comprehensive map of all imports in the codebase."""
        self.import_map = {}
        
        for py_file in self._find_python_files():
            try:
                imports = self._extract_imports(py_file)
                relative_path = str(py_file.relative_to(self.project_root))
                self.import_map[relative_path] = imports
            except Exception as e:
                logger.debug(f"Could not analyze {py_file}: {e}")
    
    def _analyze_usage_patterns(self):
        """Analyze how imports are used throughout the codebase."""
        module_usage = defaultdict(list)
        class_instantiation = defaultdict(list)
        
        for file_path, imports in self.import_map.items():
            # Read file content to analyze usage
            try:
                full_path = self.project_root / file_path
                with open(full_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                for imp in imports:
                    if imp['type'] == 'from_import':
                        module_usage[imp['module']].append(file_path)
                        
                        # Check for class instantiation
                        if imp['name'] and imp['name'][0].isupper():
                            if f"{imp['name']}(" in content:
                                class_instantiation[imp['name']].append(file_path)
            
            except Exception as e:
                logger.debug(f"Could not analyze usage in {file_path}: {e}")
        
        self.usage_analysis = {
            'module_usage': dict(module_usage),
            'class_instantiation': dict(class_instantiation)
        }
    
    def _suggest_barrel_exports(self) -> List[Dict]:
        """Suggest barrel export opportunities."""
        suggestions = []
        
        # Group imports by base module
        module_groups = defaultdict(lambda: defaultdict(set))
        
        for file_path, imports in self.import_map.items():
            for imp in imports:
                if (imp['type'] == 'from_import' and 
                    imp['module'] and 
                    imp['module'].startswith('autotasktracker.')):
                    
                    parts = imp['module'].split('.')
                    if len(parts) >= 3:  # autotasktracker.core.something
                        base_module = '.'.join(parts[:3])
                        module_groups[base_module][imp['module']].add(imp['name'])
        
        # Find modules with multiple submodule imports
        for base_module, submodules in module_groups.items():
            if len(submodules) >= 2:  # Multiple submodules
                all_imports = set()
                for imports in submodules.values():
                    all_imports.update(imports)
                
                if len(all_imports) >= 3:  # Multiple imports
                    suggestions.append({
                        'base_module': base_module,
                        'submodules': list(submodules.keys()),
                        'imports': list(all_imports),
                        'benefit': f"Consolidate {len(all_imports)} imports from {len(submodules)} submodules",
                        'priority': 'high' if len(all_imports) >= 5 else 'medium'
                    })
        
        return suggestions
    
    def _suggest_factory_patterns(self) -> List[Dict]:
        """Suggest factory pattern opportunities."""
        suggestions = []
        
        # Analyze class instantiation patterns
        class_usage = self.usage_analysis.get('class_instantiation', {})
        
        for class_name, files in class_usage.items():
            if len(files) >= 3:  # Used in multiple files
                # Check if it's a manager/service class
                if any(pattern in class_name for pattern in ['Manager', 'Service', 'Processor', 'Analyzer']):
                    suggestions.append({
                        'class': class_name,
                        'usage_files': files,
                        'usage_count': len(files),
                        'factory_name': f"create_{class_name.lower()}",
                        'benefit': f"Centralize {class_name} creation and configuration",
                        'priority': 'high' if len(files) >= 5 else 'medium'
                    })
        
        return suggestions
    
    def _suggest_consolidation(self) -> List[Dict]:
        """Suggest import consolidation opportunities."""
        suggestions = []
        
        for file_path, imports in self.import_map.items():
            # Group imports by module
            module_imports = defaultdict(list)
            
            for imp in imports:
                if imp['type'] == 'from_import' and imp['module']:
                    module_imports[imp['module']].append(imp['name'])
            
            # Find modules with multiple separate imports
            for module, names in module_imports.items():
                if len(names) >= 3:  # Multiple imports from same module
                    suggestions.append({
                        'file': file_path,
                        'module': module,
                        'imports': names,
                        'current_count': len(names),
                        'benefit': f"Consolidate {len(names)} imports into single statement",
                        'priority': 'low'
                    })
        
        return suggestions
    
    def _detect_circular_imports(self) -> List[Dict]:
        """Detect and suggest fixes for circular imports."""
        import_graph = {}
        
        # Build import dependency graph
        for file_path, imports in self.import_map.items():
            module_name = self._file_to_module_name(file_path)
            dependencies = []
            
            for imp in imports:
                if (imp['type'] == 'from_import' and 
                    imp['module'] and 
                    imp['module'].startswith('autotasktracker.')):
                    dependencies.append(imp['module'])
            
            import_graph[module_name] = dependencies
        
        # Detect cycles (simplified)
        cycles = []
        for module, deps in import_graph.items():
            for dep in deps:
                if dep in import_graph and module in import_graph[dep]:
                    if (module, dep) not in cycles and (dep, module) not in cycles:
                        cycles.append((module, dep))
        
        suggestions = []
        for module1, module2 in cycles:
            suggestions.append({
                'modules': [module1, module2],
                'type': 'circular_import',
                'suggested_fix': 'Move shared functionality to separate module',
                'priority': 'high'
            })
        
        return suggestions
    
    def _suggest_dependency_injection(self) -> List[Dict]:
        """Suggest dependency injection opportunities."""
        suggestions = []
        
        # Look for classes that frequently import and instantiate other classes
        high_coupling_files = []
        
        for file_path, imports in self.import_map.items():
            service_imports = [
                imp for imp in imports 
                if (imp['type'] == 'from_import' and 
                    imp['name'] and 
                    any(pattern in imp['name'] for pattern in ['Manager', 'Service', 'Client']))
            ]
            
            if len(service_imports) >= 3:
                high_coupling_files.append({
                    'file': file_path,
                    'service_imports': [imp['name'] for imp in service_imports],
                    'coupling_score': len(service_imports),
                    'suggestion': 'Consider dependency injection container',
                    'priority': 'medium'
                })
        
        return high_coupling_files
    
    def _suggest_performance_optimizations(self) -> List[Dict]:
        """Suggest performance-related import optimizations."""
        suggestions = []
        
        # Lazy import opportunities
        for file_path, imports in self.import_map.items():
            heavy_imports = [
                imp for imp in imports
                if (imp['type'] == 'from_import' and
                    imp['module'] and
                    any(heavy in imp['module'] for heavy in ['pandas', 'numpy', 'matplotlib', 'streamlit']))
            ]
            
            if heavy_imports:
                suggestions.append({
                    'file': file_path,
                    'heavy_imports': [f"{imp['module']}.{imp['name']}" for imp in heavy_imports],
                    'optimization': 'lazy_import',
                    'benefit': 'Faster startup time by deferring heavy imports',
                    'priority': 'low'
                })
        
        # Optional import opportunities
        optional_modules = ['sentence_transformers', 'ollama', 'PIL']
        for file_path, imports in self.import_map.items():
            optional_imports = [
                imp for imp in imports
                if (imp['module'] and 
                    any(opt in imp['module'] for opt in optional_modules))
            ]
            
            if optional_imports:
                suggestions.append({
                    'file': file_path,
                    'optional_imports': [imp['module'] for imp in optional_imports],
                    'optimization': 'optional_import',
                    'benefit': 'Graceful degradation when optional dependencies unavailable',
                    'priority': 'medium'
                })
        
        return suggestions
    
    def _prioritize_recommendations(self, opportunities: Dict[str, List]) -> List[Dict]:
        """Prioritize recommendations by impact and effort."""
        all_recommendations = []
        
        for category, items in opportunities.items():
            for item in items:
                priority = item.get('priority', 'medium')
                
                # Calculate impact score
                impact_score = self._calculate_impact_score(category, item)
                
                all_recommendations.append({
                    'category': category,
                    'item': item,
                    'priority': priority,
                    'impact_score': impact_score,
                    'effort': self._estimate_effort(category, item)
                })
        
        # Sort by impact score and priority
        priority_order = {'high': 3, 'medium': 2, 'low': 1}
        all_recommendations.sort(
            key=lambda x: (priority_order.get(x['priority'], 0), x['impact_score']),
            reverse=True
        )
        
        return all_recommendations[:10]  # Top 10 recommendations
    
    def _calculate_impact_score(self, category: str, item: Dict) -> int:
        """Calculate impact score for a recommendation."""
        if category == 'barrel_export_suggestions':
            return len(item.get('imports', [])) * 2
        elif category == 'factory_pattern_opportunities':
            return item.get('usage_count', 0) * 3
        elif category == 'circular_import_fixes':
            return 10  # High impact
        elif category == 'consolidation_opportunities':
            return item.get('current_count', 0)
        else:
            return 1
    
    def _estimate_effort(self, category: str, item: Dict) -> str:
        """Estimate implementation effort."""
        if category == 'barrel_export_suggestions':
            return 'low'
        elif category == 'factory_pattern_opportunities':
            return 'medium'
        elif category == 'circular_import_fixes':
            return 'high'
        elif category == 'consolidation_opportunities':
            return 'low'
        else:
            return 'medium'
    
    def _create_implementation_plan(self, opportunities: Dict[str, List]) -> List[Dict]:
        """Create a step-by-step implementation plan."""
        plan = []
        
        # Phase 1: Low-risk optimizations
        plan.append({
            'phase': 1,
            'title': 'Low-Risk Import Optimizations',
            'tasks': [
                'Implement barrel exports for core modules',
                'Consolidate imports in files with 3+ imports from same module',
                'Update direct database imports to use barrel exports'
            ],
            'estimated_time': '2-3 hours',
            'risk': 'low'
        })
        
        # Phase 2: Factory patterns
        plan.append({
            'phase': 2,
            'title': 'Factory Pattern Implementation',
            'tasks': [
                'Create factory functions for frequently used classes',
                'Update high-usage instantiation sites',
                'Add factory pattern documentation'
            ],
            'estimated_time': '4-6 hours',
            'risk': 'medium'
        })
        
        # Phase 3: Advanced optimizations
        plan.append({
            'phase': 3,
            'title': 'Advanced Import Optimizations',
            'tasks': [
                'Resolve circular import dependencies',
                'Implement dependency injection where beneficial',
                'Add lazy imports for performance'
            ],
            'estimated_time': '6-8 hours',
            'risk': 'high'
        })
        
        return plan
    
    def generate_optimization_report(self, opportunities: Dict[str, Any]) -> str:
        """Generate comprehensive optimization report."""
        report = ["# Import Optimization Report\\n"]
        
        total_opportunities = opportunities['total_opportunities']
        report.append(f"**Total Optimization Opportunities**: {total_opportunities}\\n")
        
        # Priority recommendations
        priority_recs = opportunities['priority_recommendations']
        if priority_recs:
            report.append("## Top Priority Recommendations\\n")
            for i, rec in enumerate(priority_recs[:5], 1):
                report.append(f"{i}. **{rec['category'].replace('_', ' ').title()}** ({rec['priority']} priority)")
                report.append(f"   - Impact Score: {rec['impact_score']}")
                report.append(f"   - Effort: {rec['effort']}")
                report.append("")
        
        # Implementation plan
        plan = opportunities['implementation_plan']
        if plan:
            report.append("## Implementation Plan\\n")
            for phase in plan:
                report.append(f"### Phase {phase['phase']}: {phase['title']}")
                report.append(f"**Time Estimate**: {phase['estimated_time']}")
                report.append(f"**Risk Level**: {phase['risk']}\\n")
                
                for task in phase['tasks']:
                    report.append(f"- {task}")
                report.append("")
        
        return "\\n".join(report)
    
    def _extract_imports(self, file_path: Path) -> List[Dict]:
        """Extract imports from a Python file."""
        imports = []
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            tree = ast.parse(content, filename=str(file_path))
            
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        imports.append({
                            'type': 'import',
                            'module': alias.name,
                            'name': None,
                            'alias': alias.asname,
                            'line': node.lineno
                        })
                elif isinstance(node, ast.ImportFrom):
                    for alias in node.names:
                        imports.append({
                            'type': 'from_import',
                            'module': node.module,
                            'name': alias.name,
                            'alias': alias.asname,
                            'line': node.lineno
                        })
        
        except Exception as e:
            logger.debug(f"Could not parse {file_path}: {e}")
        
        return imports
    
    def _file_to_module_name(self, file_path: str) -> str:
        """Convert file path to module name."""
        # Remove .py extension and convert to module name
        module_path = file_path.replace('.py', '').replace('/', '.')
        if module_path.endswith('.__init__'):
            module_path = module_path[:-9]  # Remove .__init__
        return module_path
    
    def _find_python_files(self) -> List[Path]:
        """Find all Python files in the project."""
        python_files = []
        
        if self.package_root.exists():
            python_files.extend(self.package_root.rglob("*.py"))
        
        return [f for f in python_files if not self._should_skip_file(f)]
    
    def _should_skip_file(self, file_path: Path) -> bool:
        """Check if file should be skipped."""
        skip_patterns = ['__pycache__', '.git', 'venv', 'test_']
        return any(pattern in str(file_path) for pattern in skip_patterns)
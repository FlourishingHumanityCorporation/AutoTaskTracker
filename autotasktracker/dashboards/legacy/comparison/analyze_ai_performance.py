#!/usr/bin/env python3
"""
AI Performance Analysis Tool for AutoTaskTracker.
Analyzes multiple screenshots with different AI methods and generates comparison reports.
"""
import os
import sys
import json
import pandas as pd
from datetime import datetime
import argparse
from typing import Dict, List

# Add project to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from autotasktracker.core.database import DatabaseManager
from autotasktracker.core.task_extractor import TaskExtractor
from autotasktracker.core.categorizer import ActivityCategorizer
from autotasktracker.ai.enhanced_task_extractor import AIEnhancedTaskExtractor
from autotasktracker.ai.ocr_enhancement import OCREnhancer
from autotasktracker.ai.vlm_integration import VLMTaskExtractor


class AIPerformanceAnalyzer:
    def __init__(self):
        self.db_manager = DatabaseManager()
        self.basic_extractor = TaskExtractor()
        self.ocr_enhancer = OCREnhancer()
        self.vlm_extractor = VLMTaskExtractor()
        self.ai_extractor = AIEnhancedTaskExtractor(self.db_manager.db_path)
    
    def load_test_screenshots(self, limit: int = 50, filter_type: str = "all") -> pd.DataFrame:
        """Load screenshots for testing."""
        base_query = """
        SELECT 
            e.id,
            e.filepath,
            e.filename,
            datetime(e.created_at, 'localtime') as created_at,
            me_ocr.value as ocr_text,
            me_window.value as active_window,
            me_vlm.value as vlm_description,
            CASE WHEN me_emb.value IS NOT NULL THEN 1 ELSE 0 END as has_embedding
        FROM entities e
        LEFT JOIN metadata_entries me_ocr ON e.id = me_ocr.entity_id AND me_ocr."key" = 'ocr_result'
        LEFT JOIN metadata_entries me_window ON e.id = me_window.entity_id AND me_window."key" = 'active_window'
        LEFT JOIN metadata_entries me_vlm ON e.id = me_vlm.entity_id AND me_vlm."key" = 'vlm_result'
        LEFT JOIN metadata_entries me_emb ON e.id = me_emb.entity_id AND me_emb."key" = 'embedding'
        WHERE e.file_type_group = 'image'
        """
        
        if filter_type == "ocr_only":
            base_query += " AND me_ocr.value IS NOT NULL"
        elif filter_type == "vlm_only":
            base_query += " AND me_vlm.value IS NOT NULL"
        elif filter_type == "both":
            base_query += " AND me_ocr.value IS NOT NULL AND me_vlm.value IS NOT NULL"
        elif filter_type == "any_ai":
            base_query += " AND (me_ocr.value IS NOT NULL OR me_vlm.value IS NOT NULL)"
        
        base_query += f" ORDER BY e.created_at DESC LIMIT {limit}"
        
        try:
            with self.db_manager.get_connection() as conn:
                return pd.read_sql_query(base_query, conn)
        except Exception as e:
            print(f"Error loading screenshots: {e}")
            return pd.DataFrame()
    
    def process_single_screenshot(self, row: pd.Series) -> Dict:
        """Process a single screenshot with all methods."""
        window_title = row.get('active_window', '')
        ocr_text = row.get('ocr_text', '')
        vlm_description = row.get('vlm_description', '')
        entity_id = row.get('id')
        
        results = {
            'screenshot_id': entity_id,
            'filename': row.get('filename', ''),
            'created_at': row.get('created_at', ''),
            'has_ocr': bool(ocr_text),
            'has_vlm': bool(vlm_description),
            'has_embedding': bool(row.get('has_embedding', 0))
        }
        
        # Method 1: Basic Pattern Matching
        basic_task = self.basic_extractor.extract_task(window_title) if window_title else "Unknown Activity"
        basic_category = ActivityCategorizer.categorize(window_title, ocr_text)
        
        results['basic'] = {
            'task': basic_task,
            'category': basic_category,
            'confidence': 0.5,
            'method_id': 'basic'
        }
        
        # Method 2: OCR Enhanced
        if ocr_text:
            ocr_enhancement = self.ocr_enhancer.enhance_task_with_ocr(ocr_text, basic_task)
            results['ocr'] = {
                'task': ocr_enhancement.get('task', basic_task),
                'category': basic_category,
                'confidence': ocr_enhancement.get('confidence', 0.5),
                'ocr_quality': ocr_enhancement.get('ocr_quality', 'unknown'),
                'method_id': 'ocr'
            }
        else:
            results['ocr'] = {
                'task': basic_task,
                'category': basic_category,
                'confidence': 0.3,
                'ocr_quality': 'no_text',
                'method_id': 'ocr'
            }
        
        # Method 3: VLM Enhanced
        if vlm_description:
            vlm_task = self.vlm_extractor.extract_from_vlm_description(vlm_description, window_title, ocr_text)
            if vlm_task:
                results['vlm'] = {
                    'task': vlm_task.task_title,
                    'category': vlm_task.category,
                    'confidence': vlm_task.confidence,
                    'ui_state': vlm_task.ui_state,
                    'method_id': 'vlm'
                }
            else:
                results['vlm'] = {
                    'task': 'VLM failed',
                    'category': basic_category,
                    'confidence': 0.0,
                    'ui_state': None,
                    'method_id': 'vlm'
                }
        else:
            results['vlm'] = {
                'task': basic_task,
                'category': basic_category,
                'confidence': 0.3,
                'ui_state': None,
                'method_id': 'vlm'
            }
        
        # Method 4: Full AI Enhanced
        enhanced_result = self.ai_extractor.extract_enhanced_task(
            window_title=window_title,
            ocr_text=ocr_text,
            vlm_description=vlm_description,
            entity_id=entity_id
        )
        
        results['ai_full'] = {
            'task': enhanced_result['task'],
            'category': enhanced_result['category'],
            'confidence': enhanced_result['confidence'],
            'similar_tasks_count': len(enhanced_result.get('similar_tasks', [])),
            'method_id': 'ai_full'
        }
        
        return results
    
    def analyze_batch(self, screenshots_df: pd.DataFrame) -> Dict:
        """Analyze a batch of screenshots."""
        all_results = []
        
        print(f"Processing {len(screenshots_df)} screenshots...")
        
        for idx, row in screenshots_df.iterrows():
            if idx % 10 == 0:
                print(f"Processed {idx}/{len(screenshots_df)} screenshots")
            
            try:
                result = self.process_single_screenshot(row)
                all_results.append(result)
            except Exception as e:
                print(f"Error processing screenshot {row.get('id', 'unknown')}: {e}")
                continue
        
        return self.generate_analysis_report(all_results)
    
    def generate_analysis_report(self, results: List[Dict]) -> Dict:
        """Generate comprehensive analysis report."""
        if not results:
            return {"error": "No results to analyze"}
        
        report = {
            'summary': {
                'total_screenshots': len(results),
                'with_ocr': sum(1 for r in results if r['has_ocr']),
                'with_vlm': sum(1 for r in results if r['has_vlm']),
                'with_embeddings': sum(1 for r in results if r['has_embedding']),
                'analysis_timestamp': datetime.now().isoformat()
            },
            'method_performance': {},
            'confidence_analysis': {},
            'task_diversity': {},
            'category_distribution': {}
        }
        
        methods = ['basic', 'ocr', 'vlm', 'ai_full']
        
        # Method performance analysis
        for method in methods:
            method_results = [r[method] for r in results if method in r]
            
            confidences = [mr['confidence'] for mr in method_results]
            tasks = [mr['task'] for mr in method_results]
            categories = [mr['category'] for mr in method_results]
            
            report['method_performance'][method] = {
                'avg_confidence': sum(confidences) / len(confidences) if confidences else 0,
                'min_confidence': min(confidences) if confidences else 0,
                'max_confidence': max(confidences) if confidences else 0,
                'unique_tasks': len(set(tasks)),
                'unique_categories': len(set(categories)),
                'high_confidence_count': sum(1 for c in confidences if c >= 0.8),
                'medium_confidence_count': sum(1 for c in confidences if 0.6 <= c < 0.8),
                'low_confidence_count': sum(1 for c in confidences if c < 0.6)
            }
        
        # Confidence comparison
        report['confidence_analysis'] = {
            'method_ranking': sorted(
                methods, 
                key=lambda m: report['method_performance'][m]['avg_confidence'], 
                reverse=True
            ),
            'confidence_improvements': self._analyze_confidence_improvements(results)
        }
        
        # Task diversity analysis
        all_tasks_by_method = {}
        for method in methods:
            tasks = [r[method]['task'] for r in results if method in r]
            all_tasks_by_method[method] = tasks
        
        report['task_diversity'] = {
            method: {
                'total_tasks': len(tasks),
                'unique_tasks': len(set(tasks)),
                'diversity_ratio': len(set(tasks)) / len(tasks) if tasks else 0,
                'most_common_tasks': self._get_most_common(tasks, 5)
            }
            for method, tasks in all_tasks_by_method.items()
        }
        
        # Category distribution
        all_categories_by_method = {}
        for method in methods:
            categories = [r[method]['category'] for r in results if method in r]
            all_categories_by_method[method] = categories
        
        report['category_distribution'] = {
            method: {
                'total_categories': len(set(categories)),
                'distribution': self._get_most_common(categories, 10)
            }
            for method, categories in all_categories_by_method.items()
        }
        
        return report
    
    def _analyze_confidence_improvements(self, results: List[Dict]) -> Dict:
        """Analyze confidence improvements between methods."""
        improvements = {}
        
        for result in results:
            if 'basic' in result and 'ai_full' in result:
                basic_conf = result['basic']['confidence']
                ai_conf = result['ai_full']['confidence']
                improvement = ai_conf - basic_conf
                
                if result['screenshot_id'] not in improvements:
                    improvements[result['screenshot_id']] = {}
                
                improvements[result['screenshot_id']]['basic_to_ai'] = improvement
        
        # Calculate statistics
        improvement_values = [imp['basic_to_ai'] for imp in improvements.values()]
        
        return {
            'avg_improvement': sum(improvement_values) / len(improvement_values) if improvement_values else 0,
            'positive_improvements': sum(1 for imp in improvement_values if imp > 0),
            'negative_improvements': sum(1 for imp in improvement_values if imp < 0),
            'no_change': sum(1 for imp in improvement_values if imp == 0),
            'max_improvement': max(improvement_values) if improvement_values else 0,
            'min_improvement': min(improvement_values) if improvement_values else 0
        }
    
    def _get_most_common(self, items: List, top_n: int = 5) -> List:
        """Get most common items with counts."""
        from collections import Counter
        counter = Counter(items)
        return counter.most_common(top_n)
    
    def export_detailed_results(self, results: List[Dict], filename: str):
        """Export detailed results to CSV."""
        rows = []
        
        for result in results:
            base_row = {
                'screenshot_id': result['screenshot_id'],
                'filename': result['filename'],
                'created_at': result['created_at'],
                'has_ocr': result['has_ocr'],
                'has_vlm': result['has_vlm'],
                'has_embedding': result['has_embedding']
            }
            
            for method in ['basic', 'ocr', 'vlm', 'ai_full']:
                if method in result:
                    method_data = result[method]
                    row = base_row.copy()
                    row.update({
                        'method': method,
                        'task': method_data['task'],
                        'category': method_data['category'],
                        'confidence': method_data['confidence']
                    })
                    
                    # Add method-specific fields
                    if 'ocr_quality' in method_data:
                        row['ocr_quality'] = method_data['ocr_quality']
                    if 'ui_state' in method_data:
                        row['ui_state'] = method_data['ui_state']
                    if 'similar_tasks_count' in method_data:
                        row['similar_tasks_count'] = method_data['similar_tasks_count']
                    
                    rows.append(row)
        
        df = pd.DataFrame(rows)
        df.to_csv(filename, index=False)
        print(f"Detailed results exported to {filename}")


def main():
    parser = argparse.ArgumentParser(description="Analyze AI performance on screenshots")
    parser.add_argument('--limit', type=int, default=50, help='Number of screenshots to analyze')
    parser.add_argument('--filter', choices=['all', 'ocr_only', 'vlm_only', 'both', 'any_ai'], 
                       default='any_ai', help='Filter screenshots by AI data availability')
    parser.add_argument('--export', help='Export detailed results to CSV file')
    parser.add_argument('--report', help='Save analysis report to JSON file')
    
    args = parser.parse_args()
    
    print("🔬 AI Performance Analysis Tool")
    print("=" * 50)
    
    analyzer = AIPerformanceAnalyzer()
    
    # Load screenshots
    print(f"Loading up to {args.limit} screenshots with filter '{args.filter}'...")
    screenshots_df = analyzer.load_test_screenshots(args.limit, args.filter)
    
    if screenshots_df.empty:
        print("❌ No screenshots found matching criteria")
        return
    
    print(f"✅ Loaded {len(screenshots_df)} screenshots")
    
    # Analyze
    results_list = []
    report = None
    
    print("\n🔍 Processing screenshots...")
    for idx, row in screenshots_df.iterrows():
        if idx % 10 == 0:
            print(f"Processed {idx}/{len(screenshots_df)} screenshots")
        
        try:
            result = analyzer.process_single_screenshot(row)
            results_list.append(result)
        except Exception as e:
            print(f"Error processing screenshot {row.get('id', 'unknown')}: {e}")
            continue
    
    if results_list:
        print(f"\n📊 Generating analysis report...")
        report = analyzer.generate_analysis_report(results_list)
        
        # Print summary
        print(f"\n📈 Analysis Summary:")
        print(f"Screenshots processed: {report['summary']['total_screenshots']}")
        print(f"With OCR: {report['summary']['with_ocr']}")
        print(f"With VLM: {report['summary']['with_vlm']}")
        print(f"With Embeddings: {report['summary']['with_embeddings']}")
        
        print(f"\n🏆 Method Ranking by Average Confidence:")
        for i, method in enumerate(report['confidence_analysis']['method_ranking'], 1):
            avg_conf = report['method_performance'][method]['avg_confidence']
            print(f"{i}. {method}: {avg_conf:.1%}")
        
        print(f"\n🎯 Confidence Improvements:")
        improvements = report['confidence_analysis']['confidence_improvements']
        print(f"Average improvement (Basic → AI Full): {improvements['avg_improvement']:+.1%}")
        print(f"Positive improvements: {improvements['positive_improvements']}")
        print(f"Negative improvements: {improvements['negative_improvements']}")
        
    # Export results
    if args.export and results_list:
        analyzer.export_detailed_results(results_list, args.export)
    
    if args.report and report:
        with open(args.report, 'w') as f:
            json.dump(report, f, indent=2)
        print(f"Analysis report saved to {args.report}")
    
    print(f"\n✅ Analysis complete!")
    print(f"\nTo view detailed comparison, run:")
    print(f"streamlit run autotasktracker/dashboards/ai_comparison_dashboard.py")


if __name__ == "__main__":
    main()
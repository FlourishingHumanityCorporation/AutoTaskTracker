import logging
logger = logging.getLogger(__name__)

"""
Performance analysis for AI pipelines.
"""
import os
import pandas as pd
from datetime import datetime
from typing import Dict, List, Any

from autotasktracker.core import DatabaseManager
from autotasktracker.comparison.pipelines import BasicPipeline, OCRPipeline, AIFullPipeline


class PerformanceAnalyzer:
    """Analyzes performance of different AI pipelines."""
    
    def __init__(self):
        self.db_manager = DatabaseManager()
        self.pipelines = {
            'basic': BasicPipeline(),
            'ocr': OCRPipeline(),
            'ai_full': AIFullPipeline()
        }
    
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
        LEFT JOIN metadata_entries me_ocr ON e.id = me_ocr.entity_id AND me_ocr."key" = "ocr_result"
        LEFT JOIN metadata_entries me_window ON e.id = me_window.entity_id AND me_window."key" = "active_window"
        LEFT JOIN metadata_entries me_vlm ON e.id = me_vlm.entity_id AND me_vlm."key" = "vlm_structured"
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
            logger.error(f"Error loading screenshots: {e}")
            return pd.DataFrame()
    
    def process_single_screenshot(self, row: pd.Series) -> Dict[str, Any]:
        """Process a single screenshot with all pipelines."""
        screenshot_data = {
            "active_window": row.get("active_window", ''),
            "ocr_result": row.get("ocr_result", ''),
            'vlm_description': row.get('vlm_description', ''),
            'id': row.get('id')
        }
        
        results = {
            'screenshot_id': row.get('id'),
            'filename': row.get('filename', ''),
            'created_at': row.get('created_at', ''),
            'has_ocr': bool(screenshot_data["ocr_result"]),
            'has_vlm': bool(screenshot_data['vlm_description']),
            'has_embedding': bool(row.get('has_embedding', 0))
        }
        
        # Process with each pipeline
        for pipeline_name, pipeline in self.pipelines.items():
            try:
                pipeline_result = pipeline.process_screenshot(screenshot_data)
                results[pipeline_name] = pipeline_result
            except Exception as e:
                logger.error(f"Error processing with {pipeline_name}: {e}")
                results[pipeline_name] = {
                    "tasks": 'Processing failed',
                    "category": 'Error',
                    'confidence': 0.0,
                    'features_used': [],
                    'details': {'error': str(e)}
                }
        
        return results
    
    def analyze_batch(self, screenshots_df: pd.DataFrame) -> Dict[str, Any]:
        """Analyze a batch of screenshots."""
        all_results = []
        
        logger.info(f"Processing {len(screenshots_df)} screenshots...")
        
        for idx, row in screenshots_df.iterrows():
            if idx % 10 == 0:
                logger.info(f"Processed {idx}/{len(screenshots_df)} screenshots")
            
            try:
                result = self.process_single_screenshot(row)
                all_results.append(result)
            except Exception as e:
                logger.error(f"Error processing screenshot {row.get('id', 'unknown')}: {e}")
                continue
        
        return self.generate_analysis_report(all_results)
    
    def generate_analysis_report(self, results: List[Dict[str, Any]]) -> Dict[str, Any]:
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
        
        pipeline_names = list(self.pipelines.keys())
        
        # Method performance analysis
        for pipeline_name in pipeline_names:
            pipeline_results = [r[pipeline_name] for r in results if pipeline_name in r]
            
            confidences = [pr['confidence'] for pr in pipeline_results]
            tasks = [pr["tasks"] for pr in pipeline_results]
            categories = [pr["category"] for pr in pipeline_results]
            
            report['method_performance'][pipeline_name] = {
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
                pipeline_names, 
                key=lambda m: report['method_performance'][m]['avg_confidence'], 
                reverse=True
            ),
            'confidence_improvements': self._analyze_confidence_improvements(results)
        }
        
        return report
    
    def _analyze_confidence_improvements(self, results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze confidence improvements between methods."""
        improvements = []
        
        for result in results:
            if 'basic' in result and 'ai_full' in result:
                basic_conf = result['basic']['confidence']
                ai_conf = result['ai_full']['confidence']
                improvement = ai_conf - basic_conf
                improvements.append(improvement)
        
        if not improvements:
            return {}
        
        return {
            'avg_improvement': sum(improvements) / len(improvements),
            'positive_improvements': sum(1 for imp in improvements if imp > 0),
            'negative_improvements': sum(1 for imp in improvements if imp < 0),
            'no_change': sum(1 for imp in improvements if imp == 0),
            'max_improvement': max(improvements),
            'min_improvement': min(improvements)
        }
    
    def export_detailed_results(self, results: List[Dict[str, Any]], filename: str):
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
            
            for pipeline_name in self.pipelines.keys():
                if pipeline_name in result:
                    pipeline_data = result[pipeline_name]
                    row = base_row.copy()
                    row.update({
                        'pipeline': pipeline_name,
                        "tasks": pipeline_data["tasks"],
                        "category": pipeline_data["category"],
                        'confidence': pipeline_data['confidence'],
                        'features_used': ', '.join(pipeline_data['features_used'])
                    })
                    rows.append(row)
        
        df = pd.DataFrame(rows)
        df.to_csv(filename, index=False)
        logger.info(f"Detailed results exported to {filename}")
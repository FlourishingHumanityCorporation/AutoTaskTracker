#!/usr/bin/env python3
"""
Clean CLI tool for AI pipeline comparison using the organized structure.
"""
import argparse
import json
import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from autotasktracker.comparison.analysis import PerformanceAnalyzer


def main():
    parser = argparse.ArgumentParser(description="Compare AI processing pipelines")
    parser.add_argument('--limit', type=int, default=20, help='Number of screenshots to analyze')
    parser.add_argument('--filter', choices=['all', 'ocr_only', 'vlm_only', 'both', 'any_ai'], 
                       default='any_ai', help='Filter screenshots by AI data availability')
    parser.add_argument('--export', help='Export detailed results to CSV file')
    parser.add_argument('--report', help='Save analysis report to JSON file')
    
    args = parser.parse_args()
    
    print("⚖️  AI Pipeline Comparison Tool")
    print("=" * 50)
    
    analyzer = PerformanceAnalyzer()
    
    # Load screenshots
    print(f"Loading up to {args.limit} screenshots with filter '{args.filter}'...")
    screenshots_df = analyzer.load_test_screenshots(args.limit, args.filter)
    
    if screenshots_df.empty:
        print("❌ No screenshots found matching criteria")
        return
    
    print(f"✅ Loaded {len(screenshots_df)} screenshots")
    
    # Analyze
    print("\\n🔍 Processing screenshots with all pipelines...")
    report = analyzer.analyze_batch(screenshots_df)
    
    if 'error' in report:
        print(f"❌ Analysis failed: {report['error']}")
        return
    
    # Print summary
    print(f"\\n📈 Analysis Summary:")
    print(f"Screenshots processed: {report['summary']['total_screenshots']}")
    print(f"With OCR: {report['summary']['with_ocr']}")
    print(f"With VLM: {report['summary']['with_vlm']}")
    print(f"With Embeddings: {report['summary']['with_embeddings']}")
    
    print(f"\\n🏆 Pipeline Ranking by Average Confidence:")
    for i, method in enumerate(report['confidence_analysis']['method_ranking'], 1):
        avg_conf = report['method_performance'][method]['avg_confidence']
        print(f"{i}. {method}: {avg_conf:.1%}")
    
    if 'confidence_improvements' in report['confidence_analysis']:
        print(f"\\n🎯 Confidence Improvements:")
        improvements = report['confidence_analysis']['confidence_improvements']
        print(f"Average improvement (Basic → AI Full): {improvements['avg_improvement']:+.1%}")
        print(f"Positive improvements: {improvements['positive_improvements']}")
        print(f"Negative improvements: {improvements['negative_improvements']}")
    
    # Export results
    if args.export:
        # Rebuild results for export
        all_results = []
        for idx, row in screenshots_df.iterrows():
            result = analyzer.process_single_screenshot(row)
            all_results.append(result)
        
        analyzer.export_detailed_results(all_results, args.export)
    
    if args.report:
        with open(args.report, 'w') as f:
            json.dump(report, f, indent=2)
        print(f"Analysis report saved to {args.report}")
    
    print(f"\\n✅ Analysis complete!")
    print(f"\\nTo view interactive comparison, run:")
    print(f"streamlit run autotasktracker/comparison/dashboards/pipeline_comparison.py")


if __name__ == "__main__":
    main()
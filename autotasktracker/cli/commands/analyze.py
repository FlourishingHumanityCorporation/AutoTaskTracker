"""Analysis and comparison CLI commands."""
import click
import logging
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


@click.group(name='analyze')
def analyze_group():
    """Analysis and performance tools."""
    pass


@analyze_group.command()
@click.option('--methods', '-m', multiple=True, 
              type=click.Choice(['ocr', 'vlm', 'llm', 'all']),
              default=['all'],
              help='Methods to compare')
@click.option('--samples', '-s', type=int, default=10, help='Number of samples')
@click.option('--output', '-o', type=click.Path(), help='Output file for results')
def pipeline(methods, samples, output):
    """Compare AI pipeline methods."""
    from scripts.analysis.ai_pipeline_comparison import compare_pipelines
    
    if 'all' in methods:
        methods = ['ocr', 'vlm', 'llm']
    
    click.echo(f"🔬 Comparing AI pipeline methods: {', '.join(methods)}")
    click.echo(f"   Using {samples} samples")
    
    results = compare_pipelines(methods=list(methods), sample_size=samples)
    
    # Display results
    click.echo("\n📊 Comparison Results:")
    click.echo("=" * 60)
    
    for method in methods:
        if method in results:
            stats = results[method]
            click.echo(f"\n{method.upper()}:")
            click.echo(f"  Accuracy: {stats['accuracy']:.2%}")
            click.echo(f"  Avg Time: {stats['avg_time']:.2f}s")
            click.echo(f"  Success Rate: {stats['success_rate']:.2%}")
            if 'f1_score' in stats:
                click.echo(f"  F1 Score: {stats['f1_score']:.2f}")
    
    if output:
        import json
        with open(output, 'w') as f:
            json.dump(results, f, indent=2)
        click.echo(f"\n✅ Results saved to {output}")


@analyze_group.command()
@click.option('--duration', '-d', type=int, default=60, help='Test duration in seconds')
@click.option('--operations', '-o', multiple=True,
              type=click.Choice(['query', 'insert', 'cache', 'all']),
              default=['all'],
              help='Operations to benchmark')
def performance(duration, operations):
    """Run performance benchmarks."""
    from scripts.analysis.performance_baseline import run_performance_tests
    
    if 'all' in operations:
        operations = ['query', 'insert', 'cache']
    
    click.echo(f"⚡ Running performance benchmarks...")
    click.echo(f"   Duration: {duration}s")
    click.echo(f"   Operations: {', '.join(operations)}")
    
    results = run_performance_tests(duration=duration, operations=list(operations))
    
    # Display results
    click.echo("\n📊 Performance Results:")
    click.echo("=" * 60)
    
    for op in operations:
        if op in results:
            stats = results[op]
            click.echo(f"\n{op.upper()} Performance:")
            click.echo(f"  Operations/sec: {stats['ops_per_sec']:.2f}")
            click.echo(f"  Avg Latency: {stats['avg_latency']:.2f}ms")
            click.echo(f"  P95 Latency: {stats['p95_latency']:.2f}ms")
            click.echo(f"  P99 Latency: {stats['p99_latency']:.2f}ms")


@analyze_group.command()
@click.option('--days', '-d', type=int, default=7, help='Number of days to analyze')
@click.option('--format', '-f', 
              type=click.Choice(['table', 'json', 'csv']),
              default='table',
              help='Output format')
def activity(days, format):
    """Analyze user activity patterns."""
    from autotasktracker.core import DatabaseManager
    from autotasktracker.dashboards.data.repositories import TaskRepository
    
    click.echo(f"📈 Analyzing activity patterns (last {days} days)...")
    
    db = DatabaseManager()
    repo = TaskRepository(db)
    
    # Get activity data
    end_date = datetime.now()
    start_date = end_date - timedelta(days=days)
    
    tasks = repo.get_tasks_for_period(start_date, end_date)
    
    if not tasks:
        click.echo("❌ No activity data found")
        return
    
    # Analyze patterns
    from collections import Counter
    categories = Counter(task.category for task in tasks)
    hourly = Counter(task.timestamp.hour for task in tasks)
    daily = Counter(task.timestamp.date() for task in tasks)
    
    if format == 'table':
        click.echo("\n📊 Category Distribution:")
        for cat, count in categories.most_common():
            click.echo(f"  {cat:<20} {count:>5} ({count/len(tasks)*100:>5.1f}%)")
        
        click.echo("\n⏰ Peak Hours:")
        for hour, count in sorted(hourly.items()):
            bar = "█" * int(count / max(hourly.values()) * 20)
            click.echo(f"  {hour:02d}:00 {bar} {count}")
        
        click.echo(f"\n📅 Daily Average: {len(tasks) / days:.1f} tasks")
    
    elif format == 'json':
        import json
        data = {
            'period': {'start': start_date.isoformat(), 'end': end_date.isoformat()},
            'total_tasks': len(tasks),
            'categories': dict(categories),
            'hourly_distribution': dict(hourly),
            'daily_counts': {str(k): v for k, v in daily.items()}
        }
        click.echo(json.dumps(data, indent=2))
    
    elif format == 'csv':
        click.echo("timestamp,category,duration_minutes")
        for task in tasks:
            duration = getattr(task, 'duration_minutes', 0)
            click.echo(f"{task.timestamp},{task.category},{duration}")


@analyze_group.command()
@click.option('--verbose', '-v', is_flag=True, help='Show detailed analysis')
def code():
    """Analyze codebase quality metrics."""
    from scripts.utils.analyze_codebase import analyze_codebase
    
    click.echo("🔍 Analyzing codebase quality...")
    
    metrics = analyze_codebase(verbose=verbose)
    
    click.echo("\n📊 Codebase Metrics:")
    click.echo("=" * 50)
    
    click.echo(f"\nFiles: {metrics['total_files']}")
    click.echo(f"Lines of Code: {metrics['total_lines']:,}")
    click.echo(f"Functions: {metrics['total_functions']:,}")
    click.echo(f"Classes: {metrics['total_classes']:,}")
    
    click.echo(f"\n📈 Code Quality:")
    click.echo(f"Docstring Coverage: {metrics['docstring_coverage']:.1f}%")
    click.echo(f"Type Hint Coverage: {metrics['type_hint_coverage']:.1f}%")
    click.echo(f"Test Coverage: {metrics.get('test_coverage', 'N/A')}")
    
    if verbose and 'issues' in metrics:
        click.echo(f"\n⚠️  Issues Found:")
        for issue in metrics['issues'][:10]:  # Show first 10
            click.echo(f"  - {issue}")
        if len(metrics['issues']) > 10:
            click.echo(f"  ... and {len(metrics['issues']) - 10} more")
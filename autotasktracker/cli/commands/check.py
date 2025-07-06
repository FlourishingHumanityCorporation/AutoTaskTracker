"""System check and validation CLI commands."""
import click
import logging
from datetime import datetime

logger = logging.getLogger(__name__)


@click.group(name='check')
def check_group():
    """System health and compliance checks."""
    pass


@check_group.command()
@click.option('--verbose', '-v', is_flag=True, help='Show detailed output')
def health():
    """Run comprehensive health check."""
    from scripts.pensieve_health_check import main as health_check_main
    
    click.echo("🏥 Running system health check...")
    click.echo("=" * 50)
    
    # Run health check
    try:
        # TODO: Modify health_check_main to return results instead of printing
        health_check_main()
        click.echo("\n✅ Health check complete")
    except Exception as e:
        click.echo(f"\n❌ Health check failed: {e}")
        return 1


@check_group.command()
@click.option('--fix', '-f', is_flag=True, help='Automatically fix issues')
@click.option('--ci', is_flag=True, help='CI mode (exit with error code)')
def compliance():
    """Check configuration compliance."""
    from scripts.analysis.compliance_scanner import scan_compliance
    
    click.echo("🔍 Scanning configuration compliance...")
    
    issues = scan_compliance()
    
    if not issues:
        click.echo("✅ All configuration checks passed!")
        return 0
    
    click.echo(f"\n⚠️  Found {len(issues)} compliance issues:")
    for i, issue in enumerate(issues, 1):
        click.echo(f"\n{i}. {issue['title']}")
        click.echo(f"   Severity: {issue['severity']}")
        click.echo(f"   {issue['description']}")
        if 'fix' in issue:
            click.echo(f"   Fix: {issue['fix']}")
    
    if fix:
        click.echo("\n🔧 Attempting to fix issues...")
        fixed = 0
        for issue in issues:
            if 'fix_function' in issue:
                try:
                    issue['fix_function']()
                    fixed += 1
                    click.echo(f"   ✅ Fixed: {issue['title']}")
                except Exception as e:
                    click.echo(f"   ❌ Failed to fix {issue['title']}: {e}")
        
        click.echo(f"\n✅ Fixed {fixed}/{len(issues)} issues")
    
    return len(issues) if ci else 0


@check_group.command()
@click.option('--detailed', '-d', is_flag=True, help='Show detailed results')
def production():
    """Check production readiness."""
    from scripts.analysis.production_readiness import check_production_readiness
    
    click.echo("🚀 Checking production readiness...")
    click.echo("=" * 50)
    
    results = check_production_readiness(detailed=detailed)
    
    # Display results
    categories = ['security', 'performance', 'reliability', 'monitoring', 'documentation']
    
    total_score = 0
    for category in categories:
        score = results.get(category, {}).get('score', 0)
        total_score += score
        
        icon = "✅" if score >= 80 else "⚠️" if score >= 60 else "❌"
        click.echo(f"\n{icon} {category.title()}: {score}/100")
        
        if detailed and 'issues' in results[category]:
            for issue in results[category]['issues']:
                click.echo(f"   - {issue}")
    
    avg_score = total_score / len(categories)
    click.echo(f"\n{'=' * 50}")
    
    if avg_score >= 80:
        click.echo(f"✅ Production ready! (Score: {avg_score:.1f}/100)")
    elif avg_score >= 60:
        click.echo(f"⚠️  Nearly production ready (Score: {avg_score:.1f}/100)")
    else:
        click.echo(f"❌ Not production ready (Score: {avg_score:.1f}/100)")
    
    return 0 if avg_score >= 80 else 1


@check_group.command()
def integrity():
    """Run data integrity check."""
    from scripts.final_integrity_check import run_integrity_check
    
    click.echo("🔒 Running data integrity check...")
    
    results = run_integrity_check()
    
    if results['passed']:
        click.echo("✅ All integrity checks passed!")
        click.echo(f"   Entities checked: {results['entity_count']}")
        click.echo(f"   Metadata entries: {results['metadata_count']}")
    else:
        click.echo("❌ Integrity check failed!")
        for error in results['errors']:
            click.echo(f"   - {error}")
    
    return 0 if results['passed'] else 1


@check_group.command()
@click.option('--fix', '-f', is_flag=True, help='Fix architecture issues')
def architecture():
    """Verify codebase architecture."""
    from scripts.utils.verify_architecture import verify_architecture
    
    click.echo("🏗️  Verifying codebase architecture...")
    
    issues = verify_architecture()
    
    if not issues:
        click.echo("✅ Architecture verification passed!")
        return 0
    
    click.echo(f"\n⚠️  Found {len(issues)} architecture issues:")
    for issue in issues:
        click.echo(f"   - {issue}")
    
    if fix:
        click.echo("\n🔧 Attempting to fix issues...")
        # TODO: Implement architecture fixes
        click.echo("   Architecture fixes not yet implemented")
    
    return len(issues)
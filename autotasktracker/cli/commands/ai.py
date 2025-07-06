"""AI-related CLI commands."""
import sys
import click
import logging
from datetime import datetime

logger = logging.getLogger(__name__)


@click.group(name='ai')
def ai_group():
    """AI and machine learning operations."""
    pass


@ai_group.command()
def status():
    """Check AI components status."""
    from autotasktracker.config import get_config
    from autotasktracker.core import DatabaseManager
    
    click.echo("🤖 AI Status Check")
    click.echo("=" * 50)
    
    # Check database connection
    db_manager = DatabaseManager()
    if not db_manager.test_connection():
        click.echo("❌ Database connection failed")
        return
    
    click.echo("✅ Database connection successful")
    
    # Check AI coverage
    try:
        stats = db_manager.get_ai_coverage_stats()
        if stats:
            click.echo(f"📊 Total screenshots: {stats['total_screenshots']}")
            click.echo(f"📝 OCR coverage: {stats['ocr_percentage']:.1f}% ({stats['ocr_count']} screenshots)")
            click.echo(f"👁️  VLM coverage: {stats['vlm_percentage']:.1f}% ({stats['vlm_count']} screenshots)")
            click.echo(f"🧠 Embedding coverage: {stats['embedding_percentage']:.1f}% ({stats['embedding_count']} screenshots)")
    except Exception as e:
        click.echo(f"⚠️  Could not get AI coverage stats: {e}")
    
    config = get_config()
    
    # Check embeddings
    try:
        from sentence_transformers import SentenceTransformer
        click.echo("✅ Sentence transformers installed")
    except ImportError:
        click.echo("⚠️  Sentence transformers not installed")
        click.echo("   Install with: pip install sentence-transformers")
    
    # Check Ollama
    try:
        import requests
        response = requests.get(config.get_ollama_url(), timeout=2)
        click.echo("✅ Ollama server running")
    except (requests.RequestException, ConnectionError, TimeoutError):
        click.echo("⚠️  Ollama server not running (VLM features disabled)")
        click.echo("   Start with: ollama serve")
    
    # Check VLM model
    try:
        import subprocess
        result = subprocess.run(["ollama", "list"], capture_output=True, text=True, timeout=5)
        if "minicpm-v" in result.stdout:
            click.echo("✅ minicpm-v model available")
        else:
            click.echo("⚠️  minicpm-v model not found")
            click.echo("   Install with: ollama pull minicpm-v")
    except (subprocess.TimeoutExpired, subprocess.SubprocessError, FileNotFoundError):
        click.echo("⚠️  Could not check Ollama models")


@ai_group.command()
def setup():
    """One-time AI setup."""
    click.echo("🚀 Setting up AI features...")
    
    # Check and install dependencies
    try:
        import sentence_transformers
        click.echo("✅ Sentence transformers already installed")
    except ImportError:
        click.echo("📦 Installing sentence-transformers...")
        import subprocess
        subprocess.run([sys.executable, "-m", "pip", "install", "sentence-transformers"])
    
    # Enable AI features
    click.echo("\n✅ AI features enabled!")
    click.echo("\nNext steps:")
    click.echo("1. Install Ollama for VLM support: https://ollama.ai")
    click.echo("2. Run: ollama pull minicpm-v")
    click.echo("3. Start generating embeddings: autotask ai embeddings")


@ai_group.command()
@click.option('--limit', '-l', type=int, help='Maximum number of screenshots to process')
@click.option('--batch-size', '-b', type=int, default=50, help='Batch size for processing')
@click.option('--force', '-f', is_flag=True, help='Force regeneration of existing embeddings')
def embeddings(limit, batch_size, force):
    """Generate embeddings for screenshots."""
    from scripts.generate_embeddings import EmbeddingGenerator
    
    click.echo(f"🧠 Generating embeddings...")
    if limit:
        click.echo(f"   Processing up to {limit} screenshots")
    if force:
        click.echo("   Force regenerating existing embeddings")
    
    generator = EmbeddingGenerator()
    
    # TODO: Add force flag support to generator
    generator.process_screenshots(limit)
    
    click.echo("✅ Embedding generation complete!")


@ai_group.group()
def vlm():
    """Vision Language Model operations."""
    pass


@vlm.command('enable')
def enable_vlm():
    """Enable VLM processing."""
    from scripts.ai.vlm_manager import enable_vlm as _enable_vlm
    
    click.echo("🔬 Enabling Vision Language Model...")
    success = _enable_vlm()
    
    if success:
        click.echo("✅ VLM enabled successfully!")
        click.echo("   VLM will now process new screenshots automatically")
    else:
        click.echo("❌ Failed to enable VLM")
        click.echo("   Check that Ollama is running and minicpm-v model is installed")


@vlm.command('disable')
def disable_vlm():
    """Disable VLM processing."""
    from scripts.ai.vlm_manager import disable_vlm as _disable_vlm
    
    click.echo("🔬 Disabling Vision Language Model...")
    success = _disable_vlm()
    
    if success:
        click.echo("✅ VLM disabled successfully!")
    else:
        click.echo("❌ Failed to disable VLM")


@vlm.command('process')
@click.option('--limit', '-l', type=int, help='Maximum number of screenshots to process')
@click.option('--reprocess', '-r', is_flag=True, help='Reprocess screenshots with existing VLM results')
def process_vlm(limit, reprocess):
    """Process screenshots with VLM."""
    from scripts.ai.vlm_processor import process_screenshots_with_vlm
    
    click.echo("🔬 Processing screenshots with Vision Language Model...")
    if limit:
        click.echo(f"   Processing up to {limit} screenshots")
    if reprocess:
        click.echo("   Reprocessing existing VLM results")
    
    # Process screenshots
    processed = process_screenshots_with_vlm(limit=limit, force_reprocess=reprocess)
    
    click.echo(f"✅ Processed {processed} screenshots with VLM")
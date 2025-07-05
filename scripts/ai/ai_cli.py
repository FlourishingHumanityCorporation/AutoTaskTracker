#!/usr/bin/env python3
"""
AutoTaskTracker AI CLI - Simple command-line interface for AI features.
"""
import os
import sys
import argparse
import logging
from datetime import datetime

# Add project to path
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.append(project_root)

from generate_embeddings_simple import EmbeddingGenerator
from autotasktracker.core import DatabaseManager
from autotasktracker.config import get_config

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')
logger = logging.getLogger(__name__)

def check_ai_status():
    """Check the status of AI features."""
    print("🤖 AutoTaskTracker AI Status")
    print("=" * 40)
    
    # Check database
    db_manager = DatabaseManager()
    if not db_manager.test_connection():
        print("❌ Database connection failed")
        return
    
    print("✅ Database connection successful")
    
    # Check AI coverage
    stats = db_manager.get_ai_coverage_stats()
    if stats:
        print(f"📊 Total screenshots: {stats['total_screenshots']}")
        print(f"📝 OCR coverage: {stats['ocr_percentage']:.1f}% ({stats['ocr_count']} screenshots)")
        print(f"👁️  VLM coverage: {stats['vlm_percentage']:.1f}% ({stats['vlm_count']} screenshots)")
        print(f"🧠 Embedding coverage: {stats['embedding_percentage']:.1f}% ({stats['embedding_count']} screenshots)")
    
    # Check AI features availability
    try:
        from sentence_transformers import SentenceTransformer
        print("✅ Sentence Transformers available")
    except ImportError:
        print("❌ Sentence Transformers not installed")
        print("   Install with: pip install sentence-transformers")
    
    try:
        import requests
        response = requests.get(get_config().get_ollama_url(), timeout=2)
        print("✅ Ollama server running")
    except:
        print("⚠️  Ollama server not running (VLM features disabled)")
        print("   Start with: ollama serve")
    
    # Check if minicpm-v model exists
    try:
        import subprocess
        result = subprocess.run(["ollama", "list"], capture_output=True, text=True, timeout=5)
        if "minicpm-v" in result.stdout:
            print("✅ minicpm-v model available")
        else:
            print("⚠️  minicpm-v model not found")
            print("   Install with: ollama pull minicpm-v")
    except:
        print("⚠️  Could not check Ollama models")

def generate_embeddings(limit=None):
    """Generate embeddings for screenshots."""
    print(f"🧠 Generating embeddings...")
    if limit:
        print(f"   Processing up to {limit} screenshots")
    
    generator = EmbeddingGenerator()
    generator.process_screenshots(limit)
    print("✅ Embedding generation complete")

def enable_vlm():
    """Enable VLM in Pensieve configuration."""
    config_path = get_config().memos_dir_property / "config.yaml"
    
    if not os.path.exists(config_path):
        print("❌ Memos config not found. Initialize memos first with: memos init")
        return
    
    # Read config
    with open(config_path, 'r') as f:
        content = f.read()
    
    # Check if VLM is already enabled
    if "- builtin_vlm" in content and not "# - builtin_vlm" in content:
        print("✅ VLM already enabled")
        return
    
    # Enable VLM
    content = content.replace("# - builtin_vlm", "- builtin_vlm")
    
    # Write back
    with open(config_path, 'w') as f:
        f.write(content)
    
    print("✅ VLM enabled in config")
    print("   Restart memos to apply: memos restart")

def disable_vlm():
    """Disable VLM in Pensieve configuration."""
    config_path = get_config().memos_dir_property / "config.yaml"
    
    if not os.path.exists(config_path):
        print("❌ Memos config not found")
        return
    
    # Read config
    with open(config_path, 'r') as f:
        content = f.read()
    
    # Disable VLM
    content = content.replace("- builtin_vlm", "# - builtin_vlm")
    
    # Write back
    with open(config_path, 'w') as f:
        f.write(content)
    
    print("✅ VLM disabled in config")
    print("   Restart memos to apply: memos restart")

def setup_ai():
    """One-command setup for AI features."""
    print("🚀 Setting up AutoTaskTracker AI features...")
    
    # Install dependencies
    print("\n1. Installing Python dependencies...")
    try:
        import subprocess
        subprocess.run([sys.executable, "-m", "pip", "install", "sentence-transformers"], check=True)
        print("✅ Sentence Transformers installed")
    except Exception as e:
        print(f"❌ Failed to install dependencies: {e}")
        return
    
    # Generate embeddings for recent screenshots
    print("\n2. Generating embeddings for recent screenshots...")
    generate_embeddings(limit=100)
    
    # Check Ollama
    print("\n3. Checking VLM setup...")
    try:
        import requests
        response = requests.get(get_config().get_ollama_url(), timeout=2)
        print("✅ Ollama server detected")
        
        # Check for minicpm-v model
        try:
            result = subprocess.run(["ollama", "list"], capture_output=True, text=True, timeout=5)
            if "minicpm-v" in result.stdout:
                print("✅ minicpm-v model found")
                print("\n4. Enabling VLM...")
                enable_vlm()
            else:
                print("⚠️  minicpm-v model not found")
                print("   To enable VLM, run: ollama pull minicpm-v")
                print("   Then run: python ai_cli.py enable-vlm")
        except:
            print("⚠️  Could not check models")
    except:
        print("⚠️  Ollama not running")
        print("   To enable VLM:")
        print("   1. Install Ollama: https://ollama.ai")
        print("   2. Run: ollama serve")
        print("   3. Run: ollama pull minicpm-v")
        print("   4. Run: python ai_cli.py enable-vlm")
    
    print("\n✅ AI setup complete!")
    print("\nNext steps:")
    print("1. Run the AI-enhanced dashboard: streamlit run autotasktracker/dashboards/task_board.py")
    print("2. Check AI status: python ai_cli.py status")

def main():
    parser = argparse.ArgumentParser(
        description="AutoTaskTracker AI CLI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python ai_cli.py status              # Check AI feature status
  python ai_cli.py setup               # One-command setup
  python ai_cli.py embeddings          # Generate embeddings for all screenshots
  python ai_cli.py embeddings --limit 50  # Generate for 50 recent screenshots
  python ai_cli.py enable-vlm          # Enable VLM features
  python ai_cli.py disable-vlm         # Disable VLM features
        """)
    
    subparsers = parser.add_subparsers(dest='command', help='Commands')
    
    # Status command
    subparsers.add_parser('status', help='Check AI feature status')
    
    # Setup command
    subparsers.add_parser('setup', help='One-command AI setup')
    
    # Embeddings command
    embeddings_parser = subparsers.add_parser('embeddings', help='Generate embeddings')
    embeddings_parser.add_argument('--limit', type=int, help='Limit number of screenshots to process')
    
    # VLM commands
    subparsers.add_parser('enable-vlm', help='Enable VLM features')
    subparsers.add_parser('disable-vlm', help='Disable VLM features')
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
    
    try:
        if args.command == 'status':
            check_ai_status()
        elif args.command == 'setup':
            setup_ai()
        elif args.command == 'embeddings':
            generate_embeddings(args.limit)
        elif args.command == 'enable-vlm':
            enable_vlm()
        elif args.command == 'disable-vlm':
            disable_vlm()
    except KeyboardInterrupt:
        print("\n⏹️  Operation cancelled")
    except Exception as e:
        logger.error(f"Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
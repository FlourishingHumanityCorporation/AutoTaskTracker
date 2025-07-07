#!/bin/bash
# AutoTaskTracker Environment-Based Configuration Setup
# Implements Option 2: Environment-Based Configuration to avoid AITaskTracker conflicts

set -e

echo "🔧 Setting up AutoTaskTracker Environment-Based Configuration..."
echo ""

# Configuration paths
AUTOTASK_CONFIG="/Users/paulrohde/AutoTaskTracker.memos/autotask-config.yaml"
SHELL_PROFILE=""

# Detect shell and profile file
if [[ $SHELL == *"zsh"* ]]; then
    SHELL_PROFILE="$HOME/.zshrc"
    echo "📋 Detected Zsh shell, using: $SHELL_PROFILE"
elif [[ $SHELL == *"bash"* ]]; then
    SHELL_PROFILE="$HOME/.bashrc"
    echo "📋 Detected Bash shell, using: $SHELL_PROFILE"
else
    echo "⚠️  Unknown shell: $SHELL"
    echo "Please manually add the environment variable to your shell profile"
    SHELL_PROFILE="$HOME/.profile"
fi

# Verify AutoTaskTracker config exists
if [ ! -f "$AUTOTASK_CONFIG" ]; then
    echo "❌ AutoTaskTracker config not found: $AUTOTASK_CONFIG"
    echo "Creating config file..."
    
    # Create the config file
    cat > "$AUTOTASK_CONFIG" << 'EOF'
# AutoTaskTracker Dedicated Pensieve/Memos Configuration
# Environment-Based Configuration (Option 2)
# No conflicts with AITaskTracker

base_dir: /Users/paulrohde/AutoTaskTracker.memos
database_path: postgresql://postgres:mysecretpassword@localhost:5433/autotasktracker
default_library: screenshots
screenshots_dir: /Users/paulrohde/AutoTaskTracker.memos/screenshots
server_host: localhost
server_port: 8841

default_plugins:
  - builtin_ocr
  - builtin_vlm

ocr:
  concurrency: 8
  enabled: true
  endpoint: http://localhost:5555/predict
  force_jpeg: false
  use_local: true

vlm:
  concurrency: 8
  enabled: true
  endpoint: http://localhost:11434
  force_jpeg: true
  modelname: minicpm-v
  prompt: Please describe the content of this image, including the layout and visual elements.

embedding:
  endpoint: http://localhost:11434/v1/embeddings
  model: arkohut/jina-embeddings-v2-base-en
  num_dim: 768
  use_local: true

watch:
  idle_process_interval:
    - 00:00
    - 07:00
  idle_timeout: 300
  processing_interval: 1
  rate_window_size: 20
  sparsity_factor: 1.0

record_interval: 4
facet: false
EOF
    
    echo "✅ Created AutoTaskTracker config file"
fi

# Check if environment variable is already set in profile
if grep -q "MEMOS_CONFIG_PATH.*autotask-config.yaml" "$SHELL_PROFILE" 2>/dev/null; then
    echo "✅ AutoTaskTracker MEMOS_CONFIG_PATH already configured in $SHELL_PROFILE"
else
    echo ""
    echo "📝 Adding AutoTaskTracker environment configuration to $SHELL_PROFILE"
    
    # Add environment variable to shell profile
    cat >> "$SHELL_PROFILE" << EOF

# AutoTaskTracker Environment-Based Configuration (Option 2)
# Prevents conflicts with AITaskTracker shared config
export MEMOS_CONFIG_PATH="/Users/paulrohde/AutoTaskTracker.memos/autotask-config.yaml"
EOF
    
    echo "✅ Added MEMOS_CONFIG_PATH to $SHELL_PROFILE"
fi

# Set environment variable for current session
export MEMOS_CONFIG_PATH="$AUTOTASK_CONFIG"

echo ""
echo "🎉 Environment-Based Configuration Setup Complete!"
echo ""
echo "📋 Configuration Summary:"
echo "  • AutoTaskTracker config: $AUTOTASK_CONFIG"
echo "  • Environment variable: MEMOS_CONFIG_PATH"
echo "  • Shell profile: $SHELL_PROFILE"
echo "  • Database: PostgreSQL (localhost:5433/autotasktracker)"
echo "  • Server port: 8841 (AutoTaskTracker-specific)"
echo "  • Screenshots: /Users/paulrohde/AutoTaskTracker.memos/screenshots"
echo ""
echo "🔄 To apply changes:"
echo "  1. Restart your terminal OR run: source $SHELL_PROFILE"
echo "  2. Start AutoTaskTracker: python autotasktracker.py start"
echo ""
echo "✅ AutoTaskTracker will now use its own config independently of AITaskTracker"
echo "   No more conflicts with ~/.memos/config.yaml!"
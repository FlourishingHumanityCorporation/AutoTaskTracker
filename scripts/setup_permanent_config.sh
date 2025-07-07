#!/bin/bash
# AutoTaskTracker Permanent Configuration Setup
# This script ensures memos always uses AutoTaskTracker configuration

set -e

echo "🔧 Setting up permanent AutoTaskTracker configuration..."

# Configuration paths
MEMOS_CONFIG_DIR="$HOME/.memos"
AUTOTASK_CONFIG_DIR="/Users/paulrohde/AutoTaskTracker.memos"
AUTOTASK_CONFIG_FILE="$AUTOTASK_CONFIG_DIR/config.yaml"
MEMOS_CONFIG_FILE="$MEMOS_CONFIG_DIR/config.yaml"

# Create memos directory if it doesn't exist
if [ ! -d "$MEMOS_CONFIG_DIR" ]; then
    echo "📁 Creating memos config directory: $MEMOS_CONFIG_DIR"
    mkdir -p "$MEMOS_CONFIG_DIR"
fi

# Backup existing config if it exists
if [ -f "$MEMOS_CONFIG_FILE" ]; then
    BACKUP_FILE="$MEMOS_CONFIG_FILE.backup-$(date +%Y%m%d-%H%M%S)"
    echo "💾 Backing up existing config to: $BACKUP_FILE"
    cp "$MEMOS_CONFIG_FILE" "$BACKUP_FILE"
fi

# Copy AutoTaskTracker config to main memos config location
if [ -f "$AUTOTASK_CONFIG_FILE" ]; then
    echo "📋 Installing AutoTaskTracker config as main memos config"
    cp "$AUTOTASK_CONFIG_FILE" "$MEMOS_CONFIG_FILE"
    echo "✅ Configuration installed successfully"
else
    echo "❌ AutoTaskTracker config file not found: $AUTOTASK_CONFIG_FILE"
    exit 1
fi

# Verify the configuration
echo "🔍 Verifying configuration..."
if grep -q "AutoTaskTracker.memos" "$MEMOS_CONFIG_FILE"; then
    echo "✅ AutoTaskTracker paths detected in config"
else
    echo "⚠️  Warning: AutoTaskTracker paths not found in config"
fi

if grep -q "postgresql://" "$MEMOS_CONFIG_FILE"; then
    echo "✅ PostgreSQL database configuration detected"
else
    echo "⚠️  Warning: PostgreSQL database configuration not found"
fi

if grep -q "port: 8841" "$MEMOS_CONFIG_FILE"; then
    echo "✅ AutoTaskTracker port (8841) configuration detected"
else
    echo "⚠️  Warning: AutoTaskTracker port not found in config"
fi

echo ""
echo "🎉 Permanent configuration setup complete!"
echo ""
echo "📋 Configuration Summary:"
echo "  • Memos config file: $MEMOS_CONFIG_FILE"
echo "  • Base directory: /Users/paulrohde/AutoTaskTracker.memos"
echo "  • Screenshots: /Users/paulrohde/AutoTaskTracker.memos/screenshots"
echo "  • Database: PostgreSQL (localhost:5433/autotasktracker)"
echo "  • Server port: 8841"
echo ""
echo "💡 This configuration will persist across all memos operations."
echo "   No environment variables or special commands needed."
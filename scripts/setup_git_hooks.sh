#!/bin/bash
# Setup Git hooks for AutoTaskTracker security

echo "🔧 Setting up Git hooks for AI code security..."

# Check if we're in a git repository
if [ ! -d ".git" ]; then
    echo "❌ Error: Not in a git repository"
    exit 1
fi

# Configure git to use our hooks directory
git config core.hooksPath .githooks

echo "✅ Git hooks configured!"
echo ""
echo "The following hooks are now active:"
echo "- pre-commit: AI code security validation"
echo ""
echo "To test the pre-commit hook:"
echo "  make pre-commit-check"
echo ""
echo "To bypass hooks in emergency (use sparingly):"
echo "  git commit --no-verify"
echo ""
#!/bin/bash

# AutoTaskTracker Memos Wrapper Script
# This script ensures memos uses AutoTaskTracker-specific configuration

# Set environment variables for AutoTaskTracker
export MEMOS_BASE_DIR="/Users/paulrohde/AutoTaskTracker.memos"
export MEMOS_DATABASE_PATH="postgresql://postgres:mysecretpassword@localhost:5433/autotasktracker"
export MEMOS_SCREENSHOTS_DIR="/Users/paulrohde/AutoTaskTracker.memos/screenshots"
export MEMOS_SERVER_PORT="8841"
export MEMOS_SERVER_HOST="localhost"

# Activate venv if not already activated
if [[ -z "$VIRTUAL_ENV" ]]; then
    source "$(dirname "$0")/../venv/bin/activate"
fi

# Run memos with the provided arguments
exec memos "$@"
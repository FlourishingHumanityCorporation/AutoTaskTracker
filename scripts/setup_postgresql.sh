#!/bin/bash
# PostgreSQL setup script for AutoTaskTracker

set -e  # Exit on error

echo "AutoTaskTracker PostgreSQL Setup"
echo "================================"

# Detect OS
OS="unknown"
if [[ "$OSTYPE" == "darwin"* ]]; then
    OS="macos"
elif [[ "$OSTYPE" == "linux-gnu"* ]]; then
    OS="linux"
else
    echo "Unsupported OS: $OSTYPE"
    exit 1
fi

# Check if PostgreSQL is installed
if ! command -v psql &> /dev/null; then
    echo "PostgreSQL not found. Please install PostgreSQL first."
    echo ""
    if [[ "$OS" == "macos" ]]; then
        echo "Run: brew install postgresql@15"
    else
        echo "Run: sudo apt install postgresql-15"
    fi
    exit 1
fi

# Configuration
DB_USER="postgres"
DB_PASSWORD="mysecretpassword"
DB_NAME="autotasktracker"
DB_PORT="5433"

echo "Setting up PostgreSQL for AutoTaskTracker..."
echo "Database: $DB_NAME"
echo "Port: $DB_PORT"
echo ""

# Create user if needed (may already exist)
echo "Creating database user..."
if [[ "$OS" == "macos" ]]; then
    createuser -s $DB_USER 2>/dev/null || echo "User $DB_USER already exists"
else
    sudo -u postgres createuser -s $DB_USER 2>/dev/null || echo "User $DB_USER already exists"
fi

# Set password
echo "Setting user password..."
if [[ "$OS" == "macos" ]]; then
    psql -U $DB_USER -c "ALTER USER $DB_USER PASSWORD '$DB_PASSWORD';" postgres
else
    sudo -u postgres psql -c "ALTER USER $DB_USER PASSWORD '$DB_PASSWORD';"
fi

# Create database
echo "Creating database..."
if [[ "$OS" == "macos" ]]; then
    createdb -U $DB_USER $DB_NAME 2>/dev/null || echo "Database $DB_NAME already exists"
else
    sudo -u postgres createdb $DB_NAME 2>/dev/null || echo "Database $DB_NAME already exists"
fi

# Test connection
echo ""
echo "Testing connection..."
PGPASSWORD=$DB_PASSWORD psql -h localhost -p 5432 -U $DB_USER -d $DB_NAME -c "SELECT version();" > /dev/null 2>&1
if [ $? -eq 0 ]; then
    echo "✅ PostgreSQL connection successful!"
else
    echo "❌ Connection failed. Please check PostgreSQL is running on port 5432"
    echo "   You may need to configure it to use port $DB_PORT"
    exit 1
fi

# Create tables
echo ""
echo "Creating database schema..."
PGPASSWORD=$DB_PASSWORD psql -h localhost -p 5432 -U $DB_USER -d $DB_NAME << EOF
-- Create entities table if not exists
CREATE TABLE IF NOT EXISTS entities (
    id SERIAL PRIMARY KEY,
    filepath TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create metadata_entries table if not exists
CREATE TABLE IF NOT EXISTS metadata_entries (
    id SERIAL PRIMARY KEY,
    entity_id INTEGER REFERENCES entities(id) ON DELETE CASCADE,
    key VARCHAR(255) NOT NULL,
    value TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create indexes for performance
CREATE INDEX IF NOT EXISTS idx_entities_created_at ON entities(created_at);
CREATE INDEX IF NOT EXISTS idx_metadata_entity_id ON metadata_entries(entity_id);
CREATE INDEX IF NOT EXISTS idx_metadata_key ON metadata_entries(key);

-- Grant permissions
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO $DB_USER;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO $DB_USER;
EOF

echo "✅ Database schema created"

# Update AutoTaskTracker config
echo ""
echo "Updating AutoTaskTracker configuration..."
CONFIG_DIR="$HOME/.memos"
CONFIG_FILE="$CONFIG_DIR/config_autotasktracker.yaml"

# Create config directory if needed
mkdir -p "$CONFIG_DIR"

# Check if config exists
if [ -f "$CONFIG_FILE" ]; then
    echo "Config file exists at $CONFIG_FILE"
    echo "Please verify it contains:"
    echo "  database_path: postgresql://$DB_USER:$DB_PASSWORD@localhost:$DB_PORT/$DB_NAME"
    echo "  server_port: 8841"
else
    echo "Creating config file..."
    cat > "$CONFIG_FILE" << EOF
database_path: postgresql://$DB_USER:$DB_PASSWORD@localhost:$DB_PORT/$DB_NAME
server_port: 8841
server_host: localhost
ai_model: all-MiniLM-L6-v2
auth_password: ""
auth_username: ""
base_dir: ~/.memos
cache_ttl: 600
default_library: screenshots
default_plugins:
  - builtin_ocr
  - builtin_vlm
screenshots_dir: screenshots
record_interval: 4
EOF
    echo "✅ Config file created at $CONFIG_FILE"
fi

# Final message
echo ""
echo "========================================="
echo "PostgreSQL setup complete!"
echo ""
echo "Next steps:"
echo "1. If using port 5433, update PostgreSQL config:"
echo "   - Edit postgresql.conf and set: port = 5433"
echo "   - Restart PostgreSQL service"
echo ""
echo "2. Install Python dependencies:"
echo "   pip install psycopg2-binary"
echo ""
echo "3. Test the connection:"
echo "   python autotask.py test"
echo ""
echo "4. Launch dashboards:"
echo "   python autotasktracker.py dashboard"
echo "========================================="
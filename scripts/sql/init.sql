-- PostgreSQL initialization script for AutoTaskTracker
-- This script creates the necessary tables and indexes for AutoTaskTracker

-- Set timezone
SET timezone = 'UTC';

-- Create entities table
CREATE TABLE IF NOT EXISTS entities (
    id SERIAL PRIMARY KEY,
    filepath TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create metadata_entries table
CREATE TABLE IF NOT EXISTS metadata_entries (
    id SERIAL PRIMARY KEY,
    entity_id INTEGER REFERENCES entities(id) ON DELETE CASCADE,
    key VARCHAR(255) NOT NULL,
    value TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create indexes for performance
CREATE INDEX IF NOT EXISTS idx_entities_created_at ON entities(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_entities_filepath ON entities(filepath);
CREATE INDEX IF NOT EXISTS idx_metadata_entity_id ON metadata_entries(entity_id);
CREATE INDEX IF NOT EXISTS idx_metadata_key ON metadata_entries(key);
CREATE INDEX IF NOT EXISTS idx_metadata_key_value ON metadata_entries(key, value);
CREATE INDEX IF NOT EXISTS idx_metadata_created_at ON metadata_entries(created_at DESC);

-- Create composite indexes for common queries
CREATE INDEX IF NOT EXISTS idx_entities_created_filepath ON entities(created_at DESC, filepath);
CREATE INDEX IF NOT EXISTS idx_metadata_entity_key ON metadata_entries(entity_id, key);

-- Function to update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Triggers to automatically update updated_at
CREATE TRIGGER update_entities_updated_at 
    BEFORE UPDATE ON entities 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_metadata_entries_updated_at 
    BEFORE UPDATE ON metadata_entries 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Grant permissions to postgres user
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO postgres;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO postgres;
GRANT ALL PRIVILEGES ON ALL FUNCTIONS IN SCHEMA public TO postgres;

-- Create view for common task queries
CREATE VIEW IF NOT EXISTS task_view AS
SELECT 
    e.id,
    e.filepath,
    e.created_at,
    e.updated_at,
    ocr.value as ocr_text,
    window.value as active_window,
    category.value as category,
    task.value as task_description
FROM entities e
LEFT JOIN metadata_entries ocr ON e.id = ocr.entity_id AND ocr.key = 'ocr_result'
LEFT JOIN metadata_entries window ON e.id = window.entity_id AND window.key = 'active_window'
LEFT JOIN metadata_entries category ON e.id = category.entity_id AND category.key = 'category'
LEFT JOIN metadata_entries task ON e.id = task.entity_id AND task.key = 'task';

-- Insert some sample data if tables are empty
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM entities LIMIT 1) THEN
        INSERT INTO entities (filepath, created_at) VALUES 
        ('sample_screenshot_1.png', CURRENT_TIMESTAMP - INTERVAL '1 hour'),
        ('sample_screenshot_2.png', CURRENT_TIMESTAMP - INTERVAL '2 hours');
        
        INSERT INTO metadata_entries (entity_id, key, value, created_at) VALUES
        (1, 'ocr_result', 'Sample OCR text from screenshot', CURRENT_TIMESTAMP - INTERVAL '1 hour'),
        (1, 'active_window', 'Sample Application Window', CURRENT_TIMESTAMP - INTERVAL '1 hour'),
        (2, 'ocr_result', 'Another sample OCR text', CURRENT_TIMESTAMP - INTERVAL '2 hours'),
        (2, 'active_window', 'Another Application', CURRENT_TIMESTAMP - INTERVAL '2 hours');
    END IF;
END $$;

-- Display initialization status
DO $$
DECLARE
    entity_count INTEGER;
    metadata_count INTEGER;
BEGIN
    SELECT COUNT(*) INTO entity_count FROM entities;
    SELECT COUNT(*) INTO metadata_count FROM metadata_entries;
    
    RAISE NOTICE 'AutoTaskTracker PostgreSQL initialization complete';
    RAISE NOTICE 'Entities: %', entity_count;
    RAISE NOTICE 'Metadata entries: %', metadata_count;
END $$;
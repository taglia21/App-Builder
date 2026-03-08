-- Database initialization script for Ignara
-- Run on fresh PostgreSQL installation

-- Create extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- Create schema
CREATE SCHEMA IF NOT EXISTS ignara;

-- Grant permissions
GRANT ALL PRIVILEGES ON SCHEMA ignara TO ignara;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA ignara TO ignara;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA ignara TO ignara;

-- Set search path
ALTER DATABASE ignara SET search_path TO ignara, public;

-- Create indexes for performance (applied by Alembic migrations)
-- This is a placeholder for any initial setup

SELECT 'Ignara database initialized successfully' AS status;

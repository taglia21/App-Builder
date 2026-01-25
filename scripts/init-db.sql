-- Database initialization script for LaunchForge
-- Run on fresh PostgreSQL installation

-- Create extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- Create schema
CREATE SCHEMA IF NOT EXISTS launchforge;

-- Grant permissions
GRANT ALL PRIVILEGES ON SCHEMA launchforge TO launchforge;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA launchforge TO launchforge;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA launchforge TO launchforge;

-- Set search path
ALTER DATABASE launchforge SET search_path TO launchforge, public;

-- Create indexes for performance (applied by Alembic migrations)
-- This is a placeholder for any initial setup

SELECT 'LaunchForge database initialized successfully' AS status;

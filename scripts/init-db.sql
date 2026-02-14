-- Database initialization script for Valeric
-- Run on fresh PostgreSQL installation

-- Create extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- Create schema
CREATE SCHEMA IF NOT EXISTS valeric;

-- Grant permissions
GRANT ALL PRIVILEGES ON SCHEMA valeric TO valeric;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA valeric TO valeric;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA valeric TO valeric;

-- Set search path
ALTER DATABASE valeric SET search_path TO valeric, public;

-- Create indexes for performance (applied by Alembic migrations)
-- This is a placeholder for any initial setup

SELECT 'Valeric database initialized successfully' AS status;

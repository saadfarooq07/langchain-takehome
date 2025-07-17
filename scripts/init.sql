-- Initialize the database with required extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- Create the database user if it doesn't exist
DO $$
BEGIN
    IF NOT EXISTS (SELECT FROM pg_catalog.pg_roles WHERE rolname = 'loganalyzer') THEN
        CREATE USER loganalyzer WITH PASSWORD 'password';
    END IF;
END
$$;

-- Grant necessary permissions
GRANT ALL PRIVILEGES ON DATABASE loganalyzer TO loganalyzer;
GRANT ALL ON SCHEMA public TO loganalyzer;

-- Set the default search path
ALTER USER loganalyzer SET search_path TO public;
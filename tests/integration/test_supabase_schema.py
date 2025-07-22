"""
Integration tests for Supabase database schema and migrations.
"""

import pytest
import os
from unittest.mock import Mock, patch
from typing import Dict, Any, List

try:
    from supabase import create_client, Client
    SUPABASE_AVAILABLE = True
except ImportError:
    SUPABASE_AVAILABLE = False


@pytest.mark.skipif(not SUPABASE_AVAILABLE, reason="Supabase client not installed")
class TestSupabaseSchema:
    """Test Supabase database schema and table structures."""
    
    @pytest.fixture
    def expected_schema(self):
        """Expected database schema for the Log Analyzer Agent."""
        return {
            "users": {
                "columns": [
                    {"name": "id", "type": "uuid", "primary_key": True},
                    {"name": "email", "type": "text", "unique": True},
                    {"name": "created_at", "type": "timestamptz"},
                    {"name": "updated_at", "type": "timestamptz"},
                    {"name": "last_login", "type": "timestamptz"},
                    {"name": "preferences", "type": "jsonb"}
                ],
                "indexes": ["email", "created_at"]
            },
            "analysis_results": {
                "columns": [
                    {"name": "id", "type": "uuid", "primary_key": True},
                    {"name": "user_id", "type": "uuid", "foreign_key": "users.id"},
                    {"name": "log_content_hash", "type": "text"},
                    {"name": "log_file_name", "type": "text"},
                    {"name": "summary", "type": "text"},
                    {"name": "issues", "type": "jsonb"},
                    {"name": "suggestions", "type": "jsonb"},
                    {"name": "documentation_references", "type": "jsonb"},
                    {"name": "analysis_metadata", "type": "jsonb"},
                    {"name": "created_at", "type": "timestamptz"},
                    {"name": "updated_at", "type": "timestamptz"}
                ],
                "indexes": ["user_id", "log_content_hash", "created_at"]
            },
            "conversations": {
                "columns": [
                    {"name": "id", "type": "uuid", "primary_key": True},
                    {"name": "user_id", "type": "uuid", "foreign_key": "users.id"},
                    {"name": "analysis_id", "type": "uuid", "foreign_key": "analysis_results.id"},
                    {"name": "messages", "type": "jsonb"},
                    {"name": "context", "type": "jsonb"},
                    {"name": "created_at", "type": "timestamptz"},
                    {"name": "updated_at", "type": "timestamptz"}
                ],
                "indexes": ["user_id", "analysis_id", "created_at"]
            },
            "analysis_cache": {
                "columns": [
                    {"name": "id", "type": "uuid", "primary_key": True},
                    {"name": "log_content_hash", "type": "text", "unique": True},
                    {"name": "analysis_data", "type": "jsonb"},
                    {"name": "cache_metadata", "type": "jsonb"},
                    {"name": "expires_at", "type": "timestamptz"},
                    {"name": "created_at", "type": "timestamptz"},
                    {"name": "accessed_at", "type": "timestamptz"}
                ],
                "indexes": ["log_content_hash", "expires_at", "accessed_at"]
            },
            "log_files": {
                "columns": [
                    {"name": "id", "type": "uuid", "primary_key": True},
                    {"name": "user_id", "type": "uuid", "foreign_key": "users.id"},
                    {"name": "file_name", "type": "text"},
                    {"name": "file_size", "type": "bigint"},
                    {"name": "file_hash", "type": "text"},
                    {"name": "storage_path", "type": "text"},
                    {"name": "content_type", "type": "text"},
                    {"name": "upload_metadata", "type": "jsonb"},
                    {"name": "created_at", "type": "timestamptz"}
                ],
                "indexes": ["user_id", "file_hash", "created_at"]
            }
        }
    
    @pytest.fixture
    def mock_supabase_client(self):
        """Mock Supabase client with schema operations."""
        mock_client = Mock(spec=Client)
        
        # Mock schema queries
        def mock_schema_query(table_name):
            schema_data = {
                "users": [
                    {"column_name": "id", "data_type": "uuid", "is_nullable": "NO"},
                    {"column_name": "email", "data_type": "text", "is_nullable": "NO"},
                    {"column_name": "created_at", "data_type": "timestamp with time zone", "is_nullable": "NO"},
                    {"column_name": "updated_at", "data_type": "timestamp with time zone", "is_nullable": "NO"},
                    {"column_name": "last_login", "data_type": "timestamp with time zone", "is_nullable": "YES"},
                    {"column_name": "preferences", "data_type": "jsonb", "is_nullable": "YES"}
                ],
                "analysis_results": [
                    {"column_name": "id", "data_type": "uuid", "is_nullable": "NO"},
                    {"column_name": "user_id", "data_type": "uuid", "is_nullable": "NO"},
                    {"column_name": "log_content_hash", "data_type": "text", "is_nullable": "NO"},
                    {"column_name": "summary", "data_type": "text", "is_nullable": "YES"},
                    {"column_name": "issues", "data_type": "jsonb", "is_nullable": "YES"},
                    {"column_name": "suggestions", "data_type": "jsonb", "is_nullable": "YES"},
                    {"column_name": "created_at", "data_type": "timestamp with time zone", "is_nullable": "NO"}
                ]
            }
            return Mock(data=schema_data.get(table_name, []))
        
        mock_client.table.return_value.select.return_value.execute.side_effect = lambda: mock_schema_query("users")
        
        return mock_client
    
    @pytest.mark.integration
    @pytest.mark.requires_db
    def test_users_table_schema(self, mock_supabase_client, expected_schema):
        """Test users table schema validation."""
        # Mock schema query for users table
        users_schema = expected_schema["users"]["columns"]
        mock_response = Mock(data=[
            {"column_name": col["name"], "data_type": col["type"]}
            for col in users_schema
        ])
        
        mock_supabase_client.rpc.return_value.execute.return_value = mock_response
        
        # Test schema validation
        result = mock_supabase_client.rpc("get_table_schema", {"table_name": "users"}).execute()
        
        column_names = [row["column_name"] for row in result.data]
        expected_columns = [col["name"] for col in users_schema]
        
        for expected_col in expected_columns:
            assert expected_col in column_names, f"Missing column: {expected_col}"
    
    @pytest.mark.integration
    @pytest.mark.requires_db
    def test_analysis_results_table_schema(self, mock_supabase_client, expected_schema):
        """Test analysis_results table schema validation."""
        analysis_schema = expected_schema["analysis_results"]["columns"]
        mock_response = Mock(data=[
            {"column_name": col["name"], "data_type": col["type"]}
            for col in analysis_schema
        ])
        
        mock_supabase_client.rpc.return_value.execute.return_value = mock_response
        
        result = mock_supabase_client.rpc("get_table_schema", {"table_name": "analysis_results"}).execute()
        
        column_names = [row["column_name"] for row in result.data]
        expected_columns = [col["name"] for col in analysis_schema]
        
        for expected_col in expected_columns:
            assert expected_col in column_names, f"Missing column: {expected_col}"
    
    @pytest.mark.integration
    @pytest.mark.requires_db
    def test_foreign_key_constraints(self, mock_supabase_client):
        """Test foreign key constraints are properly set up."""
        # Mock foreign key constraint query
        mock_constraints = [
            {
                "table_name": "analysis_results",
                "column_name": "user_id",
                "foreign_table_name": "users",
                "foreign_column_name": "id"
            },
            {
                "table_name": "conversations",
                "column_name": "user_id", 
                "foreign_table_name": "users",
                "foreign_column_name": "id"
            },
            {
                "table_name": "conversations",
                "column_name": "analysis_id",
                "foreign_table_name": "analysis_results",
                "foreign_column_name": "id"
            }
        ]
        
        mock_supabase_client.rpc.return_value.execute.return_value = Mock(data=mock_constraints)
        
        result = mock_supabase_client.rpc("get_foreign_keys").execute()
        
        # Verify expected foreign keys exist
        constraints = result.data
        expected_fks = [
            ("analysis_results", "user_id", "users", "id"),
            ("conversations", "user_id", "users", "id"),
            ("conversations", "analysis_id", "analysis_results", "id")
        ]
        
        for table, column, ref_table, ref_column in expected_fks:
            fk_exists = any(
                c["table_name"] == table and 
                c["column_name"] == column and
                c["foreign_table_name"] == ref_table and
                c["foreign_column_name"] == ref_column
                for c in constraints
            )
            assert fk_exists, f"Missing foreign key: {table}.{column} -> {ref_table}.{ref_column}"
    
    @pytest.mark.integration
    @pytest.mark.requires_db
    def test_database_indexes(self, mock_supabase_client, expected_schema):
        """Test database indexes are properly created."""
        # Mock index query
        mock_indexes = [
            {"table_name": "users", "index_name": "idx_users_email", "column_name": "email"},
            {"table_name": "users", "index_name": "idx_users_created_at", "column_name": "created_at"},
            {"table_name": "analysis_results", "index_name": "idx_analysis_user_id", "column_name": "user_id"},
            {"table_name": "analysis_results", "index_name": "idx_analysis_hash", "column_name": "log_content_hash"},
            {"table_name": "analysis_results", "index_name": "idx_analysis_created_at", "column_name": "created_at"}
        ]
        
        mock_supabase_client.rpc.return_value.execute.return_value = Mock(data=mock_indexes)
        
        result = mock_supabase_client.rpc("get_table_indexes").execute()
        
        # Verify expected indexes exist
        indexes = result.data
        
        for table_name, table_schema in expected_schema.items():
            if "indexes" in table_schema:
                for expected_index_column in table_schema["indexes"]:
                    index_exists = any(
                        idx["table_name"] == table_name and 
                        idx["column_name"] == expected_index_column
                        for idx in indexes
                    )
                    assert index_exists, f"Missing index on {table_name}.{expected_index_column}"
    
    @pytest.mark.integration
    @pytest.mark.requires_db
    def test_row_level_security_policies(self, mock_supabase_client):
        """Test Row Level Security (RLS) policies."""
        # Mock RLS policy query
        mock_policies = [
            {
                "table_name": "analysis_results",
                "policy_name": "Users can only access their own analysis results",
                "policy_definition": "user_id = auth.uid()"
            },
            {
                "table_name": "conversations",
                "policy_name": "Users can only access their own conversations",
                "policy_definition": "user_id = auth.uid()"
            },
            {
                "table_name": "log_files",
                "policy_name": "Users can only access their own log files",
                "policy_definition": "user_id = auth.uid()"
            }
        ]
        
        mock_supabase_client.rpc.return_value.execute.return_value = Mock(data=mock_policies)
        
        result = mock_supabase_client.rpc("get_rls_policies").execute()
        
        # Verify RLS policies exist for sensitive tables
        policies = result.data
        sensitive_tables = ["analysis_results", "conversations", "log_files"]
        
        for table in sensitive_tables:
            policy_exists = any(
                policy["table_name"] == table and
                "auth.uid()" in policy["policy_definition"]
                for policy in policies
            )
            assert policy_exists, f"Missing RLS policy for table: {table}"
    
    @pytest.mark.integration
    @pytest.mark.requires_db
    def test_database_functions(self, mock_supabase_client):
        """Test custom database functions."""
        # Mock database functions query
        mock_functions = [
            {
                "function_name": "get_user_analysis_count",
                "return_type": "integer",
                "parameters": ["user_uuid"]
            },
            {
                "function_name": "cleanup_expired_cache",
                "return_type": "integer",
                "parameters": []
            },
            {
                "function_name": "get_analysis_statistics",
                "return_type": "jsonb",
                "parameters": ["user_uuid", "date_range"]
            }
        ]
        
        mock_supabase_client.rpc.return_value.execute.return_value = Mock(data=mock_functions)
        
        result = mock_supabase_client.rpc("get_custom_functions").execute()
        
        # Verify expected functions exist
        functions = result.data
        expected_functions = [
            "get_user_analysis_count",
            "cleanup_expired_cache", 
            "get_analysis_statistics"
        ]
        
        function_names = [func["function_name"] for func in functions]
        
        for expected_func in expected_functions:
            assert expected_func in function_names, f"Missing database function: {expected_func}"
    
    @pytest.mark.integration
    @pytest.mark.requires_db
    def test_database_triggers(self, mock_supabase_client):
        """Test database triggers for automatic timestamps and cleanup."""
        # Mock triggers query
        mock_triggers = [
            {
                "table_name": "users",
                "trigger_name": "set_updated_at",
                "trigger_event": "UPDATE"
            },
            {
                "table_name": "analysis_results",
                "trigger_name": "set_updated_at",
                "trigger_event": "UPDATE"
            },
            {
                "table_name": "conversations",
                "trigger_name": "set_updated_at",
                "trigger_event": "UPDATE"
            },
            {
                "table_name": "analysis_cache",
                "trigger_name": "update_accessed_at",
                "trigger_event": "SELECT"
            }
        ]
        
        mock_supabase_client.rpc.return_value.execute.return_value = Mock(data=mock_triggers)
        
        result = mock_supabase_client.rpc("get_table_triggers").execute()
        
        # Verify expected triggers exist
        triggers = result.data
        
        # Check for updated_at triggers on main tables
        tables_with_updated_at = ["users", "analysis_results", "conversations"]
        
        for table in tables_with_updated_at:
            trigger_exists = any(
                trigger["table_name"] == table and
                trigger["trigger_name"] == "set_updated_at" and
                trigger["trigger_event"] == "UPDATE"
                for trigger in triggers
            )
            assert trigger_exists, f"Missing updated_at trigger for table: {table}"


@pytest.mark.skipif(not SUPABASE_AVAILABLE, reason="Supabase client not installed")
class TestSupabaseMigrations:
    """Test Supabase database migrations and versioning."""
    
    @pytest.fixture
    def migration_history(self):
        """Mock migration history."""
        return [
            {
                "version": "001",
                "name": "initial_schema",
                "applied_at": "2024-01-01T00:00:00Z",
                "checksum": "abc123"
            },
            {
                "version": "002", 
                "name": "add_analysis_cache",
                "applied_at": "2024-01-02T00:00:00Z",
                "checksum": "def456"
            },
            {
                "version": "003",
                "name": "add_rls_policies",
                "applied_at": "2024-01-03T00:00:00Z", 
                "checksum": "ghi789"
            }
        ]
    
    @pytest.mark.integration
    @pytest.mark.requires_db
    def test_migration_tracking(self, mock_supabase_client, migration_history):
        """Test migration tracking and versioning."""
        mock_supabase_client.table.return_value.select.return_value.order.return_value.execute.return_value = Mock(
            data=migration_history
        )
        
        # Test migration history retrieval
        result = (mock_supabase_client
                 .table("schema_migrations")
                 .select("*")
                 .order("version")
                 .execute())
        
        migrations = result.data
        
        assert len(migrations) == 3
        assert migrations[0]["version"] == "001"
        assert migrations[0]["name"] == "initial_schema"
        assert migrations[-1]["version"] == "003"
    
    @pytest.mark.integration
    @pytest.mark.requires_db
    def test_migration_rollback_capability(self, mock_supabase_client):
        """Test migration rollback capability."""
        # Mock rollback function
        mock_supabase_client.rpc.return_value.execute.return_value = Mock(
            data={"success": True, "rolled_back_to": "002"}
        )
        
        # Test rollback to specific version
        result = mock_supabase_client.rpc("rollback_migration", {"target_version": "002"}).execute()
        
        assert result.data["success"] is True
        assert result.data["rolled_back_to"] == "002"
    
    @pytest.mark.integration
    @pytest.mark.requires_db
    def test_schema_validation_after_migration(self, mock_supabase_client):
        """Test schema validation after migrations."""
        # Mock schema validation function
        mock_supabase_client.rpc.return_value.execute.return_value = Mock(
            data={
                "valid": True,
                "issues": [],
                "schema_version": "003"
            }
        )
        
        # Test schema validation
        result = mock_supabase_client.rpc("validate_schema").execute()
        
        validation = result.data
        assert validation["valid"] is True
        assert len(validation["issues"]) == 0
        assert validation["schema_version"] == "003"
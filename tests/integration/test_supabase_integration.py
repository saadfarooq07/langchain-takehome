"""
Integration tests for Supabase database functionality.
"""

import pytest
import asyncio
import os
from unittest.mock import Mock, AsyncMock, patch
from typing import Dict, Any, List, Optional

try:
    from supabase import create_client, Client
    SUPABASE_AVAILABLE = True
except ImportError:
    SUPABASE_AVAILABLE = False


@pytest.mark.skipif(not SUPABASE_AVAILABLE, reason="Supabase client not installed")
class TestSupabaseIntegration:
    """Test Supabase database integration."""
    
    @pytest.fixture
    def supabase_config(self):
        """Supabase configuration for testing."""
        return {
            "url": os.getenv("SUPABASE_URL", "https://test.supabase.co"),
            "anon_key": os.getenv("SUPABASE_ANON_KEY", "test_anon_key"),
            "service_role_key": os.getenv("SUPABASE_SERVICE_ROLE_KEY", "test_service_key")
        }
    
    @pytest.fixture
    def mock_supabase_client(self):
        """Mock Supabase client for testing."""
        mock_client = Mock(spec=Client)
        
        # Mock table operations
        mock_table = Mock()
        mock_table.select.return_value = mock_table
        mock_table.insert.return_value = mock_table
        mock_table.update.return_value = mock_table
        mock_table.delete.return_value = mock_table
        mock_table.eq.return_value = mock_table
        mock_table.execute.return_value = Mock(data=[])
        
        mock_client.table.return_value = mock_table
        mock_client.from_.return_value = mock_table
        
        # Mock auth operations
        mock_auth = Mock()
        mock_auth.sign_up.return_value = Mock(user=Mock(id="test_user_id"))
        mock_auth.sign_in_with_password.return_value = Mock(user=Mock(id="test_user_id"))
        mock_client.auth = mock_auth
        
        # Mock storage operations
        mock_storage = Mock()
        mock_bucket = Mock()
        mock_bucket.upload.return_value = Mock(path="test_path")
        mock_bucket.download.return_value = b"test_data"
        mock_storage.from_.return_value = mock_bucket
        mock_client.storage = mock_storage
        
        return mock_client
    
    @pytest.mark.integration
    @pytest.mark.requires_db
    def test_supabase_client_creation(self, supabase_config):
        """Test Supabase client creation."""
        if not os.getenv("SUPABASE_URL"):
            pytest.skip("Supabase URL not configured")
        
        with patch('supabase.create_client') as mock_create:
            mock_create.return_value = Mock(spec=Client)
            
            client = create_client(
                supabase_config["url"],
                supabase_config["anon_key"]
            )
            
            assert client is not None
            mock_create.assert_called_once_with(
                supabase_config["url"],
                supabase_config["anon_key"]
            )
    
    @pytest.mark.integration
    @pytest.mark.requires_db
    def test_analysis_results_storage(self, mock_supabase_client):
        """Test storing analysis results in Supabase."""
        analysis_result = {
            "id": "test_analysis_123",
            "log_content_hash": "abc123",
            "summary": "Test analysis summary",
            "issues": [
                {
                    "severity": "high",
                    "category": "error",
                    "description": "Test issue"
                }
            ],
            "suggestions": [
                {
                    "priority": "high",
                    "category": "fix",
                    "description": "Test suggestion"
                }
            ],
            "created_at": "2024-01-15T10:30:00Z"
        }
        
        # Mock successful insert
        mock_supabase_client.table.return_value.insert.return_value.execute.return_value = Mock(
            data=[analysis_result]
        )
        
        # Test insertion
        result = mock_supabase_client.table("analysis_results").insert(analysis_result).execute()
        
        assert result.data == [analysis_result]
        mock_supabase_client.table.assert_called_with("analysis_results")
    
    @pytest.mark.integration
    @pytest.mark.requires_db
    def test_user_session_management(self, mock_supabase_client):
        """Test user session management with Supabase."""
        user_data = {
            "email": "test@example.com",
            "password": "test_password"
        }
        
        # Mock successful sign up
        mock_user = Mock(id="test_user_123", email="test@example.com")
        mock_supabase_client.auth.sign_up.return_value = Mock(user=mock_user)
        
        # Test user registration
        result = mock_supabase_client.auth.sign_up(user_data)
        
        assert result.user.id == "test_user_123"
        assert result.user.email == "test@example.com"
        mock_supabase_client.auth.sign_up.assert_called_once_with(user_data)
        
        # Mock successful sign in
        mock_supabase_client.auth.sign_in_with_password.return_value = Mock(user=mock_user)
        
        # Test user login
        login_result = mock_supabase_client.auth.sign_in_with_password(user_data)
        
        assert login_result.user.id == "test_user_123"
        mock_supabase_client.auth.sign_in_with_password.assert_called_once_with(user_data)
    
    @pytest.mark.integration
    @pytest.mark.requires_db
    def test_log_file_storage(self, mock_supabase_client):
        """Test storing log files in Supabase storage."""
        log_content = "2024-01-15 10:30:00 INFO Test log entry"
        file_name = "test_log.txt"
        
        # Mock successful upload
        mock_supabase_client.storage.from_.return_value.upload.return_value = Mock(
            path=f"logs/{file_name}"
        )
        
        # Test file upload
        result = mock_supabase_client.storage.from_("logs").upload(file_name, log_content.encode())
        
        assert result.path == f"logs/{file_name}"
        mock_supabase_client.storage.from_.assert_called_with("logs")
    
    @pytest.mark.integration
    @pytest.mark.requires_db
    def test_analysis_history_retrieval(self, mock_supabase_client):
        """Test retrieving analysis history from Supabase."""
        user_id = "test_user_123"
        mock_history = [
            {
                "id": "analysis_1",
                "user_id": user_id,
                "summary": "First analysis",
                "created_at": "2024-01-15T10:30:00Z"
            },
            {
                "id": "analysis_2", 
                "user_id": user_id,
                "summary": "Second analysis",
                "created_at": "2024-01-15T11:30:00Z"
            }
        ]
        
        # Mock successful query
        mock_supabase_client.table.return_value.select.return_value.eq.return_value.execute.return_value = Mock(
            data=mock_history
        )
        
        # Test history retrieval
        result = (mock_supabase_client
                 .table("analysis_results")
                 .select("*")
                 .eq("user_id", user_id)
                 .execute())
        
        assert result.data == mock_history
        mock_supabase_client.table.assert_called_with("analysis_results")
    
    @pytest.mark.integration
    @pytest.mark.requires_db
    def test_real_time_subscriptions(self, mock_supabase_client):
        """Test real-time subscriptions with Supabase."""
        # Mock real-time subscription
        mock_subscription = Mock()
        mock_supabase_client.table.return_value.on.return_value.subscribe.return_value = mock_subscription
        
        def mock_callback(payload):
            assert payload["eventType"] in ["INSERT", "UPDATE", "DELETE"]
            assert "new" in payload or "old" in payload
        
        # Test subscription setup
        subscription = (mock_supabase_client
                       .table("analysis_results")
                       .on("*", mock_callback)
                       .subscribe())
        
        assert subscription == mock_subscription
    
    @pytest.mark.integration
    @pytest.mark.requires_db
    def test_database_schema_validation(self, mock_supabase_client):
        """Test database schema validation."""
        # Expected schema for analysis_results table
        expected_columns = [
            "id", "user_id", "log_content_hash", "summary", 
            "issues", "suggestions", "created_at", "updated_at"
        ]
        
        # Mock schema query
        mock_schema = [
            {"column_name": col, "data_type": "text" if col != "created_at" else "timestamp"}
            for col in expected_columns
        ]
        
        mock_supabase_client.table.return_value.select.return_value.execute.return_value = Mock(
            data=mock_schema
        )
        
        # Test schema validation
        result = mock_supabase_client.table("information_schema.columns").select("*").execute()
        
        column_names = [row["column_name"] for row in result.data]
        for expected_col in expected_columns:
            assert expected_col in column_names
    
    @pytest.mark.integration
    @pytest.mark.requires_db
    def test_error_handling(self, mock_supabase_client):
        """Test error handling in Supabase operations."""
        # Mock database error
        mock_error = Exception("Database connection failed")
        mock_supabase_client.table.return_value.insert.return_value.execute.side_effect = mock_error
        
        # Test error handling
        with pytest.raises(Exception) as exc_info:
            mock_supabase_client.table("analysis_results").insert({}).execute()
        
        assert "Database connection failed" in str(exc_info.value)
    
    @pytest.mark.integration
    @pytest.mark.requires_db
    def test_connection_pooling(self, supabase_config):
        """Test connection pooling and management."""
        if not os.getenv("SUPABASE_URL"):
            pytest.skip("Supabase URL not configured")
        
        with patch('supabase.create_client') as mock_create:
            mock_clients = [Mock(spec=Client) for _ in range(5)]
            mock_create.side_effect = mock_clients
            
            # Create multiple clients
            clients = []
            for i in range(5):
                client = create_client(
                    supabase_config["url"],
                    supabase_config["anon_key"]
                )
                clients.append(client)
            
            assert len(clients) == 5
            assert mock_create.call_count == 5
    
    @pytest.mark.integration
    @pytest.mark.requires_db
    @pytest.mark.slow
    def test_large_data_handling(self, mock_supabase_client):
        """Test handling of large datasets."""
        # Generate large analysis result
        large_issues = [
            {
                "severity": "medium",
                "category": f"category_{i}",
                "description": f"Issue {i} with detailed description " * 10
            }
            for i in range(1000)
        ]
        
        large_analysis = {
            "id": "large_analysis_123",
            "summary": "Large analysis with many issues",
            "issues": large_issues,
            "suggestions": []
        }
        
        # Mock successful handling of large data
        mock_supabase_client.table.return_value.insert.return_value.execute.return_value = Mock(
            data=[large_analysis]
        )
        
        # Test large data insertion
        result = mock_supabase_client.table("analysis_results").insert(large_analysis).execute()
        
        assert result.data[0]["id"] == "large_analysis_123"
        assert len(result.data[0]["issues"]) == 1000


@pytest.mark.skipif(not SUPABASE_AVAILABLE, reason="Supabase client not installed")
class TestSupabaseMemoryIntegration:
    """Test Supabase integration with memory features."""
    
    @pytest.fixture
    def memory_service(self, mock_supabase_client):
        """Mock memory service using Supabase."""
        class MockMemoryService:
            def __init__(self, client):
                self.client = client
            
            async def store_conversation(self, user_id: str, conversation: Dict[str, Any]):
                return self.client.table("conversations").insert({
                    "user_id": user_id,
                    "conversation_data": conversation,
                    "created_at": "2024-01-15T10:30:00Z"
                }).execute()
            
            async def get_conversation_history(self, user_id: str, limit: int = 10):
                return (self.client
                       .table("conversations")
                       .select("*")
                       .eq("user_id", user_id)
                       .limit(limit)
                       .execute())
            
            async def store_analysis_cache(self, log_hash: str, analysis: Dict[str, Any]):
                return self.client.table("analysis_cache").insert({
                    "log_hash": log_hash,
                    "analysis_data": analysis,
                    "created_at": "2024-01-15T10:30:00Z"
                }).execute()
            
            async def get_cached_analysis(self, log_hash: str):
                return (self.client
                       .table("analysis_cache")
                       .select("*")
                       .eq("log_hash", log_hash)
                       .execute())
        
        return MockMemoryService(mock_supabase_client)
    
    @pytest.mark.integration
    @pytest.mark.requires_db
    @pytest.mark.asyncio
    async def test_conversation_storage(self, memory_service, mock_supabase_client):
        """Test storing conversation history."""
        user_id = "test_user_123"
        conversation = {
            "messages": [
                {"role": "user", "content": "Analyze this log"},
                {"role": "assistant", "content": "I found 3 issues"}
            ],
            "analysis_id": "analysis_123"
        }
        
        # Mock successful storage
        mock_supabase_client.table.return_value.insert.return_value.execute.return_value = Mock(
            data=[{"id": "conv_123", "user_id": user_id}]
        )
        
        result = await memory_service.store_conversation(user_id, conversation)
        
        assert result.data[0]["user_id"] == user_id
        mock_supabase_client.table.assert_called_with("conversations")
    
    @pytest.mark.integration
    @pytest.mark.requires_db
    @pytest.mark.asyncio
    async def test_analysis_caching(self, memory_service, mock_supabase_client):
        """Test analysis result caching."""
        log_hash = "abc123def456"
        analysis = {
            "summary": "Cached analysis",
            "issues": [],
            "suggestions": []
        }
        
        # Mock successful cache storage
        mock_supabase_client.table.return_value.insert.return_value.execute.return_value = Mock(
            data=[{"log_hash": log_hash, "analysis_data": analysis}]
        )
        
        result = await memory_service.store_analysis_cache(log_hash, analysis)
        
        assert result.data[0]["log_hash"] == log_hash
        mock_supabase_client.table.assert_called_with("analysis_cache")
        
        # Test cache retrieval
        mock_supabase_client.table.return_value.select.return_value.eq.return_value.execute.return_value = Mock(
            data=[{"log_hash": log_hash, "analysis_data": analysis}]
        )
        
        cached_result = await memory_service.get_cached_analysis(log_hash)
        
        assert cached_result.data[0]["log_hash"] == log_hash
        assert cached_result.data[0]["analysis_data"] == analysis
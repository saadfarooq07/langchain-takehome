"""Memory service for managing LangGraph memory operations."""

import hashlib
import json
import time
import uuid
from typing import Dict, Any, List, Optional

from langgraph.store.base import BaseStore


class MemoryService:
    """Service for managing LangGraph memory operations."""

    def __init__(self, store: BaseStore):
        self.store = store

    def _get_namespace(self, user_id: str, context_type: str) -> tuple:
        """Generate namespace for memory organization."""
        return (user_id, context_type)

    def _hash_log_content(self, log_content: str) -> str:
        """Generate consistent hash for log content."""
        return hashlib.sha256(log_content.encode()).hexdigest()[:16]

    async def store_analysis_result(
        self,
        user_id: str,
        application_name: str,
        log_content: str,
        analysis_result: Dict[str, Any],
        performance_metrics: Dict[str, Any],
    ) -> str:
        """Store analysis result for future reference.

        Args:
            user_id: User identifier
            application_name: Name of the application
            log_content: Original log content
            analysis_result: Analysis results
            performance_metrics: Performance metrics

        Returns:
            Memory ID of stored analysis
        """
        namespace = self._get_namespace(user_id, "analysis_history")

        # Extract key information for searchability
        issues_summary = []
        if "issues" in analysis_result:
            issues_summary = [
                {
                    "type": issue.get("type", "unknown"),
                    "description": issue.get("description", ""),
                    "severity": issue.get("severity", "medium"),
                }
                for issue in analysis_result["issues"]
            ]

        memory_data = {
            "application_name": application_name,
            "log_hash": self._hash_log_content(log_content),
            "log_snippet": log_content[:500],  # First 500 chars for context
            "analysis_result": analysis_result,
            "performance_metrics": performance_metrics,
            "timestamp": time.time(),
            "issues_summary": issues_summary,
            "solutions_applied": analysis_result.get("suggestions", []),
            "documentation_refs": analysis_result.get("documentation_references", []),
        }

        memory_id = str(uuid.uuid4())
        await self.store.aput(namespace, memory_id, memory_data)
        return memory_id

    async def search_similar_issues(
        self,
        user_id: str,
        application_name: str,
        current_log_content: str,
        limit: int = 5,
    ) -> List[Dict[str, Any]]:
        """Search for similar issues in user's history.

        Args:
            user_id: User identifier
            application_name: Name of the application
            current_log_content: Current log content to find similar issues for
            limit: Maximum number of results to return

        Returns:
            List of similar issues with their solutions
        """
        namespace = self._get_namespace(user_id, "analysis_history")

        # Create search query from current log
        search_query = f"application:{application_name} {current_log_content[:300]}"

        try:
            memories = await self.store.asearch(
                namespace, query=search_query, limit=limit
            )

            similar_issues = []
            for memory in memories:
                if memory.value.get("application_name") == application_name:
                    similar_issues.append(
                        {
                            "memory_id": memory.key,
                            "timestamp": memory.value.get("timestamp", 0),
                            "issues": memory.value.get("issues_summary", []),
                            "solutions": memory.value.get("solutions_applied", []),
                            "documentation_refs": memory.value.get(
                                "documentation_refs", []
                            ),
                            "log_snippet": memory.value.get("log_snippet", ""),
                            "performance_metrics": memory.value.get(
                                "performance_metrics", {}
                            ),
                        }
                    )

            return similar_issues

        except Exception as e:
            print(f"Error searching similar issues: {e}")
            return []

    async def store_application_context(
        self, user_id: str, application_name: str, context_data: Dict[str, Any]
    ) -> str:
        """Store application-specific debugging context.

        Args:
            user_id: User identifier
            application_name: Name of the application
            context_data: Context data to store

        Returns:
            Memory ID of stored context
        """
        namespace = self._get_namespace(user_id, "application_context")

        context_memory = {
            "application_name": application_name,
            "context_data": context_data,
            "common_patterns": context_data.get("common_patterns", []),
            "successful_solutions": context_data.get("successful_solutions", []),
            "frequent_issues": context_data.get("frequent_issues", []),
            "environment_info": context_data.get("environment_info", {}),
            "last_updated": time.time(),
        }

        memory_id = f"{application_name}_context"
        await self.store.aput(namespace, memory_id, context_memory)
        return memory_id

    async def get_application_context(
        self, user_id: str, application_name: str
    ) -> Dict[str, Any]:
        """Retrieve application-specific context.

        Args:
            user_id: User identifier
            application_name: Name of the application

        Returns:
            Application context data
        """
        namespace = self._get_namespace(user_id, "application_context")

        try:
            memory_id = f"{application_name}_context"
            memories = await self.store.asearch(
                namespace, query=f"application_name:{application_name}", limit=1
            )

            if memories:
                return memories[0].value
            return {}

        except Exception as e:
            print(f"Error retrieving application context: {e}")
            return {}

    async def store_user_preferences(
        self, user_id: str, preferences: Dict[str, Any]
    ) -> str:
        """Store user preferences for analysis.

        Args:
            user_id: User identifier
            preferences: User preferences

        Returns:
            Memory ID of stored preferences
        """
        namespace = self._get_namespace(user_id, "preferences")

        preferences_data = {"preferences": preferences, "updated_at": time.time()}

        memory_id = "user_preferences"
        await self.store.aput(namespace, memory_id, preferences_data)
        return memory_id

    async def get_user_preferences(self, user_id: str) -> Dict[str, Any]:
        """Retrieve user preferences.

        Args:
            user_id: User identifier

        Returns:
            User preferences
        """
        namespace = self._get_namespace(user_id, "preferences")

        try:
            memories = await self.store.asearch(namespace, query="preferences", limit=1)

            if memories:
                return memories[0].value.get("preferences", {})
            return {}

        except Exception as e:
            print(f"Error retrieving user preferences: {e}")
            return {}

    async def store_successful_solution(
        self,
        user_id: str,
        application_name: str,
        issue_type: str,
        solution: Dict[str, Any],
    ) -> str:
        """Store a successful solution for future reference.

        Args:
            user_id: User identifier
            application_name: Name of the application
            issue_type: Type of issue that was solved
            solution: Solution details

        Returns:
            Memory ID of stored solution
        """
        namespace = self._get_namespace(user_id, "solutions")

        solution_data = {
            "application_name": application_name,
            "issue_type": issue_type,
            "solution": solution,
            "timestamp": time.time(),
            "success_rate": solution.get("success_rate", 1.0),
            "usage_count": 1,
        }

        memory_id = str(uuid.uuid4())
        await self.store.aput(namespace, memory_id, solution_data)
        return memory_id

    async def get_successful_solutions(
        self,
        user_id: str,
        issue_type: str = None,
        application_name: str = None,
        limit: int = 5,
    ) -> List[Dict[str, Any]]:
        """Retrieve successful solutions.

        Args:
            user_id: User identifier
            issue_type: Optional filter by issue type
            application_name: Optional filter by application name
            limit: Maximum number of results

        Returns:
            List of successful solutions
        """
        namespace = self._get_namespace(user_id, "solutions")

        try:
            query_parts = []
            if issue_type:
                query_parts.append(f"issue_type:{issue_type}")
            if application_name:
                query_parts.append(f"application_name:{application_name}")

            query = " ".join(query_parts) if query_parts else "solution"

            memories = await self.store.asearch(namespace, query=query, limit=limit)

            solutions = []
            for memory in memories:
                solutions.append(
                    {
                        "memory_id": memory.key,
                        "application_name": memory.value.get("application_name"),
                        "issue_type": memory.value.get("issue_type"),
                        "solution": memory.value.get("solution"),
                        "timestamp": memory.value.get("timestamp"),
                        "success_rate": memory.value.get("success_rate", 1.0),
                        "usage_count": memory.value.get("usage_count", 1),
                    }
                )

            return solutions

        except Exception as e:
            print(f"Error retrieving successful solutions: {e}")
            return []

    async def update_solution_usage(
        self, user_id: str, memory_id: str, success: bool = True
    ):
        """Update solution usage statistics.

        Args:
            user_id: User identifier
            memory_id: Memory ID of the solution
            success: Whether the solution was successful
        """
        namespace = self._get_namespace(user_id, "solutions")

        try:
            memories = await self.store.asearch(
                namespace, query=f"memory_id:{memory_id}", limit=1
            )

            if memories:
                memory = memories[0]
                solution_data = memory.value.copy()

                # Update usage statistics
                current_usage = solution_data.get("usage_count", 1)
                current_success_rate = solution_data.get("success_rate", 1.0)

                new_usage = current_usage + 1
                if success:
                    new_success_rate = (
                        (current_success_rate * current_usage) + 1
                    ) / new_usage
                else:
                    new_success_rate = (
                        current_success_rate * current_usage
                    ) / new_usage

                solution_data["usage_count"] = new_usage
                solution_data["success_rate"] = new_success_rate
                solution_data["last_used"] = time.time()

                await self.store.aput(namespace, memory_id, solution_data)

        except Exception as e:
            print(f"Error updating solution usage: {e}")

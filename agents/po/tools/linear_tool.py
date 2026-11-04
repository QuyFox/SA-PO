"""Linear API Integration Tool for PO Agent.

Allows Product Owner agent to interact with Linear:
- Create and sync backlog issues
- Query team issues and project progress
- Update issue statuses
"""

import os
import json
import logging
from typing import Any, Dict, List, Optional
import httpx

logger = logging.getLogger(__name__)

LINEAR_GRAPHQL_ENDPOINT = "https://api.linear.app/graphql"


class LinearClient:
    """Client GraphQL giao tiếp với Linear API."""

    def __init__(self, api_key: Optional[str] = None, team_id: Optional[str] = None):
        self.api_key = api_key or os.getenv("LINEAR_API_KEY", "")
        self.team_id = team_id or os.getenv("LINEAR_TEAM_ID", "")
        self.headers = {
            "Content-Type": "application/json",
            "Authorization": self.api_key,
        }

    def is_configured(self) -> bool:
        """Kiểm tra xem API Key đã được cấu hình hay chưa."""
        return bool(self.api_key and self.api_key.strip())

    def _execute_query(self, query: str, variables: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Thực thi một câu query/mutation GraphQL."""
        if not self.is_configured():
            logger.warning("LINEAR_API_KEY chưa được cấu hình. Chạy ở chế độ Mock.")
            return {"mock": True, "data": {}}

        payload = {"query": query, "variables": variables or {}}
        try:
            with httpx.Client(timeout=30.0) as client:
                res = client.post(LINEAR_GRAPHQL_ENDPOINT, headers=self.headers, json=payload)
                res.raise_for_status()
                return res.json()
        except Exception as e:
            logger.error("Lỗi khi gọi Linear GraphQL API: %s", e)
            raise RuntimeError(f"Linear API error: {e}")

    def create_issue(
        self,
        title: str,
        description: str = "",
        team_id: Optional[str] = None,
        priority: int = 2,
        estimate: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Tạo issue mới trên Linear Backlog."""
        target_team = team_id or self.team_id
        if not self.is_configured():
            return {
                "id": "mock-linear-id-001",
                "title": title,
                "team_id": target_team,
                "mock": True,
            }

        mutation = """
        mutation CreateIssue($input: IssueCreateInput!) {
            issueCreate(input: $input) {
                success
                issue {
                    id
                    identifier
                    title
                    url
                }
            }
        }
        """
        variables = {
            "input": {
                "teamId": target_team,
                "title": title,
                "description": description,
                "priority": priority,
                "estimate": estimate,
            }
        }
        res = self._execute_query(mutation, variables)
        return res.get("data", {}).get("issueCreate", {}).get("issue", {})

    def sync_backlog(self, features: List[Dict[str, Any]], team_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """Đồng bộ danh sách tính năng trong Backlog lên Linear."""
        synced = []
        for feat in features:
            title = feat.get("title", "Unnamed Feature")
            desc = feat.get("description", feat.get("summary", ""))
            estimate = feat.get("estimate_story_points")
            issue = self.create_issue(title=title, description=desc, team_id=team_id, estimate=estimate)
            synced.append(issue)
        return synced

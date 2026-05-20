"""
Jira Service for fetching requirement documents from Jira.
Supports both real Jira API and mock mode for testing.
"""
from typing import Optional, Dict, Any
import httpx
import logging

from ..config import settings
from .mock_data import MockDataService

logger = logging.getLogger(__name__)


class JiraService:
    """
    Service class for fetching requirement documents from Jira.

    Supports two modes:
    - Real mode: Connects to Jira REST API using configured credentials
    - Mock mode: Returns mock data when Jira is not configured
    """

    def __init__(self):
        """
        Initialize JiraService with configuration from settings.

        Uses mock mode if any of JIRA_BASE_URL, JIRA_EMAIL, or JIRA_API_TOKEN
        is not configured.
        """
        self.base_url = settings.JIRA_BASE_URL.rstrip('/') if settings.JIRA_BASE_URL else ""
        self.email = settings.JIRA_EMAIL
        self.api_token = settings.JIRA_API_TOKEN

        # Determine if mock mode should be used
        self._mock_mode = not (self.base_url and self.email and self.api_token)

        if self._mock_mode:
            logger.info("JiraService initialized in mock mode (missing configuration)")
        else:
            logger.info(f"JiraService initialized with base_url: {self.base_url}")

    @property
    def is_mock_mode(self) -> bool:
        """Check if service is running in mock mode."""
        return self._mock_mode

    def _get_auth(self) -> tuple:
        """
        Get authentication tuple for Jira API.

        Returns:
            Tuple of (email, api_token) for basic auth
        """
        return (self.email, self.api_token)

    def get_issue(self, issue_key: str) -> Optional[Dict[str, Any]]:
        """
        Fetch issue data from Jira REST API.

        Args:
            issue_key: Jira issue key (e.g., 'PROJ-123')

        Returns:
            Issue data as dictionary, or None if not found or error occurs
        """
        if self._mock_mode:
            logger.debug(f"Mock mode: returning None for issue {issue_key}")
            return None

        url = f"{self.base_url}/rest/api/2/issue/{issue_key}"

        try:
            with httpx.Client(timeout=30.0) as client:
                response = client.get(
                    url,
                    auth=self._get_auth(),
                    headers={"Accept": "application/json"}
                )

                if response.status_code == 200:
                    return response.json()
                elif response.status_code == 404:
                    logger.warning(f"Issue not found: {issue_key}")
                    return None
                elif response.status_code == 401:
                    logger.error("Jira authentication failed - check email and API token")
                    return None
                elif response.status_code == 403:
                    logger.error(f"Access denied to issue: {issue_key}")
                    return None
                else:
                    logger.error(f"Failed to fetch issue {issue_key}: HTTP {response.status_code}")
                    return None

        except httpx.TimeoutException:
            logger.error(f"Timeout while fetching issue: {issue_key}")
            return None
        except httpx.RequestError as e:
            logger.error(f"Network error while fetching issue {issue_key}: {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error fetching issue {issue_key}: {e}")
            return None

    def get_requirement_doc(self, issue_key: str) -> str:
        """
        Get requirement document content for a Jira issue.

        Fetches issue data and extracts:
        - Summary (title)
        - Description
        - Subtasks (if any)

        Args:
            issue_key: Jira issue key (e.g., 'PROJ-123')

        Returns:
            Formatted requirement document string
        """
        # Use mock mode if configured
        if self._mock_mode:
            logger.info(f"Using mock data for requirement: {issue_key}")
            return MockDataService.get_mock_requirement(issue_key)

        # Fetch issue from Jira
        issue = self.get_issue(issue_key)

        if not issue:
            logger.warning(f"Issue not found, using mock data: {issue_key}")
            return MockDataService.get_mock_requirement(issue_key)

        try:
            # Extract issue fields
            fields = issue.get('fields', {})

            summary = fields.get('summary', 'No Summary')
            description = fields.get('description', 'No Description')
            subtasks = fields.get('subtasks', [])

            # Build requirement document
            doc_lines = [
                f"# Requirement Document: {issue_key}",
                "",
                f"## Summary",
                summary,
                "",
                "## Description",
                description if description else "[No description provided]",
                ""
            ]

            # Add subtasks if present
            if subtasks:
                doc_lines.append("## Subtasks")
                for idx, subtask in enumerate(subtasks, 1):
                    subtask_fields = subtask.get('fields', {})
                    subtask_key = subtask.get('key', f'Unknown-{idx}')
                    subtask_summary = subtask_fields.get('summary', 'No summary')
                    subtask_status = subtask_fields.get('status', {}).get('name', 'Unknown')

                    doc_lines.append(f"{idx}. [{subtask_key}] {subtask_summary} - Status: {subtask_status}")
                doc_lines.append("")

            # Add issue metadata
            issue_type = fields.get('issuetype', {}).get('name', 'Unknown')
            status = fields.get('status', {}).get('name', 'Unknown')
            priority = fields.get('priority', {}).get('name', 'Unknown')
            assignee = fields.get('assignee')
            assignee_name = assignee.get('displayName', 'Unassigned') if assignee else 'Unassigned'

            doc_lines.extend([
                "## Issue Information",
                f"- **Type**: {issue_type}",
                f"- **Status**: {status}",
                f"- **Priority**: {priority}",
                f"- **Assignee**: {assignee_name}",
                ""
            ])

            return "\n".join(doc_lines)

        except Exception as e:
            logger.error(f"Error parsing issue data for {issue_key}: {e}")
            return MockDataService.get_mock_requirement(issue_key)


jira_service = JiraService()

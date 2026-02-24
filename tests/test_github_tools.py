# tests/test_github_tools.py

"""Tests for tools/github_tools.py."""

from unittest.mock import MagicMock, patch

import pytest
from github import GithubException

from tests.mocks.mock_github import (
    create_mock_branch,
    create_mock_failed_job,
    create_mock_file_content,
    create_mock_pull_request,
    create_mock_workflow_run,
)


# ── get_workflow_run_logs ─────────────────────────────────────

class TestGetWorkflowRunLogs:
    def test_returns_failed_step_info(self, mock_github):
        mock_g, mock_repo = mock_github
        from tools.github_tools import get_workflow_run_logs

        run = create_mock_workflow_run()
        mock_repo.get_workflow_run.return_value = run

        job = create_mock_failed_job()
        run.jobs.return_value = [job]

        result = get_workflow_run_logs.invoke(
            {"repo_name": "owner/repo", "run_id": "12345"}
        )

        assert "FAILED STEP: Run tests" in result
        assert "JOB: build" in result

    def test_no_failed_jobs(self, mock_github):
        mock_g, mock_repo = mock_github
        from tools.github_tools import get_workflow_run_logs

        run = create_mock_workflow_run(conclusion="success")
        mock_repo.get_workflow_run.return_value = run

        job = MagicMock()
        job.conclusion = "success"
        job.steps = []
        run.jobs.return_value = [job]

        result = get_workflow_run_logs.invoke(
            {"repo_name": "owner/repo", "run_id": "12345"}
        )

        assert "No failed jobs" in result

    def test_github_exception(self, mock_github):
        mock_g, mock_repo = mock_github
        from tools.github_tools import get_workflow_run_logs

        mock_repo.get_workflow_run.side_effect = GithubException(
            404, {"message": "Not Found"}, None
        )

        result = get_workflow_run_logs.invoke(
            {"repo_name": "owner/repo", "run_id": "12345"}
        )

        assert "GitHub API Error" in result or "Error" in result


# ── get_file_content ──────────────────────────────────────────

class TestGetFileContent:
    def test_returns_decoded_content(self, mock_github):
        mock_g, mock_repo = mock_github
        from tools.github_tools import get_file_content

        mock_file = create_mock_file_content(content="print('hello')", path="test.py")
        mock_repo.get_contents.return_value = mock_file

        result = get_file_content.invoke(
            {"repo_name": "owner/repo", "file_path": "test.py"}
        )

        assert "print('hello')" in result

    def test_file_not_found(self, mock_github):
        mock_g, mock_repo = mock_github
        from tools.github_tools import get_file_content

        mock_repo.get_contents.side_effect = GithubException(
            404, {"message": "Not Found"}, None
        )

        result = get_file_content.invoke(
            {"repo_name": "owner/repo", "file_path": "missing.py"}
        )

        assert "Error" in result


# ── create_pull_request ───────────────────────────────────────

class TestCreatePullRequest:
    def test_creates_pr_successfully(self, mock_github):
        mock_g, mock_repo = mock_github
        from tools.github_tools import create_pull_request

        mock_pr = create_mock_pull_request()
        mock_repo.create_pull.return_value = mock_pr

        result = create_pull_request.invoke({
            "repo_name": "owner/repo",
            "title": "Fix bug",
            "body": "Fixed the issue",
            "head_branch": "auto-fix-123",
            "base_branch": "main",
        })

        assert "Pull request created" in result
        assert "pull/42" in result


# ── create_branch_and_update_file ─────────────────────────────

class TestCreateBranchAndUpdateFile:
    def test_creates_branch_and_updates(self, mock_github):
        mock_g, mock_repo = mock_github
        from tools.github_tools import create_branch_and_update_file

        mock_repo.default_branch = "main"
        mock_repo.get_branch.return_value = create_mock_branch()
        mock_repo.get_contents.return_value = create_mock_file_content()

        result = create_branch_and_update_file.invoke({
            "repo_name": "owner/repo",
            "file_path": "test.py",
            "new_content": "print('fixed')",
            "branch_name": "auto-fix-123",
            "commit_message": "Fix issue",
        })

        assert "Created branch" in result
        mock_repo.create_git_ref.assert_called_once()
        mock_repo.update_file.assert_called_once()

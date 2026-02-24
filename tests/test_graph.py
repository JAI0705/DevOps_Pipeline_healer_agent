# tests/test_graph.py

"""Tests for agent/graph.py workflow nodes."""

import json
from unittest.mock import MagicMock, patch

import pytest

from tests.mocks.mock_llm import (
    MOCK_ANALYSIS_RESPONSE,
    MOCK_FIX_RESPONSE,
    create_mock_llm_response,
)
from utils.exceptions import GitHubAPIError, HealingError


# ── fetch_logs_node ───────────────────────────────────────────

class TestFetchLogsNode:
    @patch("agent.graph.get_workflow_run_logs")
    def test_successful_fetch(self, mock_tool, empty_state):
        from agent.graph import fetch_logs_node

        mock_tool.invoke.return_value = (
            "JOB: build\n❌ FAILED STEP: Run tests\nStatus: failure"
        )

        result = fetch_logs_node(empty_state)

        assert result["current_step"] == "logs_fetched"
        assert "FAILED STEP" in result["error_logs"]

    @patch("agent.graph.get_workflow_run_logs")
    def test_error_logs_raise(self, mock_tool, empty_state):
        from agent.graph import fetch_logs_node

        mock_tool.invoke.return_value = "Error fetching logs: Not found"

        with pytest.raises((GitHubAPIError, HealingError)):
            fetch_logs_node(empty_state)


# ── analyze_error_node ────────────────────────────────────────

class TestAnalyzeErrorNode:
    @patch("agent.graph._call_llm")
    def test_successful_analysis(self, mock_call, state_with_logs):
        from agent.graph import analyze_error_node

        mock_call.return_value = MOCK_ANALYSIS_RESPONSE

        result = analyze_error_node(state_with_logs)

        assert result["current_step"] == "error_analyzed"
        assert result["failed_file"] == "requirements.txt"
        assert "requests" in result["error_analysis"].lower()

    @patch("agent.graph._call_llm")
    def test_handles_non_json_response(self, mock_call, state_with_logs):
        from agent.graph import analyze_error_node

        mock_call.return_value = "Not JSON — just a plain text analysis"

        result = analyze_error_node(state_with_logs)

        # Should fallback gracefully
        assert result["failed_file"] == "unknown"
        assert result["current_step"] == "error_analyzed"

    @patch("agent.graph._call_llm")
    def test_handles_markdown_code_block(self, mock_call, state_with_logs):
        from agent.graph import analyze_error_node

        wrapped = f"```json\n{MOCK_ANALYSIS_RESPONSE}\n```"
        mock_call.return_value = wrapped

        result = analyze_error_node(state_with_logs)

        assert result["failed_file"] == "requirements.txt"


# ── generate_fix_node ─────────────────────────────────────────

class TestGenerateFixNode:
    @patch("agent.graph.validate_fix")
    @patch("agent.graph._call_llm")
    @patch("agent.graph.get_file_content")
    def test_successful_fix_generation(
        self, mock_get_file, mock_call, mock_validate, state_with_analysis
    ):
        from agent.graph import generate_fix_node

        mock_get_file.invoke.return_value = "flask==3.0.0\n"
        mock_call.return_value = MOCK_FIX_RESPONSE
        mock_validate.invoke.return_value = {"is_valid": True, "errors": []}

        result = generate_fix_node(state_with_analysis)

        assert result["current_step"] == "fix_generated"
        assert "requests" in result["proposed_fix"]
        assert result["fix_explanation"] != ""


# ── apply_fix_node ────────────────────────────────────────────

class TestApplyFixNode:
    @patch("agent.graph.create_branch_and_update_file")
    def test_successful_apply(self, mock_tool, state_with_fix):
        from agent.graph import apply_fix_node

        mock_tool.invoke.return_value = "✓ Created branch 'auto-fix-123' and updated requirements.txt"

        result = apply_fix_node(state_with_fix)

        assert result["current_step"] == "fix_applied"
        assert result["branch_name"].startswith("auto-fix-")

    @patch("agent.graph.create_branch_and_update_file")
    def test_apply_error_raises(self, mock_tool, state_with_fix):
        from agent.graph import apply_fix_node

        mock_tool.invoke.return_value = "Error: Branch already exists"

        with pytest.raises(GitHubAPIError):
            apply_fix_node(state_with_fix)


# ── create_pr_node ────────────────────────────────────────────

class TestCreatePrNode:
    @patch("agent.graph.create_pull_request")
    def test_successful_pr(self, mock_tool, state_with_fix):
        from agent.graph import create_pr_node

        state = {**state_with_fix, "branch_name": "auto-fix-123"}
        mock_tool.invoke.return_value = "✓ Pull request created: https://github.com/test/repo/pull/42"

        result = create_pr_node(state)

        assert result["success"] is True
        assert result["current_step"] == "completed"
        assert "pull/42" in result["pr_url"]

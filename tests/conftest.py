# tests/conftest.py

"""
Shared pytest fixtures for the Pipeline Healer Agent test suite.
"""

import os
from unittest.mock import MagicMock, patch

import pytest

from agent.state import PipelineHealingState


# ── Environment Setup ─────────────────────────────────────────

@pytest.fixture(autouse=True)
def mock_env(monkeypatch):
    """Ensure tests never use real API keys."""
    monkeypatch.setenv("GROQ_API_KEY", "gsk_test_fake_key_1234567890")
    monkeypatch.setenv("GITHUB_TOKEN", "ghp_test_fake_token_1234567890")
    monkeypatch.setenv("LLM_MODEL", "llama-3.3-70b-versatile")
    monkeypatch.setenv("LLM_TEMPERATURE", "0")
    monkeypatch.setenv("LOG_LEVEL", "DEBUG")


# ── State Fixtures ────────────────────────────────────────────

@pytest.fixture
def empty_state() -> PipelineHealingState:
    """A minimal initial state for testing."""
    return PipelineHealingState(
        repo_name="testuser/test-repo",
        run_id="123456789",
        error_logs="",
        failed_file="",
        error_analysis="",
        proposed_fix="",
        fix_explanation="",
        branch_name="",
        pr_url=None,
        current_step="starting",
        success=False,
    )


@pytest.fixture
def state_with_logs(empty_state) -> PipelineHealingState:
    """State after logs have been fetched."""
    return {
        **empty_state,
        "error_logs": (
            "\n============================================================\n"
            "JOB: build\n"
            "============================================================\n"
            "\n❌ FAILED STEP: Run tests\n"
            "Status: failure\n"
            "Error: ModuleNotFoundError: No module named 'requests'\n"
        ),
        "current_step": "logs_fetched",
    }


@pytest.fixture
def state_with_analysis(state_with_logs) -> PipelineHealingState:
    """State after error analysis."""
    return {
        **state_with_logs,
        "failed_file": "requirements.txt",
        "error_analysis": "Missing 'requests' dependency in requirements.txt",
        "current_step": "error_analyzed",
    }


@pytest.fixture
def state_with_fix(state_with_analysis) -> PipelineHealingState:
    """State after fix has been generated."""
    return {
        **state_with_analysis,
        "proposed_fix": "flask==3.0.0\nrequests==2.31.0\n",
        "fix_explanation": "Added 'requests' to requirements.txt",
        "current_step": "fix_generated",
    }


@pytest.fixture
def completed_state(state_with_fix) -> PipelineHealingState:
    """Fully completed state."""
    return {
        **state_with_fix,
        "branch_name": "auto-fix-1234567890",
        "pr_url": "https://github.com/testuser/test-repo/pull/42",
        "success": True,
        "current_step": "completed",
    }


# ── Mock Fixtures ─────────────────────────────────────────────

@pytest.fixture
def mock_github():
    """Mock the PyGithub client."""
    with patch("tools.github_tools.g") as mock_g:
        mock_repo = MagicMock()
        mock_g.get_repo.return_value = mock_repo
        yield mock_g, mock_repo


@pytest.fixture
def mock_llm():
    """Mock the ChatGroq LLM."""
    with patch("agent.graph.llm") as mock:
        yield mock

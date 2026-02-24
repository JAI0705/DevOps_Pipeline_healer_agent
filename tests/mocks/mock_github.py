# tests/mocks/mock_github.py

"""Mock GitHub API responses for testing."""

from unittest.mock import MagicMock


def create_mock_workflow_run(run_id=123456, conclusion="failure"):
    """Create a mock workflow run object."""
    run = MagicMock()
    run.id = run_id
    run.name = "CI"
    run.conclusion = conclusion
    run.head_commit.message = "Test commit message"
    return run


def create_mock_failed_job():
    """Create a mock failed job with steps."""
    job = MagicMock()
    job.name = "build"
    job.conclusion = "failure"

    step_pass = MagicMock()
    step_pass.name = "Checkout"
    step_pass.conclusion = "success"

    step_fail = MagicMock()
    step_fail.name = "Run tests"
    step_fail.conclusion = "failure"

    job.steps = [step_pass, step_fail]
    return job


def create_mock_file_content(content="print('hello')", path="test.py"):
    """Create a mock GitHub file content response."""
    import base64

    file = MagicMock()
    file.content = base64.b64encode(content.encode("utf-8")).decode("utf-8")
    file.path = path
    file.sha = "abc123def456"
    return file


def create_mock_branch(name="main", sha="abc123"):
    """Create a mock branch object."""
    branch = MagicMock()
    branch.name = name
    branch.commit.sha = sha
    return branch


def create_mock_pull_request(number=42, url="https://github.com/test/repo/pull/42"):
    """Create a mock pull request object."""
    pr = MagicMock()
    pr.number = number
    pr.html_url = url
    return pr

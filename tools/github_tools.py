# tools/github_tools.py

"""
GitHub API integration tools for the Pipeline Healer Agent.

Provides LangChain tools for fetching workflow logs, reading files,
creating branches, and opening pull requests.
"""

import base64
import os

from github import Github, GithubException
from langchain_core.tools import tool
from tenacity import retry, stop_after_attempt, wait_exponential

from utils.logger import get_logger

logger = get_logger("tools.github")

# Initialize GitHub client
github_token = os.getenv("GITHUB_TOKEN")
g = Github(github_token)


@tool
@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=10),
    reraise=True,
)
def get_workflow_run_logs(repo_name: str, run_id: str) -> str:
    """
    Fetch logs from a failed GitHub Actions workflow run.

    Args:
        repo_name: Repository in format 'owner/repo'
        run_id: The workflow run ID (number from the Actions URL)

    Returns:
        The error logs from the failed run, or an error message
    """
    try:
        repo = g.get_repo(repo_name)
        run = repo.get_workflow_run(int(run_id))
        jobs = run.jobs()

        logs = []
        for job in jobs:
            if job.conclusion == "failure":
                logs.append(f"\n{'=' * 60}")
                logs.append(f"JOB: {job.name}")
                logs.append(f"{'=' * 60}")

                for step in job.steps:
                    if step.conclusion == "failure":
                        logs.append(f"\n❌ FAILED STEP: {step.name}")
                        logs.append(f"Status: {step.conclusion}")

        if not logs:
            return "No failed jobs found in this run"

        return "\n".join(logs)

    except GithubException as e:
        msg = e.data.get("message", str(e)) if hasattr(e, "data") else str(e)
        logger.error(f"GitHub API error fetching logs: {msg}")
        return f"GitHub API Error: {msg}"
    except Exception as e:
        logger.error(f"Error fetching logs: {e}")
        return f"Error fetching logs: {str(e)}"


@tool
@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=10),
    reraise=True,
)
def get_file_content(repo_name: str, file_path: str, branch: str = "main") -> str:
    """
    Get the content of a file from a GitHub repository.

    Args:
        repo_name: Repository in format 'owner/repo'
        file_path: Path to the file (e.g., '.github/workflows/ci.yml')
        branch: Branch name (default: main)

    Returns:
        The file content as a string
    """
    try:
        repo = g.get_repo(repo_name)
        file = repo.get_contents(file_path, ref=branch)

        content = base64.b64decode(file.content).decode("utf-8")
        return f"File: {file_path}\n{'=' * 60}\n{content}"

    except GithubException as e:
        msg = e.data.get("message", "File not found") if hasattr(e, "data") else str(e)
        logger.error(f"GitHub API error reading file '{file_path}': {msg}")
        return f"Error: {msg}"
    except Exception as e:
        logger.error(f"Error reading file '{file_path}': {e}")
        return f"Error: {str(e)}"


@tool
def create_pull_request(
    repo_name: str, title: str, body: str, head_branch: str, base_branch: str = "main"
) -> str:
    """
    Create a pull request with fixes.

    Args:
        repo_name: Repository in format 'owner/repo'
        title: PR title
        body: PR description (markdown)
        head_branch: Branch with the fix
        base_branch: Target branch (default: main)

    Returns:
        URL of the created PR, or an error message
    """
    try:
        repo = g.get_repo(repo_name)
        pr = repo.create_pull(
            title=title, body=body, head=head_branch, base=base_branch
        )

        logger.info(f"PR created: {pr.html_url}")
        return f"✓ Pull request created: {pr.html_url}"

    except GithubException as e:
        msg = e.data.get("message", str(e)) if hasattr(e, "data") else str(e)
        logger.error(f"Error creating PR: {msg}")
        return f"Error creating PR: {msg}"
    except Exception as e:
        logger.error(f"Error creating PR: {e}")
        return f"Error: {str(e)}"


@tool
def create_branch_and_update_file(
    repo_name: str,
    file_path: str,
    new_content: str,
    branch_name: str,
    commit_message: str,
) -> str:
    """
    Create a new branch and update a file with a fix.

    Args:
        repo_name: Repository in format 'owner/repo'
        file_path: Path to the file to update
        new_content: New file content
        branch_name: Name for the new branch
        commit_message: Commit message

    Returns:
        Success message with branch name, or an error message
    """
    try:
        repo = g.get_repo(repo_name)

        # Get default branch SHA
        default_branch = repo.default_branch
        source = repo.get_branch(default_branch)

        # Create new branch from default
        repo.create_git_ref(ref=f"refs/heads/{branch_name}", sha=source.commit.sha)
        logger.info(f"Created branch '{branch_name}' from '{default_branch}'")

        # Get current file SHA for update
        file = repo.get_contents(file_path, ref=default_branch)

        # Update file in new branch
        repo.update_file(
            path=file_path,
            message=commit_message,
            content=new_content,
            sha=file.sha,
            branch=branch_name,
        )

        logger.info(f"Updated '{file_path}' on branch '{branch_name}'")
        return f"✓ Created branch '{branch_name}' and updated {file_path}"

    except GithubException as e:
        msg = e.data.get("message", str(e)) if hasattr(e, "data") else str(e)
        logger.error(f"GitHub API error: {msg}")
        return f"Error: {msg}"
    except Exception as e:
        logger.error(f"Error creating branch/updating file: {e}")
        return f"Error: {str(e)}"


@tool
def list_recent_workflow_runs(repo_name: str, limit: int = 5) -> str:
    """
    List recent workflow runs for a repository.

    Args:
        repo_name: Repository in format 'owner/repo'
        limit: Number of runs to return (default: 5)

    Returns:
        Formatted list of recent workflow runs with their status
    """
    try:
        repo = g.get_repo(repo_name)
        runs = repo.get_workflow_runs()

        results = []
        for i, run in enumerate(runs[:limit]):
            status_emoji = "✓" if run.conclusion == "success" else "✗"
            results.append(
                f"{status_emoji} Run #{run.id} - {run.name} - "
                f"{run.conclusion} - {run.head_commit.message[:50]}"
            )

        return "\n".join(results) if results else "No workflow runs found"

    except Exception as e:
        logger.error(f"Error listing workflow runs: {e}")
        return f"Error: {str(e)}"

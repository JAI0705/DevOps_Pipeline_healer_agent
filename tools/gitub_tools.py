# tools/github_tools.py

import base64
import os

from github import Github, GithubException
from langchain_core.tools import tool

# Initialize GitHub client
github_token = os.getenv("GITHUB_TOKEN")
g = Github(github_token)


@tool
def get_workflow_run_logs(repo_name: str, run_id: str) -> str:
    """
    Fetch logs from a failed GitHub Actions workflow run.

    Args:
        repo_name: Repository in format 'owner/repo' (e.g., 'your-username/pipeline-test')
        run_id: The workflow run ID (number)

    Returns:
        The error logs from the failed run
    """
    try:
        # Get the repository
        repo = g.get_repo(repo_name)

        # Get the specific workflow run
        run = repo.get_workflow_run(int(run_id))

        # Get jobs for this run
        jobs = run.jobs()

        logs = []
        for job in jobs:
            if job.conclusion == "failure":
                logs.append(f"\n{'=' * 60}")
                logs.append(f"JOB: {job.name}")
                logs.append(f"{'=' * 60}")

                # Get steps
                for step in job.steps:
                    if step.conclusion == "failure":
                        logs.append(f"\n❌ FAILED STEP: {step.name}")
                        logs.append(f"Status: {step.conclusion}")

        if not logs:
            return "No failed jobs found in this run"

        return "\n".join(logs)

    except GithubException as e:
        return f"GitHub API Error: {e.data.get('message', str(e))}"
    except Exception as e:
        return f"Error fetching logs: {str(e)}"


@tool
def get_file_content(repo_name: str, file_path: str, branch: str = "main") -> str:
    """
    Get the content of a file from a GitHub repository.

    Args:
        repo_name: Repository in format 'owner/repo'
        file_path: Path to the file (e.g., '.github/workflows/ci.yml')
        branch: Branch name (default: main)

    Returns:
        The file content
    """
    try:
        repo = g.get_repo(repo_name)
        file = repo.get_contents(file_path, ref=branch)

        # Decode base64 content
        content = base64.b64decode(file.content).decode("utf-8")

        return f"File: {file_path}\n{'=' * 60}\n{content}"

    except GithubException as e:
        return f"Error: {e.data.get('message', 'File not found')}"
    except Exception as e:
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
        body: PR description
        head_branch: Branch with the fix
        base_branch: Target branch (default: main)

    Returns:
        URL of the created PR
    """
    try:
        repo = g.get_repo(repo_name)
        ## Create pull is a build in github function
        pr = repo.create_pull(
            title=title, body=body, head=head_branch, base=base_branch
        )

        return f"✓ Pull request created: {pr.html_url}"

    except GithubException as e:
        return f"Error creating PR: {e.data.get('message', str(e))}"
    except Exception as e:
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
        Success message with branch name
    """
    try:
        repo = g.get_repo(repo_name)

        # Get default branch
        default_branch = repo.default_branch
        source = repo.get_branch(default_branch)

        # Create new branch
        repo.create_git_ref(ref=f"refs/heads/{branch_name}", sha=source.commit.sha)

        # Get current file
        file = repo.get_contents(file_path, ref=default_branch)

        # Update file in new branch
        repo.update_file(
            path=file_path,
            message=commit_message,
            content=new_content,
            sha=file.sha,
            branch=branch_name,
        )

        return f"✓ Created branch '{branch_name}' and updated {file_path}"

    except GithubException as e:
        return f"Error: {e.data.get('message', str(e))}"
    except Exception as e:
        return f"Error: {str(e)}"


@tool
def list_recent_workflow_runs(repo_name: str, limit: int = 5) -> str:
    """
    List recent workflow runs for a repository.

    Args:
        repo_name: Repository in format 'owner/repo'
        limit: Number of runs to return (default: 5)

    Returns:
        List of recent workflow runs with their status
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
        return f"Error: {str(e)}"

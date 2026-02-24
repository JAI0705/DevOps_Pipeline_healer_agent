# utils/validators.py

"""Input validation utilities for the Pipeline Healer Agent."""

import os
import re

from utils.exceptions import ValidationError


def validate_repo_name(repo_name: str) -> str:
    """
    Validate that a repository name follows the 'owner/repo' format.

    Returns the cleaned repo name.
    Raises ValidationError if invalid.
    """
    repo_name = repo_name.strip()

    if not repo_name:
        raise ValidationError("Repository name cannot be empty", field="repo_name")

    pattern = r"^[a-zA-Z0-9._-]+/[a-zA-Z0-9._-]+$"
    if not re.match(pattern, repo_name):
        raise ValidationError(
            f"Invalid repository format: '{repo_name}'. Expected 'owner/repo-name'",
            field="repo_name",
        )

    return repo_name


def validate_run_id(run_id: str) -> str:
    """
    Validate that a workflow run ID is numeric.

    Returns the cleaned run ID.
    Raises ValidationError if invalid.
    """
    run_id = run_id.strip()

    if not run_id:
        raise ValidationError("Run ID cannot be empty", field="run_id")

    if not run_id.isdigit():
        raise ValidationError(
            f"Invalid run ID: '{run_id}'. Must be a numeric value",
            field="run_id",
        )

    return run_id


def validate_env_vars() -> dict[str, str]:
    """
    Validate that all required environment variables are set.

    Returns a dict of validated env vars.
    Raises ValidationError if any are missing.
    """
    required_vars = {
        "GROQ_API_KEY": os.getenv("GROQ_API_KEY"),
        "GITHUB_TOKEN": os.getenv("GITHUB_TOKEN"),
    }

    missing = [name for name, value in required_vars.items() if not value]

    if missing:
        raise ValidationError(
            f"Missing required environment variables: {', '.join(missing)}. "
            "Copy .env.example to .env and fill in your values.",
            field="env_vars",
        )

    return {name: value for name, value in required_vars.items() if value is not None}


def validate_inputs(repo_name: str, run_id: str) -> tuple[str, str]:
    """
    Validate all inputs before starting the healing workflow.

    Returns (validated_repo_name, validated_run_id).
    Raises ValidationError on any invalid input.
    """
    # Validate env vars first
    validate_env_vars()

    # Validate user inputs
    repo_name = validate_repo_name(repo_name)
    run_id = validate_run_id(run_id)

    return repo_name, run_id

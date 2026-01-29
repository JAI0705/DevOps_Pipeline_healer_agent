# agent/state.py

from typing import List, Optional, TypedDict


class PipelineHealingState(TypedDict):
    """State that flows through the healing workflow."""

    # Input
    repo_name: str  # e.g., "username/pipeline-test"
    run_id: str  # Workflow run ID

    # Processing
    error_logs: str  # Raw error logs
    failed_file: str  # Which file caused the error
    error_analysis: str  # AI's understanding of the error

    # Fix generation
    proposed_fix: str  # The code fix
    fix_explanation: str  # Why this fix should work

    # Execution
    branch_name: str  # Branch created with fix
    pr_url: Optional[str]  # Pull request URL

    # Status tracking
    current_step: str  # Current step in workflow
    success: bool  # Did we fix it?

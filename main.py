# main.py

"""
Pipeline Healer Agent — CLI entry point.

Usage:
    python main.py
"""

from dotenv import load_dotenv

load_dotenv()

from agent.graph import healing_graph
from utils.exceptions import HealingError, ValidationError
from utils.logger import generate_correlation_id, get_logger
from utils.validators import validate_inputs

logger = get_logger("main")


def heal_pipeline(repo_name: str, run_id: str) -> dict | None:
    """
    Main function to heal a failed pipeline.

    Args:
        repo_name: GitHub repo in format 'owner/repo'
        run_id: The workflow run ID that failed

    Returns:
        Final state dict with PR URL, branch name, and fix details,
        or None if healing failed.
    """
    correlation_id = generate_correlation_id()

    print("🚀 Pipeline Healer Agent Starting...")
    print("=" * 60)
    print(f"Repository:     {repo_name}")
    print(f"Run ID:         {run_id}")
    print(f"Correlation ID: {correlation_id}")
    print("=" * 60)

    # ── Validate inputs ───────────────────────────────────────
    try:
        repo_name, run_id = validate_inputs(repo_name, run_id)
    except ValidationError as e:
        print(f"\n❌ Validation error: {e}")
        logger.error(f"Validation failed: {e}", extra={"correlation_id": correlation_id})
        return None

    # ── Run the healing workflow ──────────────────────────────
    initial_state = {
        "repo_name": repo_name,
        "run_id": run_id,
        "error_logs": "",
        "failed_file": "",
        "error_analysis": "",
        "proposed_fix": "",
        "fix_explanation": "",
        "branch_name": "",
        "pr_url": None,
        "current_step": "starting",
        "success": False,
    }

    try:
        final_state = healing_graph.invoke(initial_state)

        print("\n" + "=" * 60)
        if final_state.get("success"):
            print("✅ HEALING COMPLETE!")
        else:
            print("⚠️  HEALING FINISHED WITH WARNINGS")
        print("=" * 60)
        print(f"Pull Request: {final_state.get('pr_url', 'N/A')}")
        print(f"Branch:       {final_state.get('branch_name', 'N/A')}")
        print("\n📋 Summary:")
        print(f"  Error:  {final_state.get('error_analysis', 'N/A')[:100]}...")
        print(f"  Fix:    {final_state.get('fix_explanation', 'N/A')[:100]}...")

        logger.info(
            "Healing complete",
            extra={
                "correlation_id": correlation_id,
                "step": "completed",
            },
        )

        return final_state

    except HealingError as e:
        print(f"\n❌ Healing failed at step [{e.step}]: {e}")
        logger.error(
            f"Healing failed: {e}",
            extra={"correlation_id": correlation_id, "step": e.step},
        )
        return None

    except Exception as e:
        print(f"\n❌ Unexpected error during healing: {e}")
        logger.error(
            f"Unexpected error: {e}",
            extra={"correlation_id": correlation_id},
            exc_info=True,
        )
        return None


if __name__ == "__main__":
    print("Enter your repository (format: username/repo-name):")
    repo = input("> ").strip()

    print("\nEnter the failed workflow run ID:")
    print("(You can find this in the GitHub Actions URL)")
    run_id = input("> ").strip()

    heal_pipeline(repo, run_id)

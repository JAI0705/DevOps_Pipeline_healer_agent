# action_entrypoint.py

"""
GitHub Action entry point for Pipeline Healer.

Reads inputs from environment variables (set by GitHub Actions runtime),
runs the healing workflow, and writes outputs for downstream steps.
"""

import json
import os
import sys

from dotenv import load_dotenv

load_dotenv()

from agent.graph import healing_graph
from utils.logger import get_logger

logger = get_logger("action")

# ── GitHub Actions output helpers ─────────────────────────────

GITHUB_OUTPUT = os.getenv("GITHUB_OUTPUT", "")


def set_output(name: str, value: str):
    """Write an output variable for GitHub Actions."""
    if GITHUB_OUTPUT:
        with open(GITHUB_OUTPUT, "a") as f:
            f.write(f"{name}={value}\n")
    # Also print for visibility in logs
    print(f"::set-output name={name}::{value}")


def log_group(title: str):
    """Start a log group in GitHub Actions."""
    print(f"::group::{title}")


def log_endgroup():
    """End a log group in GitHub Actions."""
    print("::endgroup::")


# ── Resolve inputs ────────────────────────────────────────────

def get_inputs() -> tuple[str, str]:
    """
    Resolve repo_name and run_id from action inputs or the event payload.

    Priority:
      1. Explicit inputs (INPUT_REPO / INPUT_RUN_ID)
      2. workflow_run event payload (auto-detected)
    """
    repo_name = os.getenv("INPUT_REPO", "").strip()
    run_id = os.getenv("INPUT_RUN_ID", "").strip()

    # If not set explicitly, try to read from the GitHub event payload
    if not repo_name or not run_id:
        event_path = os.getenv("GITHUB_EVENT_PATH", "")
        if event_path and os.path.exists(event_path):
            with open(event_path) as f:
                event = json.load(f)

            # workflow_run event
            if "workflow_run" in event:
                if not repo_name:
                    repo_name = event.get("repository", {}).get("full_name", "")
                if not run_id:
                    run_id = str(event["workflow_run"].get("id", ""))

                conclusion = event["workflow_run"].get("conclusion", "")
                if conclusion != "failure":
                    print(f"⏭️  Workflow run conclusion is '{conclusion}', not 'failure'. Skipping.")
                    set_output("success", "skipped")
                    sys.exit(0)

    # Fallback to GITHUB_REPOSITORY
    if not repo_name:
        repo_name = os.getenv("GITHUB_REPOSITORY", "")

    if not repo_name or not run_id:
        print("::error::Could not determine repo_name and run_id.")
        print("Either set them as inputs or trigger this action via a workflow_run event.")
        sys.exit(1)

    return repo_name, run_id


# ── Main ──────────────────────────────────────────────────────

def main():
    print("🔧 Pipeline Healer Action Starting...")
    print("=" * 60)

    repo_name, run_id = get_inputs()
    print(f"📦 Repository: {repo_name}")
    print(f"🔢 Run ID:     {run_id}")
    print("=" * 60)

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
        log_group("📥 Fetching logs & analyzing error")
        final_state = healing_graph.invoke(initial_state)
        log_endgroup()

        success = final_state.get("success", False)
        pr_url = final_state.get("pr_url", "")
        branch = final_state.get("branch_name", "")
        analysis = final_state.get("error_analysis", "")

        # Set outputs for downstream steps
        set_output("success", str(success).lower())
        set_output("pr-url", pr_url or "")
        set_output("branch-name", branch)
        set_output("error-analysis", analysis[:500])  # Truncate for safety

        print("\n" + "=" * 60)
        if success:
            print("✅ HEALING COMPLETE!")
            print(f"📝 Pull Request: {pr_url}")
            print(f"🌿 Branch: {branch}")
        else:
            print("⚠️  Healing finished but may not have fully succeeded")
        print("=" * 60)

    except Exception as e:
        print(f"::error::Healing failed: {e}")
        set_output("success", "false")
        set_output("error-analysis", str(e)[:500])
        sys.exit(1)


if __name__ == "__main__":
    main()

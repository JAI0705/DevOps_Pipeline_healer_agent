# main.py

from dotenv import load_dotenv

from agent.graph import healing_graph

load_dotenv()


def heal_pipeline(repo_name: str, run_id: str):
    """
    Main function to heal a failed pipeline.

    Args:
        repo_name: GitHub repo in format 'owner/repo'
        run_id: The workflow run ID that failed
    """
    print("🚀 Pipeline Healer Agent Starting...")
    print("=" * 60)
    print(f"Repository: {repo_name}")
    print(f"Run ID: {run_id}")
    print("=" * 60)

    # Initial state
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

    # Run the healing workflow
    try:
        final_state = healing_graph.invoke(initial_state)

        print("\n" + "=" * 60)
        print("✅ HEALING COMPLETE!")
        print("=" * 60)
        print(f"Pull Request: {final_state.get('pr_url', 'N/A')}")
        print(f"Branch: {final_state.get('branch_name', 'N/A')}")
        print("\n📋 Summary:")
        print(f"Error: {final_state.get('error_analysis', 'N/A')[:100]}...")
        print(f"Fix: {final_state.get('fix_explanation', 'N/A')[:100]}...")

        return final_state

    except Exception as e:
        print(f"\n❌ Error during healing: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    # Example usage
    # Replace with your actual repo and run ID

    print("Enter your repository (format: username/repo-name):")
    repo = input("> ").strip()

    print("\nEnter the failed workflow run ID:")
    print("(You can find this in the GitHub Actions URL)")
    run_id = input("> ").strip()

    heal_pipeline(repo, run_id)

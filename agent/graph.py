# agent/graph.py

import os

from dotenv import load_dotenv
from langchain_core.messages import SystemMessage
from langchain_groq import ChatGroq
from langgraph.graph import END, StateGraph
from tools.github_tools import (
    create_branch_and_update_file,
    create_pull_request,
    get_file_content,
    get_workflow_run_logs,
)

from agent.state import PipelineHealingState

load_dotenv()

# Initialize LLM
llm = ChatGroq(
    model="llama-3.3-70b-versatile", temperature=0, api_key=os.getenv("GROQ_API_KEY")
)


def fetch_logs_node(state: PipelineHealingState) -> PipelineHealingState:
    """Step 1: Fetch the error logs from GitHub."""
    print("📥 Fetching logs from GitHub...")

    logs = get_workflow_run_logs.invoke(
        {"repo_name": state["repo_name"], "run_id": state["run_id"]}
    )

    return {**state, "error_logs": logs, "current_step": "logs_fetched"}


def analyze_error_node(state: PipelineHealingState) -> PipelineHealingState:
    """Step 2: Analyze what went wrong."""
    print("🔍 Analyzing error...")

    prompt = f"""
You are an expert DevOps engineer. Analyze this GitHub Actions error:

{state["error_logs"]}

Provide:
1. What type of error is this? (dependency, syntax, configuration, etc.)
2. Which file likely has the problem?
3. What specifically went wrong?

Be concise and specific. Format as JSON:
{{
    "error_type": "...",
    "failed_file": "...",
    "analysis": "..."
}}
"""

    response = llm.invoke(prompt)

    # Parse the response (in production, use proper JSON parsing)
    import json

    try:
        analysis = json.loads(response.content)
    except:
        analysis = {
            "error_type": "unknown",
            "failed_file": "unknown",
            "analysis": response.content,
        }

    return {
        **state,
        "failed_file": analysis.get("failed_file", "unknown"),
        "error_analysis": analysis.get("analysis", ""),
        "current_step": "error_analyzed",
    }


def generate_fix_node(state: PipelineHealingState) -> PipelineHealingState:
    """Step 3: Generate a fix for the error."""
    print("🔧 Generating fix...")

    # First, get the current file content
    file_content = get_file_content.invoke(
        {"repo_name": state["repo_name"], "file_path": state["failed_file"]}
    )

    prompt = f"""
You are an expert DevOps engineer. Here's a failed file and error analysis:

FILE CONTENT:
{file_content}

ERROR ANALYSIS:
{state["error_analysis"]}

ERROR LOGS:
{state["error_logs"]}

Generate a fixed version of the file. Provide:
1. The complete corrected file content
2. Explanation of what you changed and why

Format as JSON:
{{
    "fixed_content": "...",
    "explanation": "..."
}}
"""

    response = llm.invoke(prompt)

    import json

    try:
        fix = json.loads(response.content)
    except:
        fix = {"fixed_content": response.content, "explanation": "Auto-generated fix"}

    return {
        **state,
        "proposed_fix": fix.get("fixed_content", ""),
        "fix_explanation": fix.get("explanation", ""),
        "current_step": "fix_generated",
    }


def apply_fix_node(state: PipelineHealingState) -> PipelineHealingState:
    """Step 4: Create a branch and apply the fix."""
    print("✍️ Applying fix to new branch...")

    # Create unique branch name
    import time

    branch_name = f"auto-fix-{int(time.time())}"

    # Create branch and update file
    result = create_branch_and_update_file.invoke(
        {
            "repo_name": state["repo_name"],
            "file_path": state["failed_file"],
            "new_content": state["proposed_fix"],
            "branch_name": branch_name,
            "commit_message": f"🤖 Auto-fix: {state['error_analysis'][:50]}",
        }
    )

    print(result)

    return {**state, "branch_name": branch_name, "current_step": "fix_applied"}


def create_pr_node(state: PipelineHealingState) -> PipelineHealingState:
    """Step 5: Create a pull request with the fix."""
    print("📝 Creating pull request...")

    pr_body = f"""
## 🤖 Automated Fix

**Error Analysis:**
{state["error_analysis"]}

**What I Changed:**
{state["fix_explanation"]}

**File Fixed:**
`{state["failed_file"]}`

---
*This PR was automatically created by Pipeline Healer Agent*
*Please review the changes before merging!*
"""

    result = create_pull_request.invoke(
        {
            "repo_name": state["repo_name"],
            "title": f"🤖 Auto-fix: {state['failed_file']}",
            "body": pr_body,
            "head_branch": state["branch_name"],
            "base_branch": "main",
        }
    )

    print(result)

    return {**state, "pr_url": result, "success": True, "current_step": "completed"}


def create_healing_graph():
    """Create the complete healing workflow."""

    workflow = StateGraph(PipelineHealingState)

    # Add all nodes
    workflow.add_node("fetch_logs", fetch_logs_node)
    workflow.add_node("analyze_error", analyze_error_node)
    workflow.add_node("generate_fix", generate_fix_node)
    workflow.add_node("apply_fix", apply_fix_node)
    workflow.add_node("create_pr", create_pr_node)

    # Define the flow
    workflow.set_entry_point("fetch_logs")
    workflow.add_edge("fetch_logs", "analyze_error")
    workflow.add_edge("analyze_error", "generate_fix")
    workflow.add_edge("generate_fix", "apply_fix")
    workflow.add_edge("apply_fix", "create_pr")
    workflow.add_edge("create_pr", END)

    return workflow.compile()


# Create the graph
healing_graph = create_healing_graph()

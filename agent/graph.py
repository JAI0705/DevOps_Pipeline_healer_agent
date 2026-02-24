# agent/graph.py

"""
LangGraph healing workflow — the core 5‑node pipeline.

Flow: fetch_logs → analyze_error → generate_fix → apply_fix → create_pr
"""

import json
import os
import time

from dotenv import load_dotenv
from langchain_groq import ChatGroq
from langgraph.graph import END, StateGraph
from tenacity import retry, stop_after_attempt, wait_exponential

from agent.state import PipelineHealingState
from tools.code_fixer import validate_fix
from tools.github_tools import (
    create_branch_and_update_file,
    create_pull_request,
    get_file_content,
    get_workflow_run_logs,
)
from utils.exceptions import GitHubAPIError, HealingError, LLMError
from utils.logger import get_logger, log_step

load_dotenv()

# ── Logger ────────────────────────────────────────────────────
logger = get_logger("agent.graph")

# ── LLM Initialization ───────────────────────────────────────
_model = os.getenv("LLM_MODEL", "llama-3.3-70b-versatile")
_temperature = float(os.getenv("LLM_TEMPERATURE", "0"))

llm = ChatGroq(
    model=_model,
    temperature=_temperature,
    api_key=os.getenv("GROQ_API_KEY"),
)


# ── Node 1: Fetch Logs ───────────────────────────────────────

def fetch_logs_node(state: PipelineHealingState) -> PipelineHealingState:
    """Step 1: Fetch the error logs from GitHub Actions."""
    with log_step(logger, "fetch_logs", repo_name=state["repo_name"]):
        try:
            logs = get_workflow_run_logs.invoke(
                {"repo_name": state["repo_name"], "run_id": state["run_id"]}
            )

            if not logs or logs.startswith("Error") or logs.startswith("GitHub API Error"):
                raise GitHubAPIError(
                    f"Failed to fetch logs: {logs}",
                    step="fetch_logs",
                )

            return {**state, "error_logs": logs, "current_step": "logs_fetched"}

        except GitHubAPIError:
            raise
        except Exception as e:
            raise HealingError(
                f"Unexpected error fetching logs: {e}",
                step="fetch_logs",
                details={"repo": state["repo_name"], "run_id": state["run_id"]},
            ) from e


# ── Node 2: Analyze Error ────────────────────────────────────

@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
def _call_llm(prompt: str) -> str:
    """Call the LLM with retry logic."""
    response = llm.invoke(prompt)
    return response.content


def analyze_error_node(state: PipelineHealingState) -> PipelineHealingState:
    """Step 2: Use LLM to analyze what went wrong."""
    with log_step(logger, "analyze_error"):
        try:
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
            raw = _call_llm(prompt)

            try:
                analysis = json.loads(raw)
            except json.JSONDecodeError:
                # Try to extract JSON from markdown code block
                if "```" in raw:
                    json_block = raw.split("```")[1]
                    if json_block.startswith("json"):
                        json_block = json_block[4:]
                    analysis = json.loads(json_block.strip())
                else:
                    logger.warning(
                        "LLM response was not valid JSON, using raw text",
                        extra={"step": "analyze_error"},
                    )
                    analysis = {
                        "error_type": "unknown",
                        "failed_file": "unknown",
                        "analysis": raw,
                    }

            return {
                **state,
                "failed_file": analysis.get("failed_file", "unknown"),
                "error_analysis": analysis.get("analysis", ""),
                "current_step": "error_analyzed",
            }

        except json.JSONDecodeError as e:
            raise LLMError(
                f"Could not parse LLM analysis response: {e}",
                raw_response=raw,
                step="analyze_error",
            ) from e
        except Exception as e:
            raise HealingError(
                f"Error during analysis: {e}", step="analyze_error"
            ) from e


# ── Node 3: Generate Fix ─────────────────────────────────────

def generate_fix_node(state: PipelineHealingState) -> PipelineHealingState:
    """Step 3: Generate a fix for the identified error."""
    with log_step(logger, "generate_fix"):
        try:
            # Fetch current file content
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
            raw = _call_llm(prompt)

            try:
                fix = json.loads(raw)
            except json.JSONDecodeError:
                # Try to extract JSON from markdown code block
                if "```" in raw:
                    json_block = raw.split("```")[1]
                    if json_block.startswith("json"):
                        json_block = json_block[4:]
                    fix = json.loads(json_block.strip())
                else:
                    fix = {
                        "fixed_content": raw,
                        "explanation": "Auto-generated fix",
                    }

            proposed_fix = fix.get("fixed_content", "")
            fix_explanation = fix.get("explanation", "")

            # Validate the fix if we can
            try:
                validation = validate_fix.invoke({
                    "original_content": file_content,
                    "fixed_content": proposed_fix,
                    "file_path": state["failed_file"],
                })

                if not validation.get("is_valid", True):
                    logger.warning(
                        f"Fix validation found issues: {validation.get('errors')}",
                        extra={"step": "generate_fix"},
                    )
            except Exception:
                logger.debug(
                    "Fix validation skipped (non-critical)",
                    extra={"step": "generate_fix"},
                )

            return {
                **state,
                "proposed_fix": proposed_fix,
                "fix_explanation": fix_explanation,
                "current_step": "fix_generated",
            }

        except Exception as e:
            raise HealingError(
                f"Error generating fix: {e}", step="generate_fix"
            ) from e


# ── Node 4: Apply Fix ────────────────────────────────────────

def apply_fix_node(state: PipelineHealingState) -> PipelineHealingState:
    """Step 4: Create a branch and commit the fix."""
    with log_step(logger, "apply_fix"):
        try:
            branch_name = f"auto-fix-{int(time.time())}"

            result = create_branch_and_update_file.invoke(
                {
                    "repo_name": state["repo_name"],
                    "file_path": state["failed_file"],
                    "new_content": state["proposed_fix"],
                    "branch_name": branch_name,
                    "commit_message": f"🤖 Auto-fix: {state['error_analysis'][:50]}",
                }
            )

            if result.startswith("Error"):
                raise GitHubAPIError(result, step="apply_fix")

            logger.info(result, extra={"step": "apply_fix"})

            return {
                **state,
                "branch_name": branch_name,
                "current_step": "fix_applied",
            }

        except GitHubAPIError:
            raise
        except Exception as e:
            raise HealingError(
                f"Error applying fix: {e}", step="apply_fix"
            ) from e


# ── Node 5: Create PR ────────────────────────────────────────

def create_pr_node(state: PipelineHealingState) -> PipelineHealingState:
    """Step 5: Create a pull request with the fix."""
    with log_step(logger, "create_pr"):
        try:
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

            if result.startswith("Error"):
                raise GitHubAPIError(result, step="create_pr")

            logger.info(result, extra={"step": "create_pr"})

            return {
                **state,
                "pr_url": result,
                "success": True,
                "current_step": "completed",
            }

        except GitHubAPIError:
            raise
        except Exception as e:
            raise HealingError(
                f"Error creating PR: {e}", step="create_pr"
            ) from e


# ── Graph Construction ────────────────────────────────────────

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


# Create the graph instance
healing_graph = create_healing_graph()

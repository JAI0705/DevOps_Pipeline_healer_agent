# tools/code_fixer.py

"""
Code fix validation and application utilities.

Provides tools to validate generated fixes before applying them,
score fix confidence, and preview diffs.
"""

import ast
import difflib
import json
from typing import Optional

import yaml
from langchain_core.tools import tool


@tool
def validate_fix(original_content: str, fixed_content: str, file_path: str) -> dict:
    """
    Validate that a proposed fix is syntactically correct.

    Args:
        original_content: The original file content before fix
        fixed_content: The proposed fixed file content
        file_path: Path to the file (used to determine file type)

    Returns:
        Dictionary with validation results:
        - is_valid: bool
        - file_type: str
        - errors: list of error messages (empty if valid)
        - diff: unified diff between original and fixed
    """
    file_type = _detect_file_type(file_path)
    errors = []

    # Syntax validation based on file type
    if file_type == "python":
        errors = _validate_python(fixed_content)
    elif file_type == "yaml":
        errors = _validate_yaml(fixed_content)
    elif file_type == "json":
        errors = _validate_json(fixed_content)

    # Generate diff
    diff = _generate_diff(original_content, fixed_content, file_path)

    return {
        "is_valid": len(errors) == 0,
        "file_type": file_type,
        "errors": errors,
        "diff": diff,
    }


@tool
def score_fix_confidence(
    error_analysis: str,
    fix_explanation: str,
    original_content: str,
    fixed_content: str,
) -> dict:
    """
    Score the confidence of a proposed fix based on heuristics.

    Args:
        error_analysis: The AI's error analysis
        fix_explanation: The AI's explanation of the fix
        original_content: The original file content
        fixed_content: The proposed fixed content

    Returns:
        Dictionary with confidence score and reasoning:
        - score: float (0.0 to 1.0)
        - reasoning: list of factors that influenced the score
    """
    score = 1.0
    reasoning = []

    # Factor 1: Size of change — very large changes are risky
    original_lines = original_content.strip().splitlines()
    fixed_lines = fixed_content.strip().splitlines()

    if len(original_lines) > 0:
        change_ratio = abs(len(fixed_lines) - len(original_lines)) / len(
            original_lines
        )
        if change_ratio > 0.5:
            score -= 0.3
            reasoning.append(
                f"Large change ratio ({change_ratio:.1%}): fix modifies >50% of lines"
            )
        elif change_ratio > 0.2:
            score -= 0.1
            reasoning.append(
                f"Moderate change ratio ({change_ratio:.1%}): fix modifies >20% of lines"
            )
        else:
            reasoning.append(
                f"Small change ratio ({change_ratio:.1%}): targeted fix"
            )

    # Factor 2: Fix explanation quality — empty or very short is a red flag
    if not fix_explanation or len(fix_explanation.strip()) < 20:
        score -= 0.2
        reasoning.append("Fix explanation is missing or too short")
    else:
        reasoning.append("Fix explanation is detailed")

    # Factor 3: Fix is not empty
    if not fixed_content or len(fixed_content.strip()) == 0:
        score = 0.0
        reasoning.append("Fixed content is empty — cannot apply")

    # Factor 4: Check if fix actually changed something
    if original_content.strip() == fixed_content.strip():
        score -= 0.4
        reasoning.append("Fix content is identical to original — nothing changed")

    # Clamp score
    score = max(0.0, min(1.0, score))

    return {
        "score": round(score, 2),
        "reasoning": reasoning,
        "recommendation": (
            "apply" if score >= 0.6 else "review" if score >= 0.3 else "reject"
        ),
    }


@tool
def preview_diff(
    original_content: str, fixed_content: str, file_path: str
) -> str:
    """
    Generate a human-readable unified diff of the proposed fix.

    Args:
        original_content: The original file content
        fixed_content: The proposed fixed content
        file_path: Path to the file (for display)

    Returns:
        Unified diff as a formatted string
    """
    return _generate_diff(original_content, fixed_content, file_path)


# ── Internal helpers ──────────────────────────────────────────


def _detect_file_type(file_path: str) -> str:
    """Detect file type from path extension."""
    path_lower = file_path.lower()
    if path_lower.endswith(".py"):
        return "python"
    elif path_lower.endswith((".yml", ".yaml")):
        return "yaml"
    elif path_lower.endswith(".json"):
        return "json"
    elif path_lower.endswith((".js", ".ts", ".jsx", ".tsx")):
        return "javascript"
    elif path_lower.endswith((".sh", ".bash")):
        return "shell"
    elif path_lower.endswith("Dockerfile") or "dockerfile" in path_lower:
        return "dockerfile"
    else:
        return "unknown"


def _validate_python(content: str) -> list[str]:
    """Check Python syntax by parsing the AST."""
    errors = []
    try:
        ast.parse(content)
    except SyntaxError as e:
        errors.append(f"Python syntax error at line {e.lineno}: {e.msg}")
    return errors


def _validate_yaml(content: str) -> list[str]:
    """Check YAML syntax."""
    errors = []
    try:
        yaml.safe_load(content)
    except yaml.YAMLError as e:
        errors.append(f"YAML syntax error: {e}")
    return errors


def _validate_json(content: str) -> list[str]:
    """Check JSON syntax."""
    errors = []
    try:
        json.loads(content)
    except json.JSONDecodeError as e:
        errors.append(f"JSON syntax error at line {e.lineno}: {e.msg}")
    return errors


def _generate_diff(
    original: str, fixed: str, file_path: str, context_lines: int = 3
) -> str:
    """Generate a unified diff between original and fixed content."""
    original_lines = original.splitlines(keepends=True)
    fixed_lines = fixed.splitlines(keepends=True)

    diff = difflib.unified_diff(
        original_lines,
        fixed_lines,
        fromfile=f"a/{file_path}",
        tofile=f"b/{file_path}",
        n=context_lines,
    )
    return "".join(diff) or "(no changes)"

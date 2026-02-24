# tests/mocks/mock_llm.py

"""Mock LLM responses for deterministic testing."""

import json
from unittest.mock import MagicMock


MOCK_ANALYSIS_RESPONSE = json.dumps({
    "error_type": "dependency",
    "failed_file": "requirements.txt",
    "analysis": "Missing 'requests' package in requirements.txt",
})

MOCK_FIX_RESPONSE = json.dumps({
    "fixed_content": "flask==3.0.0\nrequests==2.31.0\npytest==7.4.0\n",
    "explanation": "Added missing 'requests' dependency to requirements.txt",
})

MOCK_ANALYSIS_RESPONSE_SYNTAX = json.dumps({
    "error_type": "syntax",
    "failed_file": "app.py",
    "analysis": "SyntaxError: unexpected indent on line 15",
})

MOCK_FIX_RESPONSE_SYNTAX = json.dumps({
    "fixed_content": "def hello():\n    print('hello')\n\nhello()\n",
    "explanation": "Fixed indentation error on line 15 in app.py",
})


def create_mock_llm_response(content: str) -> MagicMock:
    """Create a mock LLM response with the given content."""
    response = MagicMock()
    response.content = content
    return response


def create_mock_llm(response_content: str | None = None) -> MagicMock:
    """
    Create a mock LLM that returns a fixed response.

    If no response_content is given, defaults to the analysis response.
    """
    mock = MagicMock()
    content = response_content or MOCK_ANALYSIS_RESPONSE
    mock.invoke.return_value = create_mock_llm_response(content)
    return mock

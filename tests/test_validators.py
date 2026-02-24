# tests/test_validators.py

"""Tests for utils/validators.py."""

import os

import pytest

from utils.exceptions import ValidationError
from utils.validators import validate_env_vars, validate_inputs, validate_repo_name, validate_run_id


# ── validate_repo_name ────────────────────────────────────────

class TestValidateRepoName:
    def test_valid_repo_name(self):
        assert validate_repo_name("owner/repo") == "owner/repo"

    def test_valid_repo_name_with_dashes(self):
        assert validate_repo_name("my-user/my-repo") == "my-user/my-repo"

    def test_valid_repo_name_with_dots(self):
        assert validate_repo_name("user.name/repo.name") == "user.name/repo.name"

    def test_strips_whitespace(self):
        assert validate_repo_name("  owner/repo  ") == "owner/repo"

    def test_empty_string_raises(self):
        with pytest.raises(ValidationError, match="cannot be empty"):
            validate_repo_name("")

    def test_whitespace_only_raises(self):
        with pytest.raises(ValidationError, match="cannot be empty"):
            validate_repo_name("   ")

    def test_missing_slash_raises(self):
        with pytest.raises(ValidationError, match="Invalid repository format"):
            validate_repo_name("just-a-repo")

    def test_multiple_slashes_raises(self):
        with pytest.raises(ValidationError, match="Invalid repository format"):
            validate_repo_name("a/b/c")

    def test_special_characters_raises(self):
        with pytest.raises(ValidationError, match="Invalid repository format"):
            validate_repo_name("owner/repo name")


# ── validate_run_id ───────────────────────────────────────────

class TestValidateRunId:
    def test_valid_numeric(self):
        assert validate_run_id("123456789") == "123456789"

    def test_strips_whitespace(self):
        assert validate_run_id("  42  ") == "42"

    def test_empty_raises(self):
        with pytest.raises(ValidationError, match="cannot be empty"):
            validate_run_id("")

    def test_non_numeric_raises(self):
        with pytest.raises(ValidationError, match="Must be a numeric"):
            validate_run_id("abc123")

    def test_mixed_alpha_numeric_raises(self):
        with pytest.raises(ValidationError, match="Must be a numeric"):
            validate_run_id("123abc")

    def test_negative_number_raises(self):
        with pytest.raises(ValidationError, match="Must be a numeric"):
            validate_run_id("-123")


# ── validate_env_vars ─────────────────────────────────────────

class TestValidateEnvVars:
    def test_all_present(self):
        """The mock_env fixture sets these, so this should pass."""
        result = validate_env_vars()
        assert "GROQ_API_KEY" in result
        assert "GITHUB_TOKEN" in result

    def test_missing_groq_key(self, monkeypatch):
        monkeypatch.delenv("GROQ_API_KEY", raising=False)
        with pytest.raises(ValidationError, match="GROQ_API_KEY"):
            validate_env_vars()

    def test_missing_github_token(self, monkeypatch):
        monkeypatch.delenv("GITHUB_TOKEN", raising=False)
        with pytest.raises(ValidationError, match="GITHUB_TOKEN"):
            validate_env_vars()

    def test_missing_both(self, monkeypatch):
        monkeypatch.delenv("GROQ_API_KEY", raising=False)
        monkeypatch.delenv("GITHUB_TOKEN", raising=False)
        with pytest.raises(ValidationError, match="GROQ_API_KEY"):
            validate_env_vars()


# ── validate_inputs (integration) ─────────────────────────────

class TestValidateInputs:
    def test_valid_inputs(self):
        repo, run = validate_inputs("owner/repo", "123456")
        assert repo == "owner/repo"
        assert run == "123456"

    def test_invalid_repo_raises(self):
        with pytest.raises(ValidationError):
            validate_inputs("bad-repo", "123456")

    def test_invalid_run_id_raises(self):
        with pytest.raises(ValidationError):
            validate_inputs("owner/repo", "not-a-number")

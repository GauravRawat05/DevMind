"""Tests for the GitHub repository fetcher service."""
from __future__ import annotations

import pytest
from backend.services.github_service import parse_github_url


# ---------------------------------------------------------------------------
# parse_github_url tests
# ---------------------------------------------------------------------------

class TestParseGithubUrl:
    """Tests for URL parsing and validation."""

    def test_https_url(self) -> None:
        owner, repo = parse_github_url("https://github.com/fastapi/fastapi")
        assert owner == "fastapi"
        assert repo == "fastapi"

    def test_https_url_with_git_suffix(self) -> None:
        owner, repo = parse_github_url("https://github.com/pallets/flask.git")
        assert owner == "pallets"
        assert repo == "flask"

    def test_url_without_scheme(self) -> None:
        owner, repo = parse_github_url("github.com/django/django")
        assert owner == "django"
        assert repo == "django"

    def test_url_with_trailing_slash(self) -> None:
        owner, repo = parse_github_url("https://github.com/owner/repo/")
        assert owner == "owner"
        assert repo == "repo"

    def test_url_with_www(self) -> None:
        owner, repo = parse_github_url("https://www.github.com/owner/repo")
        assert owner == "owner"
        assert repo == "repo"

    def test_url_with_whitespace(self) -> None:
        owner, repo = parse_github_url("  https://github.com/owner/repo  ")
        assert owner == "owner"
        assert repo == "repo"

    def test_invalid_url_raises_value_error(self) -> None:
        with pytest.raises(ValueError, match="Invalid GitHub URL"):
            parse_github_url("https://gitlab.com/owner/repo")

    def test_empty_url_raises_value_error(self) -> None:
        with pytest.raises(ValueError, match="Invalid GitHub URL"):
            parse_github_url("")

    def test_non_github_url_raises(self) -> None:
        with pytest.raises(ValueError):
            parse_github_url("https://bitbucket.org/owner/repo")

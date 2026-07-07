"""GitHub repository download and extraction service.

Provides async functionality to clone public GitHub repositories by downloading
their zipball, extracting source files, and returning filtered text content
suitable for indexing and analysis.
"""

from __future__ import annotations

import io
import logging
import os
import re
import tempfile
import zipfile
from pathlib import Path

import httpx

from backend.core.config import settings

logger = logging.getLogger("devmind.github_service")

# Directories to skip during file tree walk
SKIP_DIRS: set[str] = {
    ".git",
    ".github",
    ".venv",
    "__pycache__",
    "node_modules",
    ".next",
}

# Binary / non-text file extensions to exclude
BINARY_EXTENSIONS: set[str] = {
    ".png", ".jpg", ".jpeg", ".gif", ".svg", ".ico",
    ".pdf", ".zip", ".tar", ".gz",
    ".exe", ".dll", ".so", ".dylib",
    ".pyc", ".pyo", ".whl", ".egg",
    ".mp3", ".mp4", ".wav", ".avi", ".mov",
    ".ttf", ".woff", ".woff2", ".eot",
}

# Maximum file size in bytes (500 KB)
MAX_FILE_SIZE: int = 500 * 1024

# GitHub API download timeout (seconds)
DOWNLOAD_TIMEOUT: int = 120

_GITHUB_URL_PATTERN = re.compile(
    r"(?:https?://)?(?:www\.)?github\.com/(?P<owner>[^/]+)/(?P<repo>[^/.]+)(?:\.git)?/?$"
)


def parse_github_url(url: str) -> tuple[str, str]:
    """Parse a GitHub URL and extract the owner and repository name.

    Supported formats:
        - ``https://github.com/owner/repo``
        - ``https://github.com/owner/repo.git``
        - ``github.com/owner/repo``

    Args:
        url: The GitHub repository URL to parse.

    Returns:
        A ``(owner, repo)`` tuple.

    Raises:
        ValueError: If the URL does not match any supported GitHub format.
    """
    match = _GITHUB_URL_PATTERN.match(url.strip())
    if not match:
        raise ValueError(
            f"Invalid GitHub URL: '{url}'. "
            "Expected format: https://github.com/owner/repo"
        )
    return match.group("owner"), match.group("repo")


def _is_text_file(file_path: Path) -> bool:
    """Return True if the file should be treated as a text source file."""
    return file_path.suffix.lower() not in BINARY_EXTENSIONS


def _should_skip_dir(dir_name: str) -> bool:
    """Return True if a directory should be excluded from the walk."""
    return dir_name in SKIP_DIRS or dir_name.startswith(".")


async def fetch_repository(repo_url: str) -> list[dict]:
    """Download a public GitHub repository and return its text source files.

    Downloads the default-branch zipball from the GitHub API, extracts it
    into a temporary directory, walks the file tree while filtering out
    binary files, hidden directories, and oversized files, then returns
    a list of dictionaries containing the relative path and decoded content
    of every qualifying source file.

    Args:
        repo_url: A GitHub repository URL (see :func:`parse_github_url`
                  for accepted formats).

    Returns:
        A list of dicts, each with ``path`` (relative file path) and
        ``content`` (the decoded text content of the file).

    Raises:
        ValueError: If *repo_url* cannot be parsed.
        httpx.HTTPStatusError: If the GitHub API returns an error status.
    """
    owner, repo = parse_github_url(repo_url)
    api_url = f"https://api.github.com/repos/{owner}/{repo}/zipball"

    headers: dict[str, str] = {"Accept": "application/vnd.github+json"}
    if settings.GITHUB_TOKEN:
        headers["Authorization"] = f"Bearer {settings.GITHUB_TOKEN}"

    logger.info("Downloading repository %s/%s from %s", owner, repo, api_url)

    async with httpx.AsyncClient(
        follow_redirects=True, timeout=DOWNLOAD_TIMEOUT
    ) as client:
        response = await client.get(api_url, headers=headers)
        response.raise_for_status()

    zip_bytes = response.content
    logger.info(
        "Downloaded %.2f MB for %s/%s",
        len(zip_bytes) / (1024 * 1024),
        owner,
        repo,
    )

    files: list[dict] = []

    with tempfile.TemporaryDirectory() as tmp_dir:
        with zipfile.ZipFile(io.BytesIO(zip_bytes)) as zf:
            zf.extractall(tmp_dir)

        # GitHub zipballs contain a single top-level directory
        # (e.g. ``owner-repo-<sha>/``).  Detect it so we can produce
        # clean relative paths.
        extracted_items = os.listdir(tmp_dir)
        root_dir = (
            os.path.join(tmp_dir, extracted_items[0])
            if len(extracted_items) == 1
            and os.path.isdir(os.path.join(tmp_dir, extracted_items[0]))
            else tmp_dir
        )

        for dirpath, dirnames, filenames in os.walk(root_dir):
            # Prune directories in-place so os.walk skips them
            dirnames[:] = [
                d for d in dirnames if not _should_skip_dir(d)
            ]

            for filename in filenames:
                full_path = Path(dirpath) / filename

                # Skip binary extensions
                if not _is_text_file(full_path):
                    continue

                # Skip oversized files
                try:
                    if full_path.stat().st_size > MAX_FILE_SIZE:
                        logger.debug(
                            "Skipping large file: %s (%d bytes)",
                            full_path.name,
                            full_path.stat().st_size,
                        )
                        continue
                except OSError:
                    continue

                # Read and decode content
                try:
                    content = full_path.read_text(encoding="utf-8", errors="ignore")
                except Exception as exc:
                    logger.warning("Failed to read %s: %s", full_path, exc)
                    continue

                relative_path = str(full_path.relative_to(root_dir)).replace("\\", "/")
                files.append({"path": relative_path, "content": content})

    logger.info(
        "Extracted %d text files from %s/%s", len(files), owner, repo
    )
    return files

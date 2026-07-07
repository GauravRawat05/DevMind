"""Mock S3 service implementation using the local filesystem.

Saves files to local_s3_mock/<bucket_name>/<key> to mimic AWS S3 behavior
without requiring active cloud credentials or network connection.
"""

from __future__ import annotations

import os
import logging
from pathlib import Path
from backend.core.config import settings

logger = logging.getLogger("devmind.services.s3_service")

# Base directory for the local S3 mock storage
BASE_DIR = Path(__file__).resolve().parent.parent.parent
S3_MOCK_ROOT = BASE_DIR / "local_s3_mock"


class StorageService:
    """Mock storage service that mimics AWS S3 using the local filesystem."""

    def __init__(self, bucket_name: str | None = None) -> None:
        self.bucket_name = bucket_name or settings.AWS_S3_BUCKET
        self.bucket_path = S3_MOCK_ROOT / self.bucket_name
        
        # Ensure the bucket folder exists
        try:
            self.bucket_path.mkdir(parents=True, exist_ok=True)
            logger.info("Local S3 mock initialized at: %s", self.bucket_path)
        except Exception as e:
            logger.error("Failed to create local S3 mock directory: %s", e)

    def upload_file(self, key: str, content: bytes | str) -> str:
        """Upload content to the mock bucket.

        Args:
            key: File path/key in the bucket.
            content: Bytes or string to write.

        Returns:
            The local file URL or simulated S3 path.
        """
        file_path = self.bucket_path / key
        
        # Ensure directory for the key exists
        file_path.parent.mkdir(parents=True, exist_ok=True)
        
        mode = "wb" if isinstance(content, bytes) else "w"
        encoding = None if isinstance(content, bytes) else "utf-8"
        
        with open(file_path, mode, encoding=encoding) as f:
            f.write(content)
            
        logger.info("Uploaded key '%s' to mock S3 bucket '%s'", key, self.bucket_name)
        return f"s3://{self.bucket_name}/{key}"

    def download_file(self, key: str) -> bytes:
        """Download bytes from the mock bucket by key.

        Args:
            key: File path/key in the bucket.

        Returns:
            File content in bytes.

        Raises:
            FileNotFoundError: If the key does not exist.
        """
        file_path = self.bucket_path / key
        if not file_path.exists():
            logger.error("File key '%s' not found in mock S3 bucket '%s'", key, self.bucket_name)
            raise FileNotFoundError(f"Key '{key}' not found in bucket '{self.bucket_name}'")
            
        with open(file_path, "rb") as f:
            return f.read()

    def delete_file(self, key: str) -> bool:
        """Delete a file from the mock bucket by key.

        Args:
            key: File path/key in the bucket.

        Returns:
            True if deleted, False otherwise.
        """
        file_path = self.bucket_path / key
        if file_path.exists():
            try:
                file_path.unlink()
                logger.info("Deleted key '%s' from mock S3 bucket '%s'", key, self.bucket_name)
                return True
            except Exception as e:
                logger.error("Failed to delete key '%s' from mock S3: %s", key, e)
                return False
        return False

    def list_files(self, prefix: str = "") -> list[str]:
        """List file keys matching a prefix.

        Args:
            prefix: Prefix to filter keys.

        Returns:
            List of matching keys.
        """
        keys = []
        prefix_path = self.bucket_path / prefix
        
        if not self.bucket_path.exists():
            return []
            
        for root, _, files in os.walk(self.bucket_path):
            for file in files:
                full_path = Path(root) / file
                # Get relative path from bucket root as key
                key = str(full_path.relative_to(self.bucket_path)).replace("\\", "/")
                if key.startswith(prefix):
                    keys.append(key)
        return keys

    def get_download_url(self, key: str) -> str:
        """Return a simulated URL for retrieving the file.

        Args:
            key: File path/key in the bucket.

        Returns:
            Download endpoint URL.
        """
        return f"/api/download/{self.bucket_name}/{key}"


# Global instance of storage service
storage_service = StorageService()

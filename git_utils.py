"""
Git Utilities for CCDA

Provides reusable utilities for git operations:
- Cloning repositories
- Sparse checkout for efficient partial clones
- Repository updates

Copyright (c) 2026 Oscar Valenzuela <oscar.valenzuela.b@gmail.com>
All Rights Reserved.
"""
import logging
import os
import shutil
from pathlib import Path
from typing import List, Optional
import subprocess

logger = logging.getLogger(__name__)


class GitRepository:
    """
    Git repository manager with sparse checkout support.

    Features:
    - Efficient partial clones using sparse checkout
    - Automatic cleanup and update
    - Reusable for multiple repository operations

    Example:
        ```python
        repo = GitRepository(
            url="https://github.com/github/advisory-database",
            local_path="/tmp/advisory-db"
        )

        # Clone only specific paths
        repo.clone(sparse_paths=["advisories/github-reviewed/npm/"])

        # Update existing clone
        repo.pull()

        # Cleanup
        repo.cleanup()
        ```
    """

    def __init__(self, url: str, local_path: str):
        """
        Initialize git repository manager.

        Args:
            url: Git repository URL (https or git protocol)
            local_path: Local path for cloning
        """
        self.url = url
        self.local_path = Path(local_path)
        self.exists = self.local_path.exists() and (self.local_path / ".git").exists()

    def clone(
        self,
        sparse_paths: Optional[List[str]] = None,
        depth: Optional[int] = 1,
        branch: str = "main"
    ) -> None:
        """
        Clone repository with optional sparse checkout.

        Args:
            sparse_paths: List of paths to checkout (None = full clone)
            depth: Clone depth (1 = shallow, None = full history)
            branch: Branch to clone

        Raises:
            subprocess.CalledProcessError: If git commands fail
        """
        if self.exists:
            logger.info(f"Repository already exists at {self.local_path}")
            return

        logger.info(f"Cloning {self.url} to {self.local_path}")

        # Create parent directory
        self.local_path.parent.mkdir(parents=True, exist_ok=True)

        # Build clone command
        cmd = ["git", "clone"]

        if depth:
            cmd.extend(["--depth", str(depth)])

        cmd.extend(["--branch", branch])

        # Use sparse checkout if paths specified
        if sparse_paths:
            cmd.append("--no-checkout")

        cmd.extend([self.url, str(self.local_path)])

        # Execute clone
        self._run_command(cmd)

        # Configure sparse checkout if needed
        if sparse_paths:
            self._configure_sparse_checkout(sparse_paths)

        self.exists = True
        logger.info(f"Successfully cloned repository")

    def _configure_sparse_checkout(self, paths: List[str]) -> None:
        """
        Configure sparse checkout for specified paths.

        Args:
            paths: List of paths to include in sparse checkout
        """
        logger.info(f"Configuring sparse checkout for {len(paths)} path(s)")

        # Enable sparse checkout
        self._run_command(
            ["git", "config", "core.sparseCheckout", "true"],
            cwd=self.local_path
        )

        # Write sparse checkout paths
        sparse_file = self.local_path / ".git" / "info" / "sparse-checkout"
        sparse_file.parent.mkdir(parents=True, exist_ok=True)

        with open(sparse_file, "w") as f:
            for path in paths:
                f.write(f"{path}\n")

        # Checkout files
        self._run_command(
            ["git", "checkout"],
            cwd=self.local_path
        )

        logger.info(f"Sparse checkout configured: {paths}")

    def pull(self) -> None:
        """
        Update existing repository.

        Raises:
            ValueError: If repository doesn't exist
            subprocess.CalledProcessError: If git pull fails
        """
        if not self.exists:
            raise ValueError(f"Repository does not exist at {self.local_path}")

        logger.info(f"Pulling latest changes for {self.local_path}")

        self._run_command(
            ["git", "pull"],
            cwd=self.local_path
        )

        logger.info("Successfully pulled latest changes")

    def cleanup(self) -> None:
        """
        Remove cloned repository.
        """
        if not self.exists:
            logger.info(f"Repository does not exist at {self.local_path}")
            return

        logger.info(f"Cleaning up repository at {self.local_path}")

        try:
            shutil.rmtree(self.local_path)
            self.exists = False
            logger.info("Repository cleaned up successfully")
        except Exception as e:
            logger.error(f"Failed to cleanup repository: {e}")
            raise

    def get_file_paths(self, pattern: str = "**/*.json") -> List[Path]:
        """
        Get list of files matching pattern in repository.

        Args:
            pattern: Glob pattern for matching files

        Returns:
            List of Path objects matching pattern
        """
        if not self.exists:
            return []

        return list(self.local_path.glob(pattern))

    def _run_command(
        self,
        cmd: List[str],
        cwd: Optional[Path] = None
    ) -> subprocess.CompletedProcess:
        """
        Run git command and handle errors.

        Args:
            cmd: Command and arguments
            cwd: Working directory (None = current dir)

        Returns:
            CompletedProcess result

        Raises:
            subprocess.CalledProcessError: If command fails
        """
        try:
            result = subprocess.run(
                cmd,
                cwd=cwd,
                check=True,
                capture_output=True,
                text=True
            )
            return result
        except subprocess.CalledProcessError as e:
            logger.error(f"Git command failed: {' '.join(cmd)}")
            logger.error(f"Error output: {e.stderr}")
            raise


def clone_github_advisory_database(
    local_path: str,
    ecosystems: Optional[List[str]] = None
) -> GitRepository:
    """
    Convenience function to clone GitHub Advisory Database.

    Note: GHSA advisories are organized by year/month, not ecosystem.
    Structure: advisories/github-reviewed/YEAR/MONTH/GHSA-ID/GHSA-ID.json
    Ecosystem filtering happens during JSON processing, not during clone.

    Args:
        local_path: Local path for cloning
        ecosystems: List of ecosystems to filter (filtering done in code, not git)
                   Examples: ['npm', 'pypi', 'maven']

    Returns:
        GitRepository instance

    Example:
        ```python
        # Clone all reviewed advisories (ecosystem filtering done later)
        repo = clone_github_advisory_database(
            local_path="/tmp/ghsa",
            ecosystems=["npm", "pypi"]  # Used for filtering, not sparse checkout
        )

        # Get all JSON files
        files = repo.get_file_paths("**/*.json")
        ```
    """
    repo = GitRepository(
        url="https://github.com/github/advisory-database",
        local_path=local_path
    )

    # Clone all reviewed advisories (organized by year, not ecosystem)
    # Sparse checkout by ecosystem isn't possible due to directory structure
    sparse_paths = ["advisories/github-reviewed/"]

    repo.clone(sparse_paths=sparse_paths, depth=1, branch="main")

    return repo

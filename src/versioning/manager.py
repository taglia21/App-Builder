"""Version history manager for projects."""
import hashlib
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

from .snapshot import Snapshot, SnapshotMetadata

logger = logging.getLogger(__name__)


class VersionManager:
    """Manages version history and snapshots for projects."""

    def __init__(self, storage_path: Optional[Path] = None):
        """Initialize version manager.
        
        Args:
            storage_path: Directory to store version snapshots
        """
        self.storage_path = storage_path or Path("/tmp/launchforge_versions")
        self.storage_path.mkdir(parents=True, exist_ok=True)

    def _get_project_dir(self, project_id: str) -> Path:
        """Get storage directory for a project."""
        project_dir = self.storage_path / project_id
        project_dir.mkdir(parents=True, exist_ok=True)
        return project_dir

    def _get_snapshot_path(self, project_id: str, version: int) -> Path:
        """Get file path for a specific snapshot."""
        return self._get_project_dir(project_id) / f"v{version}.json"

    def _hash_files(self, files: Dict[str, str]) -> str:
        """Generate hash of file contents."""
        content = json.dumps(files, sort_keys=True)
        return hashlib.sha256(content.encode()).hexdigest()

    async def create_snapshot(
        self,
        project_id: str,
        files: Dict[str, str],
        message: str,
        author: str = "system"
    ) -> Snapshot:
        """Create a new snapshot of the project.
        
        Args:
            project_id: Unique project identifier
            files: Dictionary mapping file paths to content
            message: Commit message describing changes
            author: Author of the snapshot
            
        Returns:
            Created snapshot
        """
        # Get next version number
        snapshots = await self.list_snapshots(project_id)
        next_version = len(snapshots) + 1

        # Create snapshot
        metadata = SnapshotMetadata(
            version=next_version,
            message=message,
            created_at=datetime.now(),
            author=author,
            file_hash=self._hash_files(files)
        )
        snapshot = Snapshot(metadata=metadata, files=files)

        # Save to disk
        snapshot_path = self._get_snapshot_path(project_id, next_version)
        with open(snapshot_path, 'w') as f:
            json.dump(snapshot.to_dict(), f, indent=2)

        logger.info(f"Created snapshot v{next_version} for project {project_id}")
        return snapshot

    async def list_snapshots(self, project_id: str) -> List[Snapshot]:
        """List all snapshots for a project.
        
        Args:
            project_id: Unique project identifier
            
        Returns:
            List of snapshots ordered by version
        """
        project_dir = self._get_project_dir(project_id)
        snapshots = []

        for snapshot_file in sorted(project_dir.glob("v*.json")):
            try:
                with open(snapshot_file, 'r') as f:
                    data = json.load(f)
                    snapshots.append(Snapshot.from_dict(data))
            except Exception as e:
                logger.error(f"Error loading snapshot {snapshot_file}: {e}")

        return sorted(snapshots, key=lambda s: s.metadata.version)

    async def get_snapshot(self, project_id: str, version: int) -> Optional[Snapshot]:
        """Get a specific snapshot by version.
        
        Args:
            project_id: Unique project identifier
            version: Version number to retrieve
            
        Returns:
            Snapshot or None if not found
        """
        snapshot_path = self._get_snapshot_path(project_id, version)
        
        if not snapshot_path.exists():
            return None

        try:
            with open(snapshot_path, 'r') as f:
                data = json.load(f)
                return Snapshot.from_dict(data)
        except Exception as e:
            logger.error(f"Error loading snapshot v{version}: {e}")
            return None

    async def restore_snapshot(self, project_id: str, version: int) -> Optional[Snapshot]:
        """Restore project to a specific snapshot version.
        
        Args:
            project_id: Unique project identifier
            version: Version number to restore
            
        Returns:
            Restored snapshot or None if not found
        """
        snapshot = await self.get_snapshot(project_id, version)
        
        if snapshot is None:
            logger.error(f"Snapshot v{version} not found for project {project_id}")
            return None

        logger.info(f"Restored project {project_id} to v{version}")
        return snapshot

    async def get_latest_snapshot(self, project_id: str) -> Optional[Snapshot]:
        """Get the most recent snapshot for a project.
        
        Args:
            project_id: Unique project identifier
            
        Returns:
            Latest snapshot or None if no snapshots exist
        """
        snapshots = await self.list_snapshots(project_id)
        return snapshots[-1] if snapshots else None

    async def delete_snapshot(self, project_id: str, version: int) -> bool:
        """Delete a specific snapshot.
        
        Args:
            project_id: Unique project identifier
            version: Version number to delete
            
        Returns:
            True if deleted, False if not found
        """
        snapshot_path = self._get_snapshot_path(project_id, version)
        
        if not snapshot_path.exists():
            return False

        try:
            snapshot_path.unlink()
            logger.info(f"Deleted snapshot v{version} for project {project_id}")
            return True
        except Exception as e:
            logger.error(f"Error deleting snapshot v{version}: {e}")
            return False

    async def compare_snapshots(
        self,
        project_id: str,
        version1: int,
        version2: int
    ) -> Dict[str, List[str]]:
        """Compare two snapshots and return differences.
        
        Args:
            project_id: Unique project identifier
            version1: First version to compare
            version2: Second version to compare
            
        Returns:
            Dictionary with 'added', 'modified', and 'deleted' file lists
        """
        snap1 = await self.get_snapshot(project_id, version1)
        snap2 = await self.get_snapshot(project_id, version2)

        if snap1 is None or snap2 is None:
            return {"added": [], "modified": [], "deleted": []}

        files1 = set(snap1.files.keys())
        files2 = set(snap2.files.keys())

        added = list(files2 - files1)
        deleted = list(files1 - files2)
        modified = [
            f for f in (files1 & files2)
            if snap1.files[f] != snap2.files[f]
        ]

        return {
            "added": added,
            "modified": modified,
            "deleted": deleted,
        }

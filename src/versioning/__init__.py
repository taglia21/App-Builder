"""Version history system for project snapshots and restoration."""

from .manager import VersionManager
from .snapshot import Snapshot, SnapshotMetadata

__all__ = ["VersionManager", "Snapshot", "SnapshotMetadata"]

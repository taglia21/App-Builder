"""Snapshot models for version history."""
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, Optional


@dataclass
class SnapshotMetadata:
    """Metadata for a snapshot version."""
    version: int
    message: str
    created_at: datetime
    author: str = "system"
    file_hash: Optional[str] = None

    def to_dict(self) -> Dict:
        """Convert to dictionary."""
        return {
            "version": self.version,
            "message": self.message,
            "created_at": self.created_at.isoformat(),
            "author": self.author,
            "file_hash": self.file_hash,
        }

    @classmethod
    def from_dict(cls, data: Dict) -> "SnapshotMetadata":
        """Create from dictionary."""
        created_at = data["created_at"]
        if isinstance(created_at, str):
            created_at = datetime.fromisoformat(created_at)
        
        return cls(
            version=data["version"],
            message=data["message"],
            created_at=created_at,
            author=data.get("author", "system"),
            file_hash=data.get("file_hash"),
        )


@dataclass
class Snapshot:
    """A snapshot of project files at a specific version."""
    metadata: SnapshotMetadata
    files: Dict[str, str] = field(default_factory=dict)

    def to_dict(self) -> Dict:
        """Convert snapshot to dictionary."""
        return {
            **self.metadata.to_dict(),
            "files": self.files,
        }

    @classmethod
    def from_dict(cls, data: Dict) -> "Snapshot":
        """Create snapshot from dictionary."""
        metadata = SnapshotMetadata.from_dict(data)
        return cls(
            metadata=metadata,
            files=data.get("files", {}),
        )

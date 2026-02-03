"""Tests for version history system."""
import pytest
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime
from pathlib import Path
import tempfile
import json

from src.versioning.manager import VersionManager
from src.versioning.snapshot import Snapshot, SnapshotMetadata


class TestSnapshot:
    """Test Snapshot model."""

    def test_snapshot_creation(self):
        """Test creating a snapshot."""
        metadata = SnapshotMetadata(
            version=1,
            message="Initial version",
            created_at=datetime.now(),
            author="test_user"
        )
        
        files = {"main.py": "print('hello')", "config.json": "{}"}
        snapshot = Snapshot(metadata=metadata, files=files)
        
        assert snapshot.metadata.version == 1
        assert snapshot.metadata.message == "Initial version"
        assert len(snapshot.files) == 2
        assert "main.py" in snapshot.files

    def test_snapshot_to_dict(self):
        """Test snapshot serialization."""
        metadata = SnapshotMetadata(
            version=1,
            message="Test",
            created_at=datetime(2024, 1, 1, 12, 0, 0),
            author="user1"
        )
        snapshot = Snapshot(metadata=metadata, files={"test.py": "pass"})
        
        data = snapshot.to_dict()
        
        assert data["version"] == 1
        assert data["message"] == "Test"
        assert "files" in data
        assert data["author"] == "user1"

    def test_snapshot_from_dict(self):
        """Test snapshot deserialization."""
        data = {
            "version": 2,
            "message": "Second version",
            "created_at": "2024-01-01T12:00:00",
            "author": "user2",
            "files": {"app.py": "import os"}
        }
        
        snapshot = Snapshot.from_dict(data)
        
        assert snapshot.metadata.version == 2
        assert snapshot.metadata.message == "Second version"
        assert snapshot.metadata.author == "user2"
        assert "app.py" in snapshot.files


class TestVersionManager:
    """Test VersionManager functionality."""

    @pytest.fixture
    def temp_storage(self):
        """Create a temporary storage directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Path(tmpdir)

    @pytest.fixture
    def version_manager(self, temp_storage):
        """Create a VersionManager instance."""
        return VersionManager(storage_path=temp_storage)

    @pytest.mark.asyncio
    async def test_create_snapshot(self, version_manager):
        """Test creating a snapshot."""
        project_id = "test_project_1"
        files = {"main.py": "print('v1')", "README.md": "# Test"}
        message = "Initial commit"
        
        snapshot = await version_manager.create_snapshot(
            project_id=project_id,
            files=files,
            message=message,
            author="test_user"
        )
        
        assert snapshot.metadata.version == 1
        assert snapshot.metadata.message == message
        assert snapshot.files == files

    @pytest.mark.asyncio
    async def test_create_multiple_snapshots(self, version_manager):
        """Test creating multiple snapshots increments version."""
        project_id = "test_project_2"
        
        snapshot1 = await version_manager.create_snapshot(
            project_id=project_id,
            files={"main.py": "v1"},
            message="Version 1"
        )
        
        snapshot2 = await version_manager.create_snapshot(
            project_id=project_id,
            files={"main.py": "v2"},
            message="Version 2"
        )
        
        assert snapshot1.metadata.version == 1
        assert snapshot2.metadata.version == 2

    @pytest.mark.asyncio
    async def test_list_snapshots(self, version_manager):
        """Test listing all snapshots for a project."""
        project_id = "test_project_3"
        
        await version_manager.create_snapshot(
            project_id=project_id,
            files={"a.py": "v1"},
            message="First"
        )
        
        await version_manager.create_snapshot(
            project_id=project_id,
            files={"a.py": "v2"},
            message="Second"
        )
        
        snapshots = await version_manager.list_snapshots(project_id)
        
        assert len(snapshots) == 2
        assert snapshots[0].metadata.version == 1
        assert snapshots[1].metadata.version == 2

    @pytest.mark.asyncio
    async def test_get_snapshot(self, version_manager):
        """Test retrieving a specific snapshot."""
        project_id = "test_project_4"
        
        await version_manager.create_snapshot(
            project_id=project_id,
            files={"main.py": "v1"},
            message="Version 1"
        )
        
        await version_manager.create_snapshot(
            project_id=project_id,
            files={"main.py": "v2"},
            message="Version 2"
        )
        
        snapshot = await version_manager.get_snapshot(project_id, version=1)
        
        assert snapshot is not None
        assert snapshot.metadata.version == 1
        assert snapshot.files["main.py"] == "v1"

    @pytest.mark.asyncio
    async def test_restore_snapshot(self, version_manager):
        """Test restoring a project to a previous snapshot."""
        project_id = "test_project_5"
        
        await version_manager.create_snapshot(
            project_id=project_id,
            files={"main.py": "v1", "config.json": "{}"},
            message="Version 1"
        )
        
        await version_manager.create_snapshot(
            project_id=project_id,
            files={"main.py": "v2", "config.json": "{}", "new.py": "new"},
            message="Version 2"
        )
        
        restored = await version_manager.restore_snapshot(project_id, version=1)
        
        assert restored.metadata.version == 1
        assert restored.files["main.py"] == "v1"
        assert "new.py" not in restored.files

    @pytest.mark.asyncio
    async def test_get_latest_snapshot(self, version_manager):
        """Test getting the latest snapshot."""
        project_id = "test_project_6"
        
        await version_manager.create_snapshot(
            project_id=project_id,
            files={"a.py": "v1"},
            message="V1"
        )
        
        await version_manager.create_snapshot(
            project_id=project_id,
            files={"a.py": "v2"},
            message="V2"
        )
        
        latest = await version_manager.get_latest_snapshot(project_id)
        
        assert latest is not None
        assert latest.metadata.version == 2
        assert latest.files["a.py"] == "v2"

    @pytest.mark.asyncio
    async def test_snapshot_persistence(self, version_manager):
        """Test that snapshots are persisted to disk."""
        project_id = "test_project_7"
        
        await version_manager.create_snapshot(
            project_id=project_id,
            files={"test.py": "data"},
            message="Test persistence"
        )
        
        # Create a new manager instance to simulate restart
        new_manager = VersionManager(storage_path=version_manager.storage_path)
        
        snapshots = await new_manager.list_snapshots(project_id)
        
        assert len(snapshots) == 1
        assert snapshots[0].files["test.py"] == "data"

    @pytest.mark.asyncio
    async def test_delete_snapshot(self, version_manager):
        """Test deleting a specific snapshot."""
        project_id = "test_project_8"
        
        await version_manager.create_snapshot(
            project_id=project_id,
            files={"a.py": "v1"},
            message="V1"
        )
        
        await version_manager.create_snapshot(
            project_id=project_id,
            files={"a.py": "v2"},
            message="V2"
        )
        
        await version_manager.delete_snapshot(project_id, version=1)
        
        snapshots = await version_manager.list_snapshots(project_id)
        assert len(snapshots) == 1
        assert snapshots[0].metadata.version == 2

    @pytest.mark.asyncio
    async def test_compare_snapshots(self, version_manager):
        """Test comparing two snapshots."""
        project_id = "test_project_9"
        
        await version_manager.create_snapshot(
            project_id=project_id,
            files={"main.py": "v1", "config.json": "{}"},
            message="V1"
        )
        
        await version_manager.create_snapshot(
            project_id=project_id,
            files={"main.py": "v2", "config.json": "{}", "new.py": "new"},
            message="V2"
        )
        
        diff = await version_manager.compare_snapshots(project_id, version1=1, version2=2)
        
        assert "added" in diff
        assert "modified" in diff
        assert "deleted" in diff
        assert "new.py" in diff["added"]
        assert "main.py" in diff["modified"]

    @pytest.mark.asyncio
    async def test_get_nonexistent_snapshot(self, version_manager):
        """Test getting a nonexistent snapshot returns None."""
        snapshot = await version_manager.get_snapshot("nonexistent", version=1)
        assert snapshot is None

    @pytest.mark.asyncio
    async def test_snapshot_with_empty_files(self, version_manager):
        """Test creating snapshot with empty files dict."""
        project_id = "test_project_10"
        
        snapshot = await version_manager.create_snapshot(
            project_id=project_id,
            files={},
            message="Empty"
        )
        
        assert snapshot.metadata.version == 1
        assert len(snapshot.files) == 0

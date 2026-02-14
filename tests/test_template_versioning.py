"""Tests for template versioning."""

import json
from pathlib import Path

import pytest

from src.templates.versioning import (
    TemplateInfo,
    get_template_info,
    list_templates,
    validate_semver,
)


@pytest.fixture()
def manifest_path(tmp_path: Path) -> Path:
    """Create a temporary manifest.json for testing."""
    data = {
        "templates": [
            {"name": "Alpha", "version": "1.0.0", "description": "Alpha theme"},
            {"name": "Beta", "version": "2.1.0", "description": "Beta theme"},
        ]
    }
    p = tmp_path / "manifest.json"
    p.write_text(json.dumps(data))
    return p


class TestListTemplates:
    def test_returns_all(self, manifest_path: Path) -> None:
        templates = list_templates(path=manifest_path)
        assert len(templates) == 2
        assert all(isinstance(t, TemplateInfo) for t in templates)

    def test_real_manifest(self) -> None:
        templates = list_templates()
        assert len(templates) >= 4
        names = [t.name for t in templates]
        assert "Modern" in names
        assert "Cyberpunk" in names


class TestGetTemplateInfo:
    def test_by_name(self, manifest_path: Path) -> None:
        t = get_template_info("Alpha", path=manifest_path)
        assert t is not None
        assert t.name == "Alpha"
        assert t.version == "1.0.0"

    def test_case_insensitive(self, manifest_path: Path) -> None:
        assert get_template_info("alpha", path=manifest_path) is not None
        assert get_template_info("BETA", path=manifest_path) is not None

    def test_missing(self, manifest_path: Path) -> None:
        assert get_template_info("Gamma", path=manifest_path) is None


class TestValidateSemver:
    @pytest.mark.parametrize("v", ["0.0.1", "1.0.0", "99.12.3"])
    def test_valid(self, v: str) -> None:
        assert validate_semver(v) is True

    @pytest.mark.parametrize("v", ["1.0", "v1.0.0", "1.0.0-beta", "abc", ""])
    def test_invalid(self, v: str) -> None:
        assert validate_semver(v) is False

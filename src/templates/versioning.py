"""
Template Versioning

Load, list, and validate template metadata from manifest.json.
"""

import json
import logging
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

_MANIFEST_PATH = Path(__file__).parent / "manifest.json"
_SEMVER_RE = re.compile(r"^\d+\.\d+\.\d+$")


@dataclass(frozen=True)
class TemplateInfo:
    """Metadata for a single template."""

    name: str
    version: str
    description: str


def _load_manifest(path: Optional[Path] = None) -> list[TemplateInfo]:
    """Parse manifest.json and return a list of TemplateInfo."""
    manifest_path = path or _MANIFEST_PATH
    with open(manifest_path, encoding="utf-8") as fh:
        data = json.load(fh)
    return [TemplateInfo(**entry) for entry in data["templates"]]


def list_templates(path: Optional[Path] = None) -> list[TemplateInfo]:
    """Return all available templates."""
    return _load_manifest(path)


def get_template_info(name: str, path: Optional[Path] = None) -> Optional[TemplateInfo]:
    """Return metadata for a single template by name (case-insensitive)."""
    for t in _load_manifest(path):
        if t.name.lower() == name.lower():
            return t
    return None


def validate_semver(version: str) -> bool:
    """Return True if *version* is a valid semver string (MAJOR.MINOR.PATCH)."""
    return bool(_SEMVER_RE.match(version))

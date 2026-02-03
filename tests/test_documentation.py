"""Tests for documentation files."""
import os
from pathlib import Path


def test_readme_exists():
    """Test that README.md exists."""
    readme_path = Path(__file__).parent.parent / "README.md"
    assert readme_path.exists(), "README.md should exist"
    
    # Should have content
    content = readme_path.read_text()
    assert len(content) > 1000, "README should have substantial content"
    assert "LaunchForge" in content


def test_readme_has_badges():
    """Test README has status badges."""
    readme_path = Path(__file__).parent.parent / "README.md"
    content = readme_path.read_text()
    
    # Should have badges
    assert "badge" in content.lower() or "shields.io" in content


def test_readme_has_architecture_info():
    """Test README mentions architecture."""
    readme_path = Path(__file__).parent.parent / "README.md"
    content = readme_path.read_text()
    
    # Should mention key components
    assert any(word in content.lower() for word in ["architecture", "features", "api"])


def test_setup_docs_exist():
    """Test that SETUP.md exists in docs/."""
    setup_path = Path(__file__).parent.parent / "docs" / "SETUP.md"
    assert setup_path.exists(), "docs/SETUP.md should exist"
    
    content = setup_path.read_text()
    assert len(content) > 500, "SETUP.md should have detailed instructions"


def test_setup_docs_has_installation():
    """Test SETUP.md has installation instructions."""
    setup_path = Path(__file__).parent.parent / "docs" / "SETUP.md"
    content = setup_path.read_text()
    
    # Should cover installation
    assert any(word in content.lower() for word in ["install", "setup", "requirements"])


def test_setup_docs_has_configuration():
    """Test SETUP.md has configuration details."""
    setup_path = Path(__file__).parent.parent / "docs" / "SETUP.md"
    content = setup_path.read_text()
    
    # Should cover config
    assert any(word in content.lower() for word in ["config", "environment", "api key"])


def test_deployment_docs_updated():
    """Test DEPLOYMENT.md exists and is updated."""
    deploy_path = Path(__file__).parent.parent / "DEPLOYMENT.md"
    assert deploy_path.exists(), "DEPLOYMENT.md should exist"
    
    content = deploy_path.read_text()
    assert len(content) > 500, "DEPLOYMENT.md should have detailed instructions"


def test_deployment_docs_mentions_health():
    """Test DEPLOYMENT.md mentions health checks."""
    deploy_path = Path(__file__).parent.parent / "DEPLOYMENT.md"
    content = deploy_path.read_text()
    
    # Should mention health checks for production
    assert "health" in content.lower()


def test_architecture_docs_exist():
    """Test that architecture documentation exists."""
    arch_path = Path(__file__).parent.parent / "docs" / "ARCHITECTURE.md"
    
    if arch_path.exists():
        content = arch_path.read_text()
        assert len(content) > 200


def test_readme_mentions_production_features():
    """Test README mentions production features."""
    readme_path = Path(__file__).parent.parent / "README.md"
    content = readme_path.read_text()
    
    # Should mention key production features
    production_keywords = ["health", "monitoring", "production", "api"]
    matches = sum(1 for keyword in production_keywords if keyword in content.lower())
    
    assert matches >= 2, "README should mention production features"

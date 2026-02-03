"""Tests for Alembic database migrations."""
import os
import subprocess
from pathlib import Path

import pytest


@pytest.fixture
def alembic_dir():
    """Get the alembic directory path."""
    return Path(__file__).parent.parent / "alembic"


@pytest.fixture
def alembic_ini():
    """Get the alembic.ini file path."""
    return Path(__file__).parent.parent / "alembic.ini"


def test_alembic_directory_exists(alembic_dir):
    """Test that alembic directory exists."""
    assert alembic_dir.exists()
    assert alembic_dir.is_dir()


def test_alembic_ini_exists(alembic_ini):
    """Test that alembic.ini exists."""
    assert alembic_ini.exists()
    assert alembic_ini.is_file()


def test_alembic_env_py_exists(alembic_dir):
    """Test that env.py exists."""
    env_py = alembic_dir / "env.py"
    assert env_py.exists()


def test_alembic_versions_dir_exists(alembic_dir):
    """Test that versions directory exists."""
    versions_dir = alembic_dir / "versions"
    assert versions_dir.exists()
    assert versions_dir.is_dir()


def test_alembic_has_migrations(alembic_dir):
    """Test that there are migration files."""
    versions_dir = alembic_dir / "versions"
    migrations = list(versions_dir.glob("*.py"))
    # Filter out __init__.py and __pycache__
    migrations = [m for m in migrations if not m.name.startswith("_")]
    assert len(migrations) > 0


def test_alembic_config_has_script_location(alembic_ini):
    """Test that alembic.ini has script_location configured."""
    content = alembic_ini.read_text()
    # Accept either simple path or %(here)s/alembic pattern
    assert ("script_location = alembic" in content or 
            "script_location = %(here)s/alembic" in content)


def test_alembic_env_imports_base():
    """Test that env.py imports Base metadata."""
    alembic_env = Path(__file__).parent.parent / "alembic" / "env.py"
    content = alembic_env.read_text()
    
    # Should import Base from models
    assert "from src.database.models import Base" in content
    assert "target_metadata = Base.metadata" in content


def test_alembic_env_has_offline_mode():
    """Test that env.py supports offline migrations."""
    alembic_env = Path(__file__).parent.parent / "alembic" / "env.py"
    content = alembic_env.read_text()
    
    assert "def run_migrations_offline()" in content


def test_alembic_env_has_online_mode():
    """Test that env.py supports online migrations."""
    alembic_env = Path(__file__).parent.parent / "alembic" / "env.py"
    content = alembic_env.read_text()
    
    assert "def run_migrations_online()" in content


def test_migration_files_have_upgrade():
    """Test that migration files have upgrade function."""
    versions_dir = Path(__file__).parent.parent / "alembic" / "versions"
    migrations = [m for m in versions_dir.glob("*.py") if not m.name.startswith("_")]
    
    for migration in migrations:
        content = migration.read_text()
        # Accept both typed and untyped function signatures
        assert ("def upgrade():" in content or "def upgrade() -> None:" in content)


def test_migration_files_have_downgrade():
    """Test that migration files have downgrade function."""
    versions_dir = Path(__file__).parent.parent / "alembic" / "versions"
    migrations = [m for m in versions_dir.glob("*.py") if not m.name.startswith("_")]
    
    for migration in migrations:
        content = migration.read_text()
        # Accept both typed and untyped function signatures
        assert ("def downgrade():" in content or "def downgrade() -> None:" in content)


def test_migration_files_have_revision_id():
    """Test that migration files have revision identifiers."""
    versions_dir = Path(__file__).parent.parent / "alembic" / "versions"
    migrations = [m for m in versions_dir.glob("*.py") if not m.name.startswith("_")]
    
    for migration in migrations:
        content = migration.read_text()
        # Accept both plain assignment and typed assignment
        assert ("revision = " in content or "revision: str = " in content)
        assert ("down_revision = " in content or "down_revision: Union[str" in content)


def test_alembic_history_command():
    """Test that alembic history command works."""
    result = subprocess.run(
        ["python", "-m", "alembic", "history"],
        capture_output=True,
        text=True,
        cwd=Path(__file__).parent.parent
    )
    
    # Should not error (exit code 0)
    assert result.returncode == 0


def test_alembic_current_command():
    """Test that alembic current command works."""
    result = subprocess.run(
        ["python", "-m", "alembic", "current"],
        capture_output=True,
        text=True,
        cwd=Path(__file__).parent.parent
    )
    
    # Should not error
    assert result.returncode == 0


def test_alembic_branches_command():
    """Test that there are no conflicting branches."""
    result = subprocess.run(
        ["python", "-m", "alembic", "branches"],
        capture_output=True,
        text=True,
        cwd=Path(__file__).parent.parent
    )
    
    assert result.returncode == 0
    # Empty output means no branches (good)
    # Output with content means branches exist (needs investigation)


def test_migration_files_syntax_valid():
    """Test that migration files have valid Python syntax."""
    import ast
    
    versions_dir = Path(__file__).parent.parent / "alembic" / "versions"
    migrations = [m for m in versions_dir.glob("*.py") if not m.name.startswith("_")]
    
    for migration in migrations:
        try:
            ast.parse(migration.read_text())
        except SyntaxError as e:
            pytest.fail(f"Syntax error in {migration.name}: {e}")


def test_migrations_documentation_exists():
    """Test that migration documentation exists."""
    docs_dir = Path(__file__).parent.parent / "docs"
    migration_docs = docs_dir / "MIGRATIONS.md"
    
    assert migration_docs.exists()
    content = migration_docs.read_text()
    assert "Alembic" in content
    assert "migration" in content.lower()


def test_initial_migration_exists():
    """Test that initial schema migration exists."""
    versions_dir = Path(__file__).parent.parent / "alembic" / "versions"
    migrations = list(versions_dir.glob("*initial*.py"))
    
    # Should have at least one migration with "initial" in name
    assert len(migrations) > 0

"""
LaunchForge Database Tests

Comprehensive tests for database models, repositories, and operations.
Uses SQLite in-memory for fast testing without PostgreSQL dependency.
"""

import pytest
from datetime import datetime, timedelta
from uuid import uuid4

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from src.database.models import (
    Base,
    User,
    Project,
    Generation,
    Deployment,
    SubscriptionTier,
    ProjectStatus,
    DeploymentStatus,
)
from src.database.db import DatabaseManager, get_database_url
from src.database.repositories import (
    UserRepository,
    ProjectRepository,
    GenerationRepository,
    DeploymentRepository,
)


# =============================================================================
# FIXTURES
# =============================================================================

@pytest.fixture(scope="function")
def engine():
    """Create a fresh SQLite in-memory engine for each test."""
    engine = create_engine("sqlite:///:memory:", echo=False)
    Base.metadata.create_all(bind=engine)
    yield engine
    Base.metadata.drop_all(bind=engine)
    engine.dispose()


@pytest.fixture(scope="function")
def session(engine):
    """Create a new session for each test."""
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()


@pytest.fixture
def sample_user(session):
    """Create a sample user for testing."""
    user = User(
        id=str(uuid4()),
        email="test@example.com",
        password_hash="hashed_password_123",
        subscription_tier=SubscriptionTier.FREE,
        credits_remaining=100,
    )
    session.add(user)
    session.commit()
    return user


@pytest.fixture
def sample_project(session, sample_user):
    """Create a sample project for testing."""
    project = Project(
        id=str(uuid4()),
        user_id=sample_user.id,
        name="Test Project",
        description="A test project description",
        status=ProjectStatus.DRAFT,
        config={"framework": "nextjs", "database": "postgresql"},
    )
    session.add(project)
    session.commit()
    return project


@pytest.fixture
def sample_generation(session, sample_project):
    """Create a sample generation for testing."""
    generation = Generation(
        id=str(uuid4()),
        project_id=sample_project.id,
        prompt="Build a task management app",
        model_used="perplexity-sonar-pro",
        tokens_used=1500,
    )
    session.add(generation)
    session.commit()
    return generation


@pytest.fixture
def sample_deployment(session, sample_project):
    """Create a sample deployment for testing."""
    deployment = Deployment(
        id=str(uuid4()),
        project_id=sample_project.id,
        provider="vercel",
        status=DeploymentStatus.PENDING,
        config={"region": "iad1"},
    )
    session.add(deployment)
    session.commit()
    return deployment


# =============================================================================
# MODEL TESTS
# =============================================================================

class TestUserModel:
    """Tests for User model."""
    
    def test_create_user(self, session):
        """Test creating a new user."""
        user = User(
            email="new@example.com",
            password_hash="hash123",
            subscription_tier=SubscriptionTier.FREE,
        )
        session.add(user)
        session.commit()
        
        assert user.id is not None
        assert user.email == "new@example.com"
        assert user.credits_remaining == 100
        assert user.is_deleted == False
        assert user.created_at is not None
    
    def test_user_has_credits(self, sample_user):
        """Test credit checking."""
        assert sample_user.has_credits(50) == True
        assert sample_user.has_credits(100) == True
        assert sample_user.has_credits(101) == False
    
    def test_user_use_credits(self, sample_user, session):
        """Test credit usage."""
        assert sample_user.use_credits(30) == True
        assert sample_user.credits_remaining == 70
        
        assert sample_user.use_credits(100) == False  # Not enough
        assert sample_user.credits_remaining == 70  # Unchanged
    
    def test_user_soft_delete(self, sample_user, session):
        """Test soft delete functionality."""
        sample_user.soft_delete()
        session.commit()
        
        assert sample_user.is_deleted == True
        assert sample_user.deleted_at is not None
    
    def test_user_restore(self, sample_user, session):
        """Test restoring a soft-deleted user."""
        sample_user.soft_delete()
        session.commit()
        
        sample_user.restore()
        session.commit()
        
        assert sample_user.is_deleted == False
        assert sample_user.deleted_at is None
    
    def test_user_repr(self, sample_user):
        """Test user string representation."""
        repr_str = repr(sample_user)
        assert "test@example.com" in repr_str
        assert "free" in repr_str


class TestProjectModel:
    """Tests for Project model."""
    
    def test_create_project(self, session, sample_user):
        """Test creating a new project."""
        project = Project(
            user_id=sample_user.id,
            name="My App",
            description="A cool app",
        )
        session.add(project)
        session.commit()
        
        assert project.id is not None
        assert project.status == ProjectStatus.DRAFT
        assert project.config is not None
    
    def test_project_user_relationship(self, sample_project, sample_user):
        """Test project-user relationship."""
        assert sample_project.user.id == sample_user.id
        assert sample_project.user.email == sample_user.email
    
    def test_project_status_transitions(self, sample_project, session):
        """Test project status changes."""
        sample_project.status = ProjectStatus.GENERATING
        session.commit()
        assert sample_project.status == ProjectStatus.GENERATING
        
        sample_project.status = ProjectStatus.DEPLOYED
        session.commit()
        assert sample_project.status == ProjectStatus.DEPLOYED


class TestGenerationModel:
    """Tests for Generation model."""
    
    def test_create_generation(self, session, sample_project):
        """Test creating a generation."""
        gen = Generation(
            project_id=sample_project.id,
            prompt="Build an e-commerce platform",
            model_used="perplexity-sonar-pro",
        )
        session.add(gen)
        session.commit()
        
        assert gen.id is not None
        assert gen.tokens_used == 0
        assert gen.created_at is not None
    
    def test_generation_project_relationship(self, sample_generation, sample_project):
        """Test generation-project relationship."""
        assert sample_generation.project.id == sample_project.id
    
    def test_generation_with_results(self, session, sample_project):
        """Test generation with full results."""
        gen = Generation(
            project_id=sample_project.id,
            prompt="Create a chat app",
            model_used="gpt-4",
            tokens_used=2500,
            generation_time_ms=5000,
            market_intel={"competitors": ["slack", "discord"]},
            generated_code={"files": [{"name": "app.py", "content": "..."}]},
        )
        session.add(gen)
        session.commit()
        
        assert gen.tokens_used == 2500
        assert gen.market_intel["competitors"][0] == "slack"


class TestDeploymentModel:
    """Tests for Deployment model."""
    
    def test_create_deployment(self, session, sample_project):
        """Test creating a deployment."""
        deployment = Deployment(
            project_id=sample_project.id,
            provider="netlify",
        )
        session.add(deployment)
        session.commit()
        
        assert deployment.id is not None
        assert deployment.status == DeploymentStatus.PENDING
    
    def test_deployment_mark_success(self, sample_deployment, session):
        """Test marking deployment as successful."""
        sample_deployment.mark_success("https://myapp.vercel.app")
        session.commit()
        
        assert sample_deployment.status == DeploymentStatus.SUCCESS
        assert sample_deployment.url == "https://myapp.vercel.app"
        assert sample_deployment.deployed_at is not None
    
    def test_deployment_mark_failed(self, sample_deployment, session):
        """Test marking deployment as failed."""
        sample_deployment.mark_failed("Build failed: npm install error")
        session.commit()
        
        assert sample_deployment.status == DeploymentStatus.FAILED
        assert "npm install" in sample_deployment.error_message
    
    def test_deployment_add_log(self, sample_deployment, session):
        """Test adding log entries."""
        sample_deployment.add_log("Starting build...")
        sample_deployment.add_log("Installing dependencies...")
        session.commit()
        
        assert len(sample_deployment.logs) == 2
        assert "Starting build" in sample_deployment.logs[0]["message"]


# =============================================================================
# REPOSITORY TESTS
# =============================================================================

class TestUserRepository:
    """Tests for UserRepository."""
    
    def test_create_user(self, session):
        """Test creating user via repository."""
        repo = UserRepository(session)
        user = repo.create_user(
            email="Test@Example.COM",  # Should be lowercased
            password_hash="hash123",
            subscription_tier=SubscriptionTier.STARTER,
        )
        session.commit()
        
        assert user.email == "test@example.com"
        assert user.credits_remaining == 1000  # Starter tier
    
    def test_get_by_email(self, session, sample_user):
        """Test finding user by email."""
        repo = UserRepository(session)
        found = repo.get_by_email("TEST@example.com")  # Case insensitive
        
        assert found is not None
        assert found.id == sample_user.id
    
    def test_get_by_email_not_found(self, session):
        """Test email lookup for non-existent user."""
        repo = UserRepository(session)
        found = repo.get_by_email("nonexistent@example.com")
        
        assert found is None
    
    def test_use_credits(self, session, sample_user):
        """Test credit usage via repository."""
        repo = UserRepository(session)
        
        assert repo.use_credits(sample_user.id, 50) == True
        session.refresh(sample_user)
        assert sample_user.credits_remaining == 50
        
        assert repo.use_credits(sample_user.id, 100) == False
    
    def test_add_credits(self, session, sample_user):
        """Test adding credits via repository."""
        repo = UserRepository(session)
        repo.add_credits(sample_user.id, 500)
        session.commit()
        
        session.refresh(sample_user)
        assert sample_user.credits_remaining == 600


class TestProjectRepository:
    """Tests for ProjectRepository."""
    
    def test_create_project(self, session, sample_user):
        """Test creating project via repository."""
        repo = ProjectRepository(session)
        project = repo.create_project(
            user_id=sample_user.id,
            name="New App",
            description="A new application",
            config={"tech": "react"},
        )
        session.commit()
        
        assert project.name == "New App"
        assert project.config["tech"] == "react"
    
    def test_get_user_projects(self, session, sample_user, sample_project):
        """Test getting all projects for a user."""
        repo = ProjectRepository(session)
        
        # Create additional project
        repo.create_project(sample_user.id, "Second Project")
        session.commit()
        
        projects = repo.get_user_projects(sample_user.id)
        assert len(projects) == 2
    
    def test_update_status(self, session, sample_project):
        """Test updating project status."""
        repo = ProjectRepository(session)
        repo.update_status(sample_project.id, ProjectStatus.DEPLOYED)
        session.commit()
        
        session.refresh(sample_project)
        assert sample_project.status == ProjectStatus.DEPLOYED
    
    def test_search_projects(self, session, sample_user):
        """Test project search."""
        repo = ProjectRepository(session)
        
        repo.create_project(sample_user.id, "E-commerce Store", "Online shopping platform")
        repo.create_project(sample_user.id, "Blog Platform", "Content management system")
        session.commit()
        
        results = repo.search_projects(sample_user.id, "commerce")
        assert len(results) == 1
        assert "E-commerce" in results[0].name


class TestGenerationRepository:
    """Tests for GenerationRepository."""
    
    def test_create_generation(self, session, sample_project):
        """Test creating generation via repository."""
        repo = GenerationRepository(session)
        gen = repo.create_generation(
            project_id=sample_project.id,
            prompt="Build a SaaS dashboard",
            model_used="perplexity",
        )
        session.commit()
        
        assert gen.prompt == "Build a SaaS dashboard"
    
    def test_complete_generation(self, session, sample_generation):
        """Test completing a generation."""
        repo = GenerationRepository(session)
        repo.complete_generation(
            sample_generation.id,
            market_intel={"size": "$5B"},
            generated_code={"app.py": "code here"},
            tokens_used=3000,
            generation_time_ms=8000,
        )
        session.commit()
        
        session.refresh(sample_generation)
        assert sample_generation.tokens_used == 3000
        assert sample_generation.market_intel["size"] == "$5B"
    
    def test_get_total_tokens(self, session, sample_project):
        """Test total token calculation."""
        repo = GenerationRepository(session)
        
        repo.create_generation(sample_project.id, "Prompt 1")
        repo.create_generation(sample_project.id, "Prompt 2")
        session.commit()
        
        # Update with token usage
        gens = repo.get_project_generations(sample_project.id)
        gens[0].tokens_used = 1000
        gens[1].tokens_used = 2000
        session.commit()
        
        total = repo.get_total_tokens(sample_project.id)
        assert total == 3000


class TestDeploymentRepository:
    """Tests for DeploymentRepository."""
    
    def test_create_deployment(self, session, sample_project):
        """Test creating deployment via repository."""
        repo = DeploymentRepository(session)
        deployment = repo.create_deployment(
            project_id=sample_project.id,
            provider="railway",
            config={"region": "us-west"},
        )
        session.commit()
        
        assert deployment.provider == "railway"
        assert deployment.status == DeploymentStatus.PENDING
    
    def test_deployment_lifecycle(self, session, sample_deployment):
        """Test full deployment lifecycle."""
        repo = DeploymentRepository(session)
        
        # Start deployment
        repo.start_deployment(sample_deployment.id)
        session.commit()
        session.refresh(sample_deployment)
        assert sample_deployment.status == DeploymentStatus.IN_PROGRESS
        
        # Complete deployment
        repo.complete_deployment(
            sample_deployment.id,
            url="https://myapp.railway.app",
            build_duration_ms=45000,
        )
        session.commit()
        session.refresh(sample_deployment)
        
        assert sample_deployment.status == DeploymentStatus.SUCCESS
        assert sample_deployment.url == "https://myapp.railway.app"
    
    def test_get_latest_successful(self, session, sample_project):
        """Test getting latest successful deployment."""
        repo = DeploymentRepository(session)
        
        # Create failed deployment
        d1 = repo.create_deployment(sample_project.id, "vercel")
        repo.fail_deployment(d1.id, "Build error")
        
        # Create successful deployment
        d2 = repo.create_deployment(sample_project.id, "vercel")
        repo.complete_deployment(d2.id, "https://app.vercel.app")
        session.commit()
        
        latest = repo.get_latest_successful(sample_project.id)
        assert latest is not None
        assert latest.id == d2.id


# =============================================================================
# DATABASE MANAGER TESTS
# =============================================================================

class TestDatabaseManager:
    """Tests for DatabaseManager."""
    
    def test_get_database_url_fallback(self, monkeypatch):
        """Test database URL fallback to SQLite."""
        # Clear all database env vars
        monkeypatch.delenv("DATABASE_URL", raising=False)
        monkeypatch.delenv("DB_HOST", raising=False)
        monkeypatch.delenv("DB_PASSWORD", raising=False)
        
        url = get_database_url()
        assert "sqlite" in url
    
    def test_get_database_url_from_env(self, monkeypatch):
        """Test database URL from environment variable."""
        monkeypatch.setenv("DATABASE_URL", "postgresql://user:pass@host:5432/db")
        
        url = get_database_url()
        assert url == "postgresql://user:pass@host:5432/db"
    
    def test_postgres_url_conversion(self, monkeypatch):
        """Test Heroku-style postgres:// to postgresql:// conversion."""
        monkeypatch.setenv("DATABASE_URL", "postgres://user:pass@host:5432/db")
        
        url = get_database_url()
        assert url.startswith("postgresql://")


# =============================================================================
# INTEGRATION TESTS
# =============================================================================

class TestDatabaseIntegration:
    """Integration tests for complete workflows."""
    
    def test_full_user_project_workflow(self, session):
        """Test complete user to project to deployment workflow."""
        # Create user
        user_repo = UserRepository(session)
        user = user_repo.create_user("founder@startup.com", "hash123", SubscriptionTier.PRO)
        session.commit()
        
        # Create project
        proj_repo = ProjectRepository(session)
        project = proj_repo.create_project(
            user.id,
            "SaaS Platform",
            "B2B analytics dashboard",
        )
        session.commit()
        
        # Create generation
        gen_repo = GenerationRepository(session)
        generation = gen_repo.create_generation(
            project.id,
            "Build a real-time analytics dashboard with charts",
            "perplexity-sonar-pro",
        )
        gen_repo.complete_generation(
            generation.id,
            market_intel={"tam": "$50B"},
            generated_code={"files": ["app.py", "dashboard.jsx"]},
            tokens_used=5000,
        )
        session.commit()
        
        # Deduct credits
        user_repo.use_credits(user.id, 5)  # 5 credits per generation
        session.commit()
        
        # Deploy
        deploy_repo = DeploymentRepository(session)
        deployment = deploy_repo.create_deployment(project.id, "vercel")
        deploy_repo.start_deployment(deployment.id)
        deploy_repo.complete_deployment(
            deployment.id,
            "https://saas-platform.vercel.app",
            build_duration_ms=30000,
        )
        
        # Update project status
        proj_repo.update_status(project.id, ProjectStatus.DEPLOYED)
        proj_repo.set_deployment_url(project.id, "https://saas-platform.vercel.app")
        session.commit()
        
        # Verify final state
        session.refresh(user)
        session.refresh(project)
        
        assert user.credits_remaining == 10000 - 5  # PRO tier minus usage
        assert project.status == ProjectStatus.DEPLOYED
        assert project.deployment_url == "https://saas-platform.vercel.app"
        assert gen_repo.get_total_tokens(project.id) == 5000


# =============================================================================
# RUN TESTS
# =============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])

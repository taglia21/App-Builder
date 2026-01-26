"""
NexusAI Database CRUD Operations

Repository pattern implementation for database operations.
Provides type-safe, reusable CRUD operations for all models.
"""

from datetime import datetime
from typing import Generic, List, Optional, Type, TypeVar
from uuid import uuid4

from sqlalchemy import and_, or_
from sqlalchemy.orm import Session

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

# Type variable for generic repository
ModelType = TypeVar("ModelType", bound=Base)


class BaseRepository(Generic[ModelType]):
    """
    Base repository with common CRUD operations.
    
    Provides generic database operations that can be
    inherited by model-specific repositories.
    """
    
    def __init__(self, session: Session, model: Type[ModelType]):
        """
        Initialize repository.
        
        Args:
            session: SQLAlchemy session
            model: Model class to operate on
        """
        self.session = session
        self.model = model
    
    def get(self, id: str) -> Optional[ModelType]:
        """Get a record by ID."""
        return self.session.query(self.model).filter(
            self.model.id == id
        ).first()
    
    def get_all(
        self,
        skip: int = 0,
        limit: int = 100,
        include_deleted: bool = False
    ) -> List[ModelType]:
        """Get all records with pagination."""
        query = self.session.query(self.model)
        
        # Filter soft-deleted records if model supports it
        if hasattr(self.model, 'is_deleted') and not include_deleted:
            query = query.filter(self.model.is_deleted == False)
        
        return query.offset(skip).limit(limit).all()
    
    def create(self, **kwargs) -> ModelType:
        """Create a new record."""
        if 'id' not in kwargs:
            kwargs['id'] = str(uuid4())
        
        instance = self.model(**kwargs)
        self.session.add(instance)
        self.session.flush()
        return instance
    
    def update(self, id: str, **kwargs) -> Optional[ModelType]:
        """Update a record by ID."""
        instance = self.get(id)
        if instance:
            for key, value in kwargs.items():
                if hasattr(instance, key):
                    setattr(instance, key, value)
            self.session.flush()
        return instance
    
    def delete(self, id: str, soft: bool = True) -> bool:
        """
        Delete a record by ID.
        
        Args:
            id: Record ID
            soft: If True, soft delete. If False, hard delete.
        
        Returns:
            bool: True if deleted, False if not found
        """
        instance = self.get(id)
        if instance:
            if soft and hasattr(instance, 'soft_delete'):
                instance.soft_delete()
            else:
                self.session.delete(instance)
            self.session.flush()
            return True
        return False
    
    def count(self, include_deleted: bool = False) -> int:
        """Get total count of records."""
        query = self.session.query(self.model)
        if hasattr(self.model, 'is_deleted') and not include_deleted:
            query = query.filter(self.model.is_deleted == False)
        return query.count()


class UserRepository(BaseRepository[User]):
    """Repository for User model operations."""
    
    def __init__(self, session: Session):
        super().__init__(session, User)
    
    def get_by_email(self, email: str) -> Optional[User]:
        """Get user by email address."""
        return self.session.query(User).filter(
            and_(
                User.email == email.lower(),
                User.is_deleted == False
            )
        ).first()
    
    def create_user(
        self,
        email: str,
        password_hash: str,
        subscription_tier: SubscriptionTier = SubscriptionTier.FREE
    ) -> User:
        """Create a new user."""
        return self.create(
            email=email.lower(),
            password_hash=password_hash,
            subscription_tier=subscription_tier,
            credits_remaining=self._get_initial_credits(subscription_tier)
        )
    
    def _get_initial_credits(self, tier: SubscriptionTier) -> int:
        """Get initial credits for subscription tier."""
        credits_map = {
            SubscriptionTier.FREE: 100,
            SubscriptionTier.STARTER: 1000,
            SubscriptionTier.PRO: 10000,
            SubscriptionTier.ENTERPRISE: 100000,
        }
        return credits_map.get(tier, 100)
    
    def update_login(self, user_id: str) -> Optional[User]:
        """Update user's last login timestamp."""
        return self.update(user_id, last_login_at=datetime.utcnow())
    
    def add_credits(self, user_id: str, amount: int) -> Optional[User]:
        """Add credits to user account."""
        user = self.get(user_id)
        if user:
            user.credits_remaining += amount
            self.session.flush()
        return user
    
    def use_credits(self, user_id: str, amount: int) -> bool:
        """
        Use credits from user account.
        
        Returns:
            bool: True if successful, False if insufficient credits
        """
        user = self.get(user_id)
        if user and user.use_credits(amount):
            self.session.flush()
            return True
        return False
    
    def get_by_tier(self, tier: SubscriptionTier) -> List[User]:
        """Get all users with a specific subscription tier."""
        return self.session.query(User).filter(
            and_(
                User.subscription_tier == tier,
                User.is_deleted == False
            )
        ).all()


class ProjectRepository(BaseRepository[Project]):
    """Repository for Project model operations."""
    
    def __init__(self, session: Session):
        super().__init__(session, Project)
    
    def get_user_projects(
        self,
        user_id: str,
        status: Optional[ProjectStatus] = None,
        skip: int = 0,
        limit: int = 100
    ) -> List[Project]:
        """Get all projects for a user."""
        query = self.session.query(Project).filter(
            and_(
                Project.user_id == user_id,
                Project.is_deleted == False
            )
        )
        
        if status:
            query = query.filter(Project.status == status)
        
        return query.order_by(Project.created_at.desc()).offset(skip).limit(limit).all()
    
    def create_project(
        self,
        user_id: str,
        name: str,
        description: Optional[str] = None,
        config: Optional[dict] = None
    ) -> Project:
        """Create a new project."""
        return self.create(
            user_id=user_id,
            name=name,
            description=description,
            config=config or {}
        )
    
    def update_status(
        self,
        project_id: str,
        status: ProjectStatus
    ) -> Optional[Project]:
        """Update project status."""
        return self.update(project_id, status=status)
    
    def set_deployment_url(
        self,
        project_id: str,
        deployment_url: str
    ) -> Optional[Project]:
        """Set project deployment URL."""
        return self.update(
            project_id,
            deployment_url=deployment_url,
            status=ProjectStatus.DEPLOYED
        )
    
    def search_projects(
        self,
        user_id: str,
        query: str
    ) -> List[Project]:
        """Search projects by name or description."""
        search_term = f"%{query}%"
        return self.session.query(Project).filter(
            and_(
                Project.user_id == user_id,
                Project.is_deleted == False,
                or_(
                    Project.name.ilike(search_term),
                    Project.description.ilike(search_term)
                )
            )
        ).all()


class GenerationRepository(BaseRepository[Generation]):
    """Repository for Generation model operations."""
    
    def __init__(self, session: Session):
        super().__init__(session, Generation)
    
    def get_project_generations(
        self,
        project_id: str,
        skip: int = 0,
        limit: int = 50
    ) -> List[Generation]:
        """Get all generations for a project."""
        return self.session.query(Generation).filter(
            Generation.project_id == project_id
        ).order_by(Generation.created_at.desc()).offset(skip).limit(limit).all()
    
    def create_generation(
        self,
        project_id: str,
        prompt: str,
        model_used: Optional[str] = None
    ) -> Generation:
        """Create a new generation record."""
        return self.create(
            project_id=project_id,
            prompt=prompt,
            model_used=model_used
        )
    
    def complete_generation(
        self,
        generation_id: str,
        market_intel: Optional[dict] = None,
        generated_code: Optional[dict] = None,
        tokens_used: int = 0,
        generation_time_ms: Optional[int] = None
    ) -> Optional[Generation]:
        """Mark generation as complete with results."""
        return self.update(
            generation_id,
            market_intel=market_intel,
            generated_code=generated_code,
            tokens_used=tokens_used,
            generation_time_ms=generation_time_ms
        )
    
    def fail_generation(
        self,
        generation_id: str,
        error_message: str
    ) -> Optional[Generation]:
        """Mark generation as failed."""
        return self.update(
            generation_id,
            error_message=error_message
        )
    
    def get_total_tokens(self, project_id: str) -> int:
        """Get total tokens used for a project."""
        from sqlalchemy import func
        result = self.session.query(
            func.sum(Generation.tokens_used)
        ).filter(
            Generation.project_id == project_id
        ).scalar()
        return result or 0


class DeploymentRepository(BaseRepository[Deployment]):
    """Repository for Deployment model operations."""
    
    def __init__(self, session: Session):
        super().__init__(session, Deployment)
    
    def get_project_deployments(
        self,
        project_id: str,
        skip: int = 0,
        limit: int = 20
    ) -> List[Deployment]:
        """Get all deployments for a project."""
        return self.session.query(Deployment).filter(
            Deployment.project_id == project_id
        ).order_by(Deployment.created_at.desc()).offset(skip).limit(limit).all()
    
    def create_deployment(
        self,
        project_id: str,
        provider: str,
        config: Optional[dict] = None
    ) -> Deployment:
        """Create a new deployment record."""
        return self.create(
            project_id=project_id,
            provider=provider,
            config=config or {},
            status=DeploymentStatus.PENDING
        )
    
    def start_deployment(self, deployment_id: str) -> Optional[Deployment]:
        """Mark deployment as in progress."""
        deployment = self.get(deployment_id)
        if deployment:
            deployment.status = DeploymentStatus.IN_PROGRESS
            deployment.add_log("Deployment started")
            self.session.flush()
        return deployment
    
    def complete_deployment(
        self,
        deployment_id: str,
        url: str,
        build_duration_ms: Optional[int] = None
    ) -> Optional[Deployment]:
        """Mark deployment as successful."""
        deployment = self.get(deployment_id)
        if deployment:
            deployment.mark_success(url)
            deployment.build_duration_ms = build_duration_ms
            deployment.add_log(f"Deployment successful: {url}")
            self.session.flush()
        return deployment
    
    def fail_deployment(
        self,
        deployment_id: str,
        error_message: str
    ) -> Optional[Deployment]:
        """Mark deployment as failed."""
        deployment = self.get(deployment_id)
        if deployment:
            deployment.mark_failed(error_message)
            deployment.add_log(f"Deployment failed: {error_message}")
            self.session.flush()
        return deployment
    
    def get_latest_successful(
        self,
        project_id: str
    ) -> Optional[Deployment]:
        """Get the latest successful deployment for a project."""
        return self.session.query(Deployment).filter(
            and_(
                Deployment.project_id == project_id,
                Deployment.status == DeploymentStatus.SUCCESS
            )
        ).order_by(Deployment.deployed_at.desc()).first()
    
    def add_deployment_log(
        self,
        deployment_id: str,
        message: str
    ) -> Optional[Deployment]:
        """Add a log entry to a deployment."""
        deployment = self.get(deployment_id)
        if deployment:
            deployment.add_log(message)
            self.session.flush()
        return deployment

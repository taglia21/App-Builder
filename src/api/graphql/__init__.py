"""GraphQL API implementation using Strawberry."""
from typing import List, Optional

import strawberry
from strawberry.fastapi import GraphQLRouter


# GraphQL Types
@strawberry.type
class Project:
    """Project GraphQL type."""
    id: str
    name: str
    description: str
    status: str
    created_at: str


@strawberry.type
class User:
    """User GraphQL type."""
    id: str
    email: str
    tier: str
    credits: int


@strawberry.type
class HealthStatus:
    """Health status type."""
    status: str
    version: str
    timestamp: str


# GraphQL Queries
@strawberry.type
class Query:
    """Root Query type."""

    @strawberry.field
    def hello(self) -> str:
        """Simple hello world query."""
        return "Hello from Valeric GraphQL!"

    @strawberry.field
    def health(self) -> HealthStatus:
        """Get health status."""
        from datetime import datetime, timezone
        return HealthStatus(
            status="healthy",
            version="1.0.0",
            timestamp=datetime.now(timezone.utc).isoformat()
        )

    @strawberry.field
    async def projects(self, limit: int = 10) -> List[Project]:
        """Get list of projects."""
        # Mock data for now - would query database in production
        return [
            Project(
                id=f"project-{i}",
                name=f"Project {i}",
                description=f"Description for project {i}",
                status="active",
                created_at="2024-01-01T00:00:00Z"
            )
            for i in range(1, min(limit + 1, 11))
        ]

    @strawberry.field
    async def project(self, id: str) -> Optional[Project]:
        """Get a single project by ID."""
        # Mock data
        return Project(
            id=id,
            name=f"Project {id}",
            description="Sample project",
            status="active",
            created_at="2024-01-01T00:00:00Z"
        )


# GraphQL Mutations
@strawberry.type
class Mutation:
    """Root Mutation type."""

    @strawberry.mutation
    async def create_project(self, name: str, description: str) -> Project:
        """Create a new project."""
        import uuid
        from datetime import datetime, timezone
        
        project_id = str(uuid.uuid4())
        return Project(
            id=project_id,
            name=name,
            description=description,
            status="pending",
            created_at=datetime.now(timezone.utc).isoformat()
        )

    @strawberry.mutation
    async def update_project(self, id: str, name: Optional[str] = None, description: Optional[str] = None) -> Project:
        """Update a project."""
        return Project(
            id=id,
            name=name or f"Updated Project {id}",
            description=description or "Updated description",
            status="active",
            created_at="2024-01-01T00:00:00Z"
        )

    @strawberry.mutation
    async def delete_project(self, id: str) -> bool:
        """Delete a project."""
        # In production, would delete from database
        return True


# Create schema
schema = strawberry.Schema(query=Query, mutation=Mutation)


def create_graphql_router() -> GraphQLRouter:
    """
    Create and configure GraphQL router.
    
    Returns:
        Configured GraphQLRouter instance
    """
    return GraphQLRouter(
        schema=schema,
        path="/graphql",
    )

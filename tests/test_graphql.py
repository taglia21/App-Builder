"""Tests for src/api/graphql - GraphQL API implementation."""
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from src.api.graphql import create_graphql_router, schema


@pytest.fixture
def app():
    """Create a test FastAPI application with GraphQL."""
    app = FastAPI()
    graphql_router = create_graphql_router()
    app.include_router(graphql_router, prefix="")
    return app


@pytest.fixture
def client(app):
    """Create a test client."""
    return TestClient(app)


def test_graphql_endpoint_exists(client):
    """Test that GraphQL endpoint is accessible."""
    response = client.get("/graphql")
    # GraphQL playground or schema introspection
    assert response.status_code in [200, 405]  # 405 if GET not supported


def test_graphql_hello_query(client):
    """Test simple hello query."""
    query = """
        query {
            hello
        }
    """
    
    response = client.post("/graphql", json={"query": query})
    
    assert response.status_code == 200
    data = response.json()
    assert "data" in data
    assert data["data"]["hello"] == "Hello from LaunchForge GraphQL!"


def test_graphql_health_query(client):
    """Test health status query."""
    query = """
        query {
            health {
                status
                version
                timestamp
            }
        }
    """
    
    response = client.post("/graphql", json={"query": query})
    
    assert response.status_code == 200
    data = response.json()
    assert "data" in data
    assert data["data"]["health"]["status"] == "healthy"
    assert data["data"]["health"]["version"] == "1.0.0"
    assert "timestamp" in data["data"]["health"]


def test_graphql_projects_query(client):
    """Test projects list query."""
    query = """
        query {
            projects(limit: 5) {
                id
                name
                description
                status
            }
        }
    """
    
    response = client.post("/graphql", json={"query": query})
    
    assert response.status_code == 200
    data = response.json()
    assert "data" in data
    projects = data["data"]["projects"]
    assert len(projects) == 5
    assert projects[0]["id"] == "project-1"
    assert projects[0]["status"] == "active"


def test_graphql_projects_query_default_limit(client):
    """Test projects query with default limit."""
    query = """
        query {
            projects {
                id
                name
            }
        }
    """
    
    response = client.post("/graphql", json={"query": query})
    
    assert response.status_code == 200
    data = response.json()
    projects = data["data"]["projects"]
    assert len(projects) == 10  # Default limit


def test_graphql_project_query(client):
    """Test single project query."""
    query = """
        query {
            project(id: "test-123") {
                id
                name
                description
                status
                createdAt
            }
        }
    """
    
    response = client.post("/graphql", json={"query": query})
    
    assert response.status_code == 200
    data = response.json()
    project = data["data"]["project"]
    assert project["id"] == "test-123"
    assert project["name"] == "Project test-123"


def test_graphql_create_project_mutation(client):
    """Test creating a project via mutation."""
    mutation = """
        mutation {
            createProject(name: "New Project", description: "Test description") {
                id
                name
                description
                status
            }
        }
    """
    
    response = client.post("/graphql", json={"query": mutation})
    
    assert response.status_code == 200
    data = response.json()
    project = data["data"]["createProject"]
    assert project["name"] == "New Project"
    assert project["description"] == "Test description"
    assert project["status"] == "pending"
    assert "id" in project


def test_graphql_update_project_mutation(client):
    """Test updating a project via mutation."""
    mutation = """
        mutation {
            updateProject(id: "project-1", name: "Updated Name", description: "Updated desc") {
                id
                name
                description
            }
        }
    """
    
    response = client.post("/graphql", json={"query": mutation})
    
    assert response.status_code == 200
    data = response.json()
    project = data["data"]["updateProject"]
    assert project["id"] == "project-1"
    assert project["name"] == "Updated Name"
    assert project["description"] == "Updated desc"


def test_graphql_update_project_partial(client):
    """Test partial update of project."""
    mutation = """
        mutation {
            updateProject(id: "project-2", name: "Only Name Updated") {
                id
                name
                description
            }
        }
    """
    
    response = client.post("/graphql", json={"query": mutation})
    
    assert response.status_code == 200
    data = response.json()
    project = data["data"]["updateProject"]
    assert project["name"] == "Only Name Updated"
    assert "description" in project


def test_graphql_delete_project_mutation(client):
    """Test deleting a project via mutation."""
    mutation = """
        mutation {
            deleteProject(id: "project-to-delete")
        }
    """
    
    response = client.post("/graphql", json={"query": mutation})
    
    assert response.status_code == 200
    data = response.json()
    assert data["data"]["deleteProject"] is True


def test_graphql_invalid_query(client):
    """Test that invalid query returns error."""
    query = """
        query {
            nonExistentField
        }
    """
    
    response = client.post("/graphql", json={"query": query})
    
    assert response.status_code == 200  # GraphQL always returns 200
    data = response.json()
    assert "errors" in data


def test_graphql_schema_exists():
    """Test that schema exists."""
    assert schema is not None


def test_create_graphql_router():
    """Test router creation."""
    router = create_graphql_router()
    assert router is not None
    # GraphQLRouter from Strawberry doesn't have a path attribute directly


def test_graphql_combined_query_and_mutation(client):
    """Test combining query and mutation in single request (not typically done but valid)."""
    # First create
    create_mutation = """
        mutation {
            createProject(name: "Test Project", description: "Test") {
                id
            }
        }
    """
    
    create_response = client.post("/graphql", json={"query": create_mutation})
    assert create_response.status_code == 200
    
    # Then query
    query = """
        query {
            projects(limit: 1) {
                id
                name
            }
        }
    """
    
    query_response = client.post("/graphql", json={"query": query})
    assert query_response.status_code == 200
    assert len(query_response.json()["data"]["projects"]) == 1


def test_graphql_introspection_query(client):
    """Test GraphQL introspection."""
    introspection_query = """
        query {
            __schema {
                queryType {
                    name
                }
                mutationType {
                    name
                }
            }
        }
    """
    
    response = client.post("/graphql", json={"query": introspection_query})
    
    assert response.status_code == 200
    data = response.json()
    assert data["data"]["__schema"]["queryType"]["name"] == "Query"
    assert data["data"]["__schema"]["mutationType"]["name"] == "Mutation"

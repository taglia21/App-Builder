# 🧪 Testing Guide

## Overview

Valeric uses pytest for testing with comprehensive coverage across all modules.

---

## Quick Start

```bash
# Install test dependencies
pip install -r requirements-dev.txt

# Run all tests
pytest

# Run with coverage
pytest --cov=src --cov-report=html

# Run specific test file
pytest tests/test_payments.py -v
```

---

## Test Structure

```
tests/
├── conftest.py              # Shared fixtures
├── test_generator.py        # Core generation tests
├── test_idea_generation.py  # Idea engine tests
├── test_intelligence.py     # Market research tests
├── test_enhanced_generator.py
├── test_readme_generator.py
├── test_retry_cache.py
├── test_progress.py
├── test_auth.py             # Authentication tests
├── test_payments.py         # Stripe integration tests
├── test_dashboard.py        # Dashboard API tests
├── test_deployment.py       # Deployment tests
├── test_business.py         # Business formation tests
└── test_monitoring.py       # Monitoring stack tests
```

---

## Running Tests

### Basic Commands

```bash
# All tests
pytest

# Verbose output
pytest -v

# Stop on first failure
pytest -x

# Run specific test
pytest tests/test_payments.py::TestStripeClient::test_create_customer

# Run tests matching pattern
pytest -k "stripe"

# Run with short traceback
pytest --tb=short
```

### Coverage

```bash
# Terminal report
pytest --cov=src

# HTML report (open htmlcov/index.html)
pytest --cov=src --cov-report=html

# XML report (for CI)
pytest --cov=src --cov-report=xml

# Fail if coverage below threshold
pytest --cov=src --cov-fail-under=80
```

### Parallel Execution

```bash
# Install pytest-xdist
pip install pytest-xdist

# Run tests in parallel
pytest -n auto

# Specify number of workers
pytest -n 4
```

---

## Writing Tests

### Basic Test Structure

```python
import pytest
from src.payments.models import SubscriptionTier

class TestSubscriptionTier:
    """Tests for SubscriptionTier enum."""
    
    def test_tier_values(self):
        """Test tier enum values."""
        assert SubscriptionTier.FREE.value == "free"
        assert SubscriptionTier.PRO.value == "pro"
        assert SubscriptionTier.ENTERPRISE.value == "enterprise"
    
    def test_tier_prices(self):
        """Test tier pricing."""
        prices = {
            SubscriptionTier.FREE: 0,
            SubscriptionTier.PRO: 2900,
            SubscriptionTier.ENTERPRISE: 9900,
        }
        for tier, price in prices.items():
            assert tier.price == price
```

### Using Fixtures

```python
import pytest
from src.payments.stripe import StripeClient

@pytest.fixture
def mock_stripe_client():
    """Create a mock Stripe client for testing."""
    return StripeClient(api_key="sk_test_mock", test_mode=True)

@pytest.fixture
def sample_customer_data():
    """Sample customer data for tests."""
    return {
        "email": "test@example.com",
        "name": "Test User",
        "metadata": {"user_id": "123"}
    }

class TestStripeClient:
    def test_create_customer(self, mock_stripe_client, sample_customer_data):
        """Test customer creation."""
        result = mock_stripe_client.create_customer(**sample_customer_data)
        assert result.id.startswith("cus_")
        assert result.email == sample_customer_data["email"]
```

### Async Tests

```python
import pytest
from src.monitoring.health import ExternalServiceHealthCheck, HealthStatus

@pytest.mark.asyncio
async def test_health_check():
    """Test async health check."""
    check = ExternalServiceHealthCheck(
        name="test-service",
        url="https://httpbin.org/get",
        timeout=5.0
    )
    result = await check.check()
    assert result.status == HealthStatus.HEALTHY
```

### Mocking External Services

```python
import pytest
from unittest.mock import Mock, AsyncMock, patch

class TestStripeIntegration:
    @patch('stripe.Customer.create')
    def test_create_customer_mock(self, mock_create):
        """Test with mocked Stripe API."""
        mock_create.return_value = Mock(
            id="cus_test123",
            email="test@example.com"
        )
        
        client = StripeClient("sk_test_...")
        result = client.create_customer(email="test@example.com")
        
        assert result.id == "cus_test123"
        mock_create.assert_called_once()
    
    @patch('httpx.AsyncClient.get')
    async def test_async_mock(self, mock_get):
        """Test with mocked async HTTP."""
        mock_get.return_value = AsyncMock(
            status_code=200,
            json=AsyncMock(return_value={"status": "ok"})
        )
        
        # Test async code...
```

### Parameterized Tests

```python
import pytest
from src.business.models import BusinessType

@pytest.mark.parametrize("business_type,expected", [
    (BusinessType.LLC, "Limited Liability Company"),
    (BusinessType.CORPORATION, "Corporation"),
    (BusinessType.SOLE_PROPRIETORSHIP, "Sole Proprietorship"),
])
def test_business_type_display(business_type, expected):
    """Test business type display names."""
    assert business_type.display_name == expected

@pytest.mark.parametrize("email,valid", [
    ("user@example.com", True),
    ("user@domain.co.uk", True),
    ("invalid", False),
    ("", False),
    ("user@", False),
])
def test_email_validation(email, valid):
    """Test email validation."""
    result = validate_email(email)
    assert result == valid
```

---

## Test Categories

### Unit Tests

Test individual functions and classes in isolation.

```python
class TestCounter:
    """Unit tests for Counter metric."""
    
    def test_increment(self):
        counter = Counter("test_counter", "A test counter")
        counter.inc()
        assert counter.get() == 1
        
    def test_increment_by_value(self):
        counter = Counter("test_counter", "A test counter")
        counter.inc(5)
        assert counter.get() == 5
```

### Integration Tests

Test multiple components working together.

```python
class TestPaymentFlow:
    """Integration tests for payment flow."""
    
    @pytest.fixture
    def payment_service(self, db_session, stripe_client):
        return PaymentService(db=db_session, stripe=stripe_client)
    
    async def test_full_subscription_flow(self, payment_service):
        """Test complete subscription lifecycle."""
        # Create customer
        customer = await payment_service.create_customer(
            email="test@example.com"
        )
        
        # Subscribe
        subscription = await payment_service.subscribe(
            customer_id=customer.id,
            plan="pro"
        )
        assert subscription.status == "active"
        
        # Cancel
        await payment_service.cancel_subscription(subscription.id)
        
        # Verify
        updated = await payment_service.get_subscription(subscription.id)
        assert updated.status == "canceled"
```

### API Tests

Test HTTP endpoints.

```python
import pytest
from fastapi.testclient import TestClient
from src.dashboard.app import create_app

@pytest.fixture
def client():
    app = create_app()
    return TestClient(app)

class TestDashboardAPI:
    def test_list_projects(self, client, auth_headers):
        """Test project listing endpoint."""
        response = client.get(
            "/api/dashboard/projects",
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert "projects" in data
        
    def test_create_project(self, client, auth_headers):
        """Test project creation."""
        response = client.post(
            "/api/dashboard/projects",
            headers=auth_headers,
            json={"name": "Test Project", "description": "A test"}
        )
        assert response.status_code == 201
        assert response.json()["name"] == "Test Project"
```

---

## Fixtures Reference

### Common Fixtures (conftest.py)

```python
import pytest
from datetime import datetime

@pytest.fixture
def sample_user():
    """Sample user for testing."""
    return {
        "id": "user_123",
        "email": "test@example.com",
        "name": "Test User",
        "created_at": datetime.utcnow()
    }

@pytest.fixture
def auth_headers(sample_user):
    """Authentication headers for API tests."""
    token = create_test_token(sample_user["id"])
    return {"Authorization": f"Bearer {token}"}

@pytest.fixture
def db_session():
    """In-memory database session."""
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    
    engine = create_engine("sqlite:///:memory:")
    Session = sessionmaker(bind=engine)
    session = Session()
    
    yield session
    
    session.close()
```

### Async Fixtures

```python
import pytest
import asyncio

@pytest.fixture
def event_loop():
    """Create event loop for async tests."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()

@pytest.fixture
async def async_client():
    """Async HTTP client."""
    import httpx
    async with httpx.AsyncClient() as client:
        yield client
```

---

## Mocking Guide

### Mock Stripe

```python
@pytest.fixture
def mock_stripe():
    """Mock Stripe SDK."""
    with patch('stripe.Customer') as mock_customer, \
         patch('stripe.Subscription') as mock_sub:
        
        mock_customer.create.return_value = Mock(id="cus_test")
        mock_sub.create.return_value = Mock(id="sub_test", status="active")
        
        yield {
            "customer": mock_customer,
            "subscription": mock_sub
        }
```

### Mock External APIs

```python
import responses

@responses.activate
def test_external_api():
    """Test with mocked HTTP responses."""
    responses.add(
        responses.GET,
        "https://api.example.com/data",
        json={"result": "success"},
        status=200
    )
    
    result = fetch_external_data()
    assert result["result"] == "success"
```

### Mock Environment Variables

```python
import os
from unittest.mock import patch

def test_with_env_vars():
    """Test with mocked environment."""
    with patch.dict(os.environ, {
        "STRIPE_SECRET_KEY": "sk_test_...",
        "DATABASE_URL": "sqlite:///:memory:"
    }):
        settings = load_settings()
        assert settings.stripe_key == "sk_test_..."
```

---

## CI/CD Integration

### GitHub Actions

```yaml
# .github/workflows/test.yml
name: Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    
    steps:
      - uses: actions/checkout@v3
      
      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.12'
      
      - name: Install dependencies
        run: |
          pip install -r requirements.txt
          pip install -r requirements-dev.txt
      
      - name: Run tests
        run: pytest --cov=src --cov-report=xml
      
      - name: Upload coverage
        uses: codecov/codecov-action@v3
        with:
          file: ./coverage.xml
```

### Pre-commit Hooks

```yaml
# .pre-commit-config.yaml
repos:
  - repo: local
    hooks:
      - id: pytest
        name: pytest
        entry: pytest --tb=short
        language: system
        pass_filenames: false
        always_run: true
```

---

## Test Data

### Factories

```python
from factory import Factory, Faker, LazyAttribute

class UserFactory(Factory):
    class Meta:
        model = User
    
    id = Faker('uuid4')
    email = Faker('email')
    name = Faker('name')
    created_at = Faker('date_time')

# Usage
user = UserFactory()
users = UserFactory.create_batch(10)
```

### Snapshots

```python
def test_generated_code_snapshot(snapshot):
    """Test code generation against snapshot."""
    result = generate_code(idea="Task manager app")
    snapshot.assert_match(result, "task_manager_code.txt")
```

---

## Performance Testing

```python
import pytest
import time

def test_generation_performance():
    """Test generation completes in reasonable time."""
    start = time.time()
    
    result = generate_ideas(count=50)
    
    duration = time.time() - start
    assert duration < 30.0  # Should complete in 30 seconds
    assert len(result) == 50

@pytest.mark.benchmark
def test_benchmark_scoring(benchmark):
    """Benchmark idea scoring."""
    ideas = generate_sample_ideas(100)
    
    result = benchmark(score_ideas, ideas)
    
    assert len(result) == 100
```

---

## Debugging Tests

### VSCode Launch Configuration

```json
{
    "version": "0.2.0",
    "configurations": [
        {
            "name": "Debug Tests",
            "type": "python",
            "request": "launch",
            "module": "pytest",
            "args": ["-v", "-x", "--tb=long"],
            "console": "integratedTerminal"
        }
    ]
}
```

### Using pdb

```python
def test_debug_example():
    """Test with debugger."""
    result = complex_function()
    
    import pdb; pdb.set_trace()  # Breakpoint
    
    assert result == expected
```

### Verbose Assertions

```python
def test_with_context():
    """Test with detailed assertion context."""
    result = generate_data()
    
    assert result["status"] == "success", f"Expected success but got: {result}"
    assert len(result["items"]) > 0, f"No items returned: {result}"
```

---

## Reference

- [pytest documentation](https://docs.pytest.org/)
- [pytest-cov](https://pytest-cov.readthedocs.io/)
- [pytest-asyncio](https://pytest-asyncio.readthedocs.io/)

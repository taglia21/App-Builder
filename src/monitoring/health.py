"""
Health Checks

Provides health check infrastructure for monitoring service health.
"""

import os
import time
import logging
import asyncio
from enum import Enum
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional, Dict, Any, List, Callable
import httpx

logger = logging.getLogger(__name__)


class HealthStatus(str, Enum):
    """Health check status."""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"


@dataclass
class ComponentHealth:
    """Health status of a component."""
    name: str
    status: HealthStatus
    message: Optional[str] = None
    response_time_ms: Optional[float] = None
    last_checked: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    details: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "name": self.name,
            "status": self.status.value,
            "message": self.message,
            "response_time_ms": self.response_time_ms,
            "last_checked": self.last_checked.isoformat(),
            "details": self.details,
        }


class HealthCheck(ABC):
    """Abstract base class for health checks."""
    
    @property
    @abstractmethod
    def name(self) -> str:
        """Component name."""
        pass
    
    @abstractmethod
    async def check(self) -> ComponentHealth:
        """
        Perform health check.
        
        Returns:
            ComponentHealth with status and details.
        """
        pass


class DatabaseHealthCheck(HealthCheck):
    """Health check for database connectivity."""
    
    def __init__(
        self,
        db_url: Optional[str] = None,
        timeout: float = 5.0,
    ):
        self.db_url = db_url or os.getenv("DATABASE_URL")
        self.timeout = timeout
        self._name = "database"
    
    @property
    def name(self) -> str:
        return self._name
    
    async def check(self) -> ComponentHealth:
        """Check database connectivity."""
        start_time = time.time()
        
        if not self.db_url:
            return ComponentHealth(
                name=self.name,
                status=HealthStatus.UNKNOWN,
                message="Database URL not configured",
            )
        
        try:
            # Try to import and use asyncpg or psycopg
            import asyncpg
            
            conn = await asyncio.wait_for(
                asyncpg.connect(self.db_url),
                timeout=self.timeout,
            )
            
            # Run simple query
            await conn.fetchval("SELECT 1")
            await conn.close()
            
            response_time = (time.time() - start_time) * 1000
            
            return ComponentHealth(
                name=self.name,
                status=HealthStatus.HEALTHY,
                message="Database connection successful",
                response_time_ms=response_time,
            )
            
        except asyncio.TimeoutError:
            return ComponentHealth(
                name=self.name,
                status=HealthStatus.UNHEALTHY,
                message=f"Database connection timeout after {self.timeout}s",
                response_time_ms=(time.time() - start_time) * 1000,
            )
        except ImportError:
            return ComponentHealth(
                name=self.name,
                status=HealthStatus.UNKNOWN,
                message="Database driver not installed",
            )
        except Exception as e:
            return ComponentHealth(
                name=self.name,
                status=HealthStatus.UNHEALTHY,
                message=f"Database connection failed: {str(e)}",
                response_time_ms=(time.time() - start_time) * 1000,
            )


class RedisHealthCheck(HealthCheck):
    """Health check for Redis connectivity."""
    
    def __init__(
        self,
        redis_url: Optional[str] = None,
        timeout: float = 5.0,
    ):
        self.redis_url = redis_url or os.getenv("REDIS_URL")
        self.timeout = timeout
        self._name = "redis"
    
    @property
    def name(self) -> str:
        return self._name
    
    async def check(self) -> ComponentHealth:
        """Check Redis connectivity."""
        start_time = time.time()
        
        if not self.redis_url:
            return ComponentHealth(
                name=self.name,
                status=HealthStatus.UNKNOWN,
                message="Redis URL not configured",
            )
        
        try:
            import redis.asyncio as aioredis
            
            client = aioredis.from_url(
                self.redis_url,
                socket_connect_timeout=self.timeout,
            )
            
            await asyncio.wait_for(
                client.ping(),
                timeout=self.timeout,
            )
            
            info = await client.info("server")
            await client.close()
            
            response_time = (time.time() - start_time) * 1000
            
            return ComponentHealth(
                name=self.name,
                status=HealthStatus.HEALTHY,
                message="Redis connection successful",
                response_time_ms=response_time,
                details={
                    "redis_version": info.get("redis_version"),
                },
            )
            
        except asyncio.TimeoutError:
            return ComponentHealth(
                name=self.name,
                status=HealthStatus.UNHEALTHY,
                message=f"Redis connection timeout after {self.timeout}s",
                response_time_ms=(time.time() - start_time) * 1000,
            )
        except ImportError:
            return ComponentHealth(
                name=self.name,
                status=HealthStatus.UNKNOWN,
                message="Redis driver not installed",
            )
        except Exception as e:
            return ComponentHealth(
                name=self.name,
                status=HealthStatus.UNHEALTHY,
                message=f"Redis connection failed: {str(e)}",
                response_time_ms=(time.time() - start_time) * 1000,
            )


class ExternalServiceHealthCheck(HealthCheck):
    """Health check for external HTTP services."""
    
    def __init__(
        self,
        name: str,
        url: str,
        method: str = "GET",
        timeout: float = 10.0,
        expected_status: int = 200,
        headers: Optional[Dict[str, str]] = None,
    ):
        self._name = name
        self.url = url
        self.method = method
        self.timeout = timeout
        self.expected_status = expected_status
        self.headers = headers or {}
    
    @property
    def name(self) -> str:
        return self._name
    
    async def check(self) -> ComponentHealth:
        """Check external service health."""
        start_time = time.time()
        
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.request(
                    method=self.method,
                    url=self.url,
                    headers=self.headers,
                )
                
                response_time = (time.time() - start_time) * 1000
                
                if response.status_code == self.expected_status:
                    return ComponentHealth(
                        name=self.name,
                        status=HealthStatus.HEALTHY,
                        message=f"Service responding (status {response.status_code})",
                        response_time_ms=response_time,
                        details={"status_code": response.status_code},
                    )
                else:
                    return ComponentHealth(
                        name=self.name,
                        status=HealthStatus.DEGRADED,
                        message=f"Unexpected status code: {response.status_code}",
                        response_time_ms=response_time,
                        details={"status_code": response.status_code},
                    )
                    
        except httpx.TimeoutException:
            return ComponentHealth(
                name=self.name,
                status=HealthStatus.UNHEALTHY,
                message=f"Service timeout after {self.timeout}s",
                response_time_ms=(time.time() - start_time) * 1000,
            )
        except Exception as e:
            return ComponentHealth(
                name=self.name,
                status=HealthStatus.UNHEALTHY,
                message=f"Service check failed: {str(e)}",
                response_time_ms=(time.time() - start_time) * 1000,
            )


class CallableHealthCheck(HealthCheck):
    """Health check using a custom callable."""
    
    def __init__(
        self,
        name: str,
        check_func: Callable[[], ComponentHealth],
    ):
        self._name = name
        self.check_func = check_func
    
    @property
    def name(self) -> str:
        return self._name
    
    async def check(self) -> ComponentHealth:
        """Run custom check function."""
        try:
            if asyncio.iscoroutinefunction(self.check_func):
                return await self.check_func()
            return self.check_func()
        except Exception as e:
            return ComponentHealth(
                name=self.name,
                status=HealthStatus.UNHEALTHY,
                message=f"Check failed: {str(e)}",
            )


@dataclass
class HealthCheckResult:
    """Overall health check result."""
    status: HealthStatus
    components: List[ComponentHealth]
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "status": self.status.value,
            "timestamp": self.timestamp.isoformat(),
            "components": [c.to_dict() for c in self.components],
        }


class HealthCheckRegistry:
    """
    Registry for health checks.
    
    Manages health check registration and execution.
    """
    
    def __init__(self):
        self._checks: Dict[str, HealthCheck] = {}
        self._cache: Dict[str, ComponentHealth] = {}
        self._cache_ttl: float = 30.0  # seconds
        self._last_check: Dict[str, float] = {}
    
    def register(self, check: HealthCheck) -> None:
        """
        Register a health check.
        
        Args:
            check: Health check to register.
        """
        self._checks[check.name] = check
        logger.debug(f"Registered health check: {check.name}")
    
    def unregister(self, name: str) -> None:
        """
        Unregister a health check.
        
        Args:
            name: Name of check to remove.
        """
        self._checks.pop(name, None)
        self._cache.pop(name, None)
        self._last_check.pop(name, None)
    
    async def check(
        self,
        names: Optional[List[str]] = None,
        use_cache: bool = True,
    ) -> HealthCheckResult:
        """
        Run health checks.
        
        Args:
            names: Specific checks to run. None for all.
            use_cache: Whether to use cached results.
        
        Returns:
            Overall health check result.
        """
        checks_to_run = self._checks
        if names:
            checks_to_run = {n: c for n, c in self._checks.items() if n in names}
        
        results: List[ComponentHealth] = []
        current_time = time.time()
        
        for name, check in checks_to_run.items():
            # Check cache
            if use_cache and name in self._cache:
                last_check_time = self._last_check.get(name, 0)
                if current_time - last_check_time < self._cache_ttl:
                    results.append(self._cache[name])
                    continue
            
            # Run check
            try:
                result = await check.check()
            except Exception as e:
                result = ComponentHealth(
                    name=name,
                    status=HealthStatus.UNHEALTHY,
                    message=f"Check raised exception: {str(e)}",
                )
            
            # Update cache
            self._cache[name] = result
            self._last_check[name] = current_time
            results.append(result)
        
        # Determine overall status
        overall_status = self._determine_overall_status(results)
        
        return HealthCheckResult(
            status=overall_status,
            components=results,
        )
    
    def _determine_overall_status(
        self,
        results: List[ComponentHealth],
    ) -> HealthStatus:
        """Determine overall health from component results."""
        if not results:
            return HealthStatus.UNKNOWN
        
        statuses = [r.status for r in results]
        
        if all(s == HealthStatus.HEALTHY for s in statuses):
            return HealthStatus.HEALTHY
        
        if any(s == HealthStatus.UNHEALTHY for s in statuses):
            return HealthStatus.UNHEALTHY
        
        if any(s == HealthStatus.DEGRADED for s in statuses):
            return HealthStatus.DEGRADED
        
        return HealthStatus.UNKNOWN
    
    async def run_continuous(
        self,
        interval: float = 60.0,
        callback: Optional[Callable[[HealthCheckResult], None]] = None,
    ):
        """
        Run health checks continuously.
        
        Args:
            interval: Check interval in seconds.
            callback: Function to call with results.
        """
        while True:
            try:
                result = await self.check(use_cache=False)
                
                if callback:
                    callback(result)
                
                if result.status != HealthStatus.HEALTHY:
                    logger.warning(
                        f"Health check status: {result.status.value}. "
                        f"Unhealthy components: {[c.name for c in result.components if c.status != HealthStatus.HEALTHY]}"
                    )
                
            except Exception as e:
                logger.error(f"Health check failed: {e}")
            
            await asyncio.sleep(interval)


def create_health_registry(
    include_database: bool = True,
    include_redis: bool = True,
    external_services: Optional[List[Dict[str, Any]]] = None,
) -> HealthCheckRegistry:
    """
    Create a health check registry with common checks.
    
    Args:
        include_database: Include database health check.
        include_redis: Include Redis health check.
        external_services: List of external service configs.
    
    Returns:
        Configured HealthCheckRegistry.
    """
    registry = HealthCheckRegistry()
    
    if include_database:
        registry.register(DatabaseHealthCheck())
    
    if include_redis:
        registry.register(RedisHealthCheck())
    
    if external_services:
        for service in external_services:
            registry.register(ExternalServiceHealthCheck(**service))
    
    return registry

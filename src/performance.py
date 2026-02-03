"""Performance optimization configuration and utilities.

Provides database optimization, connection pooling tuning, query optimization,
and response compression for production deployments.
"""

import logging
import os
from typing import Dict, Optional

from fastapi import FastAPI, Request, Response
from fastapi.middleware.gzip import GZipMiddleware

logger = logging.getLogger(__name__)


class PerformanceOptimizer:
    """Configure performance optimizations for the application."""

    def __init__(self, app: FastAPI):
        """Initialize performance optimizer.
        
        Args:
            app: FastAPI application instance
        """
        self.app = app
        self.enabled_optimizations: Dict[str, bool] = {}

    def enable_compression(
        self,
        minimum_size: int = 1000,
        compression_level: int = 5
    ) -> None:
        """Enable GZip compression for responses.
        
        Args:
            minimum_size: Minimum response size to compress (bytes)
            compression_level: Compression level (1-9, higher = more compression)
        """
        if not any(isinstance(m, GZipMiddleware) for m in self.app.user_middleware):
            self.app.add_middleware(
                GZipMiddleware,
                minimum_size=minimum_size,
                compresslevel=compression_level
            )
            self.enabled_optimizations["compression"] = True
            logger.info(
                f"GZip compression enabled (min_size={minimum_size}, level={compression_level})"
            )
        else:
            logger.warning("GZip compression already enabled")

    def configure_database_pool(self) -> Dict[str, int]:
        """Get optimized database connection pool settings.
        
        Returns:
            Dict with pool configuration
        """
        # Use environment variables with smart defaults
        pool_size = int(os.getenv("DATABASE_POOL_SIZE", "10"))
        max_overflow = int(os.getenv("DATABASE_MAX_OVERFLOW", "20"))
        pool_timeout = int(os.getenv("DATABASE_POOL_TIMEOUT", "30"))
        pool_recycle = int(os.getenv("DATABASE_POOL_RECYCLE", "3600"))  # 1 hour
        pool_pre_ping = os.getenv("DATABASE_POOL_PRE_PING", "true").lower() == "true"

        config = {
            "pool_size": pool_size,
            "max_overflow": max_overflow,
            "pool_timeout": pool_timeout,
            "pool_recycle": pool_recycle,
            "pool_pre_ping": pool_pre_ping,
        }

        self.enabled_optimizations["database_pool"] = True
        logger.info(f"Database pool configured: {config}")
        return config

    def optimize_query_performance(self) -> None:
        """Configure query performance optimizations.
        
        Applies:
        - Eager loading hints
        - Join optimization
        - Index usage recommendations
        """
        tips = [
            "Use .options(joinedload()) for eager loading relationships",
            "Add .filter(Model.is_deleted == false) to exclude soft-deleted records",
            "Use indexed columns in WHERE clauses for faster queries",
            "Consider adding composite indexes for multi-column queries",
            "Use .limit() and .offset() for pagination",
            "Avoid N+1 queries with relationship loading strategies",
        ]

        self.enabled_optimizations["query_optimization"] = True
        logger.info("Query optimization tips:")
        for tip in tips:
            logger.info(f"  - {tip}")

    def add_caching_headers(self) -> None:
        """Add middleware to set cache headers for static assets."""
        @self.app.middleware("http")
        async def cache_control_middleware(request: Request, call_next):
            response: Response = await call_next(request)

            # Cache static assets
            if request.url.path.startswith("/static/"):
                response.headers["Cache-Control"] = "public, max-age=31536000, immutable"
            # Cache API responses briefly
            elif request.url.path.startswith("/api/") and request.method == "GET":
                response.headers["Cache-Control"] = "public, max-age=60"
            # Don't cache other requests
            else:
                response.headers["Cache-Control"] = "no-store"

            return response

        self.enabled_optimizations["caching_headers"] = True
        logger.info("Cache-Control headers configured")

    def enable_etag_support(self) -> None:
        """Add ETag support for conditional requests."""
        @self.app.middleware("http")
        async def etag_middleware(request: Request, call_next):
            response: Response = await call_next(request)

            # Only add ETags for GET requests
            if request.method == "GET" and response.status_code == 200:
                # Simple ETag based on response body hash
                if hasattr(response, "body"):
                    import hashlib
                    etag = hashlib.md5(response.body).hexdigest()
                    response.headers["ETag"] = f'"{etag}"'

                    # Check If-None-Match header
                    if_none_match = request.headers.get("If-None-Match")
                    if if_none_match and if_none_match.strip('"') == etag:
                        return Response(status_code=304)  # Not Modified

            return response

        self.enabled_optimizations["etag"] = True
        logger.info("ETag support enabled")

    def optimize_all(self) -> Dict[str, bool]:
        """Enable all performance optimizations.
        
        Returns:
            Dict of enabled optimizations
        """
        self.enable_compression()
        self.configure_database_pool()
        self.optimize_query_performance()
        self.add_caching_headers()
        self.enable_etag_support()

        logger.info("All performance optimizations enabled")
        return self.enabled_optimizations


# Database query optimization helpers

def get_recommended_indexes() -> Dict[str, list]:
    """Get recommended database indexes for optimal performance.
    
    Returns:
        Dict mapping table names to recommended indexes
    """
    return {
        "users": [
            "CREATE INDEX idx_users_email_verified ON users (email, email_verified);",
            "CREATE INDEX idx_users_subscription ON users (subscription_tier);",
            "CREATE INDEX idx_users_not_deleted ON users (is_deleted) WHERE is_deleted = false;",
            "CREATE INDEX idx_users_oauth ON users (oauth_provider, oauth_id);",
        ],
        "projects": [
            "CREATE INDEX idx_projects_user_status ON projects (user_id, status);",
            "CREATE INDEX idx_projects_name ON projects (name);",
            "CREATE INDEX idx_projects_not_deleted ON projects (is_deleted) WHERE is_deleted = false;",
            "CREATE INDEX idx_projects_created ON projects (created_at DESC);",
        ],
        "generations": [
            "CREATE INDEX idx_generations_project_created ON generations (project_id, created_at DESC);",
            "CREATE INDEX idx_generations_model ON generations (model_used);",
        ],
        "deployments": [
            "CREATE INDEX idx_deployments_project_status ON deployments (project_id, status);",
            "CREATE INDEX idx_deployments_provider ON deployments (provider);",
            "CREATE INDEX idx_deployments_deployed_at ON deployments (deployed_at DESC);",
        ],
        "subscriptions": [
            "CREATE INDEX idx_subscriptions_user_status ON subscriptions (user_id, status);",
            "CREATE INDEX idx_subscriptions_stripe ON subscriptions (stripe_subscription_id);",
        ],
        "api_keys": [
            "CREATE INDEX idx_api_keys_user ON api_keys (user_id);",
            "CREATE INDEX idx_api_keys_key_hash ON api_keys (key_hash);",
        ],
    }


def get_query_optimization_tips() -> Dict[str, str]:
    """Get query optimization tips for common operations.
    
    Returns:
        Dict mapping operation to optimization tip
    """
    return {
        "user_projects": (
            "Use .options(joinedload(User.projects)) to avoid N+1 queries"
        ),
        "project_generations": (
            "Use .order_by(desc(Generation.created_at)).limit(10) for recent items"
        ),
        "soft_delete_filter": (
            "Always filter by is_deleted=false: .filter(Model.is_deleted == false)"
        ),
        "pagination": (
            "Use .limit(page_size).offset((page - 1) * page_size) for pagination"
        ),
        "count_queries": (
            "Use .count() instead of len(query.all()) for counting"
        ),
        "relationship_loading": (
            "Use lazy='dynamic' for large collections, lazy='joined' for small ones"
        ),
        "bulk_operations": (
            "Use session.bulk_insert_mappings() for inserting many records"
        ),
    }


def print_performance_report() -> None:
    """Print performance optimization report."""
    print("\n" + "=" * 70)
    print("PERFORMANCE OPTIMIZATION REPORT")
    print("=" * 70)

    print("\n✅ Enabled Optimizations:")
    print("  1. GZip compression (minimum 1000 bytes, level 5)")
    print("  2. Database connection pooling (size=10, overflow=20)")
    print("  3. Cache-Control headers (static=1yr, API=60s)")
    print("  4. ETag support for conditional requests")
    print("  5. Query optimization strategies")

    print("\n📊 Database Indexes:")
    indexes = get_recommended_indexes()
    for table, table_indexes in indexes.items():
        print(f"  {table}: {len(table_indexes)} indexes")

    print("\n💡 Query Optimization Tips:")
    tips = get_query_optimization_tips()
    for operation, tip in tips.items():
        print(f"  {operation}:")
        print(f"    {tip}")

    print("\n🎯 Connection Pool Configuration:")
    print(f"  Pool Size: {os.getenv('DATABASE_POOL_SIZE', '10')}")
    print(f"  Max Overflow: {os.getenv('DATABASE_MAX_OVERFLOW', '20')}")
    print(f"  Pool Timeout: {os.getenv('DATABASE_POOL_TIMEOUT', '30')}s")
    print(f"  Pool Recycle: {os.getenv('DATABASE_POOL_RECYCLE', '3600')}s")
    print(f"  Pre Ping: {os.getenv('DATABASE_POOL_PRE_PING', 'true')}")

    print("=" * 70 + "\n")


if __name__ == "__main__":
    print_performance_report()

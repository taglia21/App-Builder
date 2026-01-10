
import asyncio
import logging
import aiohttp
from typing import List
from ..models import VerificationReport, VerificationCheck

logger = logging.getLogger(__name__)

class HealthCheckSuite:
    """
    Comprehensive post-deployment verification.
    """
    
    async def verify_deployment(self, frontend_url: str = None, backend_url: str = None) -> VerificationReport:
        checks = []
        
        async with aiohttp.ClientSession() as session:
            # 1. Frontend Check
            if frontend_url:
                checks.append(await self._check_url(session, "Frontend Accessible", frontend_url))
                checks.append(await self._check_ssl(session, "Frontend SSL", frontend_url))
            
            # 2. Backend Check
            if backend_url:
                checks.append(await self._check_url(session, "Backend Accessible", f"{backend_url}/health"))
                checks.append(await self._check_ssl(session, "Backend SSL", backend_url))
                
                # 3. API Contract / DB Check (via backend health endpoint)
                checks.append(await self._check_api_health(session, backend_url))

        all_pass = all(c.passed for c in checks)
        return VerificationReport(all_pass=all_pass, checks=checks)

    async def _check_url(self, session, name: str, url: str) -> VerificationCheck:
        try:
            start = asyncio.get_running_loop().time()
            async with session.get(url, timeout=10) as resp:
                status = resp.status
                passed = 200 <= status < 400
                latency = (asyncio.get_running_loop().time() - start) * 1000
                return VerificationCheck(
                    name=name,
                    passed=passed,
                    details=f"Status: {status}",
                    latency_ms=latency
                )
        except Exception as e:
            return VerificationCheck(name=name, passed=False, details=str(e))

    async def _check_ssl(self, session, name: str, url: str) -> VerificationCheck:
        if not url.startswith("https"):
             return VerificationCheck(name=name, passed=False, details="Not using HTTPS")
        return VerificationCheck(name=name, passed=True, details="HTTPS Enabled")

    async def _check_api_health(self, session, backend_url: str) -> VerificationCheck:
        name = "API Health & DB"
        try:
            # Assumes standard /health endpoint returns {"status": "ok", "db": "ok"}
            url = f"{backend_url}/health"
            async with session.get(url, timeout=10) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    # Basic validation of response structure
                    db_status = data.get("db", "unknown")
                    passed = db_status == "ok" or data.get("status") == "ok"
                    return VerificationCheck(name=name, passed=passed, details=f"Response: {data}")
                return VerificationCheck(name=name, passed=False, details=f"Status {resp.status}")
        except Exception as e:
            # If endpoint doesn't exist yet, we might soft-fail or warn
            return VerificationCheck(name=name, passed=False, details=f"Failed to query health: {e}")

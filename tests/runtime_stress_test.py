import asyncio
import os
import shutil
import subprocess
import time
import sys
import argparse
from pathlib import Path
import httpx
from loguru import logger

# Configure logger
logger.remove()
logger.add(sys.stderr, format="<green>{time:HH:mm:ss}</green> | <level>{message}</level>")

class RuntimeStressTest:
    def __init__(self, app_path: str, users: int = 50, run_time: str = "30s"):
        self.app_path = Path(app_path).resolve()
        self.users = users
        self.run_time = run_time
        
        if not (self.app_path / "docker-compose.yml").exists():
            raise FileNotFoundError(f"No docker-compose.yml found in {self.app_path}")

    def create_locustfile(self):
        """Create a temporary locustfile in the app directory."""
        content = """
from locust import HttpUser, task, between

class WebsiteUser(HttpUser):
    wait_time = between(1, 3)

    @task(3)
    def index(self):
        self.client.get("/")

    @task(1)
    def health_check(self):
        self.client.get("/api/health")
        
    @task(1)
    def docs(self):
        self.client.get("/docs")
"""
        with open(self.app_path / "locustfile.py", "w") as f:
            f.write(content)
        logger.info("Created temporary locustfile.py")

    async def start_app(self):
        """Start the application using Docker Compose."""
        logger.info(f"Starting Docker services in {self.app_path}...")
        try:
            subprocess.run(
                ["docker-compose", "up", "-d", "--build"],
                cwd=self.app_path,
                check=True,
                capture_output=True
            )
        except subprocess.CalledProcessError as e:
            logger.error(f"Failed to start docker: {e.stderr.decode()}")
            raise

    async def wait_for_health(self, timeout=60):
        """Wait for the API to be healthy."""
        url = "http://localhost:8000/health"
        logger.info(f"Waiting for API at {url}...")
        
        start = time.time()
        async with httpx.AsyncClient() as client:
            while time.time() - start < timeout:
                try:
                    resp = await client.get(url)
                    if resp.status_code == 200:
                        logger.success("API is Healthy!")
                        return True
                except httpx.ConnectError:
                    pass
                await asyncio.sleep(2)
        
        logger.error("Timed out waiting for API health")
        return False

    def run_locust(self):
        """Run Locust in headless mode."""
        logger.info(f"Running Locust stress test ({self.users} users, {self.run_time})...")
        
        # Output CSV prefix
        csv_prefix = "stress_test_results"
        
        cmd = [
            "locust",
            "-f", "locustfile.py",
            "--headless",
            "-u", str(self.users),
            "-r", "10",  # Spawn rate
            "--run-time", self.run_time,
            "--host", "http://localhost:8000",
            "--csv", csv_prefix
        ]
        
        try:
            subprocess.run(cmd, cwd=self.app_path, check=True, capture_output=True)
            logger.success("Locust test completed.")
            return True
        except subprocess.CalledProcessError as e:
            logger.error(f"Locust failed: {e.stderr.decode()}")
            return False

    def analyze_results(self):
        """Analyze generated CSV files."""
        stats_file = self.app_path / "stress_test_results_stats.csv"
        if not stats_file.exists():
            logger.error("No stats file generated.")
            return False
            
        import csv
        with open(stats_file, "r") as f:
            reader = csv.DictReader(f)
            total_reqs = 0
            failures = 0
            
            for row in reader:
                if row["Name"] == "Aggregated":
                    total_reqs = int(row["Request Count"])
                    failures = int(row["Failure Count"])
                    rps = float(row["Requests/s"])
                    p95 = float(row["95%"])
                    
                    logger.info("=" * 40)
                    logger.info(f"Total Requests: {total_reqs}")
                    logger.info(f"Failures:       {failures}")
                    logger.info(f"RPS:            {rps:.2f}")
                    logger.info(f"P95 Latency:    {p95:.2f}ms")
                    logger.info("=" * 40)
                    
                    if failures > 0:
                        logger.warning(f"Test finished with {failures} failures.")
                        return False
                    return True
        return False

    async def stop_app(self):
        """Stop Docker services."""
        logger.info("Stopping Docker services...")
        subprocess.run(
            ["docker-compose", "down"],
            cwd=self.app_path,
            check=True,
            capture_output=True
        )

    async def run(self):
        try:
            self.create_locustfile()
            await self.start_app()
            if await self.wait_for_health():
                success = self.run_locust()
                if success:
                    if self.analyze_results():
                        logger.success("✅ STRESS TEST PASSED")
                    else:
                        logger.error("❌ STRESS TEST FAILED (High Errors)")
                else:
                    logger.error("❌ LOCUST CMD FAILED")
            else:
                logger.error("❌ APP HEALTH CHECK FAILED")
                
        finally:
            await self.stop_app()
            # Cleanup
            if (self.app_path / "locustfile.py").exists():
                (self.app_path / "locustfile.py").unlink()
            # Cleanup csvs
            for f in self.app_path.glob("stress_test_results*.csv"):
                f.unlink()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Runtime Stress Tester")
    parser.add_argument("path", help="Path to generated app")
    parser.add_argument("--users", type=int, default=50)
    args = parser.parse_args()
    
    tester = RuntimeStressTest(args.path, users=args.users)
    asyncio.run(tester.run())

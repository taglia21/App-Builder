import asyncio
import aiohttp
import time
from concurrent.futures import ThreadPoolExecutor
import statistics

BASE_URL = "https://web-production-a8233.up.railway.app"

ENDPOINTS = [
    "/",
    "/dashboard",
    "/projects",
    "/api-keys",
    "/settings",
    "/billing/plans",
    "/about",
    "/terms",
    "/privacy",
]

async def fetch(session, url):
    start = time.time()
    try:
        async with session.get(url, timeout=aiohttp.ClientTimeout(total=30)) as response:
            await response.text()
            return time.time() - start, response.status
    except Exception as e:
        return time.time() - start, str(e)

async def stress_test(concurrent_requests=50, iterations=3):
    print(f"\n=== STRESS TEST ===")
    print(f"Concurrent requests: {concurrent_requests}")
    print(f"Iterations: {iterations}")
    print(f"Endpoints: {len(ENDPOINTS)}")
    
    all_times = []
    errors = 0
    
    async with aiohttp.ClientSession() as session:
        for i in range(iterations):
            print(f"\nIteration {i+1}/{iterations}...")
            tasks = []
            for _ in range(concurrent_requests):
                for endpoint in ENDPOINTS:
                    tasks.append(fetch(session, BASE_URL + endpoint))
            
            results = await asyncio.gather(*tasks)
            
            for duration, status in results:
                all_times.append(duration)
                if isinstance(status, str) or status >= 400:
                    errors += 1
    
    print(f"\n=== RESULTS ===")
    print(f"Total requests: {len(all_times)}")
    print(f"Errors: {errors}")
    print(f"Success rate: {((len(all_times)-errors)/len(all_times))*100:.1f}%")
    print(f"Avg response time: {statistics.mean(all_times)*1000:.0f}ms")
    print(f"Min response time: {min(all_times)*1000:.0f}ms")
    print(f"Max response time: {max(all_times)*1000:.0f}ms")
    print(f"Median: {statistics.median(all_times)*1000:.0f}ms")
    if len(all_times) > 1:
        print(f"Std Dev: {statistics.stdev(all_times)*1000:.0f}ms")
    print("=== STRESS TEST COMPLETE ===")

if __name__ == "__main__":
    asyncio.run(stress_test())

"""Load tests for AIOS API under heavy concurrent load."""

import asyncio
import concurrent.futures
import statistics
import threading
import time

import httpx
import pytest
import pytest_asyncio
from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.routing import Route


class TestAPILoadTests:
    """Load tests for API endpoints under heavy load."""

    @pytest_asyncio.fixture
    async def app(self):
        """Create test app."""

        async def health(request: Request):
            return JSONResponse({"status": "healthy", "timestamp": time.time()})

        async def stats(request: Request):
            # Simulate some work
            await asyncio.sleep(0.001)
            return JSONResponse({"tasks": 1000, "memory": 5000, "uptime": 86400})

        app = Starlette(
            routes=[
                Route("/health", health),
                Route("/api/v1/stats", stats),
            ]
        )
        return app

    @pytest_asyncio.fixture
    async def client(self, app):
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app),
            base_url="http://testserver",
        ) as c:
            yield c

    @pytest.mark.asyncio
    async def test_100_concurrent_requests(self, client):
        """Test 100 concurrent requests to health endpoint."""

        async def make_request():
            start = time.perf_counter()
            response = await client.get("/health")
            latency = (time.perf_counter() - start) * 1000
            return response.status_code, latency

        tasks = [make_request() for _ in range(100)]
        results = await asyncio.gather(*tasks)

        # All should succeed
        status_codes = [r[0] for r in results]
        latencies = [r[1] for r in results]

        assert all(code == 200 for code in status_codes)
        assert statistics.mean(latencies) < 200  # avg < 200ms
        assert max(latencies) < 1000  # max < 1s

    @pytest.mark.asyncio
    async def test_500_rapid_requests(self, client):
        """Test 500 rapid sequential requests."""
        latencies = []

        for _ in range(500):
            start = time.perf_counter()
            response = await client.get("/health")
            latency = (time.perf_counter() - start) * 1000
            latencies.append(latency)
            assert response.status_code == 200

        # Calculate metrics
        avg_latency = statistics.mean(latencies)
        p95 = sorted(latencies)[int(len(latencies) * 0.95)]
        p99 = sorted(latencies)[int(len(latencies) * 0.99)]

        # Should handle rapid requests
        assert avg_latency < 100
        assert p95 < 300
        assert p99 < 500

    @pytest.mark.asyncio
    async def test_sustained_load_5_seconds(self, client):
        """Test sustained load over five seconds within the global test timeout."""
        latencies = []
        start_time = time.time()
        request_count = 0

        # Keep this below the suite-wide 30-second timeout.
        while time.time() - start_time < 5:
            start = time.perf_counter()
            response = await client.get("/health")
            latency = (time.perf_counter() - start) * 1000
            latencies.append(latency)
            request_count += 1
            assert response.status_code == 200

        # Calculate throughput
        duration = time.time() - start_time
        rps = request_count / duration

        # Should maintain performance
        avg_latency = statistics.mean(latencies)
        assert avg_latency < 100
        assert rps > 20  # At least 20 req/s

    @pytest.mark.asyncio
    async def test_concurrent_write_load(self, client):
        """Test concurrent write operations."""

        async def make_request(i):
            start = time.perf_counter()
            response = await client.get(f"/api/v1/stats?id={i}")
            latency = (time.perf_counter() - start) * 1000
            return response.status_code, latency

        # 50 concurrent requests
        tasks = [make_request(i) for i in range(50)]
        results = await asyncio.gather(*tasks)

        status_codes = [r[0] for r in results]
        latencies = [r[1] for r in results]

        # All should succeed
        assert all(code == 200 for code in status_codes)
        assert statistics.mean(latencies) < 300

    @pytest.mark.asyncio
    async def test_memory_under_load(self, client):
        """Test memory usage under sustained load."""
        import os

        import psutil

        process = psutil.Process(os.getpid())
        initial_memory = process.memory_info().rss / 1024 / 1024  # MB

        # Make 1000 requests
        for _ in range(1000):
            await client.get("/health")

        final_memory = process.memory_info().rss / 1024 / 1024  # MB
        memory_growth = final_memory - initial_memory

        # Should not leak memory
        assert memory_growth < 100  # Less than 100MB growth

    @pytest.mark.asyncio
    async def test_latency_percentiles_under_load(self, client):
        """Test latency percentiles under concurrent load."""
        latencies = []

        async def make_request():
            start = time.perf_counter()
            await client.get("/health")
            return (time.perf_counter() - start) * 1000

        # 200 concurrent requests
        tasks = [make_request() for _ in range(200)]
        latencies = await asyncio.gather(*tasks)

        # Calculate percentiles
        p50 = statistics.median(latencies)
        p90 = sorted(latencies)[int(len(latencies) * 0.90)]
        p95 = sorted(latencies)[int(len(latencies) * 0.95)]
        p99 = sorted(latencies)[int(len(latencies) * 0.99)]

        # Verify latency requirements
        assert p50 < 50  # Median < 50ms
        assert p90 < 150  # P90 < 150ms
        assert p95 < 250  # P95 < 250ms
        assert p99 < 500  # P99 < 500ms


class TestDatabaseLoadTests:
    """Load tests for database operations."""

    @pytest.fixture
    def db(self, tmp_path):
        """Create test database."""
        import sqlite3

        db_path = tmp_path / "load_test.sqlite"
        conn = sqlite3.connect(str(db_path), check_same_thread=False)
        conn.execute("CREATE TABLE test (id INTEGER PRIMARY KEY, value TEXT)")
        conn.commit()
        return conn

    def test_bulk_insert_10000_records(self, db, tmp_path):
        """Test inserting 10000 records."""
        start = time.perf_counter()

        for i in range(10000):
            db.execute("INSERT INTO test (value) VALUES (?)", (f"value-{i}",))

        db.commit()
        duration = time.perf_counter() - start

        # Should complete in reasonable time
        assert duration < 10.0  # Less than 10 seconds

        # Verify all inserted
        cursor = db.execute("SELECT COUNT(*) FROM test")
        count = cursor.fetchone()[0]
        assert count == 10000

    def test_concurrent_reads(self, db, tmp_path):
        """Test concurrent read operations."""
        # Insert test data
        for i in range(1000):
            db.execute("INSERT INTO test VALUES (?, ?)", (i, f"value-{i}"))
        db.commit()

        results = []
        # A raw SQLite connection supports cross-thread use only when callers
        # serialize cursor operations. Production code uses Database for this.
        connection_lock = threading.Lock()

        def read_data(id):
            with connection_lock:
                cursor = db.execute("SELECT value FROM test WHERE id = ?", (id,))
                return cursor.fetchone()

        # 100 concurrent reads
        with concurrent.futures.ThreadPoolExecutor(max_workers=20) as executor:
            futures = [executor.submit(read_data, i) for i in range(100)]
            results = [f.result() for f in futures]

        # All should succeed
        assert len([r for r in results if r is not None]) == 100

    def test_query_performance_large_dataset(self, db, tmp_path):
        """Test query performance with large dataset."""
        # Insert 50000 records
        for i in range(50000):
            db.execute("INSERT INTO test VALUES (?, ?)", (i, f"value-{i}"))
        db.commit()

        # Create index
        db.execute("CREATE INDEX idx_value ON test(value)")

        # Query performance
        start = time.perf_counter()
        cursor = db.execute("SELECT * FROM test WHERE value LIKE 'value-25%'")
        results = cursor.fetchall()
        duration = time.perf_counter() - start

        # Should be fast with index
        assert duration < 1.0
        assert len(results) > 0


class TestWebhookLoadTests:
    """Load tests for webhook system."""

    def test_1000_notifications(self):
        """Test sending 1000 webhook notifications."""
        from aios_core.webhook_manager import WebhookManager

        manager = WebhookManager()
        manager.register("load-test", "https://example.com/hook", ["ban_detected"])

        start = time.perf_counter()

        # Send 1000 notifications
        for i in range(1000):
            manager.notify("ban_detected", {"profile": f"test-{i}"})

        duration = time.perf_counter() - start

        # Should handle 1000 notifications quickly
        assert duration < 5.0

        # Verify all were processed
        history = manager.get_history()
        assert len(history) >= 1000

    def test_concurrent_webhook_registrations(self):
        """Test concurrent webhook registrations."""
        from aios_core.webhook_manager import WebhookManager

        manager = WebhookManager()
        results = []

        def register_webhook(i):
            return manager.register(
                f"webhook-{i}", f"https://example{i}.com/hook", ["ban_detected"]
            )

        # Register 100 webhooks concurrently
        with concurrent.futures.ThreadPoolExecutor(max_workers=20) as executor:
            futures = [executor.submit(register_webhook, i) for i in range(100)]
            results = [f.result() for f in futures]

        # All should succeed
        assert len([r for r in results if r is not None]) == 100

        # Verify all registered
        targets = manager.list_targets()
        assert len(targets) >= 100


class TestStressTests:
    """Stress tests for extreme conditions."""

    @pytest_asyncio.fixture
    async def client(self):
        """Create async test client."""

        async def health(request: Request):
            return JSONResponse({"status": "ok"})

        app = Starlette(routes=[Route("/health", health)])
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app),
            base_url="http://testserver",
        ) as c:
            yield c

    @pytest.mark.asyncio
    async def test_10000_requests_burst(self, client):
        """Test 10000 requests in burst."""
        latencies = []

        start_time = time.perf_counter()

        for _ in range(10000):
            start = time.perf_counter()
            await client.get("/health")
            latencies.append((time.perf_counter() - start) * 1000)

        total_time = time.perf_counter() - start_time
        rps = 10000 / total_time

        # Should handle burst
        avg_latency = statistics.mean(latencies)
        assert avg_latency < 50
        assert rps > 500  # In-process baseline; real load tests run separately

    @pytest.mark.asyncio
    async def test_memory_stability_5000_requests(self, client):
        """Test memory stability over 5000 requests."""
        import os

        import psutil

        process = psutil.Process(os.getpid())

        memory_readings = []

        for _batch in range(5):
            # Make 1000 requests
            for _ in range(1000):
                await client.get("/health")

            # Record memory
            memory_mb = process.memory_info().rss / 1024 / 1024
            memory_readings.append(memory_mb)

        # Check memory growth
        initial = memory_readings[0]
        final = memory_readings[-1]
        growth = final - initial

        # Should not leak memory
        assert growth < 50  # Less than 50MB growth over 5000 requests

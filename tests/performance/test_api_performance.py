"""Performance tests for AIOS API endpoints."""

import statistics
import time

import httpx
import pytest
import pytest_asyncio
from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.routing import Route


class TestAPIPerformance:
    """Performance benchmarks for critical API endpoints."""

    @pytest.fixture
    def simple_app(self):
        """Create a simple test app."""

        async def health(request: Request):
            return JSONResponse({"status": "healthy"})

        async def stats(request: Request):
            return JSONResponse(
                {"tasks_total": 1000, "memory_total": 5000, "uptime_seconds": 86400}
            )

        async def metrics(request: Request):
            # Simulate metrics generation
            metrics_text = """# HELP test_counter Test counter
# TYPE test_counter counter
test_counter 1000
# HELP test_gauge Test gauge
# TYPE test_gauge gauge
test_gauge 42.5
"""
            return JSONResponse({"metrics": metrics_text})

        app = Starlette(
            routes=[
                Route("/health", health),
                Route("/api/v1/stats", stats),
                Route("/metrics", metrics),
            ]
        )
        return app

    @pytest_asyncio.fixture
    async def client(self, simple_app):
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=simple_app),
            base_url="http://testserver",
        ) as c:
            yield c

    @pytest.mark.asyncio
    async def test_health_endpoint_latency(self, client):
        """Test health endpoint response time."""
        latencies = []

        # Warm up
        for _ in range(10):
            await client.get("/health")

        # Measure
        for _ in range(100):
            start = time.perf_counter()
            response = await client.get("/health")
            latency = (time.perf_counter() - start) * 1000  # ms
            latencies.append(latency)
            assert response.status_code == 200

        # Analyze
        avg_latency = statistics.mean(latencies)
        p50 = statistics.median(latencies)
        p95 = sorted(latencies)[int(len(latencies) * 0.95)]
        p99 = sorted(latencies)[int(len(latencies) * 0.99)]

        # Assert performance
        assert avg_latency < 50, f"Average latency {avg_latency:.2f}ms > 50ms"
        assert p95 < 100, f"P95 latency {p95:.2f}ms > 100ms"
        assert p99 < 200, f"P99 latency {p99:.2f}ms > 200ms"

    async def test_stats_endpoint_latency(self, client):
        """Test stats endpoint response time."""
        latencies = []

        # Warm up
        for _ in range(10):
            await client.get("/api/v1/stats")

        # Measure
        for _ in range(100):
            start = time.perf_counter()
            response = await client.get("/api/v1/stats")
            latency = (time.perf_counter() - start) * 1000
            latencies.append(latency)
            assert response.status_code == 200

        # Analyze
        avg_latency = statistics.mean(latencies)
        p95 = sorted(latencies)[int(len(latencies) * 0.95)]

        # Assert performance
        assert avg_latency < 100, f"Average latency {avg_latency:.2f}ms > 100ms"
        assert p95 < 200, f"P95 latency {p95:.2f}ms > 200ms"

    async def test_metrics_endpoint_latency(self, client):
        """Test metrics endpoint response time."""
        latencies = []

        # Warm up
        for _ in range(10):
            await client.get("/metrics")

        # Measure
        for _ in range(100):
            start = time.perf_counter()
            response = await client.get("/metrics")
            latency = (time.perf_counter() - start) * 1000
            latencies.append(latency)
            assert response.status_code == 200

        # Analyze
        avg_latency = statistics.mean(latencies)
        p95 = sorted(latencies)[int(len(latencies) * 0.95)]

        # Assert performance
        assert avg_latency < 100, f"Average latency {avg_latency:.2f}ms > 100ms"
        assert p95 < 200, f"P95 latency {p95:.2f}ms > 200ms"

    async def test_concurrent_requests(self, client):
        """Test handling of concurrent requests."""
        import concurrent.futures

        def make_request():
            start = time.perf_counter()
            response = await client.get("/health")
            latency = (time.perf_counter() - start) * 1000
            return latency

        # Make 50 concurrent requests
        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(make_request) for _ in range(50)]
            latencies = [f.result() for f in futures]

        # Analyze
        avg_latency = statistics.mean(latencies)
        p95 = sorted(latencies)[int(len(latencies) * 0.95)]

        # Should handle concurrent load
        assert avg_latency < 200, f"Average latency under load {avg_latency:.2f}ms > 200ms"
        assert p95 < 500, f"P95 latency under load {p95:.2f}ms > 500ms"

    async def test_sustained_load(self, client):
        """Test sustained load over time."""
        latencies = []

        # Simulate 5 seconds of sustained load
        start_time = time.time()
        request_count = 0

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

        # Analyze
        avg_latency = statistics.mean(latencies)
        p95 = sorted(latencies)[int(len(latencies) * 0.95)]

        # Should maintain performance under sustained load
        assert avg_latency < 100, f"Average latency under sustained load {avg_latency:.2f}ms"
        assert rps > 10, f"Throughput {rps:.2f} req/s < 10 req/s"

    async def test_response_size_impact(self, client):
        """Test that larger responses don't significantly impact latency."""
        small_latencies = []
        large_latencies = []

        # Measure small response
        for _ in range(50):
            start = time.perf_counter()
            await client.get("/health")
            small_latencies.append((time.perf_counter() - start) * 1000)

        # Measure larger response
        for _ in range(50):
            start = time.perf_counter()
            await client.get("/api/v1/stats")
            large_latencies.append((time.perf_counter() - start) * 1000)

        # Compare
        small_avg = statistics.mean(small_latencies)
        large_avg = statistics.mean(large_latencies)

        # Larger response should not be more than 2x slower
        ratio = large_avg / small_avg
        assert ratio < 2.0, f"Large response {ratio:.2f}x slower than small response"


class TestDatabasePerformance:
    """Database performance benchmarks."""

    @pytest.fixture
    def large_db(self, tmp_path):
        """Create a database with large dataset."""
        import sqlite3

        db_path = tmp_path / "large.sqlite"
        conn = sqlite3.connect(str(db_path))

        conn.execute(
            """
            CREATE TABLE tasks (
                id TEXT PRIMARY KEY,
                status TEXT,
                created_at TEXT,
                data TEXT
            )
        """
        )

        # Insert 10000 records
        for i in range(10000):
            conn.execute(
                "INSERT INTO tasks VALUES (?, ?, ?, ?)",
                (
                    f"task-{i}",
                    "completed",
                    f"2026-01-{i % 28 + 1:02d}",
                    f'{{"index": {i}, "data": "value-{i}"}}',
                ),
            )

        conn.commit()
        conn.close()
        return str(db_path)

    async def test_query_performance_with_index(self, large_db, tmp_path):
        """Test query performance with indexed data."""
        import sqlite3

        conn = sqlite3.connect(large_db)

        # Create index
        conn.execute("CREATE INDEX idx_status ON tasks(status)")
        conn.commit()

        # Measure query time
        start = time.perf_counter()
        cursor = conn.execute("SELECT COUNT(*) FROM tasks WHERE status = 'completed'")
        count = cursor.fetchone()[0]
        query_time = (time.perf_counter() - start) * 1000

        assert count == 10000
        assert query_time < 100, f"Query took {query_time:.2f}ms > 100ms"

        conn.close()

    async def test_insert_performance(self, tmp_path):
        """Test bulk insert performance."""
        import sqlite3

        db_path = tmp_path / "insert_test.sqlite"
        conn = sqlite3.connect(str(db_path))

        conn.execute("CREATE TABLE items (id INTEGER PRIMARY KEY, value TEXT)")

        # Measure insert performance
        start = time.perf_counter()
        for i in range(1000):
            conn.execute("INSERT INTO items VALUES (?, ?)", (i, f"value-{i}"))
        conn.commit()
        insert_time = (time.perf_counter() - start) * 1000

        assert insert_time < 1000, f"1000 inserts took {insert_time:.2f}ms > 1000ms"

        conn.close()

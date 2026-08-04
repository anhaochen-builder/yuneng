"""性能压测 — 并发请求 + 状态串扰检测 + 缓冲区并发安全"""
import asyncio
import threading
import time
import pytest

from fastapi.testclient import TestClient


@pytest.fixture
def client():
    from app.main import app
    return TestClient(app)


# ─── 并发压测 (50 并发) ───

class TestConcurrency:
    def test_concurrent_health_50(self, client):
        """50 并发健康检查 — 验证无死锁"""
        import concurrent.futures

        def request_health():
            r = client.get("/health")
            return r.status_code

        with concurrent.futures.ThreadPoolExecutor(max_workers=50) as pool:
            futures = [pool.submit(request_health) for _ in range(50)]
            results = [f.result() for f in concurrent.futures.as_completed(futures)]

        assert len(results) == 50
        assert all(r == 200 for r in results), f"失败请求: {results.count(0)}"

    def test_concurrent_dashboard_30(self, client):
        """30 并发 Dashboard — 验证无状态串扰"""
        import concurrent.futures

        def request_dashboard(idx):
            r = client.get("/api/dashboard")
            data = r.json()
            return data.get("project", "")

        with concurrent.futures.ThreadPoolExecutor(max_workers=30) as pool:
            futures = [pool.submit(request_dashboard, i) for i in range(30)]
            results = [f.result() for f in concurrent.futures.as_completed(futures)]

        assert len(results) == 30
        assert all("驭能" in str(r) for r in results), "状态串扰检测"

    def test_concurrent_mixed_20(self, client):
        """20 并发混合请求 — 验证多端点无干扰"""
        import concurrent.futures

        def request_endpoint(endpoint):
            r = client.get(endpoint)
            return r.status_code

        endpoints = [
            "/health", "/api/dashboard", "/api/dashboard/phases",
            "/api/skills", "/api/tools/list", "/api/audit",
            "/api/audit/skills", "/api/feedback/stats",
            "/api/knowledge/health", "/api/scada/health",
        ] * 2

        with concurrent.futures.ThreadPoolExecutor(max_workers=20) as pool:
            futures = [pool.submit(request_endpoint, ep) for ep in endpoints]
            results = [f.result() for f in concurrent.futures.as_completed(futures)]

        assert len(results) == 20
        assert all(r == 200 for r in results)


# ─── 响应时间基准 ───

class TestLatency:
    def test_health_latency(self, client):
        t0 = time.perf_counter()
        r = client.get("/health")
        elapsed = time.perf_counter() - t0
        assert r.status_code == 200
        assert elapsed < 1.0, f"健康检查超时: {elapsed:.3f}s"

    def test_dashboard_latency(self, client):
        t0 = time.perf_counter()
        r = client.get("/api/dashboard")
        elapsed = time.perf_counter() - t0
        assert r.status_code == 200
        assert elapsed < 3.0, f"Dashboard 超时: {elapsed:.3f}s"

    def test_audit_latency(self, client):
        t0 = time.perf_counter()
        r = client.get("/api/audit")
        elapsed = time.perf_counter() - t0
        assert r.status_code == 200
        assert elapsed < 5.0, f"审计报告超时: {elapsed:.3f}s"


# ─── 环形缓冲区并发安全 ───

class TestBufferConcurrency:
    def test_concurrent_push_many_threads(self):
        from app.scada.ring_buffer import RingBuffer
        from app.scada.base import ScadaDataPoint
        buf = RingBuffer(capacity=100000)
        n_threads = 20
        n_points = 500
        errors = []

        def push_worker(tid):
            try:
                for i in range(n_points):
                    dp = ScadaDataPoint(
                        timestamp=f"T{tid:02d}-{i:04d}",
                        device_id=f"DEV{tid}",
                        point_name="p",
                        value=float(i),
                        unit="",
                    )
                    buf.push(dp)
            except Exception as e:
                errors.append(str(e))

        threads = [threading.Thread(target=push_worker, args=(i,)) for i in range(n_threads)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(errors) == 0, f"并发写入错误: {errors}"
        assert buf._total_written == n_threads * n_points
        # 数据一致性: 缓冲区数量不超过容量
        assert len(buf._buffer) <= buf._capacity

    def test_concurrent_push_mixed_devices(self):
        from app.scada.ring_buffer import RingBuffer
        from app.scada.base import ScadaDataPoint
        buf = RingBuffer(capacity=50000)
        device_ids = [f"WT{i:03d}" for i in range(10)]
        n_per_device = 300
        errors = []

        def push_worker(device_id):
            try:
                for i in range(n_per_device):
                    dp = ScadaDataPoint(
                        timestamp=f"{device_id}-{i:04d}",
                        device_id=device_id,
                        point_name="温度",
                        value=float(50 + i % 40),
                        unit="°C",
                    )
                    buf.push(dp)
            except Exception as e:
                errors.append(str(e))

        threads = [threading.Thread(target=push_worker, args=(d,)) for d in device_ids]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(errors) == 0
        assert buf._total_written == len(device_ids) * n_per_device

        # 每个设备的数据都能检索到
        for device_id in device_ids:
            all_pts = [p for p in buf._buffer if p.device_id == device_id]
            assert len(all_pts) > 0, f"设备 {device_id} 数据丢失"


# ─── 知识库并发检索 ───

class TestKnowledgeConcurrency:
    def test_concurrent_rag_search(self):
        from app.rag.hybrid_search import get_knowledge_store
        import concurrent.futures
        store = get_knowledge_store()
        queries = ["IGBT过热", "齿轮箱", "变压器", "安全规程", "通讯中断",
                    "逆变器", "风机", "过压", "过流", "绝缘"] * 2

        def search_q(q):
            try:
                results = store.search(q, top_k=3)
                return len(results)
            except Exception as e:
                return -1

        with concurrent.futures.ThreadPoolExecutor(max_workers=20) as pool:
            futures = [pool.submit(search_q, q) for q in queries]
            results = [f.result() for f in concurrent.futures.as_completed(futures)]

        assert len(results) == 20
        assert all(r > 0 for r in results), "并发检索异常"

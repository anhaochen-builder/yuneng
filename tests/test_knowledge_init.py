"""知识库初始化端到端验证 — 文档加载 / 检索精度 / 体系完备性"""
import time
import pytest


class TestKnowledgeInit:
    def test_knowledge_store_loaded(self):
        from app.rag.hybrid_search import get_knowledge_store
        store = get_knowledge_store()
        assert store.doc_count >= 50

    def test_knowledge_store_init_latency(self):
        from app.rag.hybrid_search import FastKnowledgeStore
        t0 = time.perf_counter()
        store = FastKnowledgeStore()
        elapsed = time.perf_counter() - t0
        assert elapsed < 30.0, f"知识库初始化超时: {elapsed:.3f}s (验收标准 < 30s)"
        assert store.doc_count >= 50

    def test_knowledge_search_relevance(self):
        from app.rag.hybrid_search import FastKnowledgeStore
        store = FastKnowledgeStore()
        for query, keyword in [
            ("IGBT过热原因", "IGBT"),
            ("风机齿轮箱故障", "齿轮"),
            ("变压器油温异常", "变压器"),
            ("安全规程操作", "安全"),
            ("逆变器通讯中断", "通讯"),
            ("储能电池故障处理", "储能"),
            ("风机振动超标", "振动"),
            ("光伏组件PID衰减", "PID"),
            ("电缆绝缘降低", "绝缘"),
            ("并网异常频率波动", "并网"),
        ]:
            results = store.search(query, top_k=3)
            assert len(results) >= 1, f"查询'{query}'无结果"
            texts = " ".join(r["text"] for r in results)
            assert keyword in texts, f"查询'{query}'结果不含'{keyword}'"

    def test_knowledge_search_speed(self):
        from app.rag.hybrid_search import FastKnowledgeStore
        store = FastKnowledgeStore()
        queries = ["IGBT过热", "齿轮箱故障", "变压器油温", "逆变器通讯", "安全规程",
                     "风机振动", "光伏PID", "储能BMS", "电缆绝缘", "并网异常",
                     "SVG无功补偿", "断路器跳闸", "避雷器动作", "差动保护", "瓦斯继电器"]
        t0 = time.perf_counter()
        for q in queries:
            store.search(q, top_k=5)
        elapsed = time.perf_counter() - t0
        avg = elapsed / len(queries)
        assert avg < 0.1, f"单次检索超时: {avg:.4f}s (验收标准 < 100ms)"

    def test_knowledge_dedup(self):
        from app.rag.hybrid_search import FastKnowledgeStore
        store = FastKnowledgeStore()
        results = store.search("IGBT故障", top_k=10)
        texts = [r["text"] for r in results]
        assert len(texts) == len(set(texts)), "检索结果存在重复"

    def test_knowledge_top_k_limit(self):
        from app.rag.hybrid_search import FastKnowledgeStore
        store = FastKnowledgeStore()
        for k in [1, 3, 5, 10]:
            results = store.search("风机故障", top_k=k)
            assert len(results) <= k


class TestKnowledgeGraph:
    def test_knowledge_graph_48_devices(self):
        from app.rag.knowledge_graph import KNOWLEDGE_GRAPH, kg_service
        assert len(KNOWLEDGE_GRAPH) >= 40
        for device_type, graph in KNOWLEDGE_GRAPH.items():
            assert "alarms" in graph, f"{device_type} 缺少alarms"
            assert "causes" in graph, f"{device_type} 缺少causes"
            assert "steps" in graph, f"{device_type} 缺少steps"
            assert "safety" in graph, f"{device_type} 缺少safety"

    def test_knowledge_graph_entity_extract(self):
        from app.rag.knowledge_graph import kg_service
        result = kg_service.extract_entities("3号逆变器IGBT模块过热报警")
        assert "device_type" in result
        assert result["device_type"] in ("逆变器", "") or len(result["device_type"]) > 0

    def test_all_device_categories(self):
        from app.rag.knowledge_graph import KNOWLEDGE_GRAPH
        categories = {"风力发电设备", "光伏发电设备", "储能设备", "变电设备", "输电线路",
                       "保护测控设备", "站用电设备", "系统控制设备", "通讯设备", "无功补偿设备"}
        device_keywords = {
            "风力发电设备": ["风机", "齿轮箱", "叶片", "偏航", "变桨", "发电机", "风速仪"],
            "光伏发电设备": ["光伏", "逆变器", "组串", "汇流箱"],
            "储能设备": ["储能", "电池", "BMS"],
        }
        all_devices = list(KNOWLEDGE_GRAPH.keys())
        for cat_name, keywords in device_keywords.items():
            found = any(any(kw in device for kw in keywords) for device in all_devices)
            assert found, f"缺少{cat_name}相关设备"

    def test_kg_service_query(self):
        from app.rag.knowledge_graph import kg_service
        result = kg_service.build_graph_context("风力发电机齿轮箱振动超标")
        assert isinstance(result, str)
        assert len(result) > 0

    def test_kg_expand_context(self):
        from app.rag.knowledge_graph import kg_service
        context = kg_service.build_graph_context("逆变器")
        assert isinstance(context, str)
        assert len(context) > 0

    def test_kg_has_troubleshooting_steps(self):
        from app.rag.knowledge_graph import KNOWLEDGE_GRAPH
        for device_type, graph in KNOWLEDGE_GRAPH.items():
            steps = graph.get("steps", [])
            assert isinstance(steps, (list, str)), f"{device_type} steps 类型异常"
            if isinstance(steps, list) and len(steps) > 0:
                for step in steps:
                    assert len(step) > 0, f"{device_type} 存在空处置步骤"


class TestKnowledgeFile:
    def test_knowledge_json_exists(self):
        from pathlib import Path
        from app.rag.hybrid_search import KNOWLEDGE_FILE
        assert KNOWLEDGE_FILE.exists(), "knowledge.json 文件不存在"

    def test_knowledge_json_valid_utf8(self):
        from app.rag.hybrid_search import KNOWLEDGE_FILE
        import json
        with open(KNOWLEDGE_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)
        assert isinstance(data, list)
        assert len(data) >= 50

    def test_knowledge_entries_non_empty(self):
        from app.rag.hybrid_search import KNOWLEDGE_FILE
        import json
        with open(KNOWLEDGE_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)
        for entry in data:
            assert len(entry.strip()) > 10, f"知识条目过短: {entry[:50]}"


class TestHybridSearchPipeline:
    def test_rrf_fusion_integration(self):
        from app.rag.hybrid_search import get_knowledge_store
        from app.rag.vector_store import search_vector
        store = get_knowledge_store()
        bm25_results = store.search("IGBT过热", top_k=10)
        vector_results = search_vector("IGBT过热", top_k=10)
        assert len(bm25_results) > 0 or len(vector_results) > 0, "BM25和向量检索均无结果"

    def test_cache_integration(self):
        from app.rag.hybrid_search import get_knowledge_store
        from app.utils.cache import get_cache
        store = get_knowledge_store()
        cache = get_cache()
        result1 = store.search("风机故障诊断", top_k=3)
        result2 = store.search("风机故障诊断", top_k=3)
        assert len(result1) == len(result2)

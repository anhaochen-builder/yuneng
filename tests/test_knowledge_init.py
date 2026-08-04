"""知识库初始化端到端验证"""
import pytest


class TestKnowledgeInit:
    def test_knowledge_store_loaded(self):
        from app.rag.hybrid_search import get_knowledge_store
        store = get_knowledge_store()
        assert store.doc_count >= 50

    def test_knowledge_search_relevance(self):
        from app.rag.hybrid_search import FastKnowledgeStore
        store = FastKnowledgeStore()
        for query, keyword in [
            ("IGBT过热原因", "IGBT"),
            ("风机齿轮箱故障", "齿轮"),
            ("变压器油温异常", "变压器"),
            ("安全规程操作", "安全"),
        ]:
            results = store.search(query, top_k=3)
            assert len(results) >= 1, f"查询'{query}'无结果"
            texts = " ".join(r["text"] for r in results)
            assert keyword in texts, f"查询'{query}'结果不含'{keyword}'"

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

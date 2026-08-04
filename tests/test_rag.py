"""RAG + 知识库层测试"""
import pytest


class TestKnowledgeStore:
    def test_store_loaded(self):
        from app.rag.hybrid_search import get_knowledge_store
        store = get_knowledge_store()
        assert store.doc_count >= 10

    def test_keyword_search(self):
        from app.rag.hybrid_search import FastKnowledgeStore
        store = FastKnowledgeStore()
        for query in ["IGBT过热", "齿轮箱", "变压器", "安全规程", "通讯中断"]:
            results = store.search(query, top_k=3)
            assert len(results) > 0, f"查询'{query}'返回0条结果"

    def test_search_relevance(self):
        from app.rag.hybrid_search import FastKnowledgeStore
        store = FastKnowledgeStore()
        results = store.search("IGBT过热散热风扇", top_k=3)
        assert len(results) >= 2
        first = results[0]["text"]
        assert "IGBT" in first or "散热" in first

    def test_add_documents(self):
        from app.rag.hybrid_search import get_knowledge_store
        store = get_knowledge_store()
        before = store.doc_count
        store.add(["测试文档：风机齿轮箱轴承磨损需要及时更换"])
        assert store.doc_count == before + 1

    def test_search_empty_query(self):
        from app.rag.hybrid_search import FastKnowledgeStore
        store = FastKnowledgeStore()
        results = store.search("", top_k=3)
        assert isinstance(results, list)


class TestGraphRAG:
    def test_extract_entities_fan(self):
        from app.rag.graphrag import graphrag_service
        entities = graphrag_service.extract_entities("风机齿轮箱断齿振动超标")
        assert entities["device_type"] in ("风机", "未知")

    def test_extract_entities_inverter(self):
        from app.rag.graphrag import graphrag_service
        entities = graphrag_service.extract_entities("逆变器IGBT过热报警")
        assert "逆变器" in entities["device_type"]

    def test_graph_context(self):
        from app.rag.graphrag import graphrag_service
        ctx = graphrag_service.build_graph_context("逆变器IGBT过热")
        assert len(ctx) >= 0

    def test_query_graph(self):
        from app.rag.graphrag import graphrag_service
        result = graphrag_service.query_graph("风机", depth=1)
        assert "entity" in result
        assert len(result["related"]) >= 1


class TestKnowledgeGraph:
    def test_entity_extract(self):
        from app.rag.knowledge_graph import KnowledgeGraphService
        kg = KnowledgeGraphService()
        entities = kg.extract_entities("3号逆变器IGBT模块过热")
        assert isinstance(entities, dict)
        assert "device_type" in entities

    def test_graph_context_build(self):
        from app.rag.knowledge_graph import KnowledgeGraphService
        kg = KnowledgeGraphService()
        ctx = kg.build_graph_context("风机齿轮箱振动")
        assert isinstance(ctx, str)

    def test_fault_patterns(self):
        from app.rag.knowledge_graph import KnowledgeGraphService
        kg = KnowledgeGraphService()
        entities = kg.extract_entities("变压器油温过高铁芯接地")
        assert "device_type" in entities

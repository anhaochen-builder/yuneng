"""Agent 层单元测试"""
import pytest


class TestLLMClient:
    def test_llm_import(self):
        from app.agent.llm_client import llm
        assert llm is not None
        assert hasattr(llm, 'chat')
        assert hasattr(llm, 'chat_json')

    def test_llm_chat_basic(self):
        from app.agent.llm_client import llm
        result = llm.chat("你是助手。简短回答。", "你好", max_tokens=50)
        assert len(result) > 0

    def test_llm_json(self):
        from app.agent.llm_client import llm
        result = llm.chat_json(
            "输出JSON: {\"answer\": \"yes\"}",
            "测试",
            temperature=0.1,
        )
        assert isinstance(result, dict)


class TestSubAgentBase:
    def test_registry_size(self):
        from app.graph.sub_agent import sub_agent_registry
        assert len(sub_agent_registry) == 6

    def test_all_agents_compile(self):
        from app.graph.sub_agent import sub_agent_registry
        for agent in sub_agent_registry._agents.values():
            compiled = agent.build()
            assert compiled is not None
            assert len(compiled.nodes) >= 1

    def test_diagnosis_agent_has_nodes(self):
        from app.graph.sub_agent import sub_agent_registry
        agent = sub_agent_registry.get("diagnosis-agent")
        compiled = agent.build()
        nodes = [n for n in compiled.nodes.keys() if n != "__start__"]
        assert "context_load" in nodes
        assert "diagnose" in nodes


class TestSkillRegistry:
    def test_skill_count(self):
        from app.skill.registry import skill_registry
        skills = skill_registry.list_all()
        assert len(skills) == 6

    def test_skill_has_agent(self):
        from app.skill.registry import skill_registry
        for s in skill_registry.list_all():
            agent = skill_registry.get_sub_agent(s["skill_id"])
            assert agent is not None, f"Skill {s['skill_id']} 缺少子智能体"

    def test_find_by_intent(self):
        from app.skill.registry import skill_registry
        skill = skill_registry.select_by_intent("FAULT_DIAGNOSIS")
        assert skill is not None
        assert skill.skill_id == "power-fault-diagnosis"


class TestMultiModel:
    def test_client_has_models(self):
        from app.agent.multi_model import multi_client
        assert len(multi_client._available) >= 1

    def test_single_diagnosis(self):
        from app.agent.multi_model import multi_client
        result = multi_client.diagnose_single(
            "输出JSON: {\"root_cause\":\"测试\",\"confidence\":0.8,\"risk_level\":\"LOW\"}",
            "测试故障",
        )
        assert result is not None
        assert "confidence" in result

    def test_hybrid_provider(self, sample_symptoms):
        from app.agent.llm_provider import hybrid_llm
        status = hybrid_llm.mode_status()
        assert status["current"] in ("deepseek", "qwen-local", "rule-engine")
        assert "offline" in status["deployment"] or "online" in status["deployment"]


class TestDiagnosisAgent:
    def test_diagnose_returns_report(self, sample_symptoms):
        from app.agent.diagnosis_agent import DiagnosisAgent
        from app.rag.hybrid_search import HybridSearchService
        search = HybridSearchService()
        rag = search.search(sample_symptoms, top_k=3)
        rag_text = "; ".join([r["text"][:200] for r in rag])
        context = f"故障描述:\n{sample_symptoms}\n\n知识库:\n{rag_text}"
        agent = DiagnosisAgent()
        result = agent.diagnose(context)
        assert "report_text" in result
        assert len(result.get("report_text", "")) > 100

    def test_confidence_in_range(self, sample_symptoms):
        from app.agent.diagnosis_agent import DiagnosisAgent
        from app.rag.hybrid_search import HybridSearchService
        search = HybridSearchService()
        rag = search.search(sample_symptoms, top_k=3)
        rag_text = "; ".join([r["text"][:200] for r in rag])
        context = f"故障描述:\n{sample_symptoms}\n\n知识库:\n{rag_text}"
        agent = DiagnosisAgent()
        result = agent.diagnose(context)
        conf = result.get("confidence", 0)
        assert 0.3 <= conf <= 1.0, f"置信度异常: {conf}"

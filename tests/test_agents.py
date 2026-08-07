"""Agent 层单元测试 — 覆盖 Router / Judge / Diagnosis / RiskReview / SubagentExecutor"""
import pytest
import asyncio


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


class TestRouterAgent:
    def test_import(self):
        from app.agent.router_agent import RouterAgent, ROUTER_PROMPT
        assert RouterAgent is not None
        assert len(ROUTER_PROMPT) > 100

    def test_instantiate(self):
        from app.agent.router_agent import RouterAgent
        agent = RouterAgent()
        assert hasattr(agent, 'route')

    def test_route_returns_dict(self):
        from app.agent.router_agent import RouterAgent
        agent = RouterAgent()
        result = agent.route("逆变器通讯中断")
        assert isinstance(result, dict)

    def test_route_has_intent(self):
        from app.agent.router_agent import RouterAgent
        agent = RouterAgent()
        result = agent.route("风机温度过高")
        assert "intent" in result
        assert result["intent"] in (
            "FAULT_DIAGNOSIS", "ALARM_DIAGNOSIS", "SAFETY_QA",
            "DEVICE_STATUS", "DEVICE_PROFILE", "ALARM_QUERY",
            "LOG_ANALYSIS", "TICKET_QUERY", "GENERAL_CHAT",
        )

    def test_route_has_confidence(self):
        from app.agent.router_agent import RouterAgent
        agent = RouterAgent()
        result = agent.route("查询设备状态")
        assert "confidence" in result
        assert 0.0 <= result["confidence"] <= 1.0

    def test_route_has_entities(self):
        from app.agent.router_agent import RouterAgent
        agent = RouterAgent()
        result = agent.route("INV001逆变器告警")
        assert "entities" in result
        assert isinstance(result["entities"], dict)

    def test_route_intent_types(self):
        from app.agent.router_agent import RouterAgent
        agent = RouterAgent()
        valid_intents = {
            "FAULT_DIAGNOSIS", "ALARM_DIAGNOSIS", "SAFETY_QA",
            "DEVICE_STATUS", "DEVICE_PROFILE", "ALARM_QUERY",
            "LOG_ANALYSIS", "TICKET_QUERY", "GENERAL_CHAT",
        }
        test_cases = [
            "逆变器IGBT模块过温", "告警系统报通讯中断", "安全规程操作要求",
            "查询设备状态", "设备台账信息", "告警历史记录",
            "分析运行日志", "工单处理状态", "今天天气怎么样",
        ]
        for case in test_cases:
            result = agent.route(case)
            assert result["intent"] in valid_intents, f"输入'{case}'得到未知意图: {result['intent']}"


class TestRiskReviewAgent:
    def test_import(self):
        from app.agent.risk_review_agent import RiskReviewAgent, RISK_REVIEW_PROMPT
        assert RiskReviewAgent is not None
        assert len(RISK_REVIEW_PROMPT) > 100

    def test_instantiate(self):
        from app.agent.risk_review_agent import RiskReviewAgent
        agent = RiskReviewAgent()
        assert hasattr(agent, 'review')

    def test_review_returns_dict(self):
        from app.agent.risk_review_agent import RiskReviewAgent
        agent = RiskReviewAgent()
        result = agent.review("诊断结论: 需立即停机检查")
        assert isinstance(result, dict)

    def test_review_has_keys(self):
        from app.agent.risk_review_agent import RiskReviewAgent
        agent = RiskReviewAgent()
        result = agent.review("诊断结论: 正常运行")
        assert "is_compliant" in result
        assert "risk_level" in result

    def test_review_risk_level_valid(self):
        from app.agent.risk_review_agent import RiskReviewAgent
        agent = RiskReviewAgent()
        result = agent.review("诊断结论: 逆变器温度偏高")
        assert result["risk_level"] in ("HIGH", "MEDIUM", "LOW")

    def test_review_with_safety_rules(self):
        from app.agent.risk_review_agent import RiskReviewAgent
        agent = RiskReviewAgent()
        result = agent.review("诊断结论: 风机振动超标", safety_rules=[
            {"content": "风机维修需锁止叶片"},
            {"content": "高空作业需安全带"},
        ])
        assert isinstance(result, dict)
        assert "violations" in result or "suggestions" in result

    def test_review_with_empty_rules(self):
        from app.agent.risk_review_agent import RiskReviewAgent
        agent = RiskReviewAgent()
        result = agent.review("诊断结论: 变压器油温正常", safety_rules=[])
        assert isinstance(result, dict)

    def test_review_long_text(self):
        from app.agent.risk_review_agent import RiskReviewAgent
        agent = RiskReviewAgent()
        long_text = "诊断结论: " + "设备运行参数正常。 " * 100
        result = agent.review(long_text)
        assert isinstance(result, dict)


class TestSubagentExecutor:
    def test_import(self):
        from app.agent.subagent_executor import SubagentExecutor, SubagentTask, SUBAGENT_PROMPTS
        assert SubagentExecutor is not None
        assert len(SUBAGENT_PROMPTS) >= 5

    def test_instantiate(self):
        from app.agent.subagent_executor import SubagentExecutor
        executor = SubagentExecutor()
        assert hasattr(executor, 'execute_parallel')

    def test_subagent_task_dataclass(self):
        from app.agent.subagent_executor import SubagentTask
        task = SubagentTask(name="test", result="ok", success=True, elapsed=1.5)
        assert task.name == "test"
        assert task.result == "ok"
        assert task.success is True
        assert task.elapsed == 1.5

    def test_subagent_task_defaults(self):
        from app.agent.subagent_executor import SubagentTask
        task = SubagentTask(name="test")
        assert task.result == ""
        assert task.error == ""
        assert task.success is False
        assert task.elapsed == 0.0

    def test_prompts_contain_keys(self):
        from app.agent.subagent_executor import SUBAGENT_PROMPTS
        expected_names = {"regulation", "metrics", "log", "ticket", "risk_review"}
        assert set(SUBAGENT_PROMPTS.keys()) == expected_names

    def test_prompts_non_empty(self):
        from app.agent.subagent_executor import SUBAGENT_PROMPTS
        for name, prompt in SUBAGENT_PROMPTS.items():
            assert len(prompt) > 20, f"Prompt for {name} is too short"

    def test_execute_parallel_single(self):
        from app.agent.subagent_executor import SubagentExecutor
        executor = SubagentExecutor()
        results = asyncio.run(executor.execute_parallel(
            ["regulation"], "逆变器通讯中断测试"
        ))
        assert len(results) == 1
        assert results[0].success is True
        assert len(results[0].result) > 0

    def test_execute_parallel_multiple(self):
        from app.agent.subagent_executor import SubagentExecutor
        executor = SubagentExecutor()
        results = asyncio.run(executor.execute_parallel(
            ["regulation", "metrics"], "风机振动超标"
        ))
        assert len(results) == 2
        for r in results:
            assert r.success is True

    def test_execute_parallel_with_tool_results(self):
        from app.agent.subagent_executor import SubagentExecutor
        executor = SubagentExecutor()
        results = asyncio.run(executor.execute_parallel(
            ["metrics"],
            "设备状态查询",
            tool_results={"metrics": "温度85°C, 功率500kW"}
        ))
        assert len(results) == 1
        assert results[0].success is True

    def test_execute_parallel_all_names(self):
        from app.agent.subagent_executor import SubagentExecutor
        executor = SubagentExecutor()
        results = asyncio.run(executor.execute_parallel(
            ["regulation", "metrics", "log", "ticket", "risk_review"],
            "逆变器IGBT模块过温，型号INV005"
        ))
        assert len(results) == 5
        for r in results:
            assert r.success is True
            assert len(r.result) > 0
            assert r.elapsed > 0


class TestJudgeAgent:
    def test_import(self):
        from app.agent.judge_agent import JudgeAgent, JUDGE_PROMPT
        assert JudgeAgent is not None
        assert len(JUDGE_PROMPT) > 100

    def test_instantiate(self):
        from app.agent.judge_agent import JudgeAgent
        agent = JudgeAgent()
        assert hasattr(agent, 'evaluate')
        assert hasattr(agent, 'is_pass')

    def test_default_score(self):
        from app.agent.judge_agent import JudgeAgent
        agent = JudgeAgent()
        score = agent._default_score()
        assert score["total_score"] == 60
        assert score["grade"] == "D"
        assert len(score["dimensions"]) == 5
        for dim in ("evidence", "logic", "safety", "actionability", "consistency"):
            assert dim in score["dimensions"]

    def test_is_pass_above_threshold(self):
        from app.agent.judge_agent import JudgeAgent
        assert JudgeAgent.is_pass({"total_score": 85}) is True

    def test_is_pass_below_threshold(self):
        from app.agent.judge_agent import JudgeAgent
        assert JudgeAgent.is_pass({"total_score": 55}) is False

    def test_is_pass_at_threshold(self):
        from app.agent.judge_agent import JudgeAgent
        assert JudgeAgent.is_pass({"total_score": 70}) is True

    def test_is_pass_custom_threshold(self):
        from app.agent.judge_agent import JudgeAgent
        assert JudgeAgent.is_pass({"total_score": 75}, threshold=80) is False
        assert JudgeAgent.is_pass({"total_score": 85}, threshold=80) is True

    def test_validate_and_fix_score_range(self):
        from app.agent.judge_agent import JudgeAgent
        agent = JudgeAgent()
        # 超出范围
        r = {"total_score": 150, "key_improvements": [], "overall_assessment": "test"}
        agent._validate_and_fix(r)
        assert r["total_score"] == 100

        r = {"total_score": -10}
        agent._validate_and_fix(r)
        assert r["total_score"] == 0

    def test_validate_and_fix_grade_mapping(self):
        from app.agent.judge_agent import JudgeAgent
        agent = JudgeAgent()
        test_cases = [
            (95, "A"), (88, "B"), (75, "C"), (65, "D"), (45, "F"),
            (90, "A"), (80, "B"), (89, "B"), (70, "C"), (60, "D"),
            (59, "F"), (0, "F"), (100, "A"),
        ]
        for score, expected_grade in test_cases:
            r = {"total_score": score, "key_improvements": []}
            agent._validate_and_fix(r)
            assert r["grade"] == expected_grade, f"Score {score} → expected {expected_grade}, got {r['grade']}"

    def test_validate_and_fix_adds_dimensions(self):
        from app.agent.judge_agent import JudgeAgent
        agent = JudgeAgent()
        r = {"total_score": 85, "key_improvements": []}
        agent._validate_and_fix(r)
        assert "dimensions" in r
        assert len(r["dimensions"]) == 5
        for dim in ("evidence", "logic", "safety", "actionability", "consistency"):
            assert dim in r["dimensions"]
            assert r["dimensions"][dim]["score"] == 85

    def test_validate_and_fix_adds_improvements(self):
        from app.agent.judge_agent import JudgeAgent
        agent = JudgeAgent()
        r = {"total_score": 85}
        agent._validate_and_fix(r)
        assert "key_improvements" in r
        assert isinstance(r["key_improvements"], list)

    def test_evaluate_returns_dict(self):
        from app.agent.judge_agent import JudgeAgent
        agent = JudgeAgent()
        result = agent.evaluate("诊断报告: 逆变器过热，建议检查散热风扇")
        assert isinstance(result, dict)
        assert "total_score" in result

    def test_evaluate_with_context(self):
        from app.agent.judge_agent import JudgeAgent
        agent = JudgeAgent()
        result = agent.evaluate(
            "诊断报告: 风机齿轮箱磨损，建议更换",
            evidence_context={
                "evidence_count": 3,
                "device_type": "风机",
                "has_scada": True,
                "has_multimodal": True,
                "retry_count": 0,
            }
        )
        assert isinstance(result, dict)
        assert "grade" in result
        assert result["grade"] in ("A", "B", "C", "D", "F")

    def test_evaluate_with_retry_context(self):
        from app.agent.judge_agent import JudgeAgent
        agent = JudgeAgent()
        result = agent.evaluate(
            "诊断报告: 变压器油温偏高",
            evidence_context={"retry_count": 2}
        )
        assert isinstance(result, dict)


class TestSubAgentBase:
    def test_registry_size(self):
        from app.graph.sub_agent import sub_agent_registry
        assert len(sub_agent_registry) >= 6

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
        assert "entity_extract" in nodes
        assert "diagnose" in nodes


class TestSkillRegistry:
    def test_skill_count(self):
        from app.skill.registry import skill_registry
        skills = skill_registry.list_all()
        assert len(skills) >= 6

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
        from app.rag.hybrid_search import get_knowledge_store
        store = get_knowledge_store()
        rag = store.search(sample_symptoms, top_k=3)
        rag_text = "; ".join([r["text"][:200] for r in rag])
        context = f"故障描述:\n{sample_symptoms}\n\n知识库:\n{rag_text}"
        agent = DiagnosisAgent()
        result = agent.diagnose(context)
        assert "report_text" in result
        assert len(result.get("report_text", "")) > 100

    def test_confidence_in_range(self, sample_symptoms):
        from app.agent.diagnosis_agent import DiagnosisAgent
        from app.rag.hybrid_search import get_knowledge_store
        store = get_knowledge_store()
        rag = store.search(sample_symptoms, top_k=3)
        rag_text = "; ".join([r["text"][:200] for r in rag])
        context = f"故障描述:\n{sample_symptoms}\n\n知识库:\n{rag_text}"
        agent = DiagnosisAgent()
        result = agent.diagnose(context)
        conf = result.get("confidence", 0)
        assert 0.3 <= conf <= 1.0, f"置信度异常: {conf}"

    def test_diagnose_has_structured_fields(self, sample_symptoms):
        from app.agent.diagnosis_agent import DiagnosisAgent
        agent = DiagnosisAgent()
        result = agent.diagnose(sample_symptoms)
        assert "root_cause" in result
        assert "risk_level" in result
        assert "confidence" in result
        assert result["risk_level"] in ("LOW", "MEDIUM", "HIGH", "CRITICAL")

    def test_diagnose_with_device_type(self):
        from app.agent.diagnosis_agent import DiagnosisAgent
        agent = DiagnosisAgent()
        result = agent.diagnose("设备温度过高", device_type="风机")
        assert "report_text" in result
        assert len(result["report_text"]) > 100

    def test_diagnose_without_ensemble(self):
        from app.agent.diagnosis_agent import DiagnosisAgent
        agent = DiagnosisAgent()
        result = agent.diagnose("测试故障描述", use_ensemble=False)
        assert "report_text" in result

    def test_parse_diagnosis_json_block(self):
        from app.agent.diagnosis_agent import DiagnosisAgent
        agent = DiagnosisAgent()
        text = """
        诊断结果...
        ```json
        {"root_cause": "IGBT老化", "confidence": 0.85, "risk_level": "HIGH"}
        ```
        """
        result = agent._parse_diagnosis(text)
        assert result["root_cause"] == "IGBT老化"
        assert result["confidence"] == 0.85

    def test_parse_diagnosis_inline_json(self):
        from app.agent.diagnosis_agent import DiagnosisAgent
        agent = DiagnosisAgent()
        text = '{"root_cause": "轴承磨损", "confidence": 0.72}'
        result = agent._parse_diagnosis(text)
        assert result["root_cause"] == "轴承磨损"
        assert result["confidence"] == 0.72

    def test_parse_diagnosis_no_json(self):
        from app.agent.diagnosis_agent import DiagnosisAgent
        agent = DiagnosisAgent()
        text = "纯文本诊断，无JSON"
        result = agent._parse_diagnosis(text)
        assert result["root_cause"] == ""
        assert result["confidence"] == 0.5
        assert result["risk_level"] == "MEDIUM"

    def test_parse_diagnosis_malformed_json(self):
        from app.agent.diagnosis_agent import DiagnosisAgent
        agent = DiagnosisAgent()
        text = '```json\n{bad json}\n```'
        result = agent._parse_diagnosis(text)
        assert result["confidence"] == 0.5

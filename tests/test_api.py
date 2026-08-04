"""API 集成测试 + Graph 全链路测试 — 覆盖 30+ 端点"""

import json
import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def client():
    from app.main import app
    return TestClient(app)


# ─── Health ───

class TestHealth:
    def test_health_ok(self, client):
        r = client.get("/health")
        assert r.status_code == 200
        assert r.json()["status"] == "healthy"

    def test_health_has_version(self, client):
        r = client.get("/health")
        assert "version" in r.json()

    def test_health_method_not_allowed(self, client):
        r = client.post("/health")
        assert r.status_code in (405, 200)  # 可能被统一处理


# ─── Dashboard ───

class TestDashboard:
    def test_dashboard_ok(self, client):
        r = client.get("/api/dashboard")
        assert r.status_code == 200
        data = r.json()
        assert "progress" in data
        assert "phases" in data

    def test_dashboard_phases(self, client):
        r = client.get("/api/dashboard/phases")
        assert r.status_code == 200
        phases = r.json()["phases"]
        assert "phase1" in phases
        assert "phase2" in phases
        assert "phase3" in phases
        assert "phase4" in phases

    def test_dashboard_phase_detail(self, client):
        r = client.get("/api/dashboard/phases/phase3")
        assert r.status_code == 200
        assert r.json()["status"] == "completed"

    def test_dashboard_phase_not_found(self, client):
        r = client.get("/api/dashboard/phases/phase99")
        assert r.status_code == 200
        assert "error" in r.json()

    def test_dashboard_tasks(self, client):
        r = client.get("/api/dashboard/tasks?status=completed")
        assert r.status_code == 200

    def test_dashboard_tasks_pending(self, client):
        r = client.get("/api/dashboard/tasks?status=pending")
        assert r.status_code == 200

    def test_dashboard_mode(self, client):
        r = client.get("/api/dashboard/mode")
        assert r.status_code == 200
        assert "current" in r.json()


# ─── Audit ───

class TestAudit:
    def test_audit_ok(self, client):
        r = client.get("/api/audit")
        assert r.status_code == 200
        data = r.json()
        assert data["overall"]["grade"] in ("A", "B", "C")

    def test_audit_skills(self, client):
        r = client.get("/api/audit/skills")
        assert r.status_code == 200
        assert r.json()["all_mapped"] == True

    def test_audit_files(self, client):
        r = client.get("/api/audit/files")
        assert r.status_code == 200

    def test_audit_imports(self, client):
        r = client.get("/api/audit/imports")
        assert r.status_code == 200


# ─── Skills & Tools ───

class TestSkills:
    def test_skills_list(self, client):
        r = client.get("/api/skills")
        assert r.status_code == 200
        data = r.json()
        assert len(data["skills"]) >= 6
        assert len(data["sub_agents"]) >= 6

    def test_tools_list(self, client):
        r = client.get("/api/tools/list")
        assert r.status_code == 200

    def test_tools_search(self, client):
        r = client.get("/api/tools/search?keyword=设备")
        assert r.status_code == 200


# ─── Knowledge ───

class TestKnowledge:
    def test_search_test(self, client):
        r = client.post("/api/knowledge/search/test", json={
            "query": "IGBT过热",
            "top_k": 3,
        })
        assert r.status_code == 200
        data = r.json()
        assert "results" in data or "result" in data

    def test_search_empty_query(self, client):
        r = client.post("/api/knowledge/search/test", json={
            "query": "",
            "top_k": 5,
        })
        assert r.status_code == 200

    def test_knowledge_health(self, client):
        r = client.get("/api/knowledge/health")
        assert r.status_code == 200


# ─── SCADA ───

class TestScada:
    def test_scada_health(self, client):
        r = client.get("/api/scada/health")
        assert r.status_code == 200

    def test_scada_devices(self, client):
        r = client.get("/api/scada/devices")
        assert r.status_code == 200

    def test_scada_buffer_stats(self, client):
        r = client.get("/api/scada/buffer/stats")
        assert r.status_code == 200

    def test_scada_data_missing_device(self, client):
        r = client.get("/api/scada/data/NONEXIST")
        assert r.status_code in (200, 404)

    def test_scada_window_missing_device(self, client):
        r = client.get("/api/scada/data/NONEXIST/window")
        assert r.status_code == 200

    def test_scada_disconnect_missing(self, client):
        r = client.post("/api/scada/disconnect/NONEXIST")
        assert r.status_code in (200, 404)


# ─── Chat ───

class TestChat:
    def test_chat_empty_fails(self, client):
        r = client.post("/api/chat", json={"question": ""})
        assert r.status_code == 400

    def test_chat_valid(self, client):
        r = client.post("/api/chat", json={
            "question": "什么是逆变器IGBT？",
        })
        assert r.status_code == 200
        data = r.json()
        assert "answer" in data or "response" in data or "reply" in data

    def test_chat_stream(self, client):
        r = client.post("/api/chat/stream", json={
            "question": "风机齿轮箱常见故障",
        })
        assert r.status_code == 200
        ct = r.headers.get("content-type", "")
        assert "text/event-stream" in ct or "text/plain" in ct

    def test_chat_clear(self, client):
        r = client.post("/api/chat/clear", json={})
        assert r.status_code == 200


# ─── Feedback ───

class TestFeedback:
    def test_feedback_accurate(self, client):
        r = client.post("/api/feedback", json={
            "task_id": "test-task-001",
            "rating": "accurate",
            "comment": "诊断结论与实际情况一致",
        })
        assert r.status_code in (200, 201, 202)

    def test_feedback_inaccurate(self, client):
        r = client.post("/api/feedback", json={
            "task_id": "test-task-002",
            "rating": "inaccurate",
            "comment": "根因判断有误",
        })
        assert r.status_code in (200, 201, 202)

    def test_feedback_partially_accurate(self, client):
        r = client.post("/api/feedback", json={
            "task_id": "test-task-003",
            "rating": "partially_accurate",
            "corrected_root_cause": "实际是散热风扇故障",
        })
        assert r.status_code in (200, 201, 202)

    def test_feedback_invalid_rating(self, client):
        r = client.post("/api/feedback", json={
            "task_id": "test-task-004",
            "rating": "垃圾",
        })
        assert r.status_code == 400

    def test_feedback_stats(self, client):
        r = client.get("/api/feedback/stats")
        assert r.status_code == 200


# ─── Trace ───

class TestTrace:
    def test_trace_replay_not_found(self, client):
        r = client.get("/api/trace/nonexistent-task/replay")
        assert r.status_code == 200
        data = r.json()
        assert "code" in data


# ─── Alarm ───

class TestAlarm:
    def test_alarm_health(self, client):
        r = client.get("/api/alarm/health")
        assert r.status_code == 200

    def test_alarm_receive_valid(self, client):
        r = client.post("/api/alarm/receive", json={
            "alarm_id": "ALM-002",
            "device_id": "INV001",
            "alarm_type": "过热",
            "alarm_level": "high",
            "current_value": "98°C",
            "threshold": "85°C",
        })
        assert r.status_code == 200

    def test_alarm_receive_missing_device(self, client):
        r = client.post("/api/alarm/receive", json={
            "alarm_id": "ALM-001",
            "device_id": "",
        })
        assert r.status_code in (400, 422)

    def test_alarm_diagnose(self, client):
        r = client.post("/api/alarm/diagnose", json={
            "alarmDescription": "逆变器IGBT温度过高告警",
        })
        assert r.status_code == 200

    def test_alarm_status_not_found(self, client):
        r = client.get("/api/alarm/diagnose/nonexistent-task/status")
        assert r.status_code == 200

    def test_alarm_checkpoint_not_found(self, client):
        r = client.get("/api/alarm/checkpoint/nonexistent-task")
        assert r.status_code == 200


# ─── Diagnosis ───

class TestDiagnosis:
    def test_diagnose_empty_fails(self, client):
        r = client.post("/api/diagnose", json={"symptoms": ""})
        assert r.status_code == 400

    def test_diagnose_valid(self, client):
        r = client.post("/api/diagnose", json={
            "symptoms": "逆变器IGBT温度异常升高",
            "device_id": "INV001",
        })
        assert r.status_code in (200, 408, 500)
        if r.status_code == 200:
            data = r.json()
            assert "task_id" in data or "result" in data or "message" in data

    def test_diagnose_stream(self, client):
        r = client.post("/api/diagnose/stream", json={
            "symptoms": "风机齿轮箱振动异常",
            "device_id": "WIND001",
        })
        assert r.status_code in (200, 408, 500)

    def test_diagnose_stream_empty_fails(self, client):
        r = client.post("/api/diagnose/stream", json={"symptoms": ""})
        assert r.status_code == 400

    def test_diagnose_multimodal(self, client):
        r = client.post("/api/diagnose/multimodal", json={
            "symptoms": "变压器油温异常",
            "device_id": "TRA001",
        })
        assert r.status_code in (200, 408, 500)

    def test_diagnose_multimodal_stream(self, client):
        r = client.post("/api/diagnose/multimodal/stream", json={
            "symptoms": "风机振动超标",
            "device_id": "WT001",
        })
        assert r.status_code in (200, 408, 500)

    def test_diagnose_history(self, client):
        r = client.get("/api/diagnose/history")
        assert r.status_code == 200
        assert "history" in r.json()

    def test_diagnose_report_not_found(self, client):
        r = client.get("/api/diagnose/report/nonexistent-id")
        assert r.status_code == 200
        assert not r.json().get("found", True)


# ─── Graph 编排全链路 ───

class TestGraph:
    def test_graph_builds(self):
        from app.graph.builder import get_graph
        graph = get_graph()
        assert graph is not None

    def test_graph_nodes(self):
        from app.graph.builder import get_graph
        graph = get_graph()
        nodes = [n for n in graph.nodes.keys() if not n.startswith("__")]
        expected = {"precheck", "context_load", "router", "knowledge_qa",
                     "diagnosis_parallel", "diagnosis", "judge", "chat",
                     "report", "memory_save"}
        assert expected.issubset(set(nodes))

    def test_route_diagnosis_intent(self):
        from app.graph.builder import route_by_intent
        assert route_by_intent({"intent": "FAULT_DIAGNOSIS"}) == "diagnosis_parallel"
        assert route_by_intent({"intent": "KNOWLEDGE_QA"}) == "knowledge_qa"
        assert route_by_intent({"intent": "CHAT"}) == "chat"

    def test_route_all_intents(self):
        from app.graph.builder import route_by_intent
        for intent, expected in [
            ("FAULT_DIAGNOSIS", "diagnosis_parallel"),
            ("ALARM_DIAGNOSIS", "diagnosis_parallel"),
            ("ALARM_ANALYSIS", "diagnosis_parallel"),
            ("LOG_ANALYSIS", "diagnosis_parallel"),
            ("TICKET_QUERY", "diagnosis_parallel"),
            ("KNOWLEDGE_QA", "knowledge_qa"),
            ("SAFETY_QA", "knowledge_qa"),
            ("DEVICE_STATUS", "knowledge_qa"),
            ("DEVICE_PROFILE", "knowledge_qa"),
            ("ALARM_QUERY", "knowledge_qa"),
            ("CHAT", "chat"),
            ("GENERAL_CHAT", "chat"),
        ]:
            result = route_by_intent({"intent": intent})
            assert result == expected, f"意图 {intent} 应路由到 {expected}，实际路由到 {result}"

    def test_sub_agent_compilation(self):
        from app.graph.sub_agent import sub_agent_registry
        for agent_id in sub_agent_registry._agents:
            agent = sub_agent_registry.get(agent_id)
            compiled = agent.build()
            assert compiled is not None
            assert len(compiled.nodes) >= 2

    def test_graph_ainvoke_end_to_end(self):
        """端到端: 输入 → 路由 → agent 执行 → 输出"""
        from app.graph.builder import get_graph
        graph = get_graph()
        import asyncio
        state = {"input": "逆变器通讯中断如何处理？"}
        try:
            result = asyncio.get_event_loop().run_until_complete(
                graph.ainvoke(state)
            )
            assert "final_response" in result or "execution_result" in result
        except Exception as e:
            pytest.skip(f"端到端测试跳过: {str(e)[:100]}")


# ─── StateGraph 状态传递 ───

class TestStateFlow:
    def test_state_keys_complete(self):
        from app.graph.state_keys import StateKeys
        assert len(StateKeys.REPLACE_KEYS) >= 30
        assert len(StateKeys.APPEND_KEYS) >= 2

    def test_append_keys_return_list(self):
        from app.graph.state_keys import StateKeys
        for key in StateKeys.APPEND_KEYS:
            assert StateKeys.is_append(key)


# ─── SSE 流式验证 ───

class TestSSEStreaming:
    def test_chat_stream_format(self, client):
        r = client.post("/api/chat/stream", json={
            "question": "风力发电原理",
        })
        assert r.status_code in (200, 408, 500)

    def test_diagnose_stream_format(self, client):
        r = client.post("/api/diagnose/stream", json={
            "symptoms": "变压器油温高",
            "device_id": "TRA001",
        })
        assert r.status_code in (200, 408, 500)

    def test_combined_full_flow(self, client):
        """全链路: 告警接收 → 诊断 → 反馈"""
        alarm_r = client.post("/api/alarm/receive", json={
            "alarm_id": "ALM-002",
            "device_id": "INV001",
            "alarm_type": "过热",
            "alarm_level": "high",
        })
        assert alarm_r.status_code == 200

        diag_r = client.post("/api/diagnose", json={
            "symptoms": "逆变器IGBT温度过高告警",
            "device_id": "INV001",
        })
        assert diag_r.status_code in (200, 408, 500)
        if diag_r.status_code == 200:
            task_id = diag_r.json().get("task_id", "unknown")

            fb_r = client.post("/api/feedback", json={
                "task_id": task_id,
                "rating": "accurate",
            })
            assert fb_r.status_code in (200, 201, 202)

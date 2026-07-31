"""API 集成测试 + Graph 全链路测试"""
import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def client():
    from app.main import app
    return TestClient(app)


class TestHealth:
    def test_health_ok(self, client):
        r = client.get("/health")
        assert r.status_code == 200
        assert r.json()["status"] == "healthy"

    def test_health_has_version(self, client):
        r = client.get("/health")
        assert "version" in r.json()


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

    def test_dashboard_phase_detail(self, client):
        r = client.get("/api/dashboard/phases/phase3")
        assert r.status_code == 200
        assert r.json()["status"] == "completed"

    def test_dashboard_tasks(self, client):
        r = client.get("/api/dashboard/tasks?status=completed")
        assert r.status_code == 200

    def test_dashboard_mode(self, client):
        r = client.get("/api/dashboard/mode")
        assert r.status_code == 200
        assert "current" in r.json()


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


class TestSkills:
    def test_skills_list(self, client):
        r = client.get("/api/skills")
        assert r.status_code == 200
        data = r.json()
        assert len(data["skills"]) == 6
        assert len(data["sub_agents"]) == 6

    def test_tools_list(self, client):
        r = client.get("/api/tools/list")
        assert r.status_code == 200


class TestDiagnosis:
    def test_diagnose_empty_fails(self, client):
        r = client.post("/api/diagnose", json={"symptoms": ""})
        assert r.status_code == 400

    def test_diagnose_valid(self, client):
        r = client.post("/api/diagnose", json={
            "symptoms": "逆变器IGBT温度异常升高",
            "device_id": "INV001",
        })
        assert r.status_code == 200
        data = r.json()
        assert "task_id" in data
        assert "confidence" in data
        assert data["confidence"] >= 0.3

    def test_diagnose_stream(self, client):
        r = client.post("/api/diagnose/stream", json={
            "symptoms": "风机齿轮箱振动异常",
            "device_id": "WIND001",
        })
        assert r.status_code == 200
        assert "text/event-stream" in r.headers.get("content-type", "")

    def test_diagnose_history(self, client):
        r = client.get("/api/diagnose/history")
        assert r.status_code == 200
        assert "history" in r.json()

    def test_diagnose_report_not_found(self, client):
        r = client.get("/api/diagnose/report/nonexistent-id")
        assert r.status_code == 200
        assert not r.json().get("found", True)


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
                     "diagnosis", "chat", "safety_review", "memory_save"}
        assert expected.issubset(set(nodes))

    def test_route_diagnosis_intent(self):
        from app.graph.builder import route_by_intent
        assert route_by_intent({"intent": "FAULT_DIAGNOSIS"}) == "diagnosis"
        assert route_by_intent({"intent": "KNOWLEDGE_QA"}) == "knowledge_qa"
        assert route_by_intent({"intent": "CHAT"}) == "chat"

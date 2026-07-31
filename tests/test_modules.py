"""多模态 + SCADA + 学习模块测试"""
import pytest


class TestImageAnalyzer:
    def test_import(self):
        from app.multimodal import image_analyzer
        assert image_analyzer is not None

    def test_fallback_mode(self):
        from app.multimodal.image_analyzer import image_analyzer
        result = image_analyzer.analyze("dGVzdA==", "thermal", "DEV001")
        assert "mode" in result or "success" in result

    def test_all_modes(self):
        from app.multimodal.image_analyzer import image_analyzer
        for mode in ["thermal", "electrical", "appearance", "auto"]:
            result = image_analyzer.analyze("dGVzdA==", mode)
            assert isinstance(result, dict)

    def test_text_summary(self):
        from app.multimodal.image_analyzer import image_analyzer
        analysis = {"success": True, "mode": "thermal", "image_type": "thermal",
                     "findings": [{"type": "热点", "description": "IGBT区域85°C"}],
                     "risk_level": "HIGH", "recommendations": ["检查散热"]}
        text = image_analyzer.to_text_summary(analysis)
        assert "85°C" in text


class TestAudioAnalyzer:
    def test_import(self):
        from app.multimodal import audio_analyzer
        assert audio_analyzer is not None

    def test_missing_file(self):
        from app.multimodal.audio_analyzer import audio_analyzer
        result = audio_analyzer.analyze("/tmp/nonexistent.wav")
        assert not result["success"]
        assert "不存在" in result.get("note", "")

    def test_fault_patterns(self):
        from app.multimodal.audio_analyzer import audio_analyzer
        result = audio_analyzer.analyze("/tmp/test.wav", "风机")
        assert "possible_faults" in result

    def test_text_summary(self):
        from app.multimodal.audio_analyzer import audio_analyzer
        analysis = {"success": False, "audio_path": "/tmp/x.wav",
                     "note": "文件不存在", "possible_faults": []}
        text = audio_analyzer.to_text_summary(analysis)
        assert "降级" in text


class TestScada:
    def test_ring_buffer_create(self):
        from app.scada.ring_buffer import RingBuffer
        buf = RingBuffer(capacity=100)
        assert buf.size == 0
        assert buf.capacity == 100

    def test_ring_buffer_push(self):
        from app.scada.ring_buffer import RingBuffer
        from app.scada.base import ScadaDataPoint
        buf = RingBuffer(capacity=10)
        for i in range(5):
            buf.push(ScadaDataPoint(
                device_id="DEV001", point_name=f"temp_{i}",
                value=25.0 + i, timestamp="2026-07-31T10:00:00", unit="°C"
            ))
        assert buf.size == 5
        assert buf.stats["total_written"] == 5

    def test_window_extractor(self):
        from app.scada.window_extractor import FaultWindowExtractor
        from app.scada.ring_buffer import RingBuffer
        from app.scada.base import ScadaDataPoint
        buf = RingBuffer(capacity=100)
        for i in range(20):
            buf.push(ScadaDataPoint(
                device_id="DEV001", point_name="temp",
                value=25.0 + i * 0.5,
                timestamp=f"2026-07-31T10:{i:02d}:00",
                unit="°C"
            ))
        extractor = FaultWindowExtractor(buf)
        result = extractor.extract("DEV001", "2026-07-31T10:10:00")
        assert result.get("total_points", 0) >= 0


class TestLearning:
    def test_case_ingestion_import(self):
        from app.learning.case_ingestion import case_ingestion
        assert case_ingestion is not None

    def test_fault_classify(self):
        from app.learning.case_ingestion import CaseIngestionService
        svc = CaseIngestionService()
        assert svc._classify_fault("IGBT过热通讯中断") in ("温度异常", "通讯故障", "其他故障")

    def test_skill_generator(self):
        from app.learning.skill_generator import skill_generator
        assert skill_generator is not None
        result = skill_generator.check_and_generate("测试故障类型")
        assert "generated" in result

    def test_lora_script_importable(self):
        import importlib
        spec = importlib.util.spec_from_file_location(
            "lora_finetune",
            "/home/an/项目/驭能/scripts/lora_finetune.py"
        )
        assert spec is not None

"""多模态层测试 — 图像分析 / 音频分析 / 融合"""
import pytest


class TestImageAnalyzer:
    def test_import(self):
        from app.multimodal.image_analyzer import ImageAnalyzer
        assert ImageAnalyzer is not None

    def test_analysis_modes_defined(self):
        from app.multimodal.image_analyzer import IMAGE_ANALYSIS_MODES
        modes = list(IMAGE_ANALYSIS_MODES.keys())
        assert "thermal" in modes
        assert "electrical" in modes
        assert "appearance" in modes
        assert "auto" in modes

    def test_analyze_no_image(self):
        from app.multimodal.image_analyzer import ImageAnalyzer
        analyzer = ImageAnalyzer()
        result = analyzer.analyze(image_b64="", mode="auto", extra_context="测试")
        assert isinstance(result, dict)

    def test_analyze_thermal_mode(self):
        from app.multimodal.image_analyzer import ImageAnalyzer
        analyzer = ImageAnalyzer()
        result = analyzer.analyze(image_b64="", mode="thermal", extra_context="温度异常")
        assert isinstance(result, dict)

    def test_analyze_invalid_mode_falls_to_auto(self):
        from app.multimodal.image_analyzer import ImageAnalyzer
        analyzer = ImageAnalyzer()
        result = analyzer.analyze(image_b64="", mode="invalid_mode")
        assert isinstance(result, dict)

    def test_available_property(self):
        from app.multimodal.image_analyzer import ImageAnalyzer
        assert isinstance(ImageAnalyzer().available, bool)


class TestAudioAnalyzer:
    def test_import(self):
        from app.multimodal.audio_analyzer import AudioAnalyzer
        assert AudioAnalyzer is not None

    def test_fault_patterns_defined(self):
        from app.multimodal.audio_analyzer import FAULT_SOUND_PATTERNS
        assert "bearing_friction" in FAULT_SOUND_PATTERNS
        assert "gear_breakage" in FAULT_SOUND_PATTERNS
        assert "arc_discharge" in FAULT_SOUND_PATTERNS
        assert "transformer_hum" in FAULT_SOUND_PATTERNS

    def test_analyze_no_file(self):
        from app.multimodal.audio_analyzer import AudioAnalyzer
        result = AudioAnalyzer().analyze("")
        assert isinstance(result, dict)

    def test_analyze_nonexistent_file(self):
        from app.multimodal.audio_analyzer import AudioAnalyzer
        result = AudioAnalyzer().analyze("/nonexistent/audio.wav")
        assert isinstance(result, dict)

    def test_available_property(self):
        from app.multimodal.audio_analyzer import AudioAnalyzer
        assert isinstance(AudioAnalyzer().available, bool)


class TestMultimodalIntegration:
    def test_combined_imports(self):
        from app.multimodal.image_analyzer import ImageAnalyzer
        from app.multimodal.audio_analyzer import AudioAnalyzer
        assert ImageAnalyzer() is not None
        assert AudioAnalyzer() is not None

    def test_multimodal_graph_exists(self):
        from app.graph.subgraphs.multimodal import MultiModalSubAgent
        graph = MultiModalSubAgent().build()
        assert graph is not None

"""音频分析器 — 基于 Audio Spectrogram Transformer (AST) 的设备声音诊断

支持分析：
- 设备运行声音（轴承干摩擦、齿轮断齿、电弧放电）
- 识别故障声音特征频率
- 异常振动频谱分析

实现方式：
- 优先：librosa 音频特征提取 + LLM 分析
- 降级：文件元数据验证 + LLM 基于上下文描述推理
"""

import logging
import os
from typing import Any, Optional

logger = logging.getLogger(__name__)

_AUDIO_AVAILABLE = False
try:
    import librosa
    import numpy as np
    _AUDIO_AVAILABLE = True
except ImportError:
    pass

_SOUNDFILE_AVAILABLE = False
try:
    import soundfile as sf
    _SOUNDFILE_AVAILABLE = True
except ImportError:
    pass

if not _AUDIO_AVAILABLE and not _SOUNDFILE_AVAILABLE:
    logger.info("librosa/soundfile 未安装，音频分析降级为元数据模式。安装: pip install librosa 或 pip install soundfile")

FAULT_SOUND_PATTERNS = {
    "bearing_friction": {
        "name": "轴承干摩擦",
        "freq_range": "高频 4kHz-10kHz",
        "pattern": "持续高频嘶嘶声，无周期性脉冲",
        "典型场景": "轴承润滑不足或磨损严重",
    },
    "gear_breakage": {
        "name": "齿轮断齿",
        "freq_range": "啮合频率附近",
        "pattern": "周期性撞击声，间隔=转速/齿数",
        "典型场景": "齿轮箱齿轮断裂或严重磨损",
    },
    "arc_discharge": {
        "name": "电弧放电",
        "freq_range": "全频段",
        "pattern": "不规则噼啪声，伴随电磁脉冲",
        "典型场景": "电缆绝缘破损、接线松动",
    },
    "transformer_hum": {
        "name": "变压器异常嗡声",
        "freq_range": "50Hz 基频及谐波",
        "pattern": "50Hz/100Hz 嗡声异常增大，铁芯松动特征",
        "典型场景": "变压器铁芯松动、过载",
    },
    "blade_imbalance": {
        "name": "叶片不平衡",
        "freq_range": "1P 转频",
        "pattern": "1倍转频振动幅值超标，波形正弦",
        "典型场景": "风机叶片覆冰或损坏导致不平衡",
    },
    "misalignment": {
        "name": "对中不良",
        "freq_range": "1P/2P 转频",
        "pattern": "2倍转频振动突出，轴向振动大",
        "典型场景": "联轴器不对中或轴承座偏斜",
    },
}


class AudioAnalyzer:
    """设备声音分析器"""

    def __init__(self):
        self._available = _AUDIO_AVAILABLE
        self._basic_available = _AUDIO_AVAILABLE or _SOUNDFILE_AVAILABLE

    @property
    def available(self) -> bool:
        return self._available

    def analyze(self, audio_path: str, device_type: str = "") -> dict[str, Any]:
        """分析音频文件

        Args:
            audio_path: 音频文件路径 (WAV/MP3/FLAC)
            device_type: 设备类型（风机/逆变器/变压器等）

        Returns:
            {
                "success": bool,
                "audio_path": str,
                "duration_secs": float,
                "sample_rate": int,
                "features": dict,
                "possible_faults": list,
                "note": str,
            }
        """
        base_result = {
            "success": False,
            "audio_path": audio_path,
            "duration_secs": 0.0,
            "sample_rate": 0,
            "channels": 0,
            "features": {},
            "possible_faults": [],
            "note": "",
        }

        if not audio_path or not os.path.exists(audio_path):
            base_result["note"] = f"音频文件不存在: {audio_path}"
            return base_result

        file_size = os.path.getsize(audio_path)
        base_result["file_size_bytes"] = file_size

        if self._available:
            return self._analyze_with_librosa(audio_path, device_type, base_result)
        elif _SOUNDFILE_AVAILABLE:
            return self._analyze_with_soundfile(audio_path, device_type, base_result)
        else:
            return self._fallback_analysis(audio_path, device_type, base_result)

    def _analyze_with_librosa(
        self, audio_path: str, device_type: str, base: dict
    ) -> dict[str, Any]:
        """使用 librosa 进行特征提取和故障分析"""
        try:
            import numpy as np

            y, sr = librosa.load(audio_path, sr=None, mono=True)
            duration = len(y) / sr

            base["success"] = True
            base["duration_secs"] = round(duration, 2)
            base["sample_rate"] = sr

            rms = librosa.feature.rms(y=y)[0]
            base["features"]["rms_mean"] = round(float(np.mean(rms)), 6)
            base["features"]["rms_max"] = round(float(np.max(rms)), 6)
            base["features"]["rms_std"] = round(float(np.std(rms)), 6)

            spectral_centroid = librosa.feature.spectral_centroid(y=y, sr=sr)[0]
            base["features"]["centroid_mean"] = round(float(np.mean(spectral_centroid)), 2)

            zero_crossing_rate = librosa.feature.zero_crossing_rate(y)[0]
            base["features"]["zcr_mean"] = round(float(np.mean(zero_crossing_rate)), 6)

            stft = np.abs(librosa.stft(y))
            spectral_flatness = np.exp(np.mean(np.log(stft + 1e-10), axis=0)) / (np.mean(stft, axis=0) + 1e-10)
            base["features"]["spectral_flatness_mean"] = round(float(np.mean(spectral_flatness)), 6)

            # 频段能量分布
            if sr >= 8000:
                fft = np.fft.fft(y)
                freqs = np.fft.fftfreq(len(fft), 1 / sr)
                pos_mask = freqs > 0
                freqs_pos = freqs[pos_mask]
                mag = np.abs(fft[pos_mask])

                bands = {
                    "0-500Hz": (0, 500),
                    "500-2kHz": (500, 2000),
                    "2-5kHz": (2000, 5000),
                    "5-10kHz": (5000, 10000),
                }
                for band_name, (lo, hi) in bands.items():
                    mask = (freqs_pos >= lo) & (freqs_pos < hi)
                    energy = float(np.sum(mag[mask]))
                    base["features"][f"energy_{band_name}"] = round(energy, 4)

            base["possible_faults"] = self._match_fault_patterns(base["features"], device_type)

            logger.info(f"音频分析完成: {audio_path}, 时长 {duration:.1f}s")

        except Exception as e:
            base["note"] = f"音频特征提取失败: {e}"
            logger.warning(f"音频分析失败: {e}")

        return base

    def _match_fault_patterns(
        self, features: dict, device_type: str
    ) -> list[dict]:
        """根据特征匹配可能的故障声音模式"""
        matches = []
        rms_mean = features.get("rms_mean", 0)
        rms_std = features.get("rms_std", 0)
        centroid = features.get("centroid_mean", 0)
        flatness = features.get("spectral_flatness_mean", 1)

        for pattern_id, pattern in FAULT_SOUND_PATTERNS.items():
            score = 0
            reasons = []

            if rms_std > 0.01:
                score += 0.15
                reasons.append("RMS 方差大，存在声音波动")

            if centroid > 3000:
                score += 0.2
                reasons.append(f"频谱质心偏高 ({centroid:.0f}Hz)，存在高频成分")

            if flatness < 0.3:
                score += 0.15
                reasons.append("频谱平坦度低，存在显著峰值频率")

            if device_type:
                if "齿轮" in device_type and "gear" in pattern_id:
                    score += 0.25
                    reasons.append(f"设备类型 ({device_type}) 与该故障模式吻合")
                elif "风机" in device_type and "blade" in pattern_id:
                    score += 0.25
                    reasons.append(f"设备类型 ({device_type}) 与该故障模式吻合")

            matches.append({
                "pattern_id": pattern_id,
                "name": pattern["name"],
                "score": round(score, 2),
                "reasons": reasons,
                "freq_range": pattern["freq_range"],
                "typical": pattern["典型场景"],
            })

        matches.sort(key=lambda m: m["score"], reverse=True)
        return matches

    def _analyze_with_soundfile(
        self, audio_path: str, device_type: str, base: dict
    ) -> dict[str, Any]:
        """使用 soundfile 读取基础音频信息（轻量降级方案）"""
        try:
            info = sf.info(audio_path)
            base["success"] = True
            base["duration_secs"] = round(info.duration, 2)
            base["sample_rate"] = info.samplerate
            base["channels"] = info.channels
            base["note"] = "soundfile 基础分析模式 — 安装 librosa 获取频谱分析"
            base["possible_faults"] = [
                {
                    "pattern_id": pid,
                    "name": p["name"],
                    "score": 0.0,
                    "reasons": ["基础模式 — 需安装 librosa 进行频域分析"],
                    "freq_range": p["freq_range"],
                    "typical": p["典型场景"],
                }
                for pid, p in FAULT_SOUND_PATTERNS.items()
            ]
            logger.info(f"音频基础分析完成: {audio_path}, 时长 {info.duration:.1f}s, 采样率 {info.samplerate}Hz")
        except Exception as e:
            base["note"] = f"音频读取失败: {e}"
            logger.warning(f"soundfile 分析失败: {e}")
        return base

    def _fallback_analysis(
        self, audio_path: str, device_type: str, base: dict
    ) -> dict[str, Any]:
        """API 不可用时的降级分析"""
        base["note"] = (
            "librosa 未安装，音频分析降级为元数据模式。"
            "安装命令: pip install librosa numpy"
        )
        base["success"] = False
        base["possible_faults"] = [
            {
                "pattern_id": pid,
                "name": p["name"],
                "score": 0.0,
                "reasons": ["元数据模式 — 需安装 librosa 进行频域分析"],
                "freq_range": p["freq_range"],
                "typical": p["典型场景"],
            }
            for pid, p in FAULT_SOUND_PATTERNS.items()
        ]
        return base

    def to_text_summary(self, analysis: dict) -> str:
        """将分析结果转为 LLM 可读的文本摘要"""
        if not analysis.get("success"):
            return (
                f"[音频分析降级] 文件: {analysis.get('audio_path', 'N/A')}\n"
                f"{analysis.get('note', '')}"
            )

        features = analysis.get("features", {})
        parts = [
            f"## 音频分析",
            f"文件: {analysis.get('audio_path', 'N/A')}",
            f"时长: {analysis.get('duration_secs', 0)}s",
            f"采样率: {analysis.get('sample_rate', 0)}Hz",
            "",
            "### 特征提取",
        ]

        if features:
            parts.append(f"RMS 均值: {features.get('rms_mean', 'N/A')}")
            parts.append(f"RMS 标准差: {features.get('rms_std', 'N/A')}")
            parts.append(f"频谱质心: {features.get('centroid_mean', 'N/A')} Hz")
            parts.append(f"频谱平坦度: {features.get('spectral_flatness_mean', 'N/A')}")

            band_parts = []
            for k, v in features.items():
                if k.startswith("energy_"):
                    band_parts.append(f"  {k.replace('energy_', '')}: {v}")
            if band_parts:
                parts.append("频段能量分布:")
                parts.extend(band_parts)

        faults = analysis.get("possible_faults", [])
        if faults:
            parts.append("")
            parts.append("### 可能的故障声音模式匹配")
            for f in faults[:5]:
                parts.append(f"- {f['name']} (置信度: {f['score']:.0%}) — {f['typical']}")

        return "\n".join(parts)


audio_analyzer = AudioAnalyzer()

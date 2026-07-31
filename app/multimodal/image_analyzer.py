"""图像分析器 — 基于 Qwen-VL-Max 的多模态图像诊断

支持三种分析模式：
1. 红外热像分析 — 检测温度异常、热点区域
2. 电气图分析   — 识别符号、线路、保护装置
3. 设备外观分析 — 检测物理损伤、腐蚀、变形

API 调用方式：阿里云 DashScope / OpenAI 兼容接口
降级策略：API 不可用时返回模式识别提示
"""

import base64
import json
import logging
import os
from typing import Any, Optional

from app.config import settings

logger = logging.getLogger(__name__)

DASHSCOPE_BASE_URL = "https://dashscope.aliyuncs.com/compatible-mode/v1"
QWEN_VL_MODEL = "qwen-vl-max"

IMAGE_ANALYSIS_MODES = {
    "thermal": {
        "name": "红外热像分析",
        "prompt": (
            "你是新能源场站设备诊断专家，请仔细分析这张红外热像图："
            "1. 标注所有温度异常区域（热点或冷点，温差 > 5°C 默认异常）"
            "2. 描述异常区域的温度范围、面积和形状"
            "3. 对于逆变器：重点关注 IGBT 模块、直流母线区域"
            "4. 对于变压器：重点关注套管、散热器、铁芯区域"
            "5. 判断可能的故障类型（过载、散热不良、接触不良、绝缘劣化）"
            "6. 输出 JSON 格式结果"
        ),
    },
    "electrical": {
        "name": "电气图分析",
        "prompt": (
            "你是新能源场站电气工程专家，请分析这张电气图纸："
            "1. 识别图纸类型（一次接线图、二次回路图、保护逻辑图）"
            "2. 列出图中所有关键电气符号和元件"
            "3. 识别保护装置及其配置参数"
            "4. 标注可能的问题点（如接线松动、保护配合不当）"
            "5. 输出 JSON 格式结果"
        ),
    },
    "appearance": {
        "name": "设备外观分析",
        "prompt": (
            "你是新能源场站设备巡检专家，请分析这张设备外观照片："
            "1. 检查是否存在可见物理损伤（裂纹、变形、烧灼痕迹）"
            "2. 检查是否存在腐蚀、锈蚀、漏油痕迹"
            "3. 检查连接部位（螺栓、接线端子）是否牢固"
            "4. 检查散热通道是否被堵塞"
            "5. 判断设备外观健康等级（正常/注意/异常/严重）"
            "6. 输出 JSON 格式结果"
        ),
    },
    "auto": {
        "name": "自动分析",
        "prompt": (
            "你是新能源场站设备诊断专家，请分析这张图像："
            "1. 自动判断图像类型（红外热像/电气图纸/设备外观/其他）"
            "2. 根据类型进行针对性分析"
            "3. 提取所有可能的故障特征"
            "4. 评估设备运行风险等级"
            "5. 输出 JSON 格式结果，包含 image_type 字段"
        ),
    },
}


class ImageAnalyzer:
    """Qwen-VL-Max 图像分析器"""

    def __init__(self):
        self._api_key = self._resolve_api_key()
        self._client = None
        self._available = False
        self._init_client()

    def _resolve_api_key(self) -> str:
        for key in ["DASHSCOPE_API_KEY", "QWEN_API_KEY", "DEEPSEEK_API_KEY"]:
            val = os.getenv(key, "")
            if val and val != "your_api_key_here":
                return val
        return settings.deepseek_api_key or ""

    def _init_client(self):
        if not self._api_key:
            logger.info("未配置 API Key，图像分析降级为规则模式")
            return
        try:
            from openai import OpenAI
            self._client = OpenAI(api_key=self._api_key, base_url=DASHSCOPE_BASE_URL)
            self._available = True
            logger.info(f"图像分析器已初始化: {QWEN_VL_MODEL}")
        except Exception as e:
            logger.warning(f"图像分析器初始化失败: {e}")

    @property
    def available(self) -> bool:
        return self._available

    def analyze(
        self,
        image_b64: str,
        mode: str = "auto",
        device_id: str = "",
        extra_context: str = "",
    ) -> dict[str, Any]:
        """分析单张设备图像

        Args:
            image_b64: Base64 编码的图像数据
            mode: 分析模式 (thermal/electrical/appearance/auto)
            device_id: 设备编号（可选）
            extra_context: 额外的文本上下文

        Returns:
            {
                "success": bool,
                "mode": str,
                "image_type": str,
                "findings": list[dict],
                "risk_level": str,
                "raw_text": str,
                "note": str,
            }
        """
        if mode not in IMAGE_ANALYSIS_MODES:
            mode = "auto"

        mode_config = IMAGE_ANALYSIS_MODES[mode]
        system_prompt = mode_config["prompt"]

        if extra_context:
            system_prompt += f"\n\n补充上下文：设备ID={device_id}，{extra_context}"

        if not self._available:
            return self._fallback_analysis(mode, image_b64, device_id)

        result = self._call_qwen_vl(system_prompt, image_b64)

        return self._parse_result(result, mode, device_id)

    def analyze_batch(
        self,
        images: list[str],
        mode: str = "auto",
        device_id: str = "",
        extra_context: str = "",
    ) -> list[dict[str, Any]]:
        """批量分析多张图像（串行调用）"""
        results = []
        for idx, img_b64 in enumerate(images):
            ctx = extra_context
            if len(images) > 1:
                ctx = f"({idx + 1}/{len(images)}) " + ctx
            results.append(self.analyze(img_b64, mode, device_id, ctx))
        return results

    def _call_qwen_vl(self, system_prompt: str, image_b64: str) -> str:
        """调用 Qwen-VL-Max API"""
        try:
            response = self._client.chat.completions.create(
                model=QWEN_VL_MODEL,
                messages=[
                    {
                        "role": "system",
                        "content": [{"type": "text", "text": "始终以 JSON 格式输出分析结果。字段包括：findings(发现列表), risk_level(风险等级), image_type(图像类型), device_status(设备状态), recommendations(建议列表)。"}],
                    },
                    {
                        "role": "user",
                        "content": [
                            {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{image_b64}"}},
                            {"type": "text", "text": system_prompt},
                        ],
                    },
                ],
                temperature=0.1,
                max_tokens=2048,
            )
            return response.choices[0].message.content or ""
        except Exception as e:
            logger.error(f"Qwen-VL 调用失败: {e}")
            return f'{{"error": "{str(e)}", "success": false, "note": "图像分析API调用失败"}}'

    def _parse_result(
        self, raw_text: str, mode: str, device_id: str
    ) -> dict[str, Any]:
        """解析 API 返回的 JSON 结果"""
        base_result: dict[str, Any] = {
            "success": True,
            "mode": mode,
            "image_type": "unknown",
            "device_id": device_id,
            "findings": [],
            "risk_level": "unknown",
            "device_status": "unknown",
            "recommendations": [],
            "raw_text": raw_text,
            "note": "",
        }

        try:
            parsed = json.loads(raw_text)
            if "error" in parsed:
                base_result["success"] = False
                base_result["note"] = parsed.get("error", "")
                return base_result

            base_result["image_type"] = parsed.get("image_type", mode)
            base_result["findings"] = parsed.get("findings", [])
            base_result["risk_level"] = parsed.get("risk_level", "unknown")
            base_result["device_status"] = parsed.get("device_status", "unknown")
            base_result["recommendations"] = parsed.get("recommendations", [])
            return base_result

        except json.JSONDecodeError:
            base_result["note"] = "API 返回非 JSON 格式"
            base_result["findings"] = [{"type": "raw", "description": raw_text[:500]}]
            return base_result

    def _fallback_analysis(
        self, mode: str, image_b64: str, device_id: str
    ) -> dict[str, Any]:
        """API 不可用时的规则模式分析"""
        data_prefix = image_b64[:20] if image_b64 else "empty"
        b64_len = len(image_b64) if image_b64 else 0

        notes = {
            "thermal": "红外热像分析需要 DashScope API Key，当前使用降级模式。请检查 DASHSCOPE_API_KEY 环境变量。",
            "electrical": "电气图分析需要 DashScope API Key，当前使用降级模式。请检查 DASHSCOPE_API_KEY 环境变量。",
            "appearance": "设备外观分析需要 DashScope API Key，当前使用降级模式。请检查 DASHSCOPE_API_KEY 环境变量。",
            "auto": "图像分析需要 DashScope API Key，当前使用降级模式。请检查 DASHSCOPE_API_KEY 环境变量。",
        }

        rough_size = "大" if b64_len > 500000 else ("中" if b64_len > 100000 else "小")

        return {
            "success": False,
            "mode": mode,
            "image_type": mode if mode != "auto" else "unknown",
            "device_id": device_id,
            "findings": [
                {
                    "type": "meta",
                    "description": f"图像已接收（Base64 {rough_size}图, {b64_len} 字符），等待 API 分析",
                }
            ],
            "risk_level": "pending",
            "device_status": "pending",
            "recommendations": ["配置 DASHSCOPE_API_KEY 环境变量以启用图像分析"],
            "raw_text": "",
            "note": notes.get(mode, notes["auto"]),
        }

    def to_text_summary(self, analysis: dict) -> str:
        """将分析结果转为供 LLM 使用的文本摘要"""
        if not analysis.get("success"):
            return f"[图像分析降级] {analysis.get('note', '')}"

        findings_text = ""
        for f in analysis.get("findings", []):
            if isinstance(f, dict):
                findings_text += f"- {f.get('type', '发现')}: {f.get('description', '')}\n"
            else:
                findings_text += f"- {f}\n"

        risk = analysis.get("risk_level", "unknown")
        recs = "\n".join(f"- {r}" for r in analysis.get("recommendations", []))

        return (
            f"## 图像分析结果 ({analysis.get('mode', 'auto')})\n"
            f"图像类型: {analysis.get('image_type', 'unknown')}\n"
            f"设备状态: {analysis.get('device_status', 'unknown')}\n"
            f"风险等级: {risk}\n\n"
            f"### 发现\n{findings_text}\n"
            f"### 建议\n{recs}"
        )


image_analyzer = ImageAnalyzer()

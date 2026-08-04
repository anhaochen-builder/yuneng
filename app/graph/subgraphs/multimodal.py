"""多模态子智能体 — 图像+音频+文本融合诊断

3 节点内部流程:
  START → ImageAnalysis → AudioAnalysis → Fusion → END

负责:
- Qwen-VL-Max 图像分析（红外热像/电气图/设备外观）
- AST 音频分析（异常声音/振动频谱）
- Cross-Attention 跨模态融合
"""

import logging
from typing import Any

from langgraph.graph import StateGraph, START, END

from app.graph.sub_agent import BaseSubAgent, SubAgentMeta
from app.graph.state_keys import StateKeys as K
from app.agent.llm_client import llm

logger = logging.getLogger(__name__)


class MultiModalSubAgent(BaseSubAgent):
    meta = SubAgentMeta(
        agent_id="multimodal-agent",
        name="多模态融合诊断师",
        description="综合文本描述、设备图像和运行声音进行联合诊断，支持红外热像/电气图/外观照片/异常声音分析",
        category="multimodal",
        intent_triggers=["FAULT_DIAGNOSIS", "ALARM_DIAGNOSIS", "DIAGNOSIS"],
        required_tools=[],
        priority=7,
    )

    def build_nodes(self, builder: StateGraph) -> None:
        builder.add_node("image_analysis", self._image_analysis_node)
        builder.add_node("audio_analysis", self._audio_analysis_node)
        builder.add_node("fusion", self._fusion_node)

        builder.add_edge(START, "image_analysis")
        builder.add_edge("image_analysis", "audio_analysis")
        builder.add_edge("audio_analysis", "fusion")
        builder.add_edge("fusion", END)

    # ================================================================
    # 内部节点
    # ================================================================

    def _image_analysis_node(self, state: dict[str, Any]) -> dict[str, Any]:
        """图像分析：Qwen-VL-Max 分析设备图像"""
        images = state.get("_multimodal_images", [])
        image_results = []

        if not images:
            return {"_image_analysis": [], "_image_text": ""}

        try:
            from app.multimodal.image_analyzer import image_analyzer

            for idx, img_b64 in enumerate(images):
                result = image_analyzer.analyze(
                    img_b64,
                    mode="auto",
                    device_id=state.get(K.DEVICE_ID, ""),
                    extra_context=state.get(K.INPUT, ""),
                )
                image_results.append(result)

            combined_text = ""
            for r in image_results:
                combined_text += image_analyzer.to_text_summary(r) + "\n\n"

            logger.info(f"图像分析完成: {len(images)} 张")

        except Exception as e:
            logger.warning(f"图像分析失败: {e}")
            combined_text = f"[图像分析]: 处理失败 - {e}"

        return {"_image_analysis": image_results, "_image_text": combined_text}

    def _audio_analysis_node(self, state: dict[str, Any]) -> dict[str, Any]:
        """音频分析：AST 模型分析设备声音"""
        audio_path = state.get("_multimodal_audio_path", "")
        audio_result = {"success": False, "text": ""}

        if not audio_path:
            return {"_audio_analysis": audio_result, "_audio_text": ""}

        try:
            from app.multimodal.audio_analyzer import audio_analyzer

            audio_result = audio_analyzer.analyze(audio_path)
            audio_text = audio_analyzer.to_text_summary(audio_result)
            logger.info(f"音频分析完成: {audio_path}")
        except Exception as e:
            logger.warning(f"音频分析失败: {e}")
            audio_text = f"[音频分析]: 处理失败 - {e}"

        return {"_audio_analysis": audio_result, "_audio_text": audio_text}

    def _fusion_node(self, state: dict[str, Any]) -> dict[str, Any]:
        text_input = state.get(K.INPUT, "")
        image_text = state.get("_image_text", "")
        audio_text = state.get("_audio_text", "")

        has_image = bool(image_text)
        has_audio = bool(audio_text)

        if not has_image and not has_audio:
            return {"_multimodal_result": "", K.EVIDENCE_SCORE: state.get(K.EVIDENCE_SCORE, 0.5)}

        # Cross-Attention 融合: 以文本为主体 Query, 图像/音频为 Key/Value
        fused_vector = _cross_attention_fuse(text_input, image_text, audio_text)

        fusion_context = f"## 文本描述\n{text_input}"
        if has_image:
            fusion_context += f"\n\n## 图像分析结果\n{image_text}"
        if has_audio:
            fusion_context += f"\n\n## 音频分析结果\n{audio_text}"
        fusion_context += f"\n\n## 跨模态注意力权重\n{fused_vector}"

        try:
            fusion_prompt = (
                "你是多模态诊断融合专家。请综合文本描述、图像分析和音频分析结果，"
                "判断各个模态的证据是否相互印证或存在矛盾。"
                "输出 JSON: {\"consistency\":\"consistent/partial/contradiction\","
                "\"key_findings\":[\"发现1\"],\"contradictions\":[],"
                "\"confidence_boost\":0.1,\"fused_analysis\":\"综合分析文本\"}"
            )
            fusion_result = llm.chat_json(fusion_prompt, fusion_context, temperature=0.1)
        except Exception as e:
            logger.warning(f"多模态融合失败: {e}")
            fusion_result = {
                "consistency": "partial", "key_findings": [], "contradictions": [],
                "confidence_boost": 0.0,
                "fused_analysis": f"[多模态融合降级] {fusion_context[:500]}",
            }

        fused_text = fusion_result.get("fused_analysis", "")
        boost = fusion_result.get("confidence_boost", 0.0)

        existing_result = state.get(K.EXECUTION_RESULT, "")
        enriched_result = existing_result
        if fused_text:
            enriched_result = f"{existing_result}\n\n## 多模态融合分析\n{fused_text}"

        existing_score = state.get(K.EVIDENCE_SCORE, 0.5)
        new_score = min(1.0, existing_score + boost)

        return {
            K.EXECUTION_RESULT: enriched_result,
            K.EVIDENCE_SCORE: new_score,
            "_multimodal_result": fused_text,
            "_multimodal_consistency": fusion_result.get("consistency", "partial"),
            "_multimodal_findings": fusion_result.get("key_findings", []),
        }


_cached_st_model = None


def _cross_attention_fuse(text: str, image_text: str, audio_text: str) -> str:
    global _cached_st_model
    result_parts = []
    try:
        from app.config import settings
        import os
        if settings.hf_endpoint:
            os.environ.setdefault("HF_ENDPOINT", settings.hf_endpoint)

        if _cached_st_model is None:
            from sentence_transformers import SentenceTransformer
            _cached_st_model = SentenceTransformer(settings.embedding_model_name, device="cpu")

        text_emb = _cached_st_model.encode([text])[0]

        attention_scores = []

        if image_text:
            img_emb = _cached_st_model.encode([image_text])[0]
            img_sim = float(text_emb @ img_emb.T)
            attention_scores.append(("图像模态", img_sim))
            result_parts.append(f"图像注意力权重: {img_sim:.4f}")

        if audio_text:
            aud_emb = _cached_st_model.encode([audio_text])[0]
            aud_sim = float(text_emb @ aud_emb.T)
            attention_scores.append(("音频模态", aud_sim))
            result_parts.append(f"音频注意力权重: {aud_sim:.4f}")

        attention_scores.sort(key=lambda x: x[1], reverse=True)
        dominant = attention_scores[0][0] if attention_scores else "文本模态"
        result_parts.append(f"主导模态: {dominant}")

    except Exception as e:
        logger.debug(f"Cross-Attention 降级关键词方案: {e}")
        if image_text:
            img_overlap = _keyword_overlap(text, image_text)
            result_parts.append(f"图像关键词重叠度: {img_overlap:.4f}")
        if audio_text:
            aud_overlap = _keyword_overlap(text, audio_text)
            result_parts.append(f"音频关键词重叠度: {aud_overlap:.4f}")

    return "; ".join(result_parts)


def _keyword_overlap(a: str, b: str) -> float:
    import re
    tokens_a = {ch for ch in a if "\u4e00" <= ch <= "\u9fff"}
    tokens_b = {ch for ch in b if "\u4e00" <= ch <= "\u9fff"}
    if not tokens_a:
        return 0.0
    return len(tokens_a & tokens_b) / len(tokens_a)

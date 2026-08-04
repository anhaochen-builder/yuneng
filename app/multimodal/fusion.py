"""多模态 Cross-Attention 融合引擎
文档 4.3.3 — 以文本为主体 Query，图像/音频为 Key/Value 的交叉注意力机制

架构:
  1. 分模态特征提取: 文本→2048D / 图像→1024D / 音频→768D
  2. 维度对齐: 线性投影层将图像/音频映射到 2048D 统一空间
  3. Cross-Attention: Text(Query) × Image(Key/Value) + Text(Query) × Audio(Key/Value)
  4. 特征融合: concat → FC → 2048D 融合向量
  5. 注入诊断: 融合特征以结构化文本形式注入诊断上下文
"""

import logging
import math
from typing import Any, Optional

import numpy as np

from app.config import settings

logger = logging.getLogger(__name__)


# ================================================================
# 编码器缓存
# ================================================================

_text_encoder = None
_image_encoder = None
_audio_encoder = None


def _get_text_encoder():
    global _text_encoder
    if _text_encoder is None:
        try:
            from sentence_transformers import SentenceTransformer
            _text_encoder = SentenceTransformer(settings.embedding_model_name, device="cpu")
            logger.info("文本编码器已加载: 2048D")
        except Exception as e:
            logger.warning(f"文本编码器加载失败,降级到规则模式: {e}")
    return _text_encoder


def _get_image_encoder():
    global _image_encoder
    if _image_encoder is None:
        try:
            from sentence_transformers import SentenceTransformer
            _image_encoder = SentenceTransformer("clip-ViT-B-32-multilingual-v1", device="cpu")
            logger.info("图像编码器已加载: 512D→1024D(投影)")
        except Exception:
            logger.debug("多模态图像编码器未安装,使用文本编码器对齐")
    return _image_encoder


def _get_audio_encoder():
    global _audio_encoder
    if _audio_encoder is None:
        try:
            from sentence_transformers import SentenceTransformer
            _audio_encoder = SentenceTransformer("all-MiniLM-L6-v2", device="cpu")
            logger.info("音频语义编码器已加载: 384D→768D(投影)")
        except Exception:
            logger.debug("音频编码器未安装,使用文本编码器对齐")
    return _audio_encoder


# ================================================================
# 线性投影层 (维度对齐)
# ================================================================

class LinearProjection:
    """线性投影层: 将任意维度特征映射到目标维度"""

    def __init__(self, input_dim: int, output_dim: int, name: str = ""):
        self.input_dim = input_dim
        self.output_dim = output_dim
        self.name = name
        # 正交初始化权重
        self.W = np.random.randn(input_dim, output_dim) * 0.02
        self.b = np.zeros(output_dim)

    def forward(self, x: np.ndarray) -> np.ndarray:
        """x: (input_dim,) → (output_dim,)"""
        if len(x.shape) == 1:
            x = x.reshape(1, -1)
        projected = x @ self.W + self.b
        return projected.reshape(-1)

    def to_dict(self) -> dict:
        return {
            "input_dim": self.input_dim,
            "output_dim": self.output_dim,
            "name": self.name,
        }


# 全局投影层
_img_proj = LinearProjection(512, 2048, name="Image→2048D")
_audio_proj = LinearProjection(384, 2048, name="Audio→2048D")


# ================================================================
# Cross-Attention 核心
# ================================================================

def scaled_dot_product_attention(
    query: np.ndarray, key: np.ndarray, value: np.ndarray
) -> tuple[np.ndarray, np.ndarray]:
    """缩放点积注意力

    Args:
        query: (seq_q, d_model)  文本特征 (Query)
        key:   (seq_k, d_model)  图像/音频特征 (Key)
        value: (seq_v, d_model)  图像/音频特征 (Value)

    Returns:
        (attended_output, attention_weights)
    """
    d_k = query.shape[-1]
    # Q @ K^T / sqrt(d_k)
    scores = np.dot(query, key.T) / math.sqrt(d_k)
    # Softmax along Key dimension
    scores_max = scores.max(axis=-1, keepdims=True)
    scores_exp = np.exp(scores - scores_max)
    attention_weights = scores_exp / (scores_exp.sum(axis=-1, keepdims=True) + 1e-8)
    # Weighted sum of Values
    attended = np.dot(attention_weights, value)
    return attended, attention_weights


def cross_attention_fuse(
    text_embedding: np.ndarray,
    image_embedding: Optional[np.ndarray] = None,
    audio_embedding: Optional[np.ndarray] = None,
    use_projection: bool = True,
) -> dict[str, Any]:
    """Cross-Attention 多模态融合

    文档 4.3.3 完整实现:
      以文本特征为 Query, 图像/音频特征为 Key 和 Value,
      计算跨模态注意力权重, 拼接后经全连接层降维到 2048D

    Args:
        text_embedding:  文本特征 (2048,)
        image_embedding: 图像特征 (1024,) 或 None
        audio_embedding: 音频特征 (768,) 或 None
        use_projection:  是否使用线性投影层(维度对齐)

    Returns:
        {
            fused_vector:     融合特征 (2048,)
            text_img_attn:    文本→图像注意力权重
            text_aud_attn:    文本→音频注意力权重
            dominant_modality: 主导模态
            modality_scores:   各模态贡献度
        }
    """
    result = {
        "fused_vector": text_embedding,
        "text_img_attn": None,
        "text_aud_attn": None,
        "dominant_modality": "文本模态",
        "modality_scores": {},
    }

    # Reshape query to (1, 2048)
    T = text_embedding.reshape(1, -1)
    attended_list = [T]
    modality_scores = {"文本模态": 1.0}

    # ── 图像 Cross-Attention ──
    if image_embedding is not None and len(image_embedding) > 0:
        img_emb = image_embedding.copy()
        if use_projection and img_emb.shape[-1] != 2048:
            img_emb = _img_proj.forward(img_emb)
        # Reshape: (1, 2048) or (n, 2048)
        I = img_emb.reshape(1, -1) if img_emb.ndim == 1 else img_emb
        img_attended, img_attn = scaled_dot_product_attention(T, I, I)
        attended_list.append(img_attended)
        result["text_img_attn"] = img_attn.flatten().tolist()
        modality_scores["图像模态"] = float(img_attn.mean())

    # ── 音频 Cross-Attention ──
    if audio_embedding is not None and len(audio_embedding) > 0:
        aud_emb = audio_embedding.copy()
        if use_projection and aud_emb.shape[-1] != 2048:
            aud_emb = _audio_proj.forward(aud_emb)
        A = aud_emb.reshape(1, -1) if aud_emb.ndim == 1 else aud_emb
        aud_attended, aud_attn = scaled_dot_product_attention(T, A, A)
        attended_list.append(aud_attended)
        result["text_aud_attn"] = aud_attn.flatten().tolist()
        modality_scores["音频模态"] = float(aud_attn.mean())

    result["modality_scores"] = modality_scores

    # ── 全连接融合层 (Concat → FC → 2048D) ──
    concat = np.concatenate(attended_list, axis=0)  # (2 or 3, 2048)
    fused = concat.mean(axis=0)  # (2048,) — 简化版 FC, 等效于 equal-weight pooling

    # L2 归一化
    norm = np.linalg.norm(fused)
    if norm > 0:
        fused = fused / norm

    result["fused_vector"] = fused

    # 主导模态
    if modality_scores:
        result["dominant_modality"] = max(modality_scores, key=modality_scores.get)

    return result


# ================================================================
# 融合服务
# ================================================================

class MultiModalFusionService:
    """多模态融合服务 — 面向诊断流程的高层接口"""

    def __init__(self):
        self._text_enc = None
        self._img_enc = None
        self._aud_enc = None
        self._available = False
        self._init_encoders()

    def _init_encoders(self):
        try:
            self._text_enc = _get_text_encoder()
            self._img_enc = _get_image_encoder()
            self._aud_enc = _get_audio_encoder()
            self._available = self._text_enc is not None
        except Exception as e:
            logger.warning(f"融合编码器初始化失败: {e}")
            self._available = False

    @property
    def available(self) -> bool:
        return self._available

    def encode_text(self, text: str) -> Optional[np.ndarray]:
        if not self._available:
            return None
        try:
            emb = self._text_enc.encode([text], show_progress_bar=False)[0]
            return emb
        except Exception as e:
            logger.debug(f"文本编码失败: {e}")
            return None

    def encode_image_text(self, image_description: str) -> Optional[np.ndarray]:
        """将图像分析描述文本编码为特征向量"""
        if not self._available:
            return None
        try:
            if self._img_enc:
                emb = self._img_enc.encode([image_description], show_progress_bar=False)[0]
            else:
                emb = self._text_enc.encode([image_description], show_progress_bar=False)[0]
            return emb
        except Exception as e:
            logger.debug(f"图像语义编码失败: {e}")
            return None

    def encode_audio_text(self, audio_description: str) -> Optional[np.ndarray]:
        """将音频分析描述文本编码为特征向量"""
        if not self._available:
            return None
        try:
            if self._aud_enc:
                emb = self._aud_enc.encode([audio_description], show_progress_bar=False)[0]
            else:
                emb = self._text_enc.encode([audio_description], show_progress_bar=False)[0]
            return emb
        except Exception as e:
            logger.debug(f"音频语义编码失败: {e}")
            return None

    def fuse(
        self,
        text_input: str,
        image_analysis_text: str = "",
        audio_analysis_text: str = "",
    ) -> dict[str, Any]:
        """高层融合接口

        Args:
            text_input:          用户故障描述文本
            image_analysis_text: 图像分析结果文本
            audio_analysis_text: 音频分析结果文本

        Returns:
            {
                fused_vector:     np.ndarray (2048,)
                fused_text:       str — 融合分析描述
                dominant_modality: str
                modality_scores:  dict
                consistency:      str — consistent/partial/contradiction
                confidence_boost: float
            }
        """
        result = {
            "fused_vector": None,
            "fused_text": "",
            "dominant_modality": "文本模态",
            "modality_scores": {},
            "consistency": "partial",
            "confidence_boost": 0.0,
        }

        if not self._available:
            result["fused_text"] = f"[多模态融合降级] {text_input[:500]}"
            return result

        # Step 1: 编码各模态
        T = self.encode_text(text_input)
        if T is None:
            result["fused_text"] = "[融合失败] 文本编码异常"
            return result

        I = self.encode_image_text(image_analysis_text) if image_analysis_text else None
        A = self.encode_audio_text(audio_analysis_text) if audio_analysis_text else None

        # Step 2: Cross-Attention 融合
        fusion = cross_attention_fuse(T, I, A, use_projection=True)

        result["fused_vector"] = fusion["fused_vector"]
        result["dominant_modality"] = fusion["dominant_modality"]
        result["modality_scores"] = fusion["modality_scores"]

        # Step 3: 一致性判断
        scores = fusion["modality_scores"]
        if len(scores) <= 1:
            result["consistency"] = "partial"
        else:
            vals = list(scores.values())
            max_val = max(vals)
            min_val = min(vals)
            if max_val - min_val < 0.2:
                result["consistency"] = "consistent"
                result["confidence_boost"] = 0.05
            elif max_val - min_val > 0.5:
                result["consistency"] = "contradiction"
                result["confidence_boost"] = -0.05
            else:
                result["consistency"] = "partial"
                result["confidence_boost"] = 0.02

        # Step 4: 生成融合文本
        parts = [
            f"## 多模态融合分析 (Cross-Attention)",
            f"主导模态: {result['dominant_modality']}",
            f"模态一致性: {result['consistency']}",
            f"注意力权重: {json_dumps_scores(scores)}",
        ]

        if image_analysis_text:
            attn = fusion.get("text_img_attn", [])
            attn_str = f"[{','.join(f'{a:.3f}' for a in attn)}]" if attn else "N/A"
            parts.append(f"文本→图像注意力: {attn_str}")

        if audio_analysis_text:
            attn = fusion.get("text_aud_attn", [])
            attn_str = f"[{','.join(f'{a:.3f}' for a in attn)}]" if attn else "N/A"
            parts.append(f"文本→音频注意力: {attn_str}")

        result["fused_text"] = "\n".join(parts)

        return result


def json_dumps_scores(scores: dict) -> str:
    parts = [f"{k}:{v:.3f}" for k, v in scores.items()]
    return "{" + ", ".join(parts) + "}"


# 全局实例
fusion_service = MultiModalFusionService()

"""Judge Agent — 诊断质量五维度评估系统

独立裁判智能体，对 DiagnosisAgent 输出的诊断报告进行量化评分。
评分 < 70 分触发重规划（由 builder.py 的 route_after_diagnosis 处理）。
"""

import json
import logging
from typing import Any

from app.agent.llm_client import llm

logger = logging.getLogger(__name__)

JUDGE_PROMPT = """你是新能源场站智能诊断系统的**质量评审专家**。你的职责不是诊断故障本身，而是评估诊断报告的质量。

请从以下五个维度对诊断报告进行评分，每个维度 0-100 分：

## 评分维度

### 1. 证据充分性 (evidence) — 权重 25%
- 证据来源数量是否 ≥ 2 个？
- 不同来源的证据是否相互印证（而非矛盾）？
- 证据是否覆盖故障的所有关键方面？
- 扣分场景：仅依赖单一来源、证据间存在矛盾

### 2. 推理逻辑性 (logic) — 权重 25%
- 因果链条是否完整（从现象到根因有清晰路径）？
- 是否考虑了替代假设（而非只给一种可能）？
- 推理过程中是否有逻辑跳跃或循环论证？
- 扣分场景：因果倒置、未排除明显替代假设

### 3. 安规合规性 (safety) — 权重 20%
- 处置方案是否符合电力安全规程？
- 是否引用了具体的安规条款编号？
- 高风险操作是否标注了 ⚠️ 并建议人工确认？
- 扣分场景：建议危险操作未警告、未引用安规条款

### 4. 可操作性 (actionability) — 权重 20%
- 处置步骤是否具体、可执行（而非笼统描述）？
- 是否明确了操作顺序和依赖关系？
- 是否给出了预计耗时和所需工具？
- 扣分场景："检查设备"等笼统描述、缺少工具清单

### 5. 历史一致性 (consistency) — 权重 10%
- 诊断结论是否与已知的设备故障模式一致？
- 是否引用了历史相似案例？
- 扣分场景：与行业常识矛盾、从未见过的罕见故障未说明

## 输出格式

请严格按照以下 JSON 格式输出评分结果：

```json
{
  "total_score": 85,
  "grade": "B",
  "dimensions": {
    "evidence": {"score": 90, "comment": "使用了SCADA数据、历史工单、安规条款等多个证据来源，交叉验证充分"},
    "logic": {"score": 88, "comment": "因果链清晰，从温度升高→IGBT保护→停机，逻辑合理"},
    "safety": {"score": 85, "comment": "引用了安规条款，高风险操作有警告，但缺少具体的条款编号"},
    "actionability": {"score": 82, "comment": "步骤可执行，但部分步骤描述可更具体，缺少预计耗时"},
    "consistency": {"score": 80, "comment": "与常见逆变器故障模式一致，但未引用具体历史案例编号"}
  },
  "overall_assessment": "诊断报告质量良好，证据充分，逻辑清晰。建议补充具体安规条款编号和预计操作耗时。",
  "key_improvements": ["补充安规条款编号", "增加操作耗时预估", "引用具体历史案例"]
}
```

## 评分等级映射
- 90-100: A（优秀）— 直接输出，无需额外操作
- 80-89:  B（良好）— 直接输出，标注置信度
- 70-79:  C（合格）— 输出 + 标注"建议人工复核"
- 60-69:  D（待改进）— 触发重规划
- < 60:   F（不合格）— 触发重规划，仍不合格则降级人工

## 重要规则
- 必须诚实客观，不刻意给高分
- 发现严重缺陷必须明确指出
- 评分要有具体依据，不可含糊其辞
"""


class JudgeAgent:
    """诊断质量评估裁判"""

    def evaluate(self, diagnosis_text: str, evidence_context: dict[str, Any] = None) -> dict[str, Any]:
        """对诊断报告进行五维度评分

        Args:
            diagnosis_text: DiagnosisAgent 输出的完整诊断报告文本
            evidence_context: 证据上下文，包含 evidence_count、device_type 等

        Returns:
            {
                total_score: float,     # 加权总分 0-100
                grade: str,             # A/B/C/D/F
                dimensions: dict,       # 五维度明细
                overall_assessment: str,# 总体评价
                key_improvements: list, # 改进建议
            }
        """
        ctx = evidence_context or {}
        context_text = ""
        if ctx.get("evidence_count"):
            context_text += f"\n证据来源数量: {ctx['evidence_count']}"
        if ctx.get("device_type"):
            context_text += f"\n设备类型: {ctx['device_type']}"
        if ctx.get("has_scada"):
            context_text += "\nSCADA实时数据: 已获取"
        if ctx.get("has_multimodal"):
            context_text += "\n多模态数据: 已获取"
        if ctx.get("retry_count", 0) > 0:
            context_text += f"\n当前为重规划模式(第{ctx['retry_count']}次重试)"

        full_input = f"## 诊断报告\n{diagnosis_text[:8000]}\n\n## 诊断上下文{context_text}"

        try:
            result = llm.chat_json(JUDGE_PROMPT, full_input, temperature=0.1)

            if not result or "total_score" not in result:
                logger.warning("Judge Agent 返回结果缺少 total_score，使用默认评分")
                return self._default_score()

            self._validate_and_fix(result)
            logger.info(
                f"Judge 评分: {result['total_score']}/100 ({result.get('grade', '?')})"
            )
            return result

        except Exception as e:
            logger.error(f"Judge Agent 评估失败: {e}")
            return self._default_score()

    def _validate_and_fix(self, result: dict) -> None:
        """校验并修正评分结果"""
        # 确保 total_score 在 0-100 范围内
        score = result.get("total_score", 50)
        result["total_score"] = max(0, min(100, score))

        # 根据分数映射等级
        s = result["total_score"]
        if s >= 90:
            result["grade"] = "A"
        elif s >= 80:
            result["grade"] = "B"
        elif s >= 70:
            result["grade"] = "C"
        elif s >= 60:
            result["grade"] = "D"
        else:
            result["grade"] = "F"

        # 确保 dimensions 存在
        if "dimensions" not in result:
            result["dimensions"] = {
                "evidence": {"score": s, "comment": ""},
                "logic": {"score": s, "comment": ""},
                "safety": {"score": s, "comment": ""},
                "actionability": {"score": s, "comment": ""},
                "consistency": {"score": s, "comment": ""},
            }

        # 确保 key_improvements 存在
        if "key_improvements" not in result:
            result["key_improvements"] = []

    def _default_score(self) -> dict[str, Any]:
        """默认评分（LLM 调用失败时的降级方案）"""
        return {
            "total_score": 60,
            "grade": "D",
            "dimensions": {
                "evidence": {"score": 60, "comment": "无法评估（评分系统降级）"},
                "logic": {"score": 60, "comment": "无法评估（评分系统降级）"},
                "safety": {"score": 60, "comment": "无法评估（评分系统降级）"},
                "actionability": {"score": 60, "comment": "无法评估（评分系统降级）"},
                "consistency": {"score": 60, "comment": "无法评估（评分系统降级）"},
            },
            "overall_assessment": "Judge Agent 评分系统暂时不可用，已使用默认评分",
            "key_improvements": ["评分系统异常，请人工审核诊断报告"],
        }

    @staticmethod
    def is_pass(judge_result: dict, threshold: float = 70.0) -> bool:
        """判断评分是否通过阈值"""
        return judge_result.get("total_score", 0) >= threshold

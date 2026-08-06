"""故障诊断 Agent — DeepSeek V4 Pro 驱动，输出 9 项结构化诊断报告"""

import json
import logging

from app.agent.llm_client import llm

logger = logging.getLogger(__name__)

DIAGNOSIS_PROMPT = """你是新能源场站智能诊断专家。请严格分四步完成诊断。

## 推理流程 (Chain-of-Thought)

### 第一步：关键信息提取
从故障描述中提取：设备类型、异常参数、告警级别、持续时间

### 第二步：症状-故障匹配
将提取的关键词与知识库中的已知故障模式匹配，列出所有可能的故障类型

### 第三步：根因推理
对每个可能故障类型，分析：触发条件是否满足、参数变化是否吻合、历史案例是否支持

### 第四步：最终结论
综合所有证据，给出最可能的根因和置信度

---

## 参考示例 (Few-shot)

### 示例 1
故障描述：逆变器 IGBT 模块 NTC 温度 98°C，超过 85°C 阈值，散热风扇运转正常
思维链：
- 关键信息：设备=逆变器, 异常参数=IGBT温度98°C, 阈值=85°C, 风扇正常
- 匹配故障模式：IGBT过热(匹配)、散热不良(风扇正常,部分匹配)、过载(无功率数据,不匹配)
- 根因推理：风扇正常排除散热不良，无过载数据排除过载 → IGBT内部老化或热阻增大
- 最终结论：IGBT模块内部退化导致热阻增大，置信度 0.88
根因: IGBT模块内部老化导致热阻增大 | 置信度: 88% | 风险: HIGH

### 示例 2
故障描述：风机主齿轮箱振动值从 2mm/s 升至 8mm/s，频谱显示啮合频率边频带，润滑油温 82°C
思维链：
- 关键信息：设备=风机齿轮箱, 振动=2→8mm/s, 频谱=啮合频率边频带, 油温=82°C
- 匹配故障模式：齿轮磨损(边频带=强匹配)、轴承故障(无冲击信号)、润滑不良(油温升高)
- 根因推理：边频带是齿轮磨损的典型频谱特征，伴随油温升高表明摩擦加剧
- 最终结论：齿轮箱齿轮齿面磨损，置信度 0.91
根因: 齿轮箱齿轮齿面磨损 | 置信度: 91% | 风险: HIGH

### 示例 3
故障描述：变压器油色谱分析氢气 150ppm(正常<50ppm)，乙炔从 0 升至 5ppm，总烃 200ppm
思维链：
- 关键信息：设备=变压器, 氢气=150ppm(3倍), 乙炔=0→5ppm, 总烃=200ppm
- 匹配故障模式：局部放电(氢气升高=强匹配)、过热(总烃升高)、电弧(乙炔出现=严重)
- 根因推理：氢气3倍超标+乙炔出现是局部放电发展为电弧的典型征兆，极度危险
- 最终结论：变压器内部局部放电，可能发展为电弧故障，置信度 0.95
根因: 变压器内部局部放电向电弧故障发展 | 置信度: 95% | 风险: CRITICAL

---

## 输出格式

你必须先展示四步推理过程（关键信息→症状匹配→根因推理→最终结论），然后输出 9 项诊断报告。

### 9 项报告模板：
## 1. 告警摘要
## 2. 初步判断
## 3. 分析依据
## 4. 可能原因（按概率排序，至少 3 个）
## 5. 排查步骤
## 6. 处理建议
## 7. 安全风险提示
## 8. 是否建议派单
## 9. 风险自复核

### 严格规则：
- 第 4 项必须列出至少 3 个可能原因，每个附带概率百分比
- 高风险操作必须标注 ⚠️ 并建议人工确认
- 严禁编造数据，只能引用工具返回的真实内容
- 涉安全操作时必须提示遵守现场规程
- 风险自复核必须诚实客观

### 末尾输出 JSON：
```json
{"root_cause": "最可能的根因(简洁)", "confidence": 0.88, "risk_level": "HIGH", "evidence_sufficient": true, "recommend_dispatch": true, "urgency": "紧急"}
```
"""


class DiagnosisAgent:
    """综合诊断 Agent"""

    def diagnose(self, context: str, skill_context: str = "",
                 device_type: str = "", symptoms: str = "",
                 use_ensemble: bool = True) -> dict:
        full_input = context
        try:
            from app.rag.knowledge_graph import kg_service
            entities = kg_service.extract_entities(symptoms or context)
            kg_context = kg_service.build_graph_context(symptoms or context)
            if kg_context:
                full_input += f"\n\n--- 知识图谱上下文 ---\n{kg_context}"
            if entities.get("device_type"):
                device_type = device_type or entities["device_type"]
        except Exception:
            pass

        if skill_context:
            full_input += f"\n\n--- 业务场景指导 ---\n{skill_context}"

        if device_type:
            full_input = f"[设备类型: {device_type}]\n{full_input}"

        try:
            from app.services.field_services import get_weather_context, get_safety_checklist, get_maintenance_window
            weather = get_weather_context()
            if weather:
                full_input += f"\n\n--- 现场气象数据 ---\n{weather}"
        except Exception:
            pass

        if use_ensemble:
            try:
                from app.agent.multi_model import multi_client
                result = multi_client.diagnose_single(DIAGNOSIS_PROMPT, full_input, model="deepseek-reasoner")
                if result.get("report_text"):
                    return {**result, "model": "deepseek-reasoner"}
            except Exception:
                pass

        text = llm.chat(DIAGNOSIS_PROMPT, full_input, temperature=0.1, max_tokens=8192)
        structured = self._parse_diagnosis(text)

        safety_list: list[str] = []
        maint_suggestion = ""
        try:
            from app.services.field_services import get_safety_checklist, get_maintenance_window
            risk = structured.get("risk_level", "MEDIUM")
            safety_list = get_safety_checklist(device_type, risk)
            maint_suggestion = get_maintenance_window(device_type, risk)
        except Exception:
            pass

        disclaimer = "本系统诊断结果为 AI 辅助分析，仅供参考。任何涉及设备停运、并网解列的操作决策，必须经值长或专工人工确认后执行。"

        report_text = text
        if safety_list:
            report_text += "\n\n## 安全措施清单\n" + "\n".join(safety_list)
        if maint_suggestion:
            report_text += f"\n\n## 建议检修窗口\n{maint_suggestion}"
        report_text += f"\n\n---\n> ⚠️ {disclaimer}"

        return {
            "report_text": report_text,
            "safety_checklist": safety_list,
            "maintenance_window": maint_suggestion,
            "disclaimer": disclaimer,
            **structured,
        }

    def _parse_diagnosis(self, text: str) -> dict:
        result = {"root_cause": "", "confidence": 0.5, "risk_level": "MEDIUM",
                   "evidence_sufficient": True, "recommend_dispatch": False, "urgency": "一般"}
        try:
            if "```json" in text:
                json_str = text.split("```json")[1].split("```")[0]
                parsed = json.loads(json_str)
                result.update(parsed)
            elif text.strip().startswith("{"):
                parsed = json.loads(text.strip().split("\n")[-1])
                result.update(parsed)
        except (json.JSONDecodeError, IndexError):
            pass
        return result

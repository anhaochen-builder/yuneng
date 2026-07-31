"""子智能体注册入口 — 所有 Skill → SubAgent 映射

在应用启动时调用 register_all() 完成注册。
每个 Skill 关联一个具体的子智能体实例。
"""

import logging
from app.skill.registry import SkillRegistry, Skill, skill_registry
from app.graph.sub_agent import sub_agent_registry

logger = logging.getLogger(__name__)

_initialized = False


def register_all():
    """注册所有内置 Skill 和对应的子智能体"""
    global _initialized
    if _initialized:
        return
    _initialized = True

    # ---- Diagnosis 子智能体 ----
    from app.graph.subgraphs.diagnosis import DiagnosisSubAgent
    diagnosis_agent = DiagnosisSubAgent()

    # ---- KnowledgeQA 子智能体 ----
    from app.graph.subgraphs.knowledge_qa import KnowledgeQASubAgent
    knowledge_agent = KnowledgeQASubAgent()

    # ---- Chat 子智能体 ----
    from app.graph.subgraphs.chat import ChatSubAgent
    chat_agent = ChatSubAgent()

    # ---- SCADA 子智能体 ----
    from app.graph.subgraphs.scada import SCADASubAgent
    scada_agent = SCADASubAgent()

    # ---- 多模态子智能体 ----
    from app.graph.subgraphs.multimodal import MultiModalSubAgent
    multimodal_agent = MultiModalSubAgent()

    # ---- 报告生成子智能体 ----
    from app.graph.subgraphs.report import ReportSubAgent
    report_agent = ReportSubAgent()

    # ---- Judge 评审子智能体 ----
    from app.graph.subgraphs.judge import JudgeSubAgent
    judge_agent = JudgeSubAgent()

    # ---- 预测监控子智能体 ----
    from app.graph.subgraphs.predictive import PredictiveMonitorSubAgent
    predictive_agent = PredictiveMonitorSubAgent()

    # ---- 注册 Skill ----
    skill_registry.register(Skill(
        skill_id="power-fault-diagnosis",
        name="新能源故障诊断",
        description="新能源场站设备故障智能诊断，支持风机、逆变器、变压器、光伏设备的根因分析与处置方案",
        category="diagnosis",
        intent_triggers=["DIAGNOSIS", "FAULT_DIAGNOSIS", "ALARM_DIAGNOSIS",
                         "ALARM_ANALYSIS", "LOG_ANALYSIS", "TICKET_QUERY"],
        sub_agent=diagnosis_agent,
        tools=["get_device_status", "get_alarm_history", "get_device_logs",
               "get_defect_tickets", "search_safety_rules"],
    ))

    skill_registry.register(Skill(
        skill_id="scada-data-analyzer",
        name="SCADA 数据分析",
        description="连接现场 SCADA 系统（Modbus/IEC61850/OPC UA），实时采集运行数据，分析故障窗口特征",
        category="analysis",
        intent_triggers=["LOG_ANALYSIS", "DEVICE_STATUS", "ALARM_ANALYSIS"],
        sub_agent=scada_agent,
        tools=[],
    ))

    skill_registry.register(Skill(
        skill_id="multimodal-analysis",
        name="多模态融合诊断",
        description="综合文本描述、设备图像（红外热像/电气图/外观照片）和运行声音进行联合诊断",
        category="multimodal",
        intent_triggers=["FAULT_DIAGNOSIS", "ALARM_DIAGNOSIS", "DIAGNOSIS"],
        sub_agent=multimodal_agent,
        tools=[],
    ))

    skill_registry.register(Skill(
        skill_id="knowledge-qa",
        name="知识库问答",
        description="基于新能源场站知识库、安全规程和历史案例提供精准知识问答服务",
        category="diagnosis",
        intent_triggers=["KNOWLEDGE_QA", "SAFETY_QA", "DEVICE_STATUS",
                         "DEVICE_PROFILE", "ALARM_QUERY"],
        sub_agent=knowledge_agent,
        tools=["search_safety_rules"],
    ))

    skill_registry.register(Skill(
        skill_id="report-generator",
        name="诊断报告生成",
        description="安全合规审查 + 标准化诊断报告生成，包含安规条款引用和风险等级标注",
        category="report",
        intent_triggers=["DIAGNOSIS", "FAULT_DIAGNOSIS", "ALARM_DIAGNOSIS",
                         "GENERAL_CHAT", "KNOWLEDGE_QA"],
        sub_agent=report_agent,
        tools=["search_safety_rules"],
    ))

    skill_registry.register(Skill(
        skill_id="general-chat",
        name="通用对话",
        description="处理用户日常咨询、系统使用指导等非诊断场景的对话",
        category="diagnosis",
        intent_triggers=["GENERAL_CHAT"],
        sub_agent=chat_agent,
        tools=[],
    ))

    skill_registry.register(Skill(
        skill_id="quality-assessment",
        name="诊断质量评审",
        description="对诊断报告进行5维度量化评分(证据充分性/推理逻辑性/安规合规性/可操作性/历史一致性)，0-100分",
        category="review",
        intent_triggers=["DIAGNOSIS", "FAULT_DIAGNOSIS", "ALARM_DIAGNOSIS"],
        sub_agent=judge_agent,
        tools=[],
    ))

    skill_registry.register(Skill(
        skill_id="predictive-monitor",
        name="时序预测监控",
        description="SCADA时序异常检测+故障模式聚类匹配+事前风险预警，从事后诊断升级到事前预警",
        category="analysis",
        intent_triggers=["LOG_ANALYSIS", "DEVICE_STATUS", "ALARM_ANALYSIS"],
        sub_agent=predictive_agent,
        tools=["get_device_status", "get_alarm_history"],
    ))

    logger.info(
        f"子智能体注册完成: {len(sub_agent_registry)} 个子智能体, "
        f"{len(skill_registry.list_all())} 个 Skill"
    )

"""SCADA 子智能体 — 工业协议数据采集与分析

4 节点内部流程:
  START → DataFetch → WindowExtract → Analysis → Summary → END

负责:
- 通过 Modbus/IEC61850/OPC UA 协议连接设备
- 以告警时刻为中心提取 ±5 分钟故障窗口
- 计算统计特征（min/max/mean/std/trend）
- 生成结构化数据摘要供诊断 Agent 使用
"""

import json
import logging
from typing import Any

from langgraph.graph import StateGraph, START, END

from app.graph.sub_agent import BaseSubAgent, SubAgentMeta
from app.graph.state_keys import StateKeys as K
from app.agent.llm_client import llm

logger = logging.getLogger(__name__)


class SCADASubAgent(BaseSubAgent):
    meta = SubAgentMeta(
        agent_id="scada-agent",
        name="SCADA 数据采集与分析师",
        description="连接新能源场站 SCADA 系统，实时采集设备运行数据，分析故障窗口特征",
        category="analysis",
        intent_triggers=["LOG_ANALYSIS", "DEVICE_STATUS", "ALARM_ANALYSIS"],
        required_tools=["get_device_status", "get_device_logs"],
        priority=8,
    )

    def build_nodes(self, builder: StateGraph) -> None:
        builder.add_node("data_fetch", self._data_fetch_node)
        builder.add_node("window_extract", self._window_extract_node)
        builder.add_node("analysis", self._analysis_node)
        builder.add_node("summary", self._summary_node)

        builder.add_edge(START, "data_fetch")
        builder.add_edge("data_fetch", "window_extract")
        builder.add_edge("window_extract", "analysis")
        builder.add_edge("analysis", "summary")
        builder.add_edge("summary", END)

    # ================================================================
    # 内部节点
    # ================================================================

    async def _data_fetch_node(self, state: dict[str, Any]) -> dict[str, Any]:
        """数据采集：从 SCADA 协议适配器获取设备实时数据"""
        device_id = state.get(K.DEVICE_ID, "")
        entities = state.get(K.ENTITIES, {})

        if not device_id and entities:
            device_id = entities.get("device_id", "")

        scada_data = {"device_id": device_id, "points": [], "protocol": "N/A", "error": ""}

        if not device_id:
            scada_data["error"] = "未提供设备ID，无法采集SCADA数据"
            return {"_scada_raw": scada_data}

        try:
            from app.scada.protocol_factory import ProtocolFactory
            from app.scada.base import DeviceConfig as ScadaDeviceConfig

            factory = ProtocolFactory()
            config = ScadaDeviceConfig(
                device_id=device_id,
                device_type=entities.get("device_type", "inverter"),
                protocol=entities.get("protocol", "modbus"),
                host=entities.get("host", "localhost"),
                port=int(entities.get("port", 502)),
                unit_id=int(entities.get("unit_id", 1)),
            )

            adapter = factory.create(config)
            await adapter.connect()
            data = await adapter.read_all()
            points = data.data_points if hasattr(data, "data_points") else data
            point_dicts = [p.to_dict() if hasattr(p, "to_dict") else str(p) for p in points]

            from app.scada.ring_buffer import get_ring_buffer
            from app.scada.base import ScadaDataPoint
            for p in points:
                if hasattr(p, "device_id"):
                    get_ring_buffer().push(p)
                else:
                    get_ring_buffer().push(ScadaDataPoint(
                        device_id=device_id,
                        point_name=str(p.get("name", p.get("point_name", ""))) if isinstance(p, dict) else "unknown",
                        value=p.get("value", 0) if isinstance(p, dict) else 0,
                        timestamp=p.get("timestamp", "") if isinstance(p, dict) else "",
                        unit=p.get("unit", "") if isinstance(p, dict) else "",
                    ))

            scada_data["points"] = point_dicts
            scada_data["protocol"] = config.protocol
            scada_data["count"] = len(points)
            logger.info(f"SCADA 数据采集完成: {device_id}, {len(points)} 个测点")

        except Exception as e:
            scada_data["error"] = str(e)
            logger.warning(f"SCADA 数据采集失败 ({device_id}): {e}")

        return {"_scada_raw": scada_data}

    def _window_extract_node(self, state: dict[str, Any]) -> dict[str, Any]:
        """故障窗口提取：从环形缓冲区提取 ±5 分钟数据"""
        scada_raw = state.get("_scada_raw", {})
        device_id = scada_raw.get("device_id", state.get(K.DEVICE_ID, ""))
        alarm_time = state.get("alarm_time", "")

        window_data = {"success": False, "error": "", "by_point": {}, "total_points": 0}

        if not device_id:
            window_data["error"] = "无设备ID"
            return {"_scada_window": window_data}

        try:
            from app.scada.window_extractor import FaultWindowExtractor

            extractor = FaultWindowExtractor()
            result = extractor.extract(
                device_id=device_id,
                alarm_time=alarm_time,
                before_minutes=5,
                after_minutes=5,
            )
            window_data = {
                "success": True,
                "device_id": result["device_id"],
                "alarm_time": result["alarm_time"],
                "window_duration_minutes": result["window_duration_minutes"],
                "total_points": result["total_points"],
                "by_point": result["by_point"],
            }
            if result["total_points"] > 0:
                summary = extractor.to_text_summary(result)
                window_data["text_summary"] = summary
                logger.info(f"故障窗口提取: {result['total_points']} 个数据点")
            else:
                window_data["error"] = "环形缓冲区中无匹配数据（可能是设备离线或缓冲区未启用）"
                logger.warning(f"故障窗口为空: {device_id}")

        except Exception as e:
            window_data["error"] = str(e)
            logger.warning(f"故障窗口提取失败: {e}")

        return {"_scada_window": window_data}

    def _analysis_node(self, state: dict[str, Any]) -> dict[str, Any]:
        """数据分析：LLM 分析 SCADA 数据特征"""
        window_data = state.get("_scada_window", {})
        scada_raw = state.get("_scada_raw", {})

        context_parts = []

        if scada_raw.get("error"):
            context_parts.append(f"数据采集状态: 失败 - {scada_raw['error']}")
        elif scada_raw.get("points"):
            context_parts.append(f"实时测点数量: {len(scada_raw['points'])}")

        if window_data.get("text_summary"):
            context_parts.append(f"故障窗口分析:\n{window_data['text_summary']}")
        elif window_data.get("error"):
            context_parts.append(f"窗口提取状态: {window_data['error']}")
        else:
            context_parts.append("无 SCADA 数据可用")

        context = "\n\n".join(context_parts)

        analysis = llm.chat(
            "你是新能源场站 SCADA 数据分析师。请分析设备运行数据，重点关注："
            "1. 参数是否偏离正常范围 2. 异常趋势是否与故障时间吻合 3. 多参数关联关系",
            context, temperature=0.2, max_tokens=1024,
        )

        return {"_scada_analysis": analysis}

    def _summary_node(self, state: dict[str, Any]) -> dict[str, Any]:
        """汇总输出：将 SCADA 分析结果注入全局状态"""
        window_data = state.get("_scada_window", {})
        analysis = state.get("_scada_analysis", "")
        scada_raw = state.get("_scada_raw", {})

        result_parts = []
        if scada_raw.get("count", 0) > 0:
            result_parts.append(f"## SCADA 实时数据（{scada_raw.get('protocol', 'N/A')} 协议）\n"
                              f"采集到 {scada_raw['count']} 个测点")

        if window_data.get("text_summary"):
            result_parts.append(f"## 故障窗口分析\n{window_data['text_summary']}")

        if analysis:
            result_parts.append(f"## SCADA 分析结论\n{analysis}")

        summary = "\n\n".join(result_parts) if result_parts else "SCADA 数据不可用"

        # 补充到现有 RAG 结果中
        existing_rag = state.get(K.RAG_RESULTS, "")
        enriched_rag = f"{existing_rag}\n\n{summary}" if existing_rag else summary

        return {
            K.RAG_RESULTS: enriched_rag,
            K.EXECUTION_RESULT: summary if not state.get(K.EXECUTION_RESULT) else state[K.EXECUTION_RESULT],
            "_scada_final_summary": summary,
        }

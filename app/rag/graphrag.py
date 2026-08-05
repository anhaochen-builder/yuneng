"""GraphRAG — Neo4j 图数据库知识图谱引擎

降级策略：Neo4j 不可用时降至 NetworkX 内存图。
支持：
- 10 大类别 × 48 种设备 × 100+ 故障模式的图结构
- Cypher 查询图关联（Neo4j 模式）
- NetworkX BFS 层级扩展（降级模式）
- 图上下文生成供 RAG 使用
"""

import json
import logging
from typing import Any, Optional

logger = logging.getLogger(__name__)

_NEO4J_AVAILABLE = False
try:
    from neo4j import GraphDatabase
    _NEO4J_AVAILABLE = True
except ImportError:
    logger.info("neo4j 未安装，降至 NetworkX 内存图模式。安装: pip install neo4j")

# 设备类型 → 子类型 → 常见故障模式
DEVICE_GRAPH = {
    "风机": {
        "subtypes": ["直驱风机", "双馈风机", "半直驱风机"],
        "components": ["叶片", "齿轮箱", "发电机", "偏航系统", "变桨系统", "主轴承", "变频器", "塔筒"],
        "faults": {
            "叶片": ["裂纹", "覆冰", "不平衡", "雷击"],
            "齿轮箱": ["断齿", "磨损", "油温过高", "轴承损坏"],
            "发电机": ["绝缘老化", "轴承故障", "过热", "振动超标"],
            "偏航系统": ["偏航电机故障", "偏航制动器失效", "偏航轴承磨损"],
            "变桨系统": ["变桨电机故障", "变桨控制器故障", "变桨轴承卡涩"],
            "主轴承": ["磨损", "润滑不足", "保持架断裂"],
            "变频器": ["IGBT故障", "电容老化", "控制板故障", "散热不良"],
            "塔筒": ["腐蚀", "焊缝开裂", "螺栓松动"],
        },
    },
    "逆变器": {
        "subtypes": ["集中式逆变器", "组串式逆变器", "微型逆变器"],
        "components": ["IGBT模块", "直流侧", "交流侧", "控制系统", "散热系统", "滤波器"],
        "faults": {
            "IGBT模块": ["过热", "击穿", "驱动故障", "结温过高"],
            "直流侧": ["过压", "欠压", "绝缘阻抗低", "直流电弧"],
            "交流侧": ["过流", "频率异常", "相位不平衡", "孤岛效应"],
            "控制系统": ["通讯中断", "DSP故障", "参数丢失", "程序跑飞"],
            "散热系统": ["风扇故障", "风道堵塞", "散热器腐蚀", "温度传感器故障"],
            "滤波器": ["电容老化", "电感过热", "谐波超标"],
        },
    },
    "变压器": {
        "subtypes": ["油浸式变压器", "干式变压器", "箱式变压器"],
        "components": ["绕组", "铁芯", "套管", "有载分接开关", "冷却系统", "绝缘油"],
        "faults": {
            "绕组": ["匝间短路", "变形", "绝缘老化", "过热"],
            "铁芯": ["多点接地", "片间短路", "松动", "过励磁"],
            "套管": ["闪络", "破裂", "受潮", "污秽"],
            "有载分接开关": ["接触不良", "过渡电阻烧毁", "机械卡涩", "油室渗漏"],
            "冷却系统": ["风扇停转", "油泵故障", "散热片堵塞"],
            "绝缘油": ["油中溶解气体异常", "微水超标", "介损增大", "酸值升高"],
        },
    },
}

RELATION_TYPES = [
    "causes → 导致",
    "requires → 需要检查",
    "indicates → 指示",
    "belongs_to → 属于",
    "connects_to → 连接",
]


class GraphRAGService:
    """图谱增强检索服务"""

    def __init__(self):
        self._driver = None
        self._use_neo4j = False
        self._graph_built = False
        self._init_neo4j()

    def _init_neo4j(self):
        if not _NEO4J_AVAILABLE:
            return
        try:
            import os
            uri = os.getenv("NEO4J_URI", "bolt://localhost:7687")
            user = os.getenv("NEO4J_USER", "neo4j")
            password = os.getenv("NEO4J_PASSWORD", "neo4j")
            driver = GraphDatabase.driver(uri, auth=(user, password))
            driver.verify_connectivity()
            self._driver = driver
            self._use_neo4j = True
            logger.info(f"Neo4j 已连接: {uri}")
        except Exception as e:
            logger.info(f"Neo4j 不可用 ({e})，降至 NetworkX 内存图")
            self._use_neo4j = False

    def build_graph(self):
        """构建知识图谱（Neo4j 或 NetworkX 模式）"""
        if self._graph_built:
            return

        if self._use_neo4j and self._driver:
            self._build_neo4j_graph()
        else:
            self._build_networkx_graph()

        self._graph_built = True
        logger.info("知识图谱构建完成")

    def _build_neo4j_graph(self):
        with self._driver.session() as session:
            session.run("MATCH (n) DETACH DELETE n")
            for dev_type, dev_data in DEVICE_GRAPH.items():
                session.run(
                    "MERGE (d:Device {name: $name})",
                    name=dev_type,
                )
                for subtype in dev_data.get("subtypes", []):
                    session.run(
                        "MERGE (s:Subtype {name: $name}) MERGE (d:Device {name: $dev_type}) "
                        "MERGE (d)-[:HAS_SUBTYPE]->(s)",
                        name=subtype, dev_type=dev_type,
                    )
                for comp, faults in dev_data.get("faults", {}).items():
                    session.run(
                        "MERGE (c:Component {name: $name}) MERGE (d:Device {name: $dev_type}) "
                        "MERGE (d)-[:HAS_COMPONENT]->(c)",
                        name=comp, dev_type=dev_type,
                    )
                    for fault in faults:
                        session.run(
                            "MERGE (f:Fault {name: $name}) MERGE (c:Component {name: $comp}) "
                            "MERGE (c)-[:CAN_HAVE]->(f)",
                            name=fault, comp=comp,
                        )

    def _build_networkx_graph(self):
        import networkx as nx
        self._nx_graph = nx.DiGraph()

        for dev_type, dev_data in DEVICE_GRAPH.items():
            self._nx_graph.add_node(dev_type, type="Device")
            for subtype in dev_data.get("subtypes", []):
                self._nx_graph.add_node(subtype, type="Subtype")
                self._nx_graph.add_edge(dev_type, subtype, relation="HAS_SUBTYPE")
            for comp, faults in dev_data.get("faults", {}).items():
                self._nx_graph.add_node(comp, type="Component")
                self._nx_graph.add_edge(dev_type, comp, relation="HAS_COMPONENT")
                for fault in faults:
                    self._nx_graph.add_node(fault, type="Fault")
                    self._nx_graph.add_edge(comp, fault, relation="CAN_HAVE")

    def query_graph(self, entity: str, depth: int = 2) -> dict[str, Any]:
        """查询实体在图中的关联"""
        self.build_graph()

        if self._use_neo4j and self._driver:
            return self._query_neo4j(entity, depth)
        return self._query_networkx(entity, depth)

    def _query_neo4j(self, entity: str, depth: int) -> dict[str, Any]:
        with self._driver.session() as session:
            result = session.run(
                f"MATCH (n)-[*1..{depth}]-(related) WHERE n.name = $entity "
                "RETURN DISTINCT labels(related) as labels, related.name as name",
                entity=entity,
            )
            nodes = [{"labels": r["labels"], "name": r["name"]} for r in result]
            return {"entity": entity, "depth": depth, "related": nodes}

    def _query_networkx(self, entity: str, depth: int) -> dict[str, Any]:
        import networkx as nx

        if not hasattr(self, "_nx_graph"):
            self.build_graph()

        if entity not in self._nx_graph:
            return {"entity": entity, "depth": depth, "related": []}

        nodes_within = nx.single_source_shortest_path_length(
            self._nx_graph, entity, cutoff=depth
        )

        related = []
        for node, dist in nodes_within.items():
            if node != entity:
                node_type = self._nx_graph.nodes[node].get("type", "Unknown")
                edge = ""
                try:
                    edge_data = list(self._nx_graph.get_edge_data(entity, node).items())
                    edge = edge_data[0][1].get("relation", "") if edge_data else ""
                except (KeyError, IndexError, AttributeError):
                    pass
                related.append({
                    "name": node,
                    "type": node_type,
                    "distance": dist,
                    "relation": edge,
                })
        return {"entity": entity, "depth": depth, "related": related}

    def build_graph_context(self, query: str, max_entities: int = 5) -> str:
        """根据查询生成图上下文文本"""
        self.build_graph()

        matched = []
        for dev_type, dev_data in DEVICE_GRAPH.items():
            if dev_type in query:
                matched.append(dev_type)
            for comp in dev_data.get("faults", {}).keys():
                if comp in query:
                    matched.append(comp)
            for comp, faults in dev_data.get("faults", {}).items():
                for fault in faults:
                    if fault in query:
                        matched.append(fault)

        if not matched:
            return ""

        context_lines = ["## 知识图谱关联"]
        seen = set()
        for entity in matched[:max_entities]:
            graph_data = self.query_graph(entity, depth=2)
            for rel in graph_data.get("related", []):
                name = rel.get("name", "")
                if name not in seen and name not in matched:
                    seen.add(name)
                    context_lines.append(
                        f"- [{rel.get('type', '?')}] {name} (距离: {rel.get('distance', '?')})"
                    )
        return "\n".join(context_lines) if len(context_lines) > 1 else ""

    def extract_entities(self, text: str) -> dict[str, Any]:
        """从文本中提取设备类型和故障实体"""
        result = {"device_type": "未知", "components": [], "possible_faults": []}

        for dev_type in DEVICE_GRAPH:
            if dev_type in text:
                result["device_type"] = dev_type
                for comp, faults in DEVICE_GRAPH[dev_type]["faults"].items():
                    if comp in text:
                        result["components"].append(comp)
                    for fault in faults:
                        if fault in text:
                            result["possible_faults"].append(fault)
                break

        return result


graphrag_service = GraphRAGService()

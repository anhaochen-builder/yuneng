"""混合检索引擎 — 三重检索 + RRF 融合 + BGE Reranker 精排

管道:
  向量检索(BGE-Large-ZH, ChromaDB HNSW) ┐
  BM25 关键词检索 (电力领域词典)       ├→ RRF 融合(Top-20) → BGE Reranker → Top-5
  知识图谱上下文扩展                    ┘

RRF 算法: score(d) = Σ weight_s / (k + rank_s(d)), k=60
权重: 向量=1.0, BM25=1.0, 图谱=0.8
"""

import json
import logging
import math
from collections import defaultdict
from pathlib import Path
from typing import Any

from app.config import settings

logger = logging.getLogger(__name__)

KNOWLEDGE_FILE = Path(settings.vector_db_path) / "knowledge.json"

POWER_KEYWORDS = [
    "电压", "电流", "功率", "频率", "温度", "振动", "故障", "告警",
    "逆变器", "风机", "变压器", "断路器", "保护", "接地", "短路", "过载",
    "通讯中断", "绝缘", "IGBT", "PLC", "SCADA", "齿轮箱", "叶片", "偏航",
    "变桨", "直流侧", "交流侧", "并网", "脱网", "低电压穿越", "高电压穿越",
    "AGC", "AVC", "无功补偿", "有功功率", "箱变", "集电线路", "SVG",
    "油温", "过温", "过热", "散热", "轴承", "发电机", "差动", "瓦斯",
    "IGBT模块", "IGBT过热", "IGBT过温", "直流母线", "交流输出",
    "安全规程", "安规", "操作票", "工作票", "验电", "接地线",
    "套管", "DGA", "绝缘电阻", "绝缘阻抗", "绕组", "铁芯",
    "组串", "光伏组件", "PID衰减", "MPPT", "汇流箱",
]

# RRF 参数
RRF_K: int = 60               # 平滑常数
RRF_VECTOR_WEIGHT: float = 1.0
RRF_BM25_WEIGHT: float = 1.0
RRF_KG_WEIGHT: float = 0.8
RRF_TOP_K: int = 20           # RRF 融合后保留候选数

DEFAULT_KNOWLEDGE = [
    "逆变器IGBT模块过热常见原因：1.散热风扇故障或停转 2.散热器积尘堵塞 3.导热硅脂老化干涸 4.IGBT模块老化导通电阻增大 5.环境温度过高。标准处置：立即降负载至70%，检查散热风扇，清洁散热器，检测IGBT结温(>125°C报警)。更换前必须断电验电。",
    "逆变器通讯中断排查步骤：1.检查485/CAN通讯线缆是否松动断线 2.检查通讯模块电源指示灯 3.重启通讯模块看是否恢复 4.测量通讯线路终端电阻(485应120Ω) 5.检查通讯参数配置 6.更换通讯板卡。",
    "逆变器直流侧过压保护动作：可能原因1.光伏组串开路电压过高 2.MPPT跟踪异常 3.直流母线电容老化 4.雷击浪涌。应检查组串开路电压是否在设计范围内，检查避雷器是否动作。",
    "逆变器交流侧过流故障：1.电网电压骤降致输出电流突增 2.输出滤波器电容击穿 3.负载侧短路 4.逆变器内部IGBT击穿。优先检查电网电压波形和输出侧绝缘电阻。",
    "逆变器绝缘阻抗低告警：1.直流侧电缆绝缘老化破损 2.光伏组件接线盒进水 3.逆变器内部受潮 4.接地不良。正负极对地绝缘电阻应大于1MΩ。雨天特别注意。",
    "逆变器效率下降需排查：效率低于额定5%以上1.IGBT模块老化开关损耗增大 2.直流母线电容ESR增大 3.散热不良导致降功率运行 4.MPPT算法偏差。记录输入输出功率对比。",
    "风电机组齿轮箱常见故障模式：1.齿轮断齿或磨损(啮合频率附近出现边频带) 2.轴承磨损(高频振动加冲击脉冲) 3.油温过高(散热器堵塞或冷却风扇故障) 4.润滑油劣化(铁磁性颗粒超标) 5.齿轮箱异响(啮合不良或轴承损坏)。振动频谱分析是关键诊断手段。",
    "风机齿轮箱油温过高处置方案：原因包括1.冷却系统风扇故障停机 2.散热器片积尘堵塞 3.润滑油量不足或润滑油变质 4.齿轮箱内部磨损加剧发热 5.环境温度过高。处置措施：检查油位和油质，清洁散热器表面，强制风冷散热，必要时停机检修。油温超过80°C应降功率运行。",
    "风机振动超标诊断分析：可能原因1.叶片质量不平衡导致1P频率振动 2.齿轮箱齿轮啮合问题导致啮合频率振动 3.发电机轴承故障导致高频振动 4.塔筒共振在某些风速下发生 5.地脚螺栓松动或基础松动。应进行振动频谱分析确定故障频率，结合风速数据和运行工况综合分析。",
    "风机偏航系统故障：1.偏航电机过载或烧毁 2.偏航制动器磨损失效 3.偏航轴承润滑不足导致卡涩 4.偏航编码器信号丢失 5.偏航控制逻辑错误。风速突变时常发生偏航故障，应检查偏航电机电流和偏航计数器。",
    "风机变桨系统故障处理：1.变桨电机编码器故障 2.变桨电池超级电容老化容量不足 3.变桨控制器通讯中断 4.变桨轴承卡涩 5.桨叶角度传感器漂移。紧急停机时变桨系统必须能可靠顺桨，务必定期测试备用电源容量和响应时间。",
    "风机叶片故障识别：1.叶片裂纹(外观检查加敲击声音异常) 2.叶片覆冰(功率曲线异常下降，振动增大) 3.雷击损伤(叶片表面烧灼痕迹) 4.叶片质量不平衡(1P频率振动超标)。可用无人机或高倍望远镜进行外观巡检，结合振动数据分析。",
    "风机发电机故障诊断：1.发电机轴承磨损(高频振动加温度持续升高) 2.发电机绝缘老化(绝缘电阻逐步下降至临界值) 3.发电机过热(冷却风道堵塞或风扇故障) 4.发电机转子不平衡 5.集电环或碳刷磨损(双馈机型)。应定期测量定子转子绝缘电阻和轴承振动值。",
    "变压器油温异常升高原因分析：1.过负荷运行超过额定容量 2.冷却系统故障(风扇或油泵停运) 3.内部绕组匝间短路导致局部过热 4.铁芯多点接地产生环流 5.环境温度过高加散热不良。油温超过85°C应发报警信号，超过95°C应减负荷或停机检修。",
    "变压器DGA分析导则(油中溶解气体)：氢气H2大于150ppm指示局部放电，乙炔C2H2大于5ppm指示电弧放电，乙烯C2H4大于100ppm指示过热超过700°C，乙烷C2H6大于150ppm指示热故障低于700°C，甲烷CO加CO2指示固体绝缘过热。使用三比值法综合判断故障类型和严重程度。",
    "变压器差动保护动作后分析：1.变压器内部相间短路 2.绕组匝间短路 3.变压器励磁涌流导致误动(二次谐波制动失效) 4.CT饱和或极性接反。动作后必须全面检查绕组直流电阻和绝缘电阻，测量变比和直流电阻，严禁未查清原因强行送电。",
    "变压器瓦斯保护动作含义：轻瓦斯(发信号)表示内部轻微故障或油位过低需检查，重瓦斯(跳闸)表示内部严重短路故障必须立即停机。瓦斯继电器内有气体时应收集气体进行点燃试验和色谱分析，判断故障性质和严重程度。重瓦斯动作后绝对禁止送电操作。",
    "变压器套管故障排查：1.套管表面闪络(污秽加潮湿天气下发生) 2.套管瓷套破裂(外力撞击或老化) 3.套管介损增大(内部受潮或绝缘老化) 4.套管连接处发热(内部导电连接不良)。应定期红外测温检测套管温度分布，雨雾天气加强巡视。",
    "光伏组串电流异常偏低排查：1.组串内部分组件遮挡(灰尘堆积鸟粪阴影等) 2.组件旁路二极管击穿导致热斑 3.连接器接触不良氧化 4.组件PID衰减(电位诱导衰减) 5.线路接头氧化或松动。使用I-V曲线测试仪逐串检测定位问题组件。",
    "光伏直流侧绝缘阻抗低排查方法：1.组件接线盒受潮进水 2.直流电缆绝缘破损或老化 3.连接器密封不良进水 4.支架接地不良。雨天绝缘阻抗低于500kΩ为严重告警，需逐串断开排查定位。夜间测量绝缘电阻更准确有效。",
    "电力安全工作规程高压设备检修安全措施：1.停电将所有可能来电的电源全部断开 2.验电使用合格验电器逐相验电 3.装设接地线先接接地端后接导体端 4.悬挂标示牌和装设遮栏 5.办理工作票和操作票。严禁约时停送电。",
    "新能源场站倒闸操作安全规定：1.操作前核对设备双重编号(设备名称加编号) 2.在模拟图上进行预演 3.一人操作一人监护 4.停电顺序为先低压后高压先负荷侧后电源侧 5.送电顺序与停电相反。雷雨天气禁止进行户外倒闸操作。",
    "风机齿轮箱油温告警真实案例：风机WIND081齿轮箱油温从正常55°C在30分钟内急剧升至82°C，超过一级告警阈值75°C。当时环境温度25°C风速12m/s有功功率1.5MW。检查发现齿轮箱散热风扇转速降低约30%散热效率下降，清洁散热器翅片后油温逐步恢复正常。",
    "风机振动告警真实案例：风机WIND082发电机驱动端轴承振动加速度从正常2.5mm/s²急剧升至8.7mm/s²，超过振动告警阈值7.0mm/s²。频谱分析显示轴承外圈故障特征频率78Hz处幅值异常增大。更换发电机驱动端轴承后振动值恢复正常水平。",
    "逆变器过热告警真实案例：逆变器INV005 IGBT模块NTC温度传感器读数从62°C在20分钟内快速升至98°C，超过IGBT保护阈值95°C，逆变器自动降功率至额定功率50%进行自我保护。检查发现散热风道被春季柳絮堵塞面积约60%，彻底清理后温度恢复正常。",
]


# ================================================================
# BM25 关键词检索引擎
# ================================================================

class KeywordIndex:
    def __init__(self):
        self._docs: list[str] = []
        self._doc_freq: dict[str, int] = defaultdict(int)
        self._built = False

    def build(self, documents: list[str]):
        self._docs = documents
        self._doc_freq.clear()
        for doc in documents:
            seen = set()
            for kw in POWER_KEYWORDS:
                if kw in doc:
                    seen.add(kw)
            for ch in doc:
                if '\u4e00' <= ch <= '\u9fff':
                    seen.add(ch)
            for term in seen:
                self._doc_freq[term] += 1
        self._built = True
        logger.info(f"BM25 索引已构建: {len(documents)} 篇, {len(self._doc_freq)} 关键词")

    def search(self, query: str, top_k: int = 10) -> list[dict]:
        if not self._built:
            return []

        query_terms = []
        for kw in POWER_KEYWORDS:
            if kw in query:
                query_terms.append(kw)
        for ch in query:
            if '\u4e00' <= ch <= '\u9fff':
                query_terms.append(ch)

        if not query_terms:
            return self._all_docs()[:top_k]

        n = len(self._docs)
        scores = []
        for idx, doc in enumerate(self._docs):
            score = 0.0
            for term in query_terms:
                tf = doc.count(term)
                df = self._doc_freq.get(term, 0)
                if df > 0 and tf > 0:
                    idf = math.log((n - df + 0.5) / (df + 0.5) + 1)
                    score += tf * idf
            if score > 0:
                scores.append((idx, score))

        scores.sort(key=lambda x: x[1], reverse=True)
        return [
            {"id": f"kw_{idx}", "text": self._docs[idx][:2000],
             "metadata": {"source": "bm25"}, "score": round(score, 4)}
            for idx, score in scores[:top_k]
        ]

    def _all_docs(self) -> list[dict]:
        return [
            {"id": f"kw_{i}", "text": doc[:2000],
             "metadata": {"source": "bm25"}, "score": 0.5}
            for i, doc in enumerate(self._docs)
        ]


class FastKnowledgeStore:
    def __init__(self):
        self._index = KeywordIndex()
        self._load()

    def _load(self):
        docs = DEFAULT_KNOWLEDGE
        if KNOWLEDGE_FILE.exists():
            try:
                stored = json.loads(KNOWLEDGE_FILE.read_text(encoding="utf-8"))
                if isinstance(stored, list) and len(stored) > len(DEFAULT_KNOWLEDGE):
                    docs = stored
            except (json.JSONDecodeError, OSError, UnicodeDecodeError) as e:
                logger.warning(f"知识库文件读取失败，使用默认数据: {e}")

        KNOWLEDGE_FILE.parent.mkdir(parents=True, exist_ok=True)
        KNOWLEDGE_FILE.write_text(json.dumps(docs, ensure_ascii=False, indent=2), encoding="utf-8")
        self._index.build(docs)
        logger.info(f"知识库已加载: {len(docs)} 条")

    def search(self, query: str, top_k: int = 10) -> list[dict]:
        return self._index.search(query, top_k)

    def add(self, texts: list[str]) -> int:
        try:
            existing = json.loads(KNOWLEDGE_FILE.read_text(encoding="utf-8")) if KNOWLEDGE_FILE.exists() else []
        except (json.JSONDecodeError, OSError, UnicodeDecodeError) as e:
            logger.warning(f"知识库文件读取失败: {e}")
            existing = []
        existing.extend(texts)
        KNOWLEDGE_FILE.write_text(json.dumps(existing, ensure_ascii=False, indent=2), encoding="utf-8")
        self._index.build(existing)
        return len(texts)

    @property
    def doc_count(self) -> int:
        return len(self._index._docs)


_knowledge_store = None


def get_knowledge_store() -> FastKnowledgeStore:
    global _knowledge_store
    if _knowledge_store is None:
        _knowledge_store = FastKnowledgeStore()
    return _knowledge_store


# ================================================================
# RRF 融合算法
# ================================================================

def rrf_fusion(
    vector_results: list[dict],
    bm25_results: list[dict],
    kg_results: list[dict] = None,
    top_k: int = RRF_TOP_K,
) -> list[dict]:
    """Reciprocal Rank Fusion — 多路检索结果融合

    RRF(d) = Σ weight_s / (k + rank_s(d))
    k=60 防止除零, 权重: 向量=1.0 BM25=1.0 图谱=0.8
    """
    doc_map: dict[str, dict] = {}
    doc_scores: dict[str, float] = defaultdict(float)

    # 向量检索结果
    for rank, doc in enumerate(vector_results, start=1):
        doc_id = doc.get("id", str(hash(doc.get("text", ""))))
        rrf_score = RRF_VECTOR_WEIGHT / (RRF_K + rank)
        doc_scores[doc_id] += rrf_score
        if doc_id not in doc_map:
            doc_map[doc_id] = dict(doc)

    # BM25 检索结果
    for rank, doc in enumerate(bm25_results, start=1):
        doc_id = doc.get("id", str(hash(doc.get("text", ""))))
        rrf_score = RRF_BM25_WEIGHT / (RRF_K + rank)
        doc_scores[doc_id] += rrf_score
        if doc_id not in doc_map:
            doc_map[doc_id] = dict(doc)

    # 知识图谱结果 (rank 从 100 起算，给较低权重)
    if kg_results:
        for rank, doc in enumerate(kg_results, start=100):
            doc_id = doc.get("id", str(hash(doc.get("text", ""))))
            rrf_score = RRF_KG_WEIGHT / (RRF_K + rank)
            doc_scores[doc_id] += rrf_score
            if doc_id not in doc_map:
                doc_map[doc_id] = dict(doc)

    # 按 RRF 分数排序
    sorted_items = sorted(doc_scores.items(), key=lambda x: x[1], reverse=True)
    fused = []
    for doc_id, rrf_score in sorted_items[:top_k]:
        doc = doc_map[doc_id]
        doc["rrf_score"] = round(rrf_score, 6)
        fused.append(doc)

    return fused


# ================================================================
# 混合检索服务 — 完整管道
# ================================================================

class HybridSearchService:
    """三重检索 + RRF 融合 + BGE Reranker 精排

    用法:
        svc = HybridSearchService()
        results = svc.search("逆变器IGBT过热", top_k=5)
    """

    def __init__(self):
        self._store = get_knowledge_store()

    def search(self, query: str, top_k: int = 10, use_rerank: bool = True) -> list[dict]:
        """执行完整混合检索管道"""
        if not query:
            return []

        # 第1重: 向量检索 (BGE-Large-ZH + ChromaDB HNSW)
        vector_results = self._vector_search(query)

        # 第2重: BM25 关键词检索
        bm25_results = self._store.search(query, top_k=20)

        # 第3重: 知识图谱上下文
        kg_results = self._kg_search(query)

        # RRF 融合
        fused = rrf_fusion(vector_results, bm25_results, kg_results)

        if not fused:
            # 降级: 任何一路有结果就返回
            fused = vector_results or bm25_results or []

        # BGE Reranker 精排
        if use_rerank and len(fused) > top_k:
            from app.rag.rerank import BGECrossEncoderReranker
            reranker = BGECrossEncoderReranker()
            fused = reranker.rerank(query, fused, top_k=top_k)

        return fused[:top_k]

    def _vector_search(self, query: str) -> list[dict]:
        try:
            from app.rag.vector_store import search_vector as chroma_search
            return chroma_search(query, top_k=20)
        except Exception as e:
            logger.debug(f"向量检索未启用: {e}")
            return []

    def _kg_search(self, query: str) -> list[dict]:
        try:
            from app.rag.knowledge_graph import KnowledgeGraphService
            kg = KnowledgeGraphService()
            ctx = kg.build_graph_context(query)
            if ctx:
                return [{"id": "kg_ctx", "text": ctx, "metadata": {"source": "knowledge_graph"}, "score": 0.6}]
        except (ImportError, RuntimeError) as e:
            logger.debug(f"知识图谱不可用: {e}")
        try:
            from app.rag.graphrag import graphrag_service
            ctx = graphrag_service.build_graph_context(query)
            if ctx:
                return [{"id": "graphrag_ctx", "text": ctx, "metadata": {"source": "graphrag"}, "score": 0.6}]
        except (ImportError, RuntimeError) as e:
            logger.debug(f"GraphRAG不可用: {e}")
        return []

    def index_keywords(self, documents: list[str]):
        self._store.add(documents)


# ================================================================
# 向后兼容接口
# ================================================================

def search_vector(query: str, collection_name: str = "", top_k: int = 10) -> list[dict]:
    return get_knowledge_store().search(query, top_k)


def add_documents(texts: list[str], metadatas: list[dict] = None, ids: list[str] = None,
                  collection_name: str = "") -> int:
    return get_knowledge_store().add(texts)

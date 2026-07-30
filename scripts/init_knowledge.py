#!/usr/bin/env python3
"""知识库初始化工具

扫描 data/raw/ 目录，解析文档(PDF/DOCX/XLSX/TXT/MD)，
分块向量化后存入 ChromaDB，并重建 BM25 索引。
"""

import json
import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.rag.document_parser import DocumentParser
from app.rag.vector_store import add_documents, is_embedding_available
from app.rag.hybrid_search import HybridSearchService

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

DATA_DIR = Path(__file__).parent.parent / "data" / "raw"

SUPPORTED_EXTENSIONS = {".pdf", ".docx", ".xlsx", ".xls", ".txt", ".md"}


def init_knowledge_base(data_dir: str = None):
    """扫描目录，解析全部文档，向量化入库"""
    scan_dir = Path(data_dir) if data_dir else DATA_DIR
    if not scan_dir.exists():
        logger.warning(f"数据目录不存在: {scan_dir}")
        return 0

    files = [f for f in scan_dir.rglob("*") if f.suffix.lower() in SUPPORTED_EXTENSIONS]
    logger.info(f"发现 {len(files)} 个文档待处理")

    all_texts = []
    all_metadatas = []
    total_chunks = 0

    for filepath in files:
        try:
            logger.info(f"解析: {filepath.name}")
            chunks = DocumentParser.parse(str(filepath))
            if not chunks:
                logger.warning(f"  跳过(空): {filepath.name}")
                continue

            for chunk in chunks:
                all_texts.append(chunk["text"])
                all_metadatas.append({
                    "source": str(filepath.relative_to(scan_dir)),
                    "type": chunk.get("type", filepath.suffix),
                    "page": chunk.get("page", 0),
                    "heading_level": chunk.get("heading_level", 0),
                })

            logger.info(f"  → {len(chunks)} chunks")
            total_chunks += len(chunks)

        except Exception as e:
            logger.error(f"解析失败 {filepath.name}: {e}")

    if not all_texts:
        logger.warning("无有效文档内容")
        return 0

    if is_embedding_available():
        count = add_documents(
            texts=all_texts,
            metadatas=all_metadatas,
            collection_name="power_knowledge",
        )
        logger.info(f"向量化入库: {count}/{len(all_texts)} chunks")
    else:
        logger.warning("嵌入模型不可用，跳过向量化")

    searcher = HybridSearchService()
    searcher.index_keywords(all_texts)
    logger.info(f"BM25 索引已重建: {len(all_texts)} 文档")

    logger.info(f"知识库初始化完成: {len(files)} 文件, {total_chunks} chunks")
    return total_chunks


def generate_seed_data():
    """生成种子知识数据（冷启动用）"""
    seeds = [
        {"text": "逆变器通讯中断故障：通讯模块故障(PLC/RS485/光纤)、散热风道堵塞、电网电压波动、组件绝缘降低是常见原因。排查步骤：检查通讯线路、清理散热风道、测量电网电压、绝缘电阻测试。", "type": "seed"},
        {"text": "风机振动超标停机：齿轮箱润滑油不足或劣化、轴承磨损或点蚀、偏航电机故障、叶片结冰或不平衡是主要原因。排查：振动频谱分析、内窥镜检查齿轮、检查偏航制动器、外观检查叶片。", "type": "seed"},
        {"text": "主变压器油温高告警：长期过载运行导致绝缘加速老化、冷却系统风扇或油泵故障、内部短路是最常见原因。处理：检查油温表油位计、取油样化验色谱分析、红外热像扫描、铁芯接地电流测试。", "type": "seed"},
        {"text": "储能电池舱电芯温度过高(>45°C)：热管理系统空调或液冷故障、BMS采集模块故障、电芯容量衰减不一致。排查：电芯单体电压和温度巡检、绝缘电阻测试、冷却系统检查、消防系统检查。", "type": "seed"},
        {"text": "断路器拒动/误动故障：操作机构机械故障卡涩或变形、SF6泄漏、控制回路断线、主触头烧蚀或接触不良。排查：分合闸时间速度测试、回路电阻测试、SF6检漏、操作机构润滑检查。", "type": "seed"},
    ]

    metadatas = [{"source": "seed_data", "type": s["type"]} for s in seeds]
    texts = [s["text"] for s in seeds]

    if is_embedding_available():
        count = add_documents(texts=texts, metadatas=metadatas, collection_name="power_knowledge")
        logger.info(f"种子数据入库: {count} 条")
    else:
        logger.warning("嵌入模型不可用，种子数据未向量化")

    return len(seeds)


if __name__ == "__main__":
    logger.info("=== 知识库初始化 ===")
    n = generate_seed_data()
    logger.info(f"种子数据: {n} 条")
    n2 = init_knowledge_base()
    logger.info(f"文档数据: {n2} chunks")
    logger.info("=== 初始化完成 ===")

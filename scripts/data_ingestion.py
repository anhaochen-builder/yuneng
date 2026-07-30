#!/usr/bin/env python3
"""
驭能 - 数据采集与数据集管理模块
支持从 Zenodo、本地文件等多种来源导入电力故障数据集
"""

import os
import json
import logging
from pathlib import Path
from typing import Optional

import pandas as pd
import numpy as np
import requests

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class PowerDataIngestor:
    """电力数据集导入器"""

    def __init__(self, data_dir: str = "./data"):
        self.data_dir = Path(data_dir)
        self.raw_dir = self.data_dir / "raw"
        self.processed_dir = self.data_dir / "processed"
        self.raw_dir.mkdir(parents=True, exist_ok=True)
        self.processed_dir.mkdir(parents=True, exist_ok=True)

    def download_zenodo_dataset(self, record_id: str) -> str:
        url = f"https://zenodo.org/api/records/{record_id}"
        logger.info(f"从 Zenodo 下载数据集: {record_id}")
        response = requests.get(url, timeout=30)
        if response.status_code != 200:
            raise RuntimeError(f"获取记录失败: {response.status_code}")
        data = response.json()
        files = data.get("files", [])
        for file_info in files:
            file_url = file_info.get("links", {}).get("download")
            if file_url:
                filename = file_info.get("key", f"download_{hash(file_url)}")
                output_path = self.raw_dir / filename
                logger.info(f"下载中: {filename}")
                r = requests.get(file_url, stream=True, timeout=300)
                with open(output_path, "wb") as f:
                    for chunk in r.iter_content(chunk_size=8192):
                        f.write(chunk)
                logger.info(f"已保存: {output_path}")
        return str(self.raw_dir)

    def load_scada_csv(self, filepath: str) -> pd.DataFrame:
        df = pd.read_csv(filepath)
        standard_columns = {
            "wind_speed": "wind_speed_ms",
            "power": "power_kw",
            "rpm": "rotor_rpm",
            "temp": "temperature_c",
            "status": "turbine_status",
        }
        df.rename(columns=standard_columns, inplace=True, errors="ignore")
        if "timestamp" in df.columns:
            df["timestamp"] = pd.to_datetime(df["timestamp"], errors="coerce")
        elif "date" in df.columns:
            df["timestamp"] = pd.to_datetime(df["date"], errors="coerce")
        if "fault" in df.columns:
            df["is_fault"] = df["fault"].apply(lambda x: 1 if x != 0 else 0)
        return df

    def create_fault_sample(self, df: pd.DataFrame, fault_column: str = "is_fault") -> dict:
        fault_samples = df[df[fault_column] == 1]
        normal_samples = df[df[fault_column] == 0]
        return {
            "total_samples": len(df),
            "fault_samples": len(fault_samples),
            "normal_samples": len(normal_samples),
            "fault_ratio": round(len(fault_samples) / len(df), 4) if len(df) > 0 else 0,
            "columns": list(df.columns),
            "sample_data": df.head(5).to_dict("records"),
        }

    def save_processed_data(self, df: pd.DataFrame, name: str) -> str:
        output_path = self.processed_dir / f"{name}.parquet"
        df.to_parquet(output_path, index=False)
        logger.info(f"已保存处理后数据: {output_path}")
        return str(output_path)

    def list_datasets(self) -> list[dict]:
        datasets = []
        for f in self.raw_dir.iterdir():
            datasets.append({"filename": f.name, "size_mb": round(f.stat().st_size / (1024 * 1024), 2)})
        for f in self.processed_dir.iterdir():
            datasets.append({"filename": f.name, "size_mb": round(f.stat().st_size / (1024 * 1024), 2), "processed": True})
        return datasets


DATASET_CONFIG = {
    "wind_turbine_scada": {
        "zenodo_id": "15071504",
        "description": "95 datasets, 89 years of SCADA time series, 36 turbines",
    },
    "dga_transformer": {
        "source": "IEEE Dataport",
        "description": "DGA 变压器故障数据集, 584条训练+70条测试",
    },
}


if __name__ == "__main__":
    ingestor = PowerDataIngestor(data_dir="./data")
    logger.info(f"数据目录: {ingestor.data_dir}")
    datasets = ingestor.list_datasets()
    logger.info(f"现有数据集: {len(datasets)} 个")
    for ds in datasets:
        logger.info(f"  - {ds['filename']} ({ds['size_mb']}MB)")

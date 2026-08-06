"""SCADA 设备自动发现服务"""
import asyncio
import logging
from typing import Any

logger = logging.getLogger(__name__)

DISCOVERY_PRESETS = [
    {"name": "Modbus 默认网段", "protocol": "modbus", "host": "192.168.1.0/24", "port_range": (502, 502), "device_type": "inverter"},
    {"name": "Modbus 工控网段", "protocol": "modbus", "host": "10.0.0.0/24", "port_range": (502, 502), "device_type": "inverter"},
    {"name": "OPC UA 服务器", "protocol": "opcua", "host": "localhost", "port_range": (4840, 4840), "device_type": "scada_host"},
    {"name": "IEC 61850 保护装置", "protocol": "iec61850", "host": "192.168.100.0/24", "port_range": (102, 102), "device_type": "ied"},
]


async def discover_modbus_devices(network: str, port: int = 502, timeout: float = 2.0) -> list[dict]:
    discovered = []
    try:
        import socket
        base_ip = network.rsplit(".", 1)[0]
        for last_octet in range(1, 255):
            ip = f"{base_ip}.{last_octet}"
            try:
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(timeout)
                result = sock.connect_ex((ip, port))
                sock.close()
                if result == 0:
                    device_id = f"MODBUS-{last_octet:03d}"
                    discovered.append({
                        "device_id": device_id, "host": ip, "port": port,
                        "protocol": "modbus", "status": "reachable",
                        "device_type": "inverter", "discovery_method": "tcp_scan",
                    })
                    logger.info(f"发现 Modbus 设备: {ip}:{port}")
            except OSError:
                pass
    except Exception as e:
        logger.warning(f"Modbus 设备发现异常: {e}")
    return discovered


async def discover_local_devices() -> list[dict]:
    discovered = []
    try:
        import psutil
        for conn in psutil.net_connections(kind="tcp"):
            if conn.status == "LISTEN" and conn.laddr:
                port = conn.laddr.port
                if port == 502:
                    discovered.append({
                        "device_id": f"MODBUS-LOCAL-{port}", "host": "127.0.0.1",
                        "port": 502, "protocol": "modbus", "status": "local",
                        "device_type": "inverter", "discovery_method": "local_port",
                    })
                elif port == 4840:
                    discovered.append({
                        "device_id": f"OPCUA-LOCAL-{port}", "host": "127.0.0.1",
                        "port": 4840, "protocol": "opcua", "status": "local",
                        "device_type": "scada_host", "discovery_method": "local_port",
                    })
                elif port == 102:
                    discovered.append({
                        "device_id": f"IEC61850-LOCAL-{port}", "host": "127.0.0.1",
                        "port": 102, "protocol": "iec61850", "status": "local",
                        "device_type": "ied", "discovery_method": "local_port",
                    })
    except (ImportError, Exception) as e:
        logger.debug(f"本地端口扫描不可用: {e}")
    return discovered


async def run_discovery(scan_network: bool = False) -> dict[str, Any]:
    results = {
        "local": [],
        "network": [],
        "total": 0,
        "timestamp": "",
    }

    local = await discover_local_devices()
    results["local"] = local
    results["total"] += len(local)

    if scan_network:
        network_devices = await discover_modbus_devices("192.168.1.0/24")
        results["network"] = network_devices
        results["total"] += len(network_devices)

    from datetime import datetime
    results["timestamp"] = datetime.now().isoformat()

    if results["total"] == 0:
        results["note"] = "未发现自动可探测设备，请手动在 SCADA 看板中添加"
    else:
        results["note"] = f"共发现 {results['total']} 个设备"

    return results

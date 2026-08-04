"""SCADA 层专项测试 — 环形缓冲 / 窗口提取 / 数据归一化 / 协议工厂"""
import threading
import pytest


class TestRingBuffer:
    def test_create_buffer(self):
        from app.scada.ring_buffer import RingBuffer
        buf = RingBuffer(capacity=100)
        assert buf._capacity == 100
        assert buf._total_written == 0

    def test_push_single_point(self):
        from app.scada.ring_buffer import RingBuffer
        from app.scada.base import ScadaDataPoint
        buf = RingBuffer(capacity=100)
        dp = ScadaDataPoint(
            timestamp="2026-08-04T10:00:00",
            device_id="INV001",
            point_name="温度",
            value=85.0,
            unit="°C",
        )
        buf.push(dp)
        assert buf._total_written == 1

    def test_push_batch(self):
        from app.scada.ring_buffer import RingBuffer
        from app.scada.base import ScadaDataPoint
        buf = RingBuffer(capacity=100)
        points = [
            ScadaDataPoint(
                timestamp=f"2026-08-04T10:{i:02d}:00",
                device_id="INV001",
                point_name="温度",
                value=float(80 + i),
                unit="°C",
            )
            for i in range(10)
        ]
        buf.push_batch(points)
        assert buf._total_written == 10

    def test_capacity_overflow(self):
        from app.scada.ring_buffer import RingBuffer
        from app.scada.base import ScadaDataPoint
        buf = RingBuffer(capacity=5)
        for i in range(10):
            dp = ScadaDataPoint(
                timestamp=f"2026-08-04T10:{i:02d}:00",
                device_id="TEST",
                point_name="p",
                value=float(i),
                unit="",
            )
            buf.push(dp)
        assert len(buf._buffer) == 5
        assert buf._total_written == 10

    def test_concurrent_push(self):
        from app.scada.ring_buffer import RingBuffer
        from app.scada.base import ScadaDataPoint
        buf = RingBuffer(capacity=10000)
        errors = []

        def push_worker(device_id, start):
            try:
                for i in range(100):
                    dp = ScadaDataPoint(
                        timestamp=f"2026-08-04T10:{start:02d}:{i:02d}",
                        device_id=device_id,
                        point_name="p",
                        value=float(i),
                        unit="",
                    )
                    buf.push(dp)
            except Exception as e:
                errors.append(str(e))

        threads = [threading.Thread(target=push_worker, args=(f"DEV{i}", i)) for i in range(5)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        assert len(errors) == 0
        assert buf._total_written == 500


class TestWindowExtractor:
    def test_import(self):
        from app.scada.window_extractor import FaultWindowExtractor
        assert FaultWindowExtractor is not None

    def test_extract_empty_buffer(self):
        from app.scada.ring_buffer import RingBuffer
        from app.scada.window_extractor import FaultWindowExtractor
        buf = RingBuffer(capacity=100)
        extractor = FaultWindowExtractor(buffer=buf)
        result = extractor.extract("INV001", "2026-08-04T10:00:00")
        assert isinstance(result, dict)

    def test_extract_with_data(self):
        from app.scada.ring_buffer import RingBuffer
        from app.scada.window_extractor import FaultWindowExtractor
        from app.scada.base import ScadaDataPoint
        buf = RingBuffer(capacity=500)
        for i in range(60):
            dp = ScadaDataPoint(
                timestamp=f"2026-08-04T10:{i//6:02d}:{i%6*10:02d}",
                device_id="INV001",
                point_name="温度",
                value=float(80 + max(0, i - 30)),
                unit="°C",
            )
            buf.push(dp)
        extractor = FaultWindowExtractor(buffer=buf)
        result = extractor.extract("INV001", "2026-08-04T10:05:00")
        assert isinstance(result, dict)


class TestDataNormalizer:
    def test_normalize_result(self):
        from app.scada.data_normalizer import DataNormalizer
        from app.scada.base import ScadaDataPoint, ScadaReadResult
        points = [
            ScadaDataPoint(timestamp="2026-08-04T10:00:00", device_id="INV001",
                           point_name="电压", value=380.0, unit="V"),
            ScadaDataPoint(timestamp="2026-08-04T10:00:01", device_id="INV001",
                           point_name="电流", value=12.5, unit="A"),
        ]
        result = ScadaReadResult(device_id="INV001", success=True, data_points=points)
        records = DataNormalizer.normalize(result)
        assert len(records) == 2
        assert records[0]["point_name"] == "电压"

    def test_normalize_empty(self):
        from app.scada.data_normalizer import DataNormalizer
        from app.scada.base import ScadaReadResult
        result = ScadaReadResult(device_id="EMPTY", success=True, data_points=[])
        records = DataNormalizer.normalize(result)
        assert len(records) == 0

    def test_to_statistics(self):
        from app.scada.data_normalizer import DataNormalizer
        from app.scada.base import ScadaDataPoint
        points = [
            ScadaDataPoint(timestamp=f"2026-08-04T10:{i:02d}:00", device_id="INV001",
                           point_name="温度", value=float(80 + i), unit="°C")
            for i in range(10)
        ]
        stats = DataNormalizer.to_statistics(points)
        assert isinstance(stats, dict)
        assert stats["count"] == 10


class TestProtocolFactory:
    def test_resolve_known_devices(self):
        from app.scada.protocol_factory import ProtocolFactory
        assert ProtocolFactory.resolve_protocol("inverter") == "modbus"
        assert ProtocolFactory.resolve_protocol("ied") == "iec61850"
        assert ProtocolFactory.resolve_protocol("scada_host") == "opcua"

    def test_resolve_unknown_falls_back(self):
        from app.scada.protocol_factory import ProtocolFactory
        assert ProtocolFactory.resolve_protocol("unknown_device") == "modbus"

    def test_auto_mode(self):
        from app.scada.protocol_factory import ProtocolFactory
        assert ProtocolFactory.auto_mode() in (True, False)

    def test_create_adapter_modbus(self):
        from app.scada.protocol_factory import ProtocolFactory
        from app.scada.base import DeviceConfig
        config = DeviceConfig("INV001", "inverter", "modbus")
        assert ProtocolFactory.create(config) is not None

    def test_create_adapter_iec61850(self):
        from app.scada.protocol_factory import ProtocolFactory
        from app.scada.base import DeviceConfig
        config = DeviceConfig("IED001", "ied", "iec61850")
        assert ProtocolFactory.create(config) is not None

    def test_create_adapter_opcua(self):
        from app.scada.protocol_factory import ProtocolFactory
        from app.scada.base import DeviceConfig
        config = DeviceConfig("SCADA001", "scada_host", "opcua")
        assert ProtocolFactory.create(config) is not None

    def test_create_adapters_list(self):
        from app.scada.protocol_factory import ProtocolFactory
        from app.scada.base import DeviceConfig
        configs = [
            DeviceConfig("INV001", "inverter", "modbus"),
            DeviceConfig("IED001", "ied", "iec61850"),
        ]
        adapters = ProtocolFactory.create_adapters(configs)
        assert len(adapters) == 2

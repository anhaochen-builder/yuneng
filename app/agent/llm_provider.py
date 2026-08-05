"""混合部署 LLM Provider — 三模自动切换

层级策略:
  L1 (主)  → DeepSeek API (在线, 最快最准)
  L2 (降1) → Qwen GGUF 本地推理 (离线, CPU)
  L3 (降2) → 规则引擎 (纯离线, 无LLM)

切换触发:
  - L1→L2: DeepSeek API 不可用(网络超时/401/500)
  - L2→L1: 定时探测 DeepSeek API 恢复
  - L2→L3: Qwen GGUF 模型加载失败
  - L3→L2: 系统闲置时尝试加载 GGUF

所有 Provider 实现统一接口: chat(), chat_json(), stream(), health_check()
"""

import json
import logging
import os
import threading
import time
from abc import ABC, abstractmethod
from typing import Any, Optional

from app.config import settings

logger = logging.getLogger(__name__)


class BaseLLMProvider(ABC):
    """LLM Provider 抽象基类"""

    @property
    @abstractmethod
    def provider_name(self) -> str:
        ...

    @abstractmethod
    def chat(self, system_prompt: str, user_prompt: str,
             temperature: float = 0.1, max_tokens: int = 2048) -> str:
        ...

    def chat_json(self, system_prompt: str, user_prompt: str,
                  temperature: float = 0.1) -> dict:
        text = self.chat(system_prompt, user_prompt, temperature, max_tokens=1024)
        try:
            if "```json" in text:
                text = text.split("```json")[1].split("```")[0]
            return json.loads(text.strip())
        except (json.JSONDecodeError, IndexError):
            return {"raw": text}

    @abstractmethod
    def health_check(self) -> bool:
        ...

    @abstractmethod
    def is_available(self) -> bool:
        ...


class DeepSeekProvider(BaseLLMProvider):
    """L1: DeepSeek API — 在线模式"""

    provider_name = "deepseek"

    def __init__(self):
        self._client = None
        self._available = False
        self._init_client()

    def _init_client(self):
        from openai import OpenAI
        key = settings.deepseek_api_key
        if not key or key == "your_api_key_here":
            logger.warning("DeepSeek API Key 未配置")
            return
        try:
            self._client = OpenAI(api_key=key, base_url=settings.deepseek_base_url)
            self._available = True
            logger.info("DeepSeek Provider 就绪")
        except Exception as e:
            logger.warning(f"DeepSeek 初始化失败: {e}")

    def chat(self, system_prompt: str, user_prompt: str,
             temperature: float = 0.1, max_tokens: int = 2048) -> str:
        if not self._client:
            raise RuntimeError("DeepSeek 客户端未初始化")
        response = self._client.chat.completions.create(
            model=settings.deepseek_model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=temperature,
            max_tokens=max_tokens,
        )
        return response.choices[0].message.content or ""

    def health_check(self) -> bool:
        if not self._client:
            return False
        try:
            self._client.models.list()
            return True
        except (OSError, TimeoutError, RuntimeError) as e:
            logger.debug(f"Provider [{self.provider_name}] 健康检查失败: {e}")
            self._available = False
            return False

    def is_available(self) -> bool:
        return self._available and self.health_check()


class QwenLocalProvider(BaseLLMProvider):
    """L2: Qwen GGUF 本地 CPU 推理"""

    provider_name = "qwen-local"

    def __init__(self):
        self._model = None
        self._available = False
        self._model_path = settings.qwen_local_path
        self._init_model()

    def _init_model(self):
        if not self._model_path or not os.path.exists(self._model_path):
            logger.info(f"Qwen GGUF 模型未找到: {self._model_path}")
            return
        try:
            from llama_cpp import Llama
            self._model = Llama(
                model_path=self._model_path,
                n_ctx=4096,
                n_threads=os.cpu_count() or 4,
                verbose=False,
            )
            self._available = True
            logger.info("Qwen Local Provider 就绪 (CPU)")
        except ImportError:
            logger.info("llama-cpp-python 未安装，Qwen Local 不可用")
        except Exception as e:
            logger.warning(f"Qwen 本地模型加载失败: {e}")

    def chat(self, system_prompt: str, user_prompt: str,
             temperature: float = 0.1, max_tokens: int = 2048) -> str:
        if not self._model:
            raise RuntimeError("Qwen 本地模型未加载")
        full_prompt = f"{system_prompt}\n\n用户: {user_prompt}\n助手:"
        output = self._model(
            full_prompt,
            max_tokens=max_tokens,
            temperature=temperature,
            stop=["用户:", "\n\n\n"],
            echo=False,
        )
        return output["choices"][0]["text"].strip()

    def health_check(self) -> bool:
        if not self._model:
            return False
        try:
            self._model("你好", max_tokens=10)
            return True
        except (OSError, TimeoutError, RuntimeError) as e:
            logger.debug(f"Local model [{self.provider_name}] 健康检查失败: {e}")
            self._available = False
            return False

    def is_available(self) -> bool:
        return self._available


OFFLINE_RULES: dict[str, dict] = {
    "过热": {"root_cause":"散热系统故障（风扇/散热器/风道堵塞）","actions":["1.检查散热风扇运行状态","2.清洁散热器翅片","3.检查通风道是否堵塞","4.降低设备负载至70%"],"risk_level":"HIGH","confidence":0.65,"related_keywords":["温度","高温","过温","散热","风扇","冷却"],"recommendations":["定期清理散热风道","夏季增加巡检频率"],"safety_notes":["操作时注意高温部件烫伤","停机后等待设备冷却再检修"]},
    "振动": {"root_cause":"机械部件磨损或松动（轴承/齿轮/螺栓）","actions":["1.振动频谱分析确认故障频率","2.检查轴承温度和润滑","3.检查地脚螺栓紧固力矩","4.必要时安排停机检修"],"risk_level":"HIGH","confidence":0.6,"related_keywords":["振动","震动","抖动","异响","噪音"],"recommendations":["每季度振动监测","建立振动趋势基线"],"safety_notes":["停机后确认设备完全停止再靠近","高风速天气注意人身安全"]},
    "通讯中断": {"root_cause":"通讯模块故障或线路问题","actions":["1.检查通讯线缆连接","2.重启通讯模块","3.检查交换机/路由器状态","4.更换通讯模块"],"risk_level":"HIGH","confidence":0.7,"related_keywords":["通讯","断线","离线","连接","光纤","网线"],"recommendations":["备用通讯链路切换","关键设备双网冗余"],"safety_notes":["更换模块前关闭设备电源","光纤接口注意激光安全"]},
    "绝缘降低": {"root_cause":"绝缘老化或受潮导致绝缘阻抗降低","actions":["1.测量正负极对地绝缘电阻","2.检查设备密封性","3.检查凝露或进水痕迹","4.停机干燥处理"],"risk_level":"CRITICAL","confidence":0.72,"related_keywords":["绝缘","阻抗","漏电","接地","对地"],"recommendations":["雨季加强巡检","配置除湿装置"],"safety_notes":["高压设备测绝缘必须停电验电","测试后必须放电"]},
    "过电压": {"root_cause":"电网电压波动或无功补偿异常","actions":["1.检查电网侧电压波动记录","2.检查无功补偿装置状态","3.检查变压器分接头位置"],"risk_level":"HIGH","confidence":0.65,"related_keywords":["过压","电压高","偏高","波动"]},
    "欠电压": {"root_cause":"电网电压跌落或负荷突增","actions":["1.检查电网侧电压曲线","2.检查负荷变化趋势","3.检查无功补偿投入状态"],"risk_level":"MEDIUM","confidence":0.6,"related_keywords":["欠压","电压低","偏低","低电压"]},
    "过电流": {"root_cause":"设备短路或负荷异常增大","actions":["1.检查是否有短路故障","2.核对负荷电流与额定值","3.检查保护装置动作记录"],"risk_level":"CRITICAL","confidence":0.68,"related_keywords":["过流","电流大","短路","过载","跳闸"]},
    "三相不平衡": {"root_cause":"单相负荷分配不均或设备缺相运行","actions":["1.测量三相电压和电流","2.检查是否存在缺相","3.重新分配单相负荷"],"risk_level":"MEDIUM","confidence":0.62,"related_keywords":["不平衡","三相","缺相","偏相","不对称"]},
    "频率异常": {"root_cause":"电网频率波动或并网控制异常","actions":["1.检查电网频率曲线","2.核对保护装置频率定值","3.检查并网逆变器频率跟踪"],"risk_level":"HIGH","confidence":0.6,"related_keywords":["频率","周波","Hz","工频"]},
    "谐波超标": {"root_cause":"电力电子设备谐波注入或电网背景谐波","actions":["1.测量各次谐波含量","2.检查有源滤波器运行状态","3.排查谐波源设备"],"risk_level":"MEDIUM","confidence":0.58,"related_keywords":["谐波","THD","畸变","波形"]},
    "功率因数低": {"root_cause":"无功补偿不足或补偿装置故障","actions":["1.检查无功补偿装置投切状态","2.检查电容器组容量","3.调整补偿策略"],"risk_level":"MEDIUM","confidence":0.55,"related_keywords":["功率因数","无功","补偿","电容器","SVG"]},
    "油温高": {"root_cause":"变压器冷却系统故障或过负荷运行","actions":["1.检查冷却风扇/油泵","2.测量顶层油温","3.检查油位","4.降低负荷"],"risk_level":"HIGH","confidence":0.68,"related_keywords":["油温","油面温度","绕组温度"],"safety_notes":["油温异常升高可能是内部故障前兆","重瓦斯保护动作时严禁送电"]},
    "油中溶解气体异常": {"root_cause":"变压器内部局部放电或过热导致绝缘油分解","actions":["1.取油样DGA色谱分析","2.三比值法判断故障类型","3.检查瓦斯继电器","4.根据分析结果安排检修"],"risk_level":"CRITICAL","confidence":0.75,"related_keywords":["DGA","氢气","乙炔","乙烯","甲烷","色谱"],"safety_notes":["乙炔超标提示电弧放电必须立即停机","取油样时注意防爆"]},
    "漏油": {"root_cause":"密封件老化或外力损伤导致泄漏","actions":["1.检查漏油点位置","2.检查油位指示","3.检查密封垫和法兰","4.补充绝缘油"],"risk_level":"HIGH","confidence":0.7,"related_keywords":["漏油","渗油","油位低","密封","法兰"]},
    "风机齿轮箱故障": {"root_cause":"齿轮磨损或润滑不良","actions":["1.检测齿轮箱振动频谱","2.检查油温和油品","3.内窥镜检查齿轮","4.更换润滑油"],"risk_level":"HIGH","confidence":0.66,"related_keywords":["齿轮箱","齿轮","增速箱","润滑油"]},
    "风机叶片故障": {"root_cause":"叶片裂纹或雷击损伤","actions":["1.无人机/望远镜检查叶片","2.检查裂纹/分层/雷击痕迹","3.检查螺栓紧固力矩","4.安排维修"],"risk_level":"CRITICAL","confidence":0.7,"related_keywords":["叶片","桨叶","裂纹","雷击","破损"],"safety_notes":["叶片检查必须停机锁定风轮","高空作业系安全带"]},
    "逆变器IGBT故障": {"root_cause":"IGBT模块过热或过流损坏","actions":["1.检查IGBT模块NTC温度","2.测量IGBT导通压降","3.检查驱动板波形","4.更换IGBT模块"],"risk_level":"CRITICAL","confidence":0.7,"related_keywords":["IGBT","逆变","功率模块","开关管","驱动板"],"safety_notes":["更换IGBT必须先断电放电","IGBT静电敏感注意防护"]},
    "组件热斑": {"root_cause":"电池片被遮挡或旁路二极管失效","actions":["1.红外热像扫描温度分布","2.排查遮挡源(灰尘/鸟粪)","3.检查旁路二极管","4.清洁或更换组件"],"risk_level":"MEDIUM","confidence":0.72,"related_keywords":["热斑","温差","组件温度","hotspot","阴影"]},
    "组件PID衰减": {"root_cause":"电位诱导衰减导致功率下降","actions":["1.测量组件对地电压","2.I-V测试对比额定功率","3.EL检测排查隐裂","4.安装PID修复装置"],"risk_level":"MEDIUM","confidence":0.6,"related_keywords":["PID","衰减","功率下降","电势诱导"]},
    "雷击": {"root_cause":"雷击导致设备绝缘击穿","actions":["1.检查避雷器动作记录","2.检查接地网电阻","3.检查SPD浪涌保护器","4.更换损坏设备"],"risk_level":"CRITICAL","confidence":0.7,"related_keywords":["雷击","雷电","雷","浪涌","避雷","SPD"],"safety_notes":["雷击后必须确认无残余电荷","雷雨天禁止户外作业"]},
    "接地故障": {"root_cause":"接地网腐蚀或接地电阻增大","actions":["1.测量接地网接地电阻","2.检查引下线连接","3.开挖检查腐蚀情况","4.补打接地极"],"risk_level":"CRITICAL","confidence":0.68,"related_keywords":["接地","地网","接地电阻","地线"],"safety_notes":["接地网故障直接影响人身安全必须立即处理"]},
    "发电机故障": {"root_cause":"绕组绝缘老化或转子机械故障","actions":["1.测量定子绕组绝缘","2.检查转子轴承温度振动","3.检测直流电阻和吸收比"],"risk_level":"CRITICAL","confidence":0.65,"related_keywords":["发电机","定子","转子","绕组","励磁"]},
    "控制系统故障": {"root_cause":"PLC/控制器程序异常或IO板卡故障","actions":["1.检查控制器面板告警","2.检查IO板卡通道","3.检查通信总线","4.更换故障板卡"],"risk_level":"HIGH","confidence":0.6,"related_keywords":["PLC","控制器","控制","IO","板卡","程序"]},
    "蓄电池故障": {"root_cause":"蓄电池老化或充电管理异常","actions":["1.测量单体电压和内阻","2.检查充电模块","3.核对性放电试验","4.更换不合格电池"],"risk_level":"MEDIUM","confidence":0.6,"related_keywords":["蓄电池","电池","UPS","直流屏","备电"]},
    "电缆故障": {"root_cause":"电缆绝缘老化或外力破坏","actions":["1.电缆路径定位排查","2.绝缘电阻测试","3.局部放电检测","4.修复或更换电缆"],"risk_level":"HIGH","confidence":0.62,"related_keywords":["电缆","线路","导线","缆","埋地"],"safety_notes":["电缆测试前必须两端停电验电","高压电缆测试后充分放电"]},
    "汇流箱故障": {"root_cause":"汇流箱内部接线松动或熔断器烧毁","actions":["1.检查熔断器状态","2.测量各路输入电流","3.检查接线端子","4.更换熔断器或紧固端子"],"risk_level":"MEDIUM","confidence":0.65,"related_keywords":["汇流箱","汇流","熔断器","保险","端子"]},
}


class RuleEngineProvider(BaseLLMProvider):
    """L3: 规则引擎 — 纯离线无LLM"""

    provider_name = "rule-engine"

    def __init__(self):
        self._rules = self._load_rules()
        self._available = True
        logger.info("规则引擎 Provider 就绪 (纯离线)")

    def _load_rules(self) -> dict[str, dict]:
        return OFFLINE_RULES

    def _match_rule(self, prompt: str) -> dict:
        for keyword, rule in self._rules.items():
            if keyword in prompt:
                return rule
        return {
            "root_cause": "需人工介入分析，规则引擎无法匹配具体故障模式",
            "actions": [
                "1. 查看设备历史告警记录",
                "2. 收集现场运行数据和照片",
                "3. 联系设备厂家技术支持",
                "4. 如需紧急处理，参考设备运维手册",
            ],
            "risk": "MEDIUM",
            "confidence": 0.3,
        }

    def chat(self, system_prompt: str, user_prompt: str,
             temperature: float = 0.1, max_tokens: int = 2048) -> str:
        rule = self._match_rule(user_prompt)
        lines = [
            "## 规则引擎诊断结果 ⚠️（离线降级模式，仅供参考）",
            "",
            f"**可能的根因**: {rule['root_cause']}",
            f"**风险等级**: {rule['risk']}",
            f"**置信度**: {rule['confidence']*100:.0f}%",
            "",
            "**推荐处置步骤**:",
        ]
        for action in rule["actions"]:
            lines.append(action)
        lines.extend([
            "",
            "> ⚠️ 当前为规则引擎降级模式，诊断精度有限。",
            "> 建议尽快恢复网络连接或启动本地推理模型以获得更准确的诊断。",
        ])
        return "\n".join(lines)

    def health_check(self) -> bool:
        return True

    def is_available(self) -> bool:
        return True


class HybridProvider:
    """混合部署调度器 — 自动降级+恢复探测"""

    def __init__(self):
        self._providers: dict[str, BaseLLMProvider] = {}
        self._current: Optional[BaseLLMProvider] = None
        self._lock = threading.Lock()
        self._recovery_interval = 60
        self._recovery_thread: Optional[threading.Thread] = None
        self._init_providers()

    def _init_providers(self):
        self._providers["deepseek"] = DeepSeekProvider()
        self._providers["qwen-local"] = QwenLocalProvider()
        self._providers["rule-engine"] = RuleEngineProvider()

        self._current = self._select_initial()
        logger.info(f"当前 Provider: {self._current.provider_name}")

        if self._current.provider_name != "deepseek":
            self._start_recovery()

    def _select_initial(self) -> BaseLLMProvider:
        for name in ["deepseek", "qwen-local", "rule-engine"]:
            p = self._providers[name]
            if p.is_available():
                return p
        return self._providers["rule-engine"]

    def _start_recovery(self):
        if self._recovery_thread and self._recovery_thread.is_alive():
            return

        def recover_loop():
            while True:
                time.sleep(self._recovery_interval)
                if self._current.provider_name != "deepseek":
                    deepseek = self._providers["deepseek"]
                    if deepseek.health_check():
                        with self._lock:
                            self._current = deepseek
                        logger.info("DeepSeek API 已恢复，切换回在线模式")

                if self._current.provider_name == "rule-engine":
                    qwen = self._providers["qwen-local"]
                    if qwen.is_available():
                        with self._lock:
                            self._current = qwen
                        logger.info("Qwen Local 已就绪，从规则引擎升级")

        self._recovery_thread = threading.Thread(target=recover_loop, daemon=True)
        self._recovery_thread.start()

    @property
    def current_provider(self) -> BaseLLMProvider:
        return self._current

    @property
    def current_mode(self) -> str:
        return self._current.provider_name

    def chat(self, system_prompt: str, user_prompt: str,
             temperature: float = 0.1, max_tokens: int = 2048) -> str:
        provider = self._current
        try:
            return provider.chat(system_prompt, user_prompt, temperature, max_tokens)
        except Exception as e:
            logger.warning(f"Provider [{provider.provider_name}] 调用失败: {e}")
            self._try_downgrade(provider)
            return self.chat(system_prompt, user_prompt, temperature, max_tokens)

    def chat_json(self, system_prompt: str, user_prompt: str,
                  temperature: float = 0.1) -> dict:
        provider = self._current
        try:
            return provider.chat_json(system_prompt, user_prompt, temperature)
        except Exception as e:
            logger.warning(f"Provider [{provider.provider_name}] JSON调用失败: {e}")
            self._try_downgrade(provider)
            return self.chat_json(system_prompt, user_prompt, temperature)

    def _try_downgrade(self, failed_provider: BaseLLMProvider):
        order = ["deepseek", "qwen-local", "rule-engine"]
        try:
            idx = order.index(failed_provider.provider_name)
        except ValueError:
            return

        for i in range(idx + 1, len(order)):
            p = self._providers[order[i]]
            if p.is_available():
                with self._lock:
                    self._current = p
                logger.warning(f"降级: {failed_provider.provider_name} → {p.provider_name}")
                self._start_recovery()
                return

    def mode_status(self) -> dict:
        return {
            "current": self._current.provider_name,
            "available": {n: p.is_available() for n, p in self._providers.items()},
            "deployment": "online" if self._current.provider_name == "deepseek"
            else ("offline-llm" if self._current.provider_name == "qwen-local"
                  else "offline-rules"),
        }


hybrid_llm = HybridProvider()

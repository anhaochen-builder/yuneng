
# 驭能前端 OpenCode 实施代码方案


## 第一部分：准备工作


### 1. 项目初始化命令

# 创建 Vue 3 + TypeScript 项目npm create vue@latest yuneng-frontend -- --typescript --router --pinia --eslint --prettier# 进入项目目录cd yuneng-frontend# 安装核心依赖npm install element-plus @element-plus/icons-vue echarts vue-echarts @vue-flow/core @vue-flow/background @vue-flow/controls @vue-flow/minimap three @tweenjs/tween.js pinia-plugin-persistedstate axios eventsource-parser# 安装开发依赖npm install -D sass unplugin-auto-import unplugin-vue-components @types/three


### 2. 环境变量配置

创建 .env.development 文件：

# 后端 API 基础路径VITE_API_BASE_URL=http://localhost:8000# SSE 流式接口基础路径VITE_SSE_BASE_URL=http://localhost:8000# 部署模式: offline-standalone | offline-standard | production-onlineVITE_DEPLOY_MODE=production-online# 应用标题VITE_APP_TITLE=驭能智能诊断平台


### 3. Nginx 反向代理配置

server {    listen 80;    server_name yuneng.local;    root /usr/share/nginx/html;    index index.html;    # 前端路由 history 模式    location / {        try_files uri uri/ /index.html;    }    # API 反向代理    location /api/ {        proxy_pass http://backend:8000/api/;        proxy_http_version 1.1;        proxy_set_header Connection '';        proxy_buffering off;       # SSE 必须关闭缓冲        proxy_cache off;        chunked_transfer_encoding on;        tcp_nopush off;    }    # 健康检查    location /health {        proxy_pass http://backend:8000/health;    }}


## 第二部分：分阶段实施提示词


### 阶段一：全局样式与基础布局（3天）


#### 目标说明

搭建项目全局科技蓝/赛博朋克风格样式系统，实现三栏 Grid 大屏布局、Header 组件、粒子背景动画，为后续所有页面提供统一视觉基座。


#### 发送给 OpenCode 的完整提示词

请为"驭能智能诊断平台"前端项目创建全局样式与基础布局，严格使用 Vue 3 Composition API + <script setup lang="ts"> + TypeScript。## 需要创建的文件### 1. src/styles/variables.scss定义全局 CSS 变量：- --color-bg-primary: #020b18（深色背景）- --color-bg-secondary: #0a1628- --color-accent: #00f0ff（青色高亮）- --color-accent-dim: rgba(0, 240, 255, 0.15)- --color-text-primary: #e0e6ed- --color-text-secondary: #8892a4- --color-critical: #ff4d4f- --color-high: #ff9c40- --color-medium: #ffd666- --color-low: #52c41a- --font-digital: 'Orbitron', 'Share Tech Mono', monospace（数字等宽字体）- --font-body: 'Inter', 'PingFang SC', sans-serif- --spacing-xs/sm/md/lg/xl: 4px/8px/16px/24px/32px- --shadow-glow: 0 0 10px rgba(0, 240, 255, 0.3)- --border-tech: 1px solid rgba(0, 240, 255, 0.2)### 2. src/styles/global.scss- 引入 variables.scss- 全局 body 样式：background var(--color-bg-primary), color var(--color-text-primary), font-family var(--font-body)- .tech-card 通用类：  - background: rgba(10, 22, 40, 0.85)  - backdrop-filter: blur(12px)  - border: var(--border-tech)  - border-radius: 4px  - position: relative  - padding: var(--spacing-lg)  - 四个角 L 型装饰（使用 ::before 和 ::after 伪元素，宽高 12px，border-color var(--color-accent)）- @keyframes breathe：呼吸灯动画（opacity 0.4 → 1 → 0.4，周期 3s）- @keyframes fadeIn：fade-in 加载动画- .animate-breathe { animation: breathe 3s ease-in-out infinite }- .animate-fade-in { animation: fadeIn 0.6s ease-out }- 数字字体工具类 .font-digital { font-family: var(--font-digital) }### 3. src/components/ParticleBackground.vue- 使用 Three.js 创建粒子背景动画- 粒子数量 200，颜色 #00f0ff，透明度 0.4- 粒子缓慢随机漂移，鼠标移动时产生微弱排斥力- 组件挂载时初始化 Three.js 场景，卸载时销毁- 使用 <canvas> 作为全屏固定定位背景，z-index: -1### 4. src/components/AppHeader.vue- 左侧：标题"驭能智能诊断平台"，使用 .font-digital- 右侧：实时时间（每秒更新）、系统状态指示灯（绿色呼吸灯）、用户信息（头像+名称）- 底部边框：1px solid rgba(0, 240, 255, 0.15)- 高度 60px### 5. src/views/Dashboard.vue- 三栏 Grid 布局：grid-template-columns: 25% 50% 25%- 高度 100vh，overflow hidden- 左栏、中栏、右栏使用 .tech-card 包裹- 各栏内部预留 slot 或注释标记后续填充区域### 6. src/App.vue- 引入 global.scss- 使用 ParticleBackground 作为全局背景- 使用 AppHeader- 使用 Dashboard 作为主内容区- 应用 fade-in 加载动画## 技术要求- 所有组件使用 <script setup lang="ts">- 样式使用 <style scoped lang="scss">- 不使用任何 UI 框架的布局组件，纯 CSS Grid/Flex 实现- Three.js 粒子背景需做好内存清理


#### 关键代码文件

src/styles/variables.scss

src/styles/global.scss

src/components/ParticleBackground.vue

src/components/AppHeader.vue

src/views/Dashboard.vue

src/App.vue


### 阶段二：ECharts 图表组件库（5天）


#### 目标说明

封装 8 个科技蓝风格的 ECharts 图表组件，覆盖 SCADA 数据可视化、设备健康度、Judge 评分、环境监测等场景，统一主题配置，支持响应式与数据动态更新。


#### 发送给 OpenCode 的完整提示词

请为"驭能智能诊断平台"创建 ECharts 图表组件库，使用 Vue 3 + TypeScript + vue-echarts，所有图表遵循科技蓝主题。## 前置：创建 src/utils/echartsTheme.js注册自定义 ECharts 主题 'techBlue'，包含：- backgroundColor: 'transparent'- textStyle.color: '#8892a4'- title.textStyle.color: '#e0e6ed'- legend.textStyle.color: '#8892a4'- tooltip 样式：backgroundColor rgba(10,22,40,0.95), borderColor #00f0ff, textStyle color #e0e6ed- 5种系列颜色：['#00f0ff', '#00d4aa', '#7b68ee', '#ff9c40', '#ff4d4f']- categoryAxis/lineStyle/splitLine 等轴线样式使用 rgba(0,240,255,0.1)- SCADA 双轴专用配置- Judge 雷达图专用配置（indicator 文字颜色、areaStyle 透明度）## 需要创建的组件（全部使用 <script setup lang="ts">）### 1. src/components/charts/PowerBarChart.vue- 实时发电功率柱状图，24小时 X 轴- Props: data: Array<{ hour: string; power: number }>- 柱状图颜色渐变：从 #00f0ff 到 #00d4aa- 支持数据动态更新（watch props）### 2. src/components/charts/EnergyTrendChart.vue- 发电量趋势折线图- 双线：今日预测（虚线 #7b68ee）vs 实际发电（实线 #00f0ff）- Props: predicted: number[], actual: number[], labels: string[]- 区域填充（areaStyle 渐变）### 3. src/components/charts/DeviceHealthRadar.vue- 设备健康度雷达图，五维：转速、温度、振动、电压、油温- Props: scores: { rpm: number; temp: number; vibration: number; voltage: number; oilTemp: number }- 使用 Judge 雷达图专用配置- 填充区域颜色 rgba(0, 240, 255, 0.2)### 4. src/components/charts/AlarmPieChart.vue- 故障类型分布环形图- Props: data: Array<{ type: string; count: number }>- 中心显示总数，使用 .font-digital- 标签颜色与系列颜色一致### 5. src/components/charts/SCADATrendChart.vue- SCADA 双轴趋势图- 左轴：功率(kW)/电流(A)，右轴：温度(℃)/风速(m/s)- Props: timeSeries: Array<{ time: string; power: number; current: number; temp: number; wind: number }>, faultWindow?: { start: string; end: string }- 故障窗口高亮：使用 markArea 浅色背景矩形 rgba(255,77,79,0.1)- 四条折线不同颜色### 6. src/components/charts/JudgeRadarChart.vue- Judge 五维度评分雷达图- Props: scores: { evidence: number; logic: number; compliance: number; operability: number; consistency: number }- 五个维度：证据充分性(25%)、推理逻辑性(25%)、安规合规性(20%)、可操作性(20%)、历史一致性(10%)- 显示评分等级 A/B/C/D/F（根据加权总分计算）- 使用 Judge 雷达图专用配置### 7. src/components/EnvironmentPanel.vue- 环境监测面板，使用 .tech-card 包裹- 展示：环境温度、湿度、辐照度、风速- 每个指标带图标和数值，数值使用 .font-digital- Props: envData: { temperature: number; humidity: number; irradiance: number; windSpeed: number }### 8. src/components/StatCard.vue- 关键指标数字卡片- Props: title: string, value: string | number, unit?: string, trend?: 'up' | 'down' | 'flat', icon?: string- 数值使用 .font-digital，大号字体- 趋势箭头（上绿下红）- 使用 .tech-card 样式## 技术要求- 所有图表组件通过 vue-echarts 的 <v-chart> 渲染- 统一引入 echartsTheme.js 并设置 theme="techBlue"- 图表容器使用 autoresize- Props 使用 defineProps + TypeScript interface- 不使用任何硬编码颜色，全部走主题配置


#### 关键代码文件

src/utils/echartsTheme.js

src/components/charts/PowerBarChart.vue

src/components/charts/EnergyTrendChart.vue

src/components/charts/DeviceHealthRadar.vue

src/components/charts/AlarmPieChart.vue

src/components/charts/SCADATrendChart.vue

src/components/charts/JudgeRadarChart.vue

src/components/EnvironmentPanel.vue

src/components/StatCard.vue


### 阶段三：SSE 流式客户端与 AI 诊断终端（7天）


#### 目标说明

实现完整的 SSE 流式通信层与 AI 诊断交互 UI，包括 SSE 客户端封装、useSSE Hook、对话式 UI、流式消息解析、9项结构化诊断报告卡片、步骤进度条、用户反馈面板。此阶段是平台核心交互能力的基石。


#### 发送给 OpenCode 的完整提示词

请为"驭能智能诊断平台"创建 SSE 流式客户端与 AI 诊断终端组件，使用 Vue 3 + TypeScript + Composition API。## 需要创建的文件### 1. src/api/sse.tsSSE 客户端封装：- createSSEConnection(url: string, params?: Record<string, string>): EventSource 封装- 支持 POST 方式的 SSE（使用 fetch + ReadableStream 模拟，因为原生 EventSource 不支持 POST）- 自动重连机制（指数退避，最大 5 次）- 返回 { onMessage, onError, onClose, disconnect } 方法- 消息类型定义：  interface SSEMessage {    type: 'start' | 'status' | 'content' | 'diagnosis' | 'done' | 'error'    data: any  }### 2. src/hooks/useSSE.tsuseSSE Composable：- useSSE(endpoint: string)- 返回：  - messages: Ref<SSEMessage[]>  - isStreaming: Ref<boolean>  - currentStep: Ref<string>  - streamedContent: Ref<string>（打字机累积文本）  - diagnosisReport: Ref<DiagnosisReport | null>  - error: Ref<string | null>  - sendMessage(content: string, files?: File[]): void  - abort(): void- 内部处理各 type 消息：  - start: 重置状态，初始化会话  - status: 更新 currentStep  - content: 逐字追加到 streamedContent（模拟打字机，30ms/字）  - diagnosis: 解析并设置 diagnosisReport  - done: 设置 isStreaming = false  - error: 设置 error 并通知### 3. src/types/diagnosis.ts诊断报告类型定义：interface DiagnosisReport {  alertSummary: string           // 1. 告警摘要  preliminaryJudgment: string    // 2. 初步判断  analysisBasis: string          // 3. 分析依据  possibleCauses: Array<{        // 4. 可能原因    cause: string    probability: number          // 百分比  }>  troubleshootingSteps: string[] // 5. 排查步骤  handlingSuggestions: string[]  // 6. 处理建议  safetyWarnings: Array<{        // 7. 安全风险提示    warning: string    regulationRef: string        // 安规条款编号  }>  dispatchRecommendation: {      // 8. 是否建议派单    shouldDispatch: boolean    urgency: 'CRITICAL' | 'HIGH' | 'MEDIUM' | 'LOW'    dispatchType: string  }  riskSelfReview: {              // 9. 风险自复核    level: 'CRITICAL' | 'HIGH' | 'MEDIUM' | 'LOW'    details: string  }}### 4. src/components/chat/ChatMessage.vue对话消息气泡组件：- Props: message: { role: 'user' | 'ai'; content: string; timestamp: number; files?: string[] }- 用户消息：右对齐，青色背景- AI 消息：左对齐，深色背景，支持 Markdown 渲染- AI 消息支持流式打字机效果（传入 isStreaming prop）- 文件/图片缩略图展示### 5. src/components/chat/AiThinkingTerminal.vueAI 思考终端组件：- 显示当前 SSE status 步骤信息- 使用 StepProgressBar 展示多步骤进度- 终端风格 UI：等宽字体、闪烁光标、滚动日志- Props: steps: Array<{ label: string; status: 'pending' | 'running' | 'done' | 'error' }>### 6. src/components/diagnosis/DiagnosisReportCard.vue9项结构化诊断报告卡片：- Props: report: DiagnosisReport- 使用 .tech-card 包裹- 9个区块按顺序渲染，每个区块有标题和图标- 可能原因：按概率从高到低排列，显示百分比进度条- 排查步骤：可勾选 Checklist（el-checkbox-group）- 安全风险提示：安规条款编号可点击，hover 显示 Tooltip 详情- 风险等级使用 RiskLevelTag 组件- 派单建议：紧急程度 + 派单类型高亮显示### 7. src/components/diagnosis/RiskLevelTag.vue风险等级 Tag 组件：- Props: level: 'CRITICAL' | 'HIGH' | 'MEDIUM' | 'LOW'- CRITICAL: 红色 #ff4d4f，带呼吸灯动画- HIGH: 橙色 #ff9c40- MEDIUM: 黄色 #ffd666- LOW: 绿色 #52c41a- 使用 el-tag，自定义颜色### 8. src/components/diagnosis/StepProgressBar.vue步骤进度条组件：- Props: steps: Array<{ label: string; status: 'pending' | 'running' | 'done' | 'error' }>- 横向排列，当前步骤高亮青色，完成步骤绿色，错误红色- 运行中步骤带呼吸灯动画- 步骤间连线动态效果### 9. src/components/chat/FeedbackPanel.vue用户反馈面板：- 三个按钮：准确 / 部分准确 / 不准确- 部分准确时展开修正意见输入框（el-input textarea）- 提交后显示感谢提示- Props: taskId: string- Emits: feedback(type: 'accurate' | 'partial' | 'inaccurate', comment?: string)### 10. src/components/chat/FileUploadButton.vue文件/图片上传按钮：- 支持拖拽上传和点击选择- 限制类型：图片(jpg/png)、PDF- 上传后显示缩略图预览- Emits: upload(files: File[])## 技术要求- 所有组件 <script setup lang="ts">- SSE 使用 fetch + ReadableStream 实现 POST 方式- 打字机效果使用 requestAnimationFrame 或 setInterval- DiagnosisReportCard 内部各区块使用折叠/展开交互- Checklist 状态通过 v-model 双向绑定- 安规 Tooltip 使用 el-tooltip- 所有颜色使用 CSS 变量，不硬编码


#### 关键代码文件

src/api/sse.ts

src/hooks/useSSE.ts

src/types/diagnosis.ts

src/components/chat/ChatMessage.vue

src/components/chat/AiThinkingTerminal.vue

src/components/diagnosis/DiagnosisReportCard.vue

src/components/diagnosis/RiskLevelTag.vue

src/components/diagnosis/StepProgressBar.vue

src/components/chat/FeedbackPanel.vue

src/components/chat/FileUploadButton.vue


### 阶段四：核心页面开发（10天）


#### 目标说明

基于前三个阶段的基础组件，开发 7 个核心业务页面，完整覆盖技术文档中所有功能模块，包括智能诊断中心、SCADA 看板、告警管理、诊断透视、知识库管理、设备状态、系统设置。


#### 发送给 OpenCode 的完整提示词

```text 请为”驭能智能诊断平台”创建 7 个核心页面，使用 Vue 3 + TypeScript + Element Plus + Composition API。所有页面使用 .tech-card 包裹内容区域，颜色使用 CSS 变量。


## 需要创建的页面


### 1. src/views/DiagnosticCenter.vue（智能诊断中心）

左侧 60%：对话区域

顶部：文件/图片上传按钮（FileUploadButton）

中间：消息列表（ChatMessage 列表，自动滚动到底部）

底部：输入框 + 发送按钮

AI 回复时显示 AiThinkingTerminal

收到 diagnosis 消息时渲染 DiagnosisReportCard

每条 AI 回复底部显示 FeedbackPanel

右侧 40%：诊断报告侧边栏

当前诊断报告详情

历史诊断记录列表

使用 useSSE hook 管理流式通信

对接 /api/chat/stream 和 /api/diagnose/stream


### 2. src/views/SCADADashboard.vue（SCADA 数据看板）

顶部行：3个 StatCard（当前功率、日发电量、设备状态）

中间行左：PowerBarChart（24h 实时功率）

中间行右：EnergyTrendChart（预测 vs 实际）

底部行左：SCADATrendChart（双轴趋势，含故障窗口高亮）

底部行右：DeviceHealthRadar（五维健康度）

右侧面板：SCADA 连接配置面板

协议类型选择（Modbus TCP / IEC 61850 / OPC-UA）


### 阶段五：高级功能与特效打磨（5天）


#### 目标说明

完成 LangGraph 拓扑可视化、多模态图片标注、实时告警浮层、三层记忆系统展示、主动学习状态面板，以及所有 CSS 动效增强（呼吸灯、扫描线、粒子背景）。


#### 发送给 OpenCode 的完整提示词

请为"驭能智能诊断平台"完成以下高级功能组件和动效增强，严格使用 Vue 3 Composition API + <script setup lang="ts"> + TypeScript。## 1. src/components/LangGraphTopology.vue（LangGraph 执行拓扑可视化）使用 @vue-flow/core 创建 LangGraph 多智能体编排的执行拓扑图，展示完整的诊断流程：- 节点列表（按技术文档编排流程）：  - START → PreCheck → ContextLoad → Supervisor → [条件路由分发]  - 并行分支：Diagnosis子图(9节点) | SCADA采集子图 | 多模态子图  - 汇聚 → Judge评估子图(5维度评分) → [评分≥70?] → SafetyReview → FinalResponse → MemorySave → END  - 重规划循环：Judge < 70 → Replanner(最多2次) → 仍不达标 → 降级人工介入- 节点样式：  - 进行中：蓝色边框 + 蓝色背景 + 呼吸动画  - 已完成：绿色边框 + 绿色背景  - 重试中：黄色边框 + 黄色背景 + 旋转动画  - 失败：红色边框 + 红色背景  - 人工介入：橙色边框 + 橙色背景- 连线样式：  - 正常流程：青色实线  - 条件分支（<70）：红色虚线标注"重规划"  - 条件分支（≥70）：绿色实线标注"通过"- 支持点击节点弹出详情面板，显示该节点的输入/输出/耗时## 2. src/components/MultimodalAnnotator.vue（多模态图片标注组件）用于展示 AI 多模态分析结果：- 图片上传区域（支持拖拽上传）- 图片预览区域（使用 canvas 覆盖层）- 标注功能：  - 红外热像图：在热点区域绘制半透明红色矩形框 + 温度标注  - 可见光照片：在异常区域绘制标注点 + 描述文字  - 频谱/波形图：在特征频率处标注- 右侧标注列表面板，显示每个标注的详情（类型、位置、温度值、面积等）- 支持标注的增删改## 3. src/components/AlarmAlertOverlay.vue（实时告警浮层）- 定位：屏幕右上角，固定定位- 正常状态：隐藏- 有告警时：从右上角滑入，带红色呼吸边框- 告警内容：  - 告警级别 Tag（critical/high/medium）  - 告警描述  - AI 初步分析气泡（"检测到 3 号风机异常，AI 正在介入分析..."）  - 关闭按钮- 严重告警时：屏幕边缘出现红色呼吸灯效果- 支持多个告警堆叠显示- 点击可跳转到告警管理页面## 4. src/components/MemorySystemPanel.vue（三层记忆系统展示面板）展示系统的三层记忆架构：- 短期记忆区：  - 标题："短期记忆（当前会话）"  - 显示最近 3 轮对话历史（用户提问 → 助手回答）  - 每条记录显示时间戳和角色标签- 工作记忆区：  - 标题："工作记忆（当前任务）"  - 以键值对形式展示 35 个状态键的关键信息  - 分组显示：输入层、会话层、意图层、诊断层、证据层、RAG层、记忆层、质量层、SCADA层、多模态层、执行层  - 每个状态键显示名称、策略（Replace/Append）、当前值（截断显示）- 长期记忆区：  - 标题："长期记忆（ChromaDB）"  - 显示已入库案例数量  - 最近入库的 5 个案例列表（设备类型、故障类型、时间戳、置信度）  - 时间衰减机制说明## 5. src/components/ActiveLearningPanel.vue（主动学习状态面板）展示主动学习系统的运行状态：- 学习机制状态卡片（4个）：  - 成功案例入库：已入库案例数 / 总案例数，进度条  - Skill 自动生成：已生成 Skill 数 / 待生成 Skill 数，触发条件说明（≥3次）  - 反馈驱动优化：待审核池数量，最近审核记录  - 模型增量微调：累积标注案例数 / 50，触发条件说明，最近微调记录- 学习闭环流程图（使用 Vue Flow 或简单 CSS 流程图）：  - 诊断完成 → 用户反馈 → 准确/部分准确/不准确 → 不同分支处理## 6. CSS 动效增强在 global.scss 中追加以下动画：### 扫描线效果给 body 添加一层固定定位的扫描线遮罩：- 使用 linear-gradient 创建水平扫描线- @keyframes scanline 实现从上到下的循环扫描- opacity: 0.03，pointer-events: none### 呼吸灯增强- .breathe-fast：1.5s 周期- .breathe-slow：5s 周期- .breathe-critical：红色呼吸 + 脉冲放大### 粒子背景优化- 粒子数量根据屏幕尺寸自适应（大屏 300 个，小屏 150 个）- 添加鼠标交互（粒子随鼠标移动产生涟漪效果）## 技术要求- 所有组件使用 <script setup lang="ts">- 样式使用 <style scoped lang="scss">- Three.js 粒子背景需做好内存清理（onBeforeUnmount 时销毁）- @vue-flow 的节点和连线使用 TypeScript 类型定义


#### 关键代码文件

• src/components/LangGraphTopology.vue

• src/components/MultimodalAnnotator.vue

• src/components/AlarmAlertOverlay.vue

• src/components/MemorySystemPanel.vue

• src/components/ActiveLearningPanel.vue

• src/styles/global.scss（追加动效）


## 第三部分：ECharts 科技蓝主题配置文件

完整的 ECharts 主题配置，覆盖折线图、柱状图、环形图、雷达图、仪表盘 5 种系列，以及 SCADA 双轴专用配置和 Judge 五维度雷达图专用配置。


### src/utils/echartsTheme.js

// ECharts 科技蓝主题配置// 严格对齐驭能技术文档的视觉规范const theme = {  // === 全局配色方案 ===  color: ['#00f2f1', '#00c0ff', '#ffa022', '#ff4d4f', '#00e676', '#76ff03', '#ff6d00', '#d500f9'],  backgroundColor: 'transparent',  textStyle: {    fontFamily: 'Share Tech Mono, Orbitron, monospace',    color: '#e0e6ed'  },  // === 标题 ===  title: {    textStyle: {      color: '#00f0ff',      fontSize: 16,      fontWeight: 'bold',      fontFamily: 'Share Tech Mono'    },    subtextStyle: {      color: '#8892a4',      fontSize: 12    }  },  // === 提示框 ===  tooltip: {    backgroundColor: 'rgba(10, 22, 40, 0.9)',    borderColor: '#00f0ff',    borderWidth: 1,    textStyle: { color: '#e0e6ed', fontFamily: 'Share Tech Mono' },    trigger: 'axis',    axisPointer: {      type: 'cross',      crossStyle: { color: '#00f0ff' },      lineStyle: { color: '#00f0ff', type: 'dashed' }    }  },  // === 图例 ===  legend: {    textStyle: { color: '#8892a4', fontFamily: 'Share Tech Mono' },    inactiveColor: '#334155'  },  // === 网格 ===  grid: {    left: '10%',    right: '10%',    top: '15%',    bottom: '10%',    containLabel: true  },  // === X轴 ===  xAxis: {    axisLine: { lineStyle: { color: 'rgba(255,255,255,0.1)' } },    axisTick: { show: false },    axisLabel: { color: '#8892a4', fontFamily: 'Share Tech Mono' },    splitLine: { lineStyle: { color: 'rgba(255,255,255,0.05)', type: 'dashed' } }  },  // === Y轴 ===  yAxis: {    axisLine: { lineStyle: { color: 'rgba(255,255,255,0.1)' } },    axisTick: { show: false },    axisLabel: { color: '#8892a4', fontFamily: 'Share Tech Mono' },    splitLine: { lineStyle: { color: 'rgba(255,255,255,0.05)', type: 'dashed' } }  },  // === 系列通用样式 ===  series: {    itemStyle: {      borderColor: '#000',      borderWidth: 1    },    lineStyle: {      width: 2,      shadowColor: '#00f2f1',      shadowBlur: 10    },    areaStyle: {      opacity: 0.3    }  }};// === SCADA 双轴专用配置 ===// 左轴：功率/电流（kW/A），右轴：温度/风速（°C/m/s）const scadaDualAxisConfig = {  tooltip: {    trigger: 'axis',    axisPointer: { type: 'cross' }  },  legend: { data: ['有功功率(kW)', '电流(A)', '温度(°C)', '风速(m/s)'] },  grid: { left: '10%', right: '15%', top: '15%', bottom: '15%', containLabel: true },  xAxis: {    type: 'time',    axisLine: { lineStyle: { color: 'rgba(255,255,255,0.1)' } },    axisLabel: { color: '#8892a4', formatter: '{HH}:{mm}:{ss}' }  },  yAxis: [    {      type: 'value',      name: '功率/电流',      nameTextStyle: { color: '#8892a4' },      axisLabel: { color: '#8892a4' },      splitLine: { lineStyle: { color: 'rgba(255,255,255,0.05)' } }    },    {      type: 'value',      name: '温度/风速',      nameTextStyle: { color: '#8892a4' },      axisLabel: { color: '#8892a4' },      splitLine: { show: false }    }  ],  series: [    {      name: '有功功率(kW)',      type: 'line',      yAxisIndex: 0,      smooth: true,      symbol: 'none',      lineStyle: { color: '#00f2f1', width: 2, shadowColor: '#00f2f1', shadowBlur: 8 },      areaStyle: {        color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [          { offset: 0, color: 'rgba(0, 242, 241, 0.3)' },          { offset: 1, color: 'rgba(0, 242, 241, 0)' }        ])      }    },    {      name: '电流(A)',      type: 'line',      yAxisIndex: 0,      smooth: true,      symbol: 'none',      lineStyle: { color: '#00c0ff', width: 2, shadowColor: '#00c0ff', shadowBlur: 8 }    },    {      name: '温度(°C)',      type: 'line',      yAxisIndex: 1,      smooth: true,      symbol: 'none',      lineStyle: { color: '#ffa022', width: 2, shadowColor: '#ffa022', shadowBlur: 8 }    },    {      name: '风速(m/s)',      type: 'line',      yAxisIndex: 1,      smooth: true,      symbol: 'none',      lineStyle: { color: '#00e676', width: 2, shadowColor: '#00e676', shadowBlur: 8 }    }  ]};// === Judge 五维度雷达图专用配置 ===// 五维度：证据充分性(25%)、推理逻辑性(25%)、安规合规性(20%)、可操作性(20%)、历史一致性(10%)const judgeRadarConfig = {  tooltip: { backgroundColor: 'rgba(10, 22, 40, 0.9)', borderColor: '#00f0ff', textStyle: { color: '#e0e6ed' } },  radar: {    indicator: [      { name: '证据充分性\n(25%)', max: 100 },      { name: '推理逻辑性\n(25%)', max: 100 },      { name: '安规合规性\n(20%)', max: 100 },      { name: '可操作性\n(20%)', max: 100 },      { name: '历史一致性\n(10%)', max: 100 }    ],    shape: 'polygon',    radius: '65%',    axisName: { color: '#8892a4', fontSize: 12, fontFamily: 'Share Tech Mono' },    splitArea: {      areaStyle: {        color: ['rgba(0, 240, 255, 0.02)', 'rgba(0, 240, 255, 0.05)']      }    },    splitLine: { lineStyle: { color: 'rgba(0, 240, 255, 0.2)' } },    axisLine: { lineStyle: { color: 'rgba(0, 240, 255, 0.2)' } }  },  series: [{    type: 'radar',    data: [{      value: [90, 88, 85, 82, 90],      name: '本次评分',      areaStyle: {        color: new echarts.graphic.RadialGradient(0.5, 0.5, 1, [          { offset: 0, color: 'rgba(0, 242, 241, 0.4)' },          { offset: 1, color: 'rgba(0, 242, 241, 0.1)' }        ])      },      lineStyle: { color: '#00f2f1', width: 2, shadowColor: '#00f2f1', shadowBlur: 10 },      itemStyle: { color: '#00f2f1', borderWidth: 2 },      symbol: 'circle',      symbolSize: 6    }]  }]};// === 仪表盘配置（设备状态概览） ===const gaugeConfig = {  series: [{    type: 'gauge',    radius: '80%',    axisLine: {      lineStyle: {        width: 10,        color: [          [0.3, '#00f2f1'],          [0.7, '#ffa022'],          [1, '#ff4d4f']        ]      }    },    pointer: { itemStyle: { color: '#00f2f1' } },    axisTick: { show: false },    splitLine: { show: false },    axisLabel: { color: '#8892a4', fontSize: 10 },    detail: {      formatter: '{value}%',      color: '#00f2f1',      fontSize: 20,      fontFamily: 'Orbitron'    },    data: [{ value: 85, name: '设备综合健康度' }]  }]};export { theme, scadaDualAxisConfig, judgeRadarConfig, gaugeConfig };


## 第四部分：Pinia 状态管理设计


### src/stores/chat.js — 会话与诊断状态

import { defineStore } from 'pinia'import { ref, computed } from 'vue'export const useChatStore = defineStore('chat', () => {  // === 状态 ===  const sessions = ref(new Map()) // sessionId -> sessionData  const currentSessionId = ref(null)  const isConnected = ref(false)  // === 计算属性 ===  const currentSession = computed(() => {    return currentSessionId.value ? sessions.value.get(currentSessionId.value) : null  })  const messageCount = computed(() => {    return currentSession.value?.messages?.length || 0  })  // === 方法 ===  function createSession(userId) {    const sessionId = 'session_' + Date.now()    const session = {      sessionId,      userId,      messages: [],      taskStatus: 'idle', // idle | thinking | analyzing | diagnosing | done | error      currentTaskId: null,      riskLevel: null, // CRITICAL | HIGH | MEDIUM | LOW      judgeScore: null,      createdAt: new Date().toISOString()    }    sessions.value.set(sessionId, session)    currentSessionId.value = sessionId    return session  }  function addMessage(sessionId, message) {    const session = sessions.value.get(sessionId)    if (session) {      session.messages.push({        ...message,        timestamp: new Date().toISOString()      })    }  }  function updateTaskStatus(sessionId, status) {    const session = sessions.value.get(sessionId)    if (session) {      session.taskStatus = status      // 根据状态更新 UI 提示      if (status === 'diagnosing') {        session.statusMessage = '正在进行综合诊断，请稍候...'      } else if (status === 'done') {        session.statusMessage = '诊断完成'      }    }  }  function setRiskLevel(sessionId, level) {    const session = sessions.value.get(sessionId)    if (session) {      session.riskLevel = level      // 高风险时触发 UI 警告      if (level === 'CRITICAL' || level === 'HIGH') {        showRiskAlert(level)      }    }  }  function setJudgeScore(sessionId, score, details) {    const session = sessions.value.get(sessionId)    if (session) {      session.judgeScore = score      session.judgeDetails = details    }  }  function showRiskAlert(level) {    // 触发全局告警通知    console.log(`[Risk Alert] ${level} risk level detected`)    // 可通过 EventBus 或 Pinia 事件总线通知其他组件  }  return {    sessions,    currentSessionId,    currentSession,    messageCount,    isConnected,    createSession,    addMessage,    updateTaskStatus,    setRiskLevel,    setJudgeScore  }})


### src/stores/alarm.js — 告警状态

import { defineStore } from 'pinia'import { ref } from 'vue'export const useAlarmStore = defineStore('alarm', () => {  const alarms = ref([])  const unreadCount = ref(0)  const isAlarmPanelOpen = ref(false)  // 告警级别优先级排序  const levelPriority = { critical: 4, high: 3, medium: 2, low: 1 }  function addAlarm(alarm) {    const formatted = {      ...alarm,      id: alarm.alarmId || 'alarm_' + Date.now(),      read: false,      receivedAt: new Date().toISOString(),      levelDisplay: alarm.severity || alarm.level    }    alarms.value.unshift(formatted)    alarms.value.sort((a, b) => levelPriority[b.levelDisplay] - levelPriority[a.levelDisplay])    unreadCount.value++    // 触发顶部告警浮层    if (formatted.levelDisplay === 'critical') {      triggerCriticalAlert(formatted)    }  }  function markAsRead(alarmId) {    const alarm = alarms.value.find(a => a.id === alarmId)    if (alarm) {      alarm.read = true      unreadCount.value = Math.max(0, unreadCount.value - 1)    }  }  function clearAll() {    alarms.value = []    unreadCount.value = 0  }  function triggerCriticalAlert(alarm) {    // 触发全屏红色呼吸告警    console.log(`[Critical Alarm] ${alarm.description}`)  }  return {    alarms,    unreadCount,    isAlarmPanelOpen,    addAlarm,    markAsRead,    clearAll  }})


### src/stores/device.js — 设备状态

import { defineStore } from 'pinia'import { ref } from 'vue'export const useDeviceStore = defineStore('device', () => {  const devices = ref(new Map()) // deviceId -> deviceData  const selectedDeviceId = ref(null)  const selectedDevice = computed(() => {    return selectedDeviceId.value ? devices.value.get(selectedDeviceId.value) : null  })  const onlineDevices = computed(() => {    return Array.from(devices.value.values()).filter(d => d.status === 'running')  })  const faultDevices = computed(() => {    return Array.from(devices.value.values()).filter(d => d.status === 'fault')  })  function updateDeviceStatus(deviceId, data) {    const existing = devices.value.get(deviceId)    if (existing) {      devices.value.set(deviceId, { ...existing, ...data, lastUpdated: new Date().toISOString() })    } else {      devices.value.set(deviceId, {        deviceId,        status: 'running',        temperature: 0,        vibration: 0,        power: 0,        voltage: 0,        current: 0,        frequency: 0,        ...data,        lastUpdated: new Date().toISOString()      })    }  }  function selectDevice(deviceId) {    selectedDeviceId.value = deviceId  }  return {    devices,    selectedDeviceId,    selectedDevice,    onlineDevices,    faultDevices,    updateDeviceStatus,    selectDevice  }})


## 第五部分：页面路由规划

完整的 10 个页面路由配置，覆盖技术文档中所有功能模块。


### src/router/index.js

import { createRouter, createWebHistory } from 'vue-router'import { useChatStore } from '@/stores/chat'const routes = [  {    path: '/',    name: 'Dashboard',    component: () => import('@/views/Dashboard.vue'),    meta: { title: '总览看板', requiresAuth: true }  },  {    path: '/diagnostic',    name: 'DiagnosticCenter',    component: () => import('@/views/DiagnosticCenter.vue'),    meta: { title: '智能诊断中心', requiresAuth: true }  },  {    path: '/scada',    name: 'SCADADashboard',    component: () => import('@/views/SCADADashboard.vue'),    meta: { title: 'SCADA 数据看板', requiresAuth: true }  },  {    path: '/alarms',    name: 'AlarmManagement',    component: () => import('@/views/AlarmManagement.vue'),    meta: { title: '告警管理', requiresAuth: true }  },  {    path: '/trace/:taskId',    name: 'DiagnosticTrace',    component: () => import('@/views/DiagnosticTrace.vue'),    meta: { title: '诊断过程透视', requiresAuth: true }  },  {    path: '/knowledge',    name: 'KnowledgeBase',    component: () => import('@/views/KnowledgeBase.vue'),    meta: { title: '知识库管理', requiresAuth: true }  },  {    path: '/devices',    name: 'DeviceStatus',    component: () => import('@/views/DeviceStatus.vue'),    meta: { title: '设备状态查询', requiresAuth: true }  },  {    path: '/feedback',    name: 'FeedbackCenter',    component: () => import('@/views/FeedbackCenter.vue'),    meta: { title: '反馈与学习', requiresAuth: true }  },  {    path: '/skills',    name: 'SkillManagement',    component: () => import('@/views/SkillManagement.vue'),    meta: { title: '技能管理', requiresAuth: true }  },  {    path: '/settings',    name: 'SystemSettings',    component: () => import('@/views/SystemSettings.vue'),    meta: { title: '系统设置', requiresAuth: true }  }]const router = createRouter({  history: createWebHistory(),  routes})// 全局路由守卫router.beforeEach((to, from, next) => {  const chatStore = useChatStore()  // 设置页面标题  document.title = `${to.meta.title} - 驭能智能诊断平台`  // 检查认证（简化版）  if (to.meta.requiresAuth) {    const token = localStorage.getItem('auth_token')    if (!token) {      next('/login')      return    }  }  // 检查后端健康状态  if (to.path === '/') {    fetch('/health')      .then(res => res.json())      .then(data => {        chatStore.isConnected = data.status === 'ok'      })      .catch(() => {        chatStore.isConnected = false      })  }  next()})export default router


## 第六部分：后端接口与前端组件映射总表

17 个后端 API 接口与前端组件的完整映射关系，确保每个接口都有对应的前端实现。

| 序号 | 接口名称 | 路径 | HTTP方法 | 前端组件 | 功能说明 |
| --- | --- | --- | --- | --- | --- |
| 1 | 对话接口 | /api/chat | POST | DiagnosticCenter.vue | 同步诊断，等待完整结果 |
| 2 | 流式对话 | /api/chat/stream | POST | useSSE.js + AiThinkingTerminal | SSE 实时推送诊断进度和内容 |
| 3 | 诊断接口 | /api/diagnose | POST | DiagnosticCenter.vue | 结构化诊断 + 置信度 |
| 4 | 流式诊断 | /api/diagnose/stream | POST | useSSE.js + ReportCard | 流式诊断 + 结构化诊断数据 |
| 5 | 告警接收 | /api/alarm/receive | POST | AlarmManagement.vue | 接收 SCADA 告警，返回 task_id |
| 6 | 告警诊断 | /api/alarm/diagnose | POST | AlarmManagement.vue | 告警触发自动诊断（SSE） |
| 7 | 诊断状态 | /api/alarm/diagnose/{id}/status | GET | AlarmManagement.vue | 查询诊断任务状态和进度 |
| 8 | 检查点查询 | /api/alarm/checkpoint/{id} | GET | DiagnosticTrace.vue | 查询诊断检查点（进度追踪） |
| 9 | 文档上传 | /api/knowledge/documents/upload | POST | KnowledgeBase.vue | 上传知识文档 |
| 10 | 知识搜索 | /api/knowledge/search/test | POST | KnowledgeBase.vue | 测试检索效果 + RRF 评分 |
| 11 | 诊断回放 | /api/trace/{id}/replay | GET | DiagnosticTrace.vue | 回放完整执行轨迹 |
| 12 | 用户反馈 | /api/feedback | POST | FeedbackPanel.vue | 提交诊断评价 + 修正意见 |
| 13 | SCADA 连接 | /api/scada/connect | POST | SCADADashboard.vue | 配置 SCADA 连接参数 |
| 14 | 工具列表 | /api/tools/list | GET | DeviceStatus.vue | 列出所有 MCP 工具 |
| 15 | 工具搜索 | /api/tools/search | GET | DeviceStatus.vue | 按关键词搜索工具 |
| 16 | 技能列表 | /api/skills | GET | SkillManagement.vue | 列出所有 Skill 及触发意图 |
| 17 | 健康检查 | /health | GET | AppHeader.vue | 检查服务健康状态 |


## 第七部分：开发路线图

四阶段 30 天详细计划，严格按照技术文档功能模块优先级排序。

| 阶段 | 天数 | 任务 | 交付物 | 对应技术文档章节 |
| --- | --- | --- | --- | --- |
| 第一阶段骨架搭建 | 第1-3天(3天) | 1. 项目初始化（npm create vue@latest + 所有依赖安装）2. 环境变量配置（.env.development / .env.production）3. Nginx 反向代理配置4. 全局 CSS 变量（variables.scss）5. .tech-card 通用类（半透明背景 + 模糊 + 角标）6. AppHeader.vue（标题 + 时间 + 系统状态 + 用户信息）7. Dashboard.vue 三栏 Grid 布局8. ParticleBackground.vue（Three.js 粒子背景）9. 全局动效（呼吸灯、fade-in、扫描线） | 全局样式系统基础布局框架粒子背景组件 | 1.4 技术栈总览1.5 部署模式2.1 六层架构 |
| 第二阶段静态可视化 | 第4-8天(5天) | 1. PowerBarChart.vue（24h 实时功率柱状图）2. EnergyTrendChart.vue（发电量趋势折线图）3. DeviceHealthRadar.vue（五维健康度雷达图）4. AlarmPieChart.vue（故障类型分布环形图）5. SCADATrendChart.vue（SCADA 双轴趋势 + 故障窗口高亮）6. JudgeRadarChart.vue（Judge 五维度雷达图）7. EnvironmentPanel.vue（环境监测面板）8. StatCard.vue（关键指标数字卡片）9. echartsTheme.js（完整主题配置）10. Dashboard.vue 填充所有图表占位 | 8个 ECharts 组件主题配置文件看板页面 | 4.1 SCADA数据连接器4.2 Judge Agent5.4 知识图谱覆盖 |
| 第三阶段AI 接入 | 第9-15天(7天) | 1. src/api/sse.js（SSE 客户端封装）2. src/hooks/useSSE.js（useSSE Hook）3. AiThinkingTerminal.vue（AI 思考终端，SSE 流式渲染）4. DiagnosisReportCard.vue（9项结构化诊断报告卡片）5. StepProgressBar.vue（步骤进度条）6. FeedbackPanel.vue（用户反馈面板）7. DiagnosticCenter.vue（智能诊断中心页面）8. 对接 /api/chat/stream 和 /api/diagnose/stream9. 对接 /api/feedback10. 多模态图片上传与标注（MultimodalAnnotator.vue） | SSE 客户端AI 终端组件诊断报告卡片诊断中心页面 | 3.4 主编排图流程3.5 Diagnosis子图4.3 多模态融合8.3 SSE流式协议 |
| 第四阶段高级功能 | 第16-25天(10天) | 1. SCADADashboard.vue（SCADA 数据看板页面）2. AlarmManagement.vue（告警管理页面）3. DiagnosticTrace.vue（诊断透视页面 + LangGraph拓扑）4. KnowledgeBase.vue（知识库管理页面）5. DeviceStatus.vue（设备状态查询页面）6. FeedbackCenter.vue（反馈与学习页面）7. SkillManagement.vue（技能管理页面）8. SystemSettings.vue（系统设置页面）9. LangGraphTopology.vue（LangGraph 拓扑可视化）10. AlarmAlertOverlay.vue（实时告警浮层）11. MemorySystemPanel.vue（三层记忆系统展示）12. ActiveLearningPanel.vue（主动学习状态面板）13. Pinia stores（chat/alarm/device）14. 路由规划（10个页面） | 7个核心页面5个高级组件状态管理路由配置 | 4.1 SCADA连接器4.2 Judge Agent4.3 多模态4.4 主动学习5 知识库RAG6 三层记忆7 MCP工具层8 API接口 |
| 第五阶段特效打磨 | 第26-30天(5天) | 1. 全局 CSS 动效增强（扫描线、呼吸灯、粒子优化）2. 响应式适配（大屏分辨率适配）3. 性能优化（图表虚拟滚动、SSE 连接池）4. 安全加固（XSS防护、敏感信息脱敏、高危操作二次确认）5. 降级策略（离线模式提示、网络故障处理）6. 端到端联调测试7. 代码审查与文档完善 | 动效增强性能优化安全加固联调测试 | 8.4 安全性设计9 完整数据流10 部署架构 |

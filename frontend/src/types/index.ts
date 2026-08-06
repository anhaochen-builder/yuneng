/** SSE 流式消息类型 */
export interface SSEMessage {
  type: 'start' | 'status' | 'content' | 'diagnosis' | 'done' | 'error'
  data?: SSEData
}

export interface SSEData {
  message?: string
  text?: string
  task_id?: string
  report?: DiagnosisReport
  confidence?: number
  risk_level?: string
}

/** 诊断报告 */
export interface DiagnosisReport {
  task_id: string
  report_text: string
  confidence: number
  root_cause: string
  risk_level: 'CRITICAL' | 'HIGH' | 'MEDIUM' | 'LOW'
  source: string
  matched_cases: number
  evidence_summary?: string
}

/** 告警 */
export interface Alarm {
  id: string
  alarmId: string
  device_id: string
  alarm_type: string
  alarm_level: string
  levelDisplay: string
  message: string
  current_value?: string
  threshold?: string
  status: 'active' | 'cleared' | 'acknowledged'
  read: boolean
  receivedAt: string
  timestamp?: string
  risk_level?: string
  report?: string
}

/** 设备 */
export interface Device {
  device_id: string
  device_type: string
  device_name: string
  status: 'running' | 'warning' | 'fault' | 'stopped'
  parameters: Record<string, number>
  lastUpdated?: string
}

/** 会话消息 */
export interface ChatMessage {
  role: 'user' | 'assistant' | 'system'
  content: string
  timestamp: string
  metadata?: Record<string, unknown>
}

/** 会话 */
export interface ChatSession {
  sessionId: string
  userId: string
  messages: ChatMessage[]
  taskStatus: 'idle' | 'diagnosing' | 'completed' | 'failed'
  currentTaskId: string | null
  riskLevel: string | null
  judgeScore: number | null
  createdAt: string
}

/** 通用 API 响应 */
export interface ApiResponse<T = unknown> {
  code: number
  data: T
  message: string
}

/** 分页 */
export interface PaginatedData<T = unknown> {
  items: T[]
  total: number
  page: number
  page_size: number
}

/** 告警接收请求 */
export interface AlarmReceivePayload {
  alarm_id: string
  device_id: string
  station?: string
  device_name?: string
  device_type?: string
  alarm_type?: string
  alarm_level?: string
  level?: string
  message?: string
  alarm_message?: string
  current_value?: string
  threshold?: string
  duration?: string
  auto_diagnose?: boolean
}

/** SCADA 连接配置 */
export interface ScadaConnectConfig {
  device_id: string
  device_type: string
  protocol?: string
  host?: string
  port?: number
  mock_mode?: boolean
}

/** 反馈 */
export interface FeedbackPayload {
  task_id: string
  rating: 'accurate' | 'partially_accurate' | 'inaccurate'
  comment?: string
  corrected_root_cause?: string
}

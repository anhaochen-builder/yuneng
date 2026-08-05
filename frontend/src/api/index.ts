import axios from 'axios'
import { autoMask } from '@/utils/mask'

const http = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || '',
  timeout: 120000,
})

http.interceptors.response.use(
  (resp) => {
    const body = resp.data
    if (body && typeof body === 'object' && 'code' in body && 'data' in body) {
      return { ...resp, data: autoMask(body.data) }
    }
    return resp
  },
  (err) => Promise.reject(err)
)

export default http

// ─── API 接口 ───

export const healthCheck = () => http.get('/health')

export const chatApi = {
  send: (question: string, sessionId?: string) =>
    http.post('/api/chat', { question, session_id: sessionId }),
  stream: (question: string, sessionId?: string) =>
    fetch(`${import.meta.env.VITE_API_BASE_URL || ''}/api/chat/stream`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ question, session_id: sessionId }),
    }),
  clear: () => http.post('/api/chat/clear', {}),
}

export const diagnoseApi = {
  diagnose: (symptoms: string, deviceId?: string, sessionId?: string) =>
    http.post('/api/diagnose', { symptoms, device_id: deviceId, session_id: sessionId }),
  stream: (symptoms: string, deviceId?: string, sessionId?: string) =>
    fetch(`${import.meta.env.VITE_API_BASE_URL || ''}/api/diagnose/stream`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ symptoms, device_id: deviceId, session_id: sessionId }),
    }),
  multimodal: (symptoms: string, deviceId?: string) =>
    http.post('/api/diagnose/multimodal', { symptoms, device_id: deviceId }),
  multimodalStream: (symptoms: string, deviceId?: string) =>
    fetch(`${import.meta.env.VITE_API_BASE_URL || ''}/api/diagnose/multimodal/stream`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ symptoms, device_id: deviceId }),
    }),
  history: () => http.get('/api/diagnose/history'),
  report: (taskId: string) => http.get(`/api/diagnose/report/${taskId}`),
}

export const alarmApi = {
  health: () => http.get('/api/alarm/health'),
  receive: (payload: Record<string, any>) => http.post('/api/alarm/receive', payload),
  diagnose: (alarmDescription: string, taskId?: string) =>
    http.post('/api/alarm/diagnose', { alarmDescription, taskId }),
  status: (taskId: string) => http.get(`/api/alarm/diagnose/${taskId}/status`),
  checkpoint: (taskId: string) => http.get(`/api/alarm/checkpoint/${taskId}`),
}

export const knowledgeApi = {
  search: (query: string, topK = 5) =>
    http.post('/api/knowledge/search/test', { query, top_k: topK }),
  upload: (formData: FormData) =>
    http.post('/api/knowledge/documents/upload', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    }),
  health: () => http.get('/api/knowledge/health'),
}

export const scadaApi = {
  health: () => http.get('/api/scada/health'),
  connect: (config: Record<string, any>) => http.post('/api/scada/connect', config),
  disconnect: (deviceId: string) => http.post(`/api/scada/disconnect/${deviceId}`),
  data: (deviceId: string) => http.get(`/api/scada/data/${deviceId}`),
  window: (deviceId: string) => http.get(`/api/scada/data/${deviceId}/window`),
  bufferStats: () => http.get('/api/scada/buffer/stats'),
  devices: () => http.get('/api/scada/devices'),
}

export const feedbackApi = {
  submit: (taskId: string, rating: string, comment?: string, correctedRootCause?: string) =>
    http.post('/api/feedback', { task_id: taskId, rating, comment, corrected_root_cause: correctedRootCause }),
  stats: () => http.get('/api/feedback/stats'),
}

export const traceApi = {
  replay: (taskId: string) => http.get(`/api/trace/${taskId}/replay`),
}

export const dashboardApi = {
  overview: () => http.get('/api/dashboard'),
  phases: () => http.get('/api/dashboard/phases'),
  phaseDetail: (phaseId: string) => http.get(`/api/dashboard/phases/${phaseId}`),
  tasks: (status?: string) => http.get(`/api/dashboard/tasks${status ? `?status=${status}` : ''}`),
  mode: () => http.get('/api/dashboard/mode'),
}

export const auditApi = {
  overview: () => http.get('/api/audit'),
  skills: () => http.get('/api/audit/skills'),
  files: () => http.get('/api/audit/files'),
  imports: () => http.get('/api/audit/imports'),
}

export const toolsApi = {
  list: () => http.get('/api/tools/list'),
  search: (keyword: string) => http.get(`/api/tools/search?keyword=${encodeURIComponent(keyword)}`),
}

export const skillsApi = {
  list: () => http.get('/api/skills'),
}

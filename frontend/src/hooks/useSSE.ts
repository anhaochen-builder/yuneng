import { ref } from 'vue'
import type { SSEMessage, DiagnosisReport } from '@/types'

export function useSSE() {
  const messages = ref<SSEMessage[]>([])
  const isStreaming = ref(false)
  const currentStep = ref('')
  const streamedContent = ref('')
  const diagnosisReport = ref<DiagnosisReport | null>(null)
  const error = ref<string | null>(null)
  let abortCtrl: AbortController | null = null

  async function sendMessage(url: string, body: Record<string, unknown>, retryCount = 0) {
    isStreaming.value = true
    streamedContent.value = ''
    diagnosisReport.value = null
    error.value = null
    messages.value = []

    abortCtrl = new AbortController()
    try {
      const resp = await fetch(url, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
        signal: abortCtrl.signal,
      })

      if (!resp.ok) {
        error.value = `请求失败: ${resp.status} ${resp.statusText}`
        return
      }

      const reader = resp.body?.getReader()
      if (!reader) { error.value = '无法读取响应流'; return }
      const decoder = new TextDecoder()
      let buffer = ''

      while (true) {
        const { done, value } = await reader.read()
        if (done) break
        buffer += decoder.decode(value, { stream: true })
        const lines = buffer.split('\n')
        buffer = lines.pop() || ''

        for (const line of lines) {
          if (!line.startsWith('data: ')) continue
          const raw = line.slice(6).trim()
          if (!raw || raw === '[DONE]') continue
          try {
            const msg: SSEMessage = JSON.parse(raw)
            messages.value.push(msg)
            if (msg.type === 'status') currentStep.value = msg.data?.message || ''
            if (msg.type === 'content') streamedContent.value += msg.data?.text || ''
            if (msg.type === 'diagnosis') diagnosisReport.value = msg.data as unknown as DiagnosisReport
          } catch {
            // 忽略非 JSON 行
          }
        }
      }
    } catch (e: unknown) {
      if (e instanceof DOMException && e.name === 'AbortError') return
      const message = e instanceof Error ? e.message : String(e)
      error.value = message

      // 自动重连（最多 3 次）
      if (retryCount < 3 && !abortCtrl?.signal.aborted) {
        isStreaming.value = false
        await new Promise(resolve => setTimeout(resolve, 1000 * (retryCount + 1)))
        await sendMessage(url, body, retryCount + 1)
      }
    } finally {
      isStreaming.value = false
    }
  }

  function abort() { abortCtrl?.abort(); isStreaming.value = false }

  return { messages, isStreaming, currentStep, streamedContent, diagnosisReport, error, sendMessage, abort }
}

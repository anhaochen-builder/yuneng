import { ref } from 'vue'

export interface SSEMessage {
  type: 'start' | 'status' | 'content' | 'diagnosis' | 'done' | 'error'
  data: any
}

export function useSSE() {
  const messages = ref<SSEMessage[]>([])
  const isStreaming = ref(false)
  const currentStep = ref('')
  const streamedContent = ref('')
  const diagnosisReport = ref<any>(null)
  const error = ref<string | null>(null)
  let abortCtrl: AbortController | null = null

  async function sendMessage(url: string, body: Record<string, any>) {
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
            if (msg.type === 'status') currentStep.value = msg.data?.message || msg.data || ''
            if (msg.type === 'content') streamedContent.value += msg.data?.text || ''
            if (msg.type === 'diagnosis') diagnosisReport.value = msg.data
          } catch {}
        }
      }
    } catch (e: any) {
      if (e.name !== 'AbortError') error.value = e.message
    } finally {
      isStreaming.value = false
    }
  }

  function abort() { abortCtrl?.abort(); isStreaming.value = false }

  return { messages, isStreaming, currentStep, streamedContent, diagnosisReport, error, sendMessage, abort }
}

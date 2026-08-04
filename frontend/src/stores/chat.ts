import { defineStore } from 'pinia'
import { ref, computed } from 'vue'

export const useChatStore = defineStore('chat', () => {
  const sessions = ref<Map<string, any>>(new Map())
  const currentSessionId = ref<string | null>(null)
  const isConnected = ref(false)

  const currentSession = computed(() =>
    currentSessionId.value ? sessions.value.get(currentSessionId.value) : null
  )
  const messageCount = computed(() => currentSession.value?.messages?.length || 0)

  function createSession(userId = 'operator') {
    const sessionId = 'session_' + Date.now()
    sessions.value.set(sessionId, {
      sessionId, userId, messages: [],
      taskStatus: 'idle', currentTaskId: null, riskLevel: null,
      judgeScore: null, createdAt: new Date().toISOString(),
    })
    currentSessionId.value = sessionId
    return sessions.value.get(sessionId)
  }

  function addMessage(sessionId: string, message: any) {
    const s = sessions.value.get(sessionId)
    if (s) s.messages.push({ ...message, timestamp: new Date().toISOString() })
  }

  function updateTaskStatus(sessionId: string, status: string) {
    const s = sessions.value.get(sessionId)
    if (s) s.taskStatus = status
  }

  return { sessions, currentSessionId, currentSession, messageCount, isConnected, createSession, addMessage, updateTaskStatus }
}, { persist: true })

import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import type { ChatSession, ChatMessage } from '@/types'

export const useChatStore = defineStore('chat', () => {
  const sessions = ref<Map<string, ChatSession>>(new Map())
  const currentSessionId = ref<string | null>(null)
  const isConnected = ref(false)

  const currentSession = computed(() =>
    currentSessionId.value ? sessions.value.get(currentSessionId.value) ?? null : null
  )
  const messageCount = computed(() => currentSession.value?.messages?.length ?? 0)

  function createSession(userId = 'operator'): ChatSession {
    const sessionId = 'session_' + Date.now()
    const session: ChatSession = {
      sessionId, userId, messages: [],
      taskStatus: 'idle', currentTaskId: null, riskLevel: null,
      judgeScore: null, createdAt: new Date().toISOString(),
    }
    sessions.value.set(sessionId, session)
    currentSessionId.value = sessionId
    return session
  }

  function addMessage(sessionId: string, message: ChatMessage) {
    const s = sessions.value.get(sessionId)
    if (s) s.messages.push({ ...message, timestamp: new Date().toISOString() })
  }

  function updateTaskStatus(sessionId: string, status: ChatSession['taskStatus']) {
    const s = sessions.value.get(sessionId)
    if (s) s.taskStatus = status
  }

  return { sessions, currentSessionId, currentSession, messageCount, isConnected, createSession, addMessage, updateTaskStatus }
}, { persist: true })

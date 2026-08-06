import { defineStore } from 'pinia'
import { ref } from 'vue'

export const useAuthStore = defineStore('auth', () => {
  const isLoggedIn = ref(!!localStorage.getItem('yuneng_token'))
  const username = ref(localStorage.getItem('yuneng_user') || '')
  const role = ref(localStorage.getItem('yuneng_role') || 'operator')

  function login(user: string, token?: string) {
    isLoggedIn.value = true
    username.value = user
    localStorage.setItem('yuneng_auth', '1')
    localStorage.setItem('yuneng_user', user)
    if (token) localStorage.setItem('yuneng_token', token)
  }

  function logout() {
    isLoggedIn.value = false
    username.value = ''
    role.value = 'operator'
    localStorage.removeItem('yuneng_auth')
    localStorage.removeItem('yuneng_user')
    localStorage.removeItem('yuneng_token')
    localStorage.removeItem('yuneng_role')
  }

  function getToken(): string | null {
    return localStorage.getItem('yuneng_token')
  }

  return { isLoggedIn, username, role, login, logout, getToken }
})

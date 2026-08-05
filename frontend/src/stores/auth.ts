import { defineStore } from 'pinia'
import { ref } from 'vue'

export const useAuthStore = defineStore('auth', () => {
  const isLoggedIn = ref(!!localStorage.getItem('yuneng_auth'))
  const username = ref(localStorage.getItem('yuneng_user') || '')

  function login(user: string) {
    isLoggedIn.value = true
    username.value = user
    localStorage.setItem('yuneng_auth', '1')
    localStorage.setItem('yuneng_user', user)
  }

  function logout() {
    isLoggedIn.value = false
    username.value = ''
    localStorage.removeItem('yuneng_auth')
    localStorage.removeItem('yuneng_user')
  }

  return { isLoggedIn, username, login, logout }
})

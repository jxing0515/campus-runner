import { defineStore } from 'pinia'
import { authApi } from '../api/request'

const read = (k, d = null) => {
  try {
    return JSON.parse(localStorage.getItem(k)) || d
  } catch {
    return d
  }
}

export const useAuthStore = defineStore('auth', {
  state: () => ({
    access: localStorage.getItem('access_token') || '',
    refresh: localStorage.getItem('refresh_token') || '',
    user: read('admin_user'),
  }),
  getters: {
    isLogin: (s) => !!s.access,
    isSuper: (s) => s.user?.role === 'super_admin',
  },
  actions: {
    setLogin(d) {
      this.access = d.access
      this.refresh = d.refresh
      this.user = d.user
      localStorage.setItem('access_token', d.access)
      localStorage.setItem('refresh_token', d.refresh)
      localStorage.setItem('admin_user', JSON.stringify(d.user))
    },
    async loadMe() {
      this.user = await authApi.me()
      localStorage.setItem('admin_user', JSON.stringify(this.user))
      return this.user
    },
    async logout() {
      try {
        await authApi.logout(this.refresh)
      } catch {
        /* 忽略登出失败 */
      }
      this.access = ''
      this.refresh = ''
      this.user = null
      localStorage.removeItem('access_token')
      localStorage.removeItem('refresh_token')
      localStorage.removeItem('admin_user')
    },
  },
})

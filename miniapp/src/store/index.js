import { reactive, computed } from 'vue'

const AUTH_KEY = 'mini_auth'

export const state = reactive({
  access: '',
  refresh: '',
  user: null,
})

// 学生/跑腿员同一账号，is_runner 控制跑腿员入口
export const isRunner = computed(() => !!state.user?.is_runner)
export const certStatus = computed(() => state.user?.cert_status || 'none')
export const isLogged = computed(() => !!state.access)

export function hydrate() {
  const saved = uni.getStorageSync(AUTH_KEY)
  if (saved && saved.access) Object.assign(state, saved)
}

export function saveAuth({ access, refresh, user }) {
  if (access) state.access = access
  if (refresh) state.refresh = refresh
  if (user) state.user = user
  uni.setStorageSync(AUTH_KEY, { access: state.access, refresh: state.refresh, user: state.user })
}

export function setUser(user) {
  if (user) saveAuth({ user })
}

export function getToken() {
  return state.access
}

export function clearAuth() {
  state.access = ''
  state.refresh = ''
  state.user = null
  uni.removeStorageSync(AUTH_KEY)
}

export function toLogin() {
  clearAuth()
  uni.reLaunch({ url: '/pages/login/login' })
}

export default { state, isRunner, certStatus, isLogged, hydrate, saveAuth, setUser, getToken, clearAuth, toLogin }

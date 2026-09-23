import axios from 'axios'
import { ElMessage } from 'element-plus'

export const http = axios.create({ baseURL: '/api/v1', timeout: 20000 })

http.interceptors.request.use((cfg) => {
  const token = localStorage.getItem('access_token')
  if (token && !cfg.url.includes('/auth/refresh')) cfg.headers.Authorization = `Bearer ${token}`
  return cfg
})

const AuthAPI = {
  login: (d) => http.post('/auth/login', d),
  refresh: (refresh) => http.post('/auth/refresh', { refresh }),
}
const csv = (url, params) => http({ url, method: 'get', params, responseType: 'blob' })

let refreshing = null

function toLogin() {
  localStorage.removeItem('access_token')
  localStorage.removeItem('refresh_token')
  localStorage.removeItem('admin_user')
  if (!location.hash.startsWith('#/login')) location.hash = '#/login'
}

http.interceptors.response.use(
  async (res) => {
    const cfg = res.config
    // 二进制导出（CSV）直接透传
    if (cfg.responseType === 'blob') {
      if ((res.data.type || '').includes('json')) throw new Error((await res.data.text()) || '导出失败')
      return res.data
    }
    const body = res.data
    if (body && typeof body === 'object' && 'code' in body) {
      if (body.code === 0) return body.data
      if (body.code === 40100) {
        if (cfg.url.includes('/auth/refresh') || cfg._retried || !localStorage.getItem('refresh_token')) {
          toLogin()
          return Promise.reject(new Error(body.message || '登录已过期'))
        }
        cfg._retried = true
        try {
          refreshing =
            refreshing ||
            AuthAPI.refresh(localStorage.getItem('refresh_token')).then((d) => {
              localStorage.setItem('access_token', d.access)
              return d.access
            })
          const access = await refreshing
          cfg.headers.Authorization = `Bearer ${access}`
          return http(cfg)
        } catch {
          toLogin()
          return Promise.reject(new Error('登录已过期，请重新登录'))
        } finally {
          refreshing = null
        }
      }
      ElMessage.error(body.message || `请求失败(${body.code})`)
      return Promise.reject(new Error(body.message || 'error'))
    }
    return body
  },
  (err) => {
    ElMessage.error(err.message || '网络异常，请稍后重试')
    return Promise.reject(err)
  },
)

const get = (url, params) => http.get(url, { params })
const post = (url, data) => http.post(url, data)
const put = (url, data) => http.put(url, data)
const del = (url) => http.delete(url)

export const authApi = {
  login: (d) => AuthAPI.login(d),
  me: () => get('/auth/me'),
  logout: (refresh) => post('/auth/logout', { refresh }),
}

export const adminApi = {
  // 看板
  statsOverview: (p) => get('/admin/stats/overview', p),
  ordersTrend: (days) => get('/admin/stats/orders-trend', { days }),
  creditDistribution: () => get('/admin/stats/credit-distribution'),
  // 认证审核
  certifications: (p) => get('/admin/certifications', p),
  auditCertification: (id, d) => post(`/admin/certifications/${id}/audit`, d),
  // 用户
  users: (p) => get('/admin/users', p),
  banUser: (id, d) => post(`/admin/users/${id}/ban`, d),
  creditUser: (id, d) => post(`/admin/users/${id}/credit`, d),
  // 需求 / 订单
  demands: (p) => get('/admin/demands', p),
  orders: (p) => get('/admin/orders', p),
  order: (orderNo) => get(`/admin/orders/${orderNo}`),
  resolveOrder: (orderNo, d) => post(`/admin/orders/${orderNo}/resolve`, d),
  // 资金
  fundFlows: (p) => get('/admin/fund-flows', p),
  exportFundFlows: (p) => csv('/admin/fund-flows/export', p),
  escrow: () => get('/admin/escrow'),
  settlements: (p) => get('/admin/settlements', p),
  refunds: (p) => get('/admin/refunds', p),
  // 提现
  withdrawals: (p) => get('/admin/withdrawals', p),
  auditWithdrawal: (id, d) => post(`/admin/withdrawals/${id}/audit`, d),
  // 规则
  rules: (p) => get('/admin/rules', p),
  createRule: (d) => post('/admin/rules', d),
  updateRule: (id, d) => put(`/admin/rules/${id}`, d),
  // 仲裁
  appeals: (p) => get('/admin/appeals', p),
  arbitrate: (id, d) => post(`/admin/appeals/${id}/arbitrate`, d),
  // 公告
  announcements: (p) => get('/admin/announcements', p),
  createAnnouncement: (d) => post('/admin/announcements', d),
  deleteAnnouncement: (id) => del(`/admin/announcements/${id}`),
  // 操作日志
  operationLogs: (p) => get('/admin/operation-logs', p),
  exportOperationLogs: (p) => csv('/admin/operation-logs/export', p),
}

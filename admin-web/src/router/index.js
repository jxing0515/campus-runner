import { createRouter, createWebHashHistory } from 'vue-router'
import { menus } from './menus'

const routes = [
  { path: '/login', name: 'login', component: () => import('../views/Login.vue') },
  {
    path: '/',
    component: () => import('../layout/Layout.vue'),
    redirect: '/dashboard',
    children: [
      { path: 'dashboard', component: () => import('../views/Dashboard.vue') },
      { path: 'certifications', component: () => import('../views/Certifications.vue') },
      { path: 'users', component: () => import('../views/Users.vue') },
      { path: 'demands', component: () => import('../views/Demands.vue') },
      { path: 'orders', component: () => import('../views/Orders.vue') },
      { path: 'fund-flows', component: () => import('../views/FundFlows.vue') },
      { path: 'escrow', component: () => import('../views/Escrow.vue') },
      { path: 'settlements', component: () => import('../views/Settlements.vue') },
      { path: 'refunds', component: () => import('../views/Refunds.vue') },
      { path: 'withdrawals', component: () => import('../views/Withdrawals.vue') },
      { path: 'rules', component: () => import('../views/Rules.vue') },
      { path: 'appeals', component: () => import('../views/Appeals.vue') },
      { path: 'stats', component: () => import('../views/Stats.vue') },
      { path: 'announcements', component: () => import('../views/Announcements.vue') },
      { path: 'logs', component: () => import('../views/Logs.vue') },
    ],
  },
  { path: '/:pathMatch(.*)*', redirect: '/dashboard' },
]

const router = createRouter({ history: createWebHashHistory(), routes })

router.beforeEach((to) => {
  const token = localStorage.getItem('access_token')
  if (to.path === '/login') return token ? { path: '/dashboard' } : true
  if (!token) return { path: '/login', query: { redirect: to.fullPath } }
  return true
})

router.afterEach((to) => {
  const hit = menus.find((m) => to.path.startsWith(m.path))
  document.title = hit ? `${hit.title} · 管理后台` : '管理后台'
})

export default router

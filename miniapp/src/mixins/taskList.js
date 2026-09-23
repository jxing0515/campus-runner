/**
 * 跑腿员任务列表的公共逻辑：分页 + 排序 + 接单
 * 供「待接单大厅」(available) 与「我的任务」(mine) 复用
 */
import orderApi from '../api/order'
import store from '../store'

export function createTaskList({ source = 'available', pageSize = 20 } = {}) {
  return {
    data() {
      return { list: [], page: 1, count: 0, loading: false, sort: 'time' }
    },
    methods: {
      async fetch(append = false) {
        if (this.loading) return
        this.loading = true
        try {
          const params = { page: this.page, page_size: pageSize }
          let res
          if (source === 'available') {
            params.sort = this.sort
            res = await orderApi.availableOrders(params)
          } else {
            params.role = 'runner'
            res = await orderApi.myOrders(params)
          }
          const results = res?.results || res || []
          this.count = res?.count || results.length
          this.list = append ? this.list.concat(results) : results
        } catch (e) {
          /* 已 toast */
        } finally {
          this.loading = false
        }
      },
      async accept(order) {
        const user = store.state.user
        if (!user?.is_runner || user.cert_status !== 'approved') {
          return uni.showModal({
            title: '需要先认证',
            content: '接单前请先完成跑腿员认证',
            confirmText: '去认证',
            success: (r) => r.confirm && uni.navigateTo({ url: '/pages/runner/certification' }),
          })
        }
        try {
          await orderApi.acceptOrder(order.order_no)
          uni.showToast({ title: '接单成功', icon: 'success' })
          setTimeout(() => uni.navigateTo({ url: `/pages/runner/task-detail?order_no=${order.order_no}` }), 500)
          this.page = 1
          this.fetch()
        } catch (e) {
          /* 400/409 已 toast */
        }
      },
      goDetail(order) {
        uni.navigateTo({ url: `/pages/runner/task-detail?order_no=${order.order_no}` })
      },
    },
  }
}

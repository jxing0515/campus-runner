<template>
  <view class="page">
    <scroll-view scroll-x class="filters">
      <view class="filter-row">
        <text
          v-for="f in filters"
          :key="f.value"
          :class="['chip', status === f.value && 'on']"
          @click="switchStatus(f.value)"
        >
          {{ f.label }}
        </text>
      </view>
    </scroll-view>

    <view v-if="!list.length && !loading" class="empty muted">暂无订单</view>
    <OrderCard
      v-for="o in list"
      :key="o.order_no"
      :order="o"
      :status-map="statusMap"
      @tap="detail"
    >
      <view class="actions">
        <button v-if="o.status === 'pending_pay'" size="mini" class="btn-primary" @click.stop="goPay(o)">去支付</button>
        <button v-if="['pending_accept', 'accepted'].includes(o.status)" size="mini" @click.stop="cancel(o)">取消</button>
        <button v-if="o.status === 'pending_confirm'" size="mini" class="btn-primary" @click.stop="confirm(o)">确认完成</button>
        <button v-if="o.status === 'completed'" size="mini" @click.stop="review(o)">评价</button>
        <button v-if="['completed', 'abnormal', 'refunded'].includes(o.status)" size="mini" @click.stop="appeal(o)">申诉</button>
      </view>
    </OrderCard>

    <view class="muted foot" v-if="list.length">{{ loading ? '加载中…' : '已加载全部' }}</view>
  </view>
</template>

<script>
import OrderCard from '../../components/OrderCard.vue'
import orderApi from '../../api/order'
import { ORDER_STATUS } from '../../utils/config'

const POLL_MS = 5000

export default {
  components: { OrderCard },
  data() {
    return {
      statusMap: ORDER_STATUS,
      status: '',
      list: [],
      page: 1,
      count: 0,
      loading: false,
      timer: null,
      filters: [
        { label: '全部', value: '' },
        ...Object.entries(ORDER_STATUS).map(([value, label]) => ({ value, label })),
      ],
    }
  },
  onLoad(options) {
    if (options.status) this.status = options.status
  },
  onShow() {
    this.page = 1
    this.fetch()
    this.startPolling()
  },
  onHide() {
    this.stopPolling()
  },
  onUnload() {
    this.stopPolling()
  },
  onReachBottom() {
    if (this.list.length < this.count) {
      this.page += 1
      this.fetch(true)
    }
  },
  onPullDownRefresh() {
    this.page = 1
    this.fetch().finally(uni.stopPullDownRefresh)
  },
  methods: {
    startPolling() {
      this.stopPolling()
      // 页面可见时 5s 轮询
      this.timer = setInterval(() => {
        this.page = 1
        this.fetch()
      }, POLL_MS)
    },
    stopPolling() {
      if (this.timer) clearInterval(this.timer)
      this.timer = null
    },
    switchStatus(v) {
      this.status = v
      this.page = 1
      this.list = []
      this.fetch()
    },
    async fetch(append = false) {
      if (this.loading) return
      this.loading = true
      try {
        const params = { role: 'student', page: this.page, page_size: 20 }
        if (this.status) params.status = this.status
        const res = await orderApi.myOrders(params)
        const results = res?.results || []
        this.count = res?.count || results.length
        this.list = append ? this.list.concat(results) : results
      } catch (e) {
        /* 已 toast */
      } finally {
        this.loading = false
      }
    },
    detail(o) {
      uni.navigateTo({ url: `/pages/student/order-detail?order_no=${o.order_no}` })
    },
    goPay(o) {
      uni.navigateTo({ url: `/pages/student/pay?order_no=${o.order_no}` })
    },
    review(o) {
      uni.navigateTo({ url: `/pages/student/review?order_no=${o.order_no}` })
    },
    appeal(o) {
      uni.navigateTo({ url: `/pages/student/appeal?order_no=${o.order_no}` })
    },
    async confirm(o) {
      const r = await new Promise((res) => uni.showModal({ title: '确认完成', content: '确认后酬金结算给跑腿员', success: (x) => res(x.confirm) }))
      if (!r) return
      try {
        await orderApi.confirmOrder(o.order_no)
        uni.showToast({ title: '已确认完成', icon: 'success' })
        this.fetch()
      } catch (e) {
        /* 已 toast */
      }
    },
    async cancel(o) {
      const r = await new Promise((res) => uni.showModal({ title: '取消订单', editable: true, placeholderText: '请输入取消原因', success: (x) => res(x) }))
      if (!r.confirm) return
      try {
        await orderApi.cancelOrder(o.order_no, r.content || '用户取消')
        uni.showToast({ title: '已取消', icon: 'success' })
        this.fetch()
      } catch (e) {
        /* 已 toast */
      }
    },
  },
}
</script>

<style scoped>
.filters {
  white-space: nowrap;
  background: #fff;
}
.filter-row {
  display: inline-flex;
  padding: 16rpx;
}
.chip {
  padding: 10rpx 26rpx;
  margin-right: 14rpx;
  border-radius: 100rpx;
  background: #f2f3f5;
  color: #606266;
  font-size: 26rpx;
}
.chip.on {
  background: #2979ff;
  color: #fff;
}
.actions {
  display: flex;
  justify-content: flex-end;
  gap: 16rpx;
  margin-top: 16rpx;
}
.empty {
  text-align: center;
  padding: 120rpx 0;
}
.foot {
  text-align: center;
  padding: 30rpx;
}
</style>

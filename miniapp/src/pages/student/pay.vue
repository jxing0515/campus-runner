<template>
  <view class="page">
    <view class="banner">模拟资金，无真实交易</view>

    <view class="card">
      <view class="row"><text class="muted">订单号</text><text>{{ order.order_no }}</text></view>
      <view class="row gap"><text class="muted">需求</text><text class="right">{{ order.description }}</text></view>
      <view class="row gap"><text class="muted">状态</text><text>{{ statusText }}</text></view>

      <view class="split"></view>
      <view class="row"><text class="muted">跑腿酬金</text><text>¥{{ order.runner_fee }}</text></view>
      <view class="row gap" v-if="order.item_fee_mode !== 'none'">
        <text class="muted">物品费（{{ order.item_fee_mode === 'platform' ? '平台代付' : '线下代付' }}）</text>
        <text>¥{{ order.item_fee_estimate }}</text>
      </view>
      <view class="row gap total">
        <text>应付合计</text>
        <text class="amount">¥{{ total }}</text>
      </view>
    </view>

    <view class="card muted">
      点击支付按钮后由后端将订单置为「待接单」，请求带 Idempotency-Key 保证幂等，重复点击不会重复扣款（本页不产生任何真实资金流水）。
    </view>

    <view class="footer">
      <button class="btn-primary" :loading="loading" :disabled="order.status !== 'pending_pay'" @click="pay">
        {{ order.status === 'pending_pay' ? '模拟支付' : '当前状态不可支付' }}
      </button>
      <button class="ghost gap" @click="goDetail">查看订单详情</button>
    </view>
  </view>
</template>

<script>
import orderApi from '../../api/order'
import { ORDER_STATUS } from '../../utils/config'

export default {
  data() {
    return { orderNo: '', order: {}, loading: false, idemKey: '' }
  },
  computed: {
    statusText() {
      return ORDER_STATUS[this.order.status] || this.order.status || '--'
    },
    total() {
      const runner = Number(this.order.runner_fee || 0)
      const item = this.order.item_fee_mode === 'none' ? 0 : Number(this.order.item_fee_estimate || 0)
      return (runner + item).toFixed(2)
    },
  },
  onLoad(options) {
    this.orderNo = options.order_no
    this.idemKey = `pay-${this.orderNo}-${Date.now()}`
    this.load()
  },
  methods: {
    async load() {
      try {
        this.order = await orderApi.orderDetail(this.orderNo)
      } catch (e) {
        /* 已 toast */
      }
    },
    async pay() {
      this.loading = true
      try {
        await orderApi.payOrder(this.orderNo, this.idemKey)
        uni.showToast({ title: '模拟支付成功', icon: 'success' })
        await this.load()
        setTimeout(() => this.goDetail(), 500)
      } catch (e) {
        /* 已 toast */
      } finally {
        this.loading = false
      }
    },
    goDetail() {
      uni.redirectTo({ url: `/pages/student/order-detail?order_no=${this.orderNo}` })
    },
  },
}
</script>

<style scoped>
.right {
  max-width: 60%;
  text-align: right;
}
.split {
  height: 1rpx;
  background: #ebeef5;
  margin: 24rpx 0;
}
.total {
  font-weight: 600;
}
.amount {
  color: #fa3534;
  font-size: 36rpx;
}
.footer {
  padding: 40rpx 20rpx;
}
.ghost {
  background: #f2f3f5;
  color: #606266;
}
</style>

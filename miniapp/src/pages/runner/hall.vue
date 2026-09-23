<template>
  <view class="page">
    <view class="bar">
      <text :class="['chip', sort === 'time' && 'on']" @click="switchSort('time')">按时间排序</text>
      <text :class="['chip', sort === 'fee' && 'on']" @click="switchSort('fee')">按酬金排序</text>
      <text class="muted" @click="refresh">刷新</text>
    </view>

    <view class="banner" v-if="user.cert_status !== 'approved'">
      接单前需完成跑腿员认证（当前：{{ certText }}）<text class="link" @click="goCert">去认证</text>
    </view>

    <view v-if="!list.length && !loading" class="empty muted">暂无待接单需求</view>
    <OrderCard v-for="o in list" :key="o.order_no" :order="o" :status-map="statusMap" @tap="goDetail">
      <view class="actions">
        <button size="mini" class="btn-primary" @click.stop="accept(o)">接单</button>
        <button size="mini" @click.stop="goDetail(o)">详情</button>
      </view>
    </OrderCard>
    <view class="foot muted" v-if="list.length">{{ loading ? '加载中…' : '已加载全部' }}</view>
  </view>
</template>

<script>
import OrderCard from '../../components/OrderCard.vue'
import { createTaskList } from '../../mixins/taskList'
import { ORDER_STATUS, CERT_STATUS } from '../../utils/config'
import store from '../../store'

export default {
  components: { OrderCard },
  mixins: [createTaskList({ source: 'available' })],
  data() {
    return { statusMap: ORDER_STATUS, user: store.state.user || {} }
  },
  computed: {
    certText() {
      return CERT_STATUS[this.user.cert_status] || '未认证'
    },
  },
  onShow() {
    this.user = store.state.user || {}
    this.page = 1
    this.fetch()
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
    switchSort(s) {
      this.sort = s
      this.page = 1
      this.list = []
      this.fetch()
    },
    refresh() {
      this.page = 1
      this.fetch()
    },
    goCert() {
      uni.navigateTo({ url: '/pages/runner/certification' })
    },
  },
}
</script>

<style scoped>
.bar {
  display: flex;
  align-items: center;
  gap: 16rpx;
  background: #fff;
  padding: 16rpx 24rpx;
}
.chip {
  padding: 10rpx 24rpx;
  border-radius: 100rpx;
  background: #f2f3f5;
  color: #606266;
  font-size: 26rpx;
}
.chip.on {
  background: #2979ff;
  color: #fff;
}
.link {
  color: #2979ff;
  text-decoration: underline;
}
.actions {
  display: flex;
  justify-content: flex-end;
  gap: 16rpx;
  margin-top: 16rpx;
}
.empty,
.foot {
  text-align: center;
  padding: 80rpx 0;
}
</style>

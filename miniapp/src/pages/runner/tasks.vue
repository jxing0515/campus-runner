<template>
  <view class="page">
    <scroll-view scroll-x class="filters">
      <view class="filter-row">
        <text v-for="f in filters" :key="f.value" :class="['chip', status === f.value && 'on']" @click="switchStatus(f.value)">
          {{ f.label }}
        </text>
      </view>
    </scroll-view>

    <view v-if="!list.length && !loading" class="empty muted">暂无任务</view>
    <OrderCard v-for="o in list" :key="o.order_no" :order="o" :status-map="statusMap" @tap="goDetail">
      <view class="actions">
        <button v-if="o.status === 'accepted'" size="mini" class="btn-primary" @click.stop="go(o, 'pickup')">取件打卡</button>
        <button v-if="['picked', 'delivering'].includes(o.status)" size="mini" class="btn-primary" @click.stop="go(o, 'deliver')">送达打卡</button>
        <button v-if="o.status === 'completed'" size="mini" @click.stop="go(o, 'review')">评价学生</button>
        <button v-if="o.status === 'completed'" size="mini" @click.stop="showReview(o)">查看收到的评价</button>
      </view>
      <view v-if="o.my_review_score || o.student_review_score" class="muted">
        收到的评价：{{ o.student_review_score || o.my_review_score }} 分
      </view>
    </OrderCard>

    <view class="foot muted" v-if="list.length">{{ loading ? '加载中…' : '已加载全部' }}</view>
  </view>
</template>

<script>
import OrderCard from '../../components/OrderCard.vue'
import { createTaskList } from '../../mixins/taskList'
import orderApi from '../../api/order'
import { ORDER_STATUS } from '../../utils/config'

const RUNNER_FLOW = ['pending_accept', 'accepted', 'picked', 'delivering', 'pending_confirm', 'completed', 'appealing', 'abnormal', 'refunded', 'cancelled']

export default {
  components: { OrderCard },
  mixins: [createTaskList({ source: 'mine' })],
  data() {
    return {
      statusMap: ORDER_STATUS,
      status: '',
      filters: [
        { label: '全部', value: '' },
        ...RUNNER_FLOW.map((value) => ({ value, label: ORDER_STATUS[value] })),
      ],
    }
  },
  onShow() {
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
    async fetch(append = false) {
      if (this.loading) return
      this.loading = true
      try {
        const params = { role: 'runner', page: this.page, page_size: 20 }
        if (this.status) params.status = this.status
        const res = await orderApi.myOrders(params)
        const results = res?.results || res || []
        this.count = res?.count || results.length
        this.list = append ? this.list.concat(results) : results
      } catch (e) {
        /* 已 toast */
      } finally {
        this.loading = false
      }
    },
    switchStatus(v) {
      this.status = v
      this.page = 1
      this.list = []
      this.fetch()
    },
    go(o, page) {
      const map = { pickup: 'pickup', deliver: 'deliver', review: 'review' }
      if (page === 'review') return uni.navigateTo({ url: `/pages/student/review?order_no=${o.order_no}&from=runner` })
      uni.navigateTo({ url: `/pages/runner/${map[page]}?order_no=${o.order_no}` })
    },
    showReview(o) {
      uni.showModal({
        title: '收到的评价',
        content: `${o.student_review_score ? o.student_review_score + ' 分' : '暂无评分'}${o.student_review_content ? '：' + o.student_review_content : ''}`,
        showCancel: false,
      })
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
  flex-wrap: wrap;
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

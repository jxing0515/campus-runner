<template>
  <view class="page">
    <view class="bar">
      <view class="chips">
        <text :class="['chip', !unreadOnly && 'on']" @click="switchOnly(false)">全部</text>
        <text :class="['chip', unreadOnly && 'on']" @click="switchOnly(true)">未读 {{ unread }}</text>
      </view>
      <text class="muted" @click="readAll">全部已读</text>
    </view>

    <view v-if="!list.length" class="empty muted">暂无消息</view>
    <view v-for="n in list" :key="n.id" class="card item" @click="open(n)">
      <view class="row">
        <text :class="['title', !n.is_read && 'unread']">{{ n.title || '通知' }}</text>
        <text class="muted">{{ n.created_at }}</text>
      </view>
      <view class="muted body">{{ n.content || n.message }}</view>
    </view>
    <view class="muted foot" v-if="list.length">每 10 秒自动刷新</view>
  </view>
</template>

<script>
import notifyApi from '../../api/notification'

const POLL_MS = 10000

export default {
  data() {
    return { list: [], unread: 0, unreadOnly: false, timer: null, loading: false }
  },
  onShow() {
    this.fetch()
    this.startPolling()
  },
  onHide() {
    this.stopPolling()
  },
  onUnload() {
    this.stopPolling()
  },
  onPullDownRefresh() {
    this.fetch().finally(uni.stopPullDownRefresh)
  },
  methods: {
    startPolling() {
      this.stopPolling()
      // 消息通知页 10s 轮询
      this.timer = setInterval(this.fetch, POLL_MS)
    },
    stopPolling() {
      if (this.timer) clearInterval(this.timer)
      this.timer = null
    },
    switchOnly(v) {
      this.unreadOnly = v
      this.fetch()
    },
    async fetch() {
      if (this.loading) return
      this.loading = true
      try {
        const params = { page: 1, page_size: 20 }
        if (this.unreadOnly) params.unread = 1
        const res = await notifyApi.notifications(params)
        this.list = res?.results || res || []
        this.unread = await this.countUnread()
      } catch (e) {
        /* 已 toast */
      } finally {
        this.loading = false
      }
    },
    async countUnread() {
      try {
        const res = await notifyApi.notifications({ unread: 1, page: 1, page_size: 1 })
        return res?.count || 0
      } catch (e) {
        return 0
      }
    },
    async open(n) {
      if (!n.is_read) {
        try {
          await notifyApi.readOne(n.id)
          n.is_read = true
          this.unread = Math.max(0, this.unread - 1)
        } catch (e) {
          /* 已 toast */
        }
      }
      // 业务消息可跳订单
      const no = n.order_no || n.data?.order_no
      if (no) uni.navigateTo({ url: `/pages/student/order-detail?order_no=${no}` })
    },
    async readAll() {
      if (!this.unread) return uni.showToast({ title: '暂无未读', icon: 'none' })
      try {
        await notifyApi.readAll()
        uni.showToast({ title: '已全部已读', icon: 'success' })
        this.fetch()
      } catch (e) {
        /* 已 toast */
      }
    },
  },
}
</script>

<style scoped>
.bar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  background: #fff;
  padding: 16rpx 24rpx;
}
.chips {
  display: flex;
  gap: 16rpx;
}
.chip {
  padding: 8rpx 24rpx;
  border-radius: 100rpx;
  background: #f2f3f5;
  color: #606266;
  font-size: 26rpx;
}
.chip.on {
  background: #2979ff;
  color: #fff;
}
.title {
  font-weight: 600;
}
.unread {
  color: #2979ff;
}
.body {
  margin-top: 10rpx;
}
.empty,
.foot {
  text-align: center;
  padding: 80rpx 0;
}
</style>

<template>
  <view class="page">
    <view class="hd">
      <view class="row">
        <view>
          <text class="hi">你好，{{ user.name || user.username || '同学' }}</text>
          <view class="muted">学号 {{ user.username }}</view>
        </view>
        <view class="badge" :class="user.credit_level" @click="go('/pages/student/credit')">
          信用 {{ user.credit_score ?? '--' }} · {{ levelText }}
        </view>
      </view>
    </view>

    <view class="card entry" @click="go('/pages/student/publish')">
      <text class="plus">＋</text>
      <view>
        <view class="strong">发布需求</view>
        <view class="muted">填写地址、时间窗与酬金，一键发单</view>
      </view>
    </view>

    <view class="grid">
      <view class="cell" @click="go('/pages/student/orders')">
        <view class="strong">我的订单</view>
        <view class="muted">全部状态筛选</view>
      </view>
      <view class="cell" @click="go('/pages/student/messages')">
        <view class="strong">消息通知</view>
        <view class="muted">{{ unread ? unread + ' 条未读' : '暂无未读' }}</view>
      </view>
      <view class="cell" @click="go('/pages/student/credit')">
        <view class="strong">信用中心</view>
        <view class="muted">{{ levelText }} · 完成 {{ user.completed_count || 0 }} 单</view>
      </view>
      <view class="cell" @click="go('/pages/runner/certification')">
        <view class="strong">跑腿员认证</view>
        <view class="muted">{{ certText }}</view>
      </view>
    </view>

    <view class="card">
      <view class="row">
        <text class="strong">账号状态</text>
        <text class="muted" @click="refresh">刷新</text>
      </view>
      <view class="line"><text class="muted">好评率</text><text>{{ rateText }}</text></view>
      <view class="line"><text class="muted">跑腿模式</text><text>{{ user.is_runner ? '已开启' : '未开启' }}</text></view>
      <view class="line"><text class="muted">账户状态</text><text>{{ user.banned ? '已封禁' : '正常' }}</text></view>
    </view>
  </view>
</template>

<script>
import authApi from '../../api/auth'
import creditApi from '../../api/credit'
import notifyApi from '../../api/notification'
import store from '../../store'
import { CREDIT_LEVEL, CERT_STATUS } from '../../utils/config'

export default {
  data() {
    return { user: store.state.user || {}, unread: 0, credit: null }
  },
  computed: {
    levelText() {
      return CREDIT_LEVEL[this.credit?.level || this.user.credit_level] || '--'
    },
    certText() {
      return CERT_STATUS[this.user.cert_status] || '未认证'
    },
    rateText() {
      return this.user.good_rate == null ? '--' : `${Math.round(this.user.good_rate * 100)}%`
    },
  },
  onShow() {
    this.refresh()
  },
  onPullDownRefresh() {
    this.refresh().finally(uni.stopPullDownRefresh)
  },
  methods: {
    go(url) {
      uni.navigateTo({ url })
    },
    async refresh() {
      try {
        const [user, credit] = await Promise.all([authApi.me(), creditApi.myCredit()])
        store.setUser(user)
        this.user = user
        this.credit = credit
      } catch (e) {
        /* 已 toast */
      }
      this.countUnread()
    },
    async countUnread() {
      try {
        const res = await notifyApi.notifications({ unread: 1, page: 1, page_size: 1 })
        this.unread = res?.count || 0
      } catch (e) {
        /* ignore */
      }
    },
  },
}
</script>

<style scoped>
.hd {
  background: linear-gradient(135deg, #2979ff, #5cadff);
  color: #fff;
  padding: 40rpx 32rpx 60rpx;
}
.hd .muted {
  color: rgba(255, 255, 255, 0.8);
}
.hi {
  font-size: 40rpx;
  font-weight: 600;
}
.badge {
  background: rgba(255, 255, 255, 0.22);
  border-radius: 100rpx;
  padding: 10rpx 24rpx;
  font-size: 24rpx;
}
.entry {
  display: flex;
  align-items: center;
  gap: 24rpx;
  margin-top: -40rpx;
}
.plus {
  font-size: 56rpx;
  color: #2979ff;
}
.strong {
  font-weight: 600;
  font-size: 30rpx;
}
.grid {
  display: flex;
  flex-wrap: wrap;
  margin: 0 20rpx;
}
.cell {
  width: calc(50% - 20rpx);
  background: #fff;
  border-radius: 16rpx;
  padding: 24rpx;
  margin: 0 10rpx 20rpx;
  box-sizing: border-box;
}
.line {
  display: flex;
  justify-content: space-between;
  padding-top: 16rpx;
}
</style>

<template>
  <view class="page">
    <view class="hd">
      <view class="avatar">{{ (user.name || user.username || 'U').slice(0, 1) }}</view>
      <view class="info">
        <view class="name">{{ user.name || '未登录' }}</view>
        <view class="muted">学号 {{ user.username }} · 信用 {{ user.credit_score ?? '--' }}（{{ levelText }}）</view>
      </view>
    </view>

    <view class="card">
      <view class="row">
        <view>
          <view class="strong">跑腿员模式</view>
          <view class="muted">{{ user.is_runner ? '已开启：显示接单 / 收入 / 任务入口' : '未开启：仅学生功能' }}</view>
        </view>
        <switch :checked="!!user.is_runner" color="#2979ff" @change="toggleRunner" />
      </view>
      <view class="muted gap">模式由账号的 is_runner 控制，开启后即可使用跑腿员入口（需先通过认证才能接单）。</view>
    </view>

    <view class="card">
      <view class="cell" @click="go('/pages/student/orders')">
        <text>我的订单</text><text class="arrow">›</text>
      </view>
      <view class="cell" @click="go('/pages/student/messages')">
        <text>消息通知</text><text class="arrow">›</text>
      </view>
      <view class="cell" @click="go('/pages/student/credit')">
        <text>信用中心</text><text class="arrow">›</text>
      </view>
      <view class="cell" @click="go('/pages/runner/certification')">
        <text>跑腿员认证</text><text class="badge">{{ certText }}</text>
      </view>
      <view class="cell" @click="go('/pages/mine/password')">
        <text>修改密码</text><text class="arrow">›</text>
      </view>
    </view>

    <view class="card" v-if="user.is_runner">
      <view class="title">跑腿员入口</view>
      <view class="grid">
        <view class="entry" @click="go('/pages/runner/hall')">待接单大厅</view>
        <view class="entry" @click="go('/pages/runner/tasks')">我的任务</view>
        <view class="entry" @click="go('/pages/runner/income')">收入统计</view>
        <view class="entry" @click="go('/pages/runner/withdraw')">提现申请</view>
        <view class="entry" @click="go('/pages/runner/credit')">信用中心</view>
      </view>
    </view>
    <view class="card" v-else>
      <view class="muted">开启跑腿员模式后，这里会显示待接单大厅、我的任务、收入统计与提现入口。</view>
    </view>

    <view class="card">
      <button class="danger" @click="logout">退出登录</button>
    </view>
  </view>
</template>

<script>
import authApi from '../../api/auth'
import store from '../../store'
import { CREDIT_LEVEL, CERT_STATUS } from '../../utils/config'

export default {
  data() {
    return { user: store.state.user || {} }
  },
  computed: {
    levelText() {
      return CREDIT_LEVEL[this.user.credit_level] || '--'
    },
    certText() {
      return CERT_STATUS[this.user.cert_status] || '未认证'
    },
  },
  onShow() {
    this.refresh()
  },
  methods: {
    go(url) {
      uni.navigateTo({ url })
    },
    async refresh() {
      try {
        const user = await authApi.me()
        store.setUser(user)
        this.user = user
      } catch (e) {
        /* 已 toast */
      }
    },
    toggleRunner(e) {
      const on = e.detail.value
      this.user.is_runner = on
      // 后端未提供模式切换接口，仅切换本地入口显示；认证通过后由管理员/后端置位
      store.setUser({ ...store.state.user, is_runner: on })
      uni.showToast({ title: on ? '已开启跑腿员入口' : '已隐藏跑腿员入口', icon: 'none' })
    },
    logout() {
      uni.showModal({
        title: '退出登录',
        content: '确认退出当前账号？',
        success: async (r) => {
          if (!r.confirm) return
          try {
            if (store.state.refresh) await authApi.logout({ refresh: store.state.refresh })
          } catch (e) {
            /* 拉黑失败也要退出本地 */
          }
          store.toLogin()
        },
      })
    },
  },
}
</script>

<style scoped>
.hd {
  display: flex;
  align-items: center;
  gap: 24rpx;
  background: linear-gradient(135deg, #2979ff, #5cadff);
  color: #fff;
  padding: 48rpx 32rpx;
}
.hd .muted {
  color: rgba(255, 255, 255, 0.85);
}
.avatar {
  width: 110rpx;
  height: 110rpx;
  border-radius: 50%;
  background: rgba(255, 255, 255, 0.24);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 44rpx;
}
.name {
  font-size: 36rpx;
  font-weight: 600;
}
.strong {
  font-weight: 600;
}
.title {
  font-weight: 600;
  margin-bottom: 16rpx;
}
.cell {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 26rpx 0;
  border-bottom: 1rpx solid #f2f3f5;
}
.cell:last-child {
  border-bottom: none;
}
.arrow {
  color: #c0c4cc;
}
.badge {
  color: #2979ff;
  font-size: 26rpx;
}
.grid {
  display: flex;
  flex-wrap: wrap;
}
.entry {
  width: calc(50% - 12rpx);
  margin: 6rpx;
  padding: 24rpx 0;
  text-align: center;
  background: #f5f7fa;
  border-radius: 12rpx;
  font-size: 26rpx;
  box-sizing: border-box;
}
.danger {
  background: #fff;
  color: #fa3534;
  border: 1rpx solid #fa3534;
}
</style>

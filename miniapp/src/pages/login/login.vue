<template>
  <view class="wrap">
    <view class="card">
      <view class="tabs">
        <text :class="['tab', mode === 'login' && 'on']" @click="mode = 'login'">登录</text>
        <text :class="['tab', mode === 'register' && 'on']" @click="mode = 'register'">注册</text>
      </view>

      <view class="field">
        <text class="label">学号</text>
        <input v-model="form.username" class="input" type="text" placeholder="请输入学号" />
      </view>
      <view class="field" v-if="mode === 'register'">
        <text class="label">姓名</text>
        <input v-model="form.name" class="input" type="text" placeholder="请输入真实姓名" />
      </view>
      <view class="field">
        <text class="label">密码</text>
        <input
          v-model="form.password"
          class="input"
          password
          placeholder="至少 8 位，含字母与数字"
          @confirm="submit"
        />
      </view>

      <button class="btn-primary" :loading="loading" @click="submit">
        {{ mode === 'login' ? '登录' : '注册并登录' }}
      </button>

      <view class="gap"></view>
      <button class="ghost" @click="wxPlaceholder">微信授权登录（占位，未实装）</button>
      <view class="muted gap">同一账号既是学生也是跑腿员，认证通过后可在「我的」切换模式。</view>
    </view>
  </view>
</template>

<script>
import api from '../../api/auth'
import store from '../../store'

export default {
  data() {
    return { mode: 'login', loading: false, form: { username: '', password: '', name: '' } }
  },
  methods: {
    // 微信授权登录：仅占位
    wxPlaceholder() {
      uni.showToast({ title: '微信授权登录暂未开放', icon: 'none' })
    },
    check() {
      const { username, password, name } = this.form
      if (!username || !password) return '请填写学号与密码'
      if (!/^(?=.*[A-Za-z])(?=.*\d).{8,}$/.test(password)) return '密码至少 8 位且同时包含字母和数字'
      if (this.mode === 'register' && !name) return '请填写姓名'
      return ''
    },
    async submit() {
      const err = this.check()
      if (err) return uni.showToast({ title: err, icon: 'none' })
      if (this.loading) return
      this.loading = true
      try {
        const body = this.form
        if (this.mode === 'register') {
          await api.register({ username: body.username, password: body.password, name: body.name })
        }
        const data = await api.login({ username: body.username, password: body.password })
        store.saveAuth(data)
        uni.showToast({ title: this.mode === 'register' ? '注册成功' : '登录成功', icon: 'success' })
        this.enter(data.user)
      } catch (e) {
        /* request.js 已统一 toast */
      } finally {
        this.loading = false
      }
    },
    enter(user) {
      const target = user && user.is_runner ? '/pages/runner/hall' : '/pages/student/home'
      setTimeout(() => uni.reLaunch({ url: target }), 400)
    },
  },
}
</script>

<style scoped>
.wrap {
  padding-top: 120rpx;
}
.tabs {
  display: flex;
  justify-content: center;
  margin-bottom: 40rpx;
}
.tab {
  padding: 0 60rpx 16rpx;
  color: #909399;
  font-size: 32rpx;
  border-bottom: 4rpx solid transparent;
}
.tab.on {
  color: #2979ff;
  font-weight: 600;
  border-bottom-color: #2979ff;
}
.field {
  display: flex;
  align-items: center;
  border-bottom: 1rpx solid #ebeef5;
  padding: 20rpx 0;
}
.label {
  width: 120rpx;
  color: #606266;
}
.input {
  flex: 1;
}
.btn-primary {
  margin-top: 48rpx;
}
.ghost {
  background: #f2f3f5;
  color: #606266;
  font-size: 26rpx;
}
</style>

<template>
  <view class="page">
    <view class="card">
      <view class="label">原密码</view>
      <input v-model="form.old_password" class="input" password placeholder="请输入原密码" />

      <view class="label">新密码</view>
      <input v-model="form.new_password" class="input" password placeholder="至少 8 位，含字母与数字" />

      <button class="btn-primary gap" :loading="loading" @click="submit">确认修改</button>
      <view class="muted gap">修改成功后后端会拉黑全部 refresh token，需要重新登录。</view>
    </view>
  </view>
</template>

<script>
import authApi from '../../api/auth'
import store from '../../store'

export default {
  data() {
    return { loading: false, form: { old_password: '', new_password: '' } }
  },
  methods: {
    async submit() {
      const { old_password, new_password } = this.form
      if (!old_password || !new_password) return uni.showToast({ title: '请填写原密码与新密码', icon: 'none' })
      if (!/^(?=.*[A-Za-z])(?=.*\d).{8,}$/.test(new_password)) return uni.showToast({ title: '新密码至少 8 位且含字母和数字', icon: 'none' })
      this.loading = true
      try {
        await authApi.changePassword({ old_password, new_password })
        uni.showToast({ title: '修改成功，请重新登录', icon: 'success' })
        setTimeout(() => store.toLogin(), 800)
      } catch (e) {
        /* 已 toast */
      } finally {
        this.loading = false
      }
    },
  },
}
</script>

<style scoped>
.label {
  font-size: 26rpx;
  color: #606266;
  margin: 20rpx 0 8rpx;
}
.input {
  border: 1rpx solid #dcdfe6;
  border-radius: 10rpx;
  padding: 18rpx;
  font-size: 28rpx;
}
</style>

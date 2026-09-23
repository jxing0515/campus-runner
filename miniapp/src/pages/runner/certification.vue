<template>
  <view class="page">
    <view class="card">
      <view class="row">
        <text class="title">认证状态</text>
        <text :class="['status', cert.status]">{{ statusText }}</text>
      </view>
      <view class="muted gap" v-if="cert.reject_reason">驳回原因：{{ cert.reject_reason }}</view>
      <view class="muted gap" v-if="cert.status === 'pending'">已提交，管理员审核通过后即可在待接单大厅接单。</view>
      <view class="muted gap">同一账号既是学生也是跑腿员；认证通过后个人中心会显示跑腿员全部入口。</view>
    </view>

    <view class="card">
      <view class="label">学号</view>
      <input v-model="form.student_no" class="input" placeholder="请输入学号" />

      <view class="label">真实姓名</view>
      <input v-model="form.real_name" class="input" placeholder="请输入真实姓名" />

      <view class="label">学生证照片（jpg/png，≤ 2MB）</view>
      <view class="proofs">
        <image v-if="cardPath" class="proof" :src="cardPath" mode="aspectFill" @click="choose" />
        <view v-else class="proof add" @click="choose">＋</view>
      </view>

      <button class="btn-primary gap" :loading="loading" :disabled="cert.status === 'pending'" @click="submit">
        {{ cert.status === 'pending' ? '审核中，不可重复提交' : '提交认证' }}
      </button>
    </view>
  </view>
</template>

<script>
import runnerApi from '../../api/runner'
import authApi from '../../api/auth'
import store from '../../store'
import { CERT_STATUS } from '../../utils/config'

export default {
  data() {
    return {
      cert: { status: 'none' },
      cardPath: '',
      loading: false,
      form: { student_no: '', real_name: '' },
    }
  },
  computed: {
    statusText() {
      return CERT_STATUS[this.cert.status] || '未认证'
    },
  },
  onShow() {
    this.load()
  },
  methods: {
    async load() {
      try {
        const cert = await runnerApi.certification()
        this.cert = cert || { status: 'none' }
        this.form.student_no = cert?.student_no || this.form.student_no
        this.form.real_name = cert?.real_name || this.form.real_name
      } catch (e) {
        /* 已 toast */
      }
    },
    choose() {
      uni.chooseImage({
        count: 1,
        sizeType: ['compressed'],
        success: async (res) => {
          const path = res.tempFilePaths[0]
          try {
            const info = await new Promise((resolve, reject) => uni.getFileInfo({ filePath: path, success: resolve, fail: reject }))
            if (info.size > 2 * 1024 * 1024) return uni.showToast({ title: '图片不能超过 2MB', icon: 'none' })
          } catch (e) {
            /* 取不到大小就交给后端校验 */
          }
          this.cardPath = path
        },
      })
    },
    async submit() {
      if (!this.form.student_no.trim() || !this.form.real_name.trim()) return uni.showToast({ title: '请填写学号与真实姓名', icon: 'none' })
      if (!this.cardPath) return uni.showToast({ title: '请上传学生证照片', icon: 'none' })
      this.loading = true
      try {
        const file = await authApi.uploadFile(this.cardPath, 'student_card')
        await runnerApi.submitCertification({ ...this.form, card_file_id: file.id })
        uni.showToast({ title: '已提交，等待审核', icon: 'success' })
        const user = await authApi.me()
        store.setUser(user)
        this.load()
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
.title {
  font-weight: 600;
  font-size: 30rpx;
}
.status {
  color: #909399;
}
.status.approved {
  color: #19be6b;
}
.status.pending {
  color: #ff9900;
}
.status.rejected {
  color: #fa3534;
}
.label {
  font-size: 26rpx;
  color: #606266;
  margin: 24rpx 0 8rpx;
}
.input {
  border: 1rpx solid #dcdfe6;
  border-radius: 10rpx;
  padding: 18rpx;
  font-size: 28rpx;
}
.proofs {
  display: flex;
}
.proof {
  width: 260rpx;
  height: 180rpx;
  border-radius: 12rpx;
  background: #f2f3f5;
}
.add {
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 60rpx;
  color: #c0c4cc;
  border: 1rpx dashed #dcdfe6;
}
</style>

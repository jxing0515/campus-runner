<template>
  <view class="page">
    <view class="card">
      <view class="center">
        <text class="hint">{{ from === 'runner' ? '评价该学生' : '本次服务评分' }}</text>
        <view class="stars">
          <text v-for="n in 5" :key="n" :class="['star', n <= score && 'on']" @click="score = n">★</text>
        </view>
        <text class="muted">{{ labels[score - 1] || '请选择评分' }}</text>
      </view>
      <textarea v-model="content" class="area gap" maxlength="200" placeholder="说说本次体验（选填，最多 200 字）" />
      <button class="btn-primary gap" :loading="loading" @click="submit">提交评价</button>
      <view class="muted gap">评价为双向评价，仅订单已完成且无申诉时可提交，提交后不可修改。</view>
    </view>
  </view>
</template>

<script>
import orderApi from '../../api/order'

export default {
  data() {
    return { orderNo: '', from: '', score: 5, content: '', loading: false, labels: ['非常差', '较差', '一般', '满意', '非常满意'] }
  },
  onLoad(options) {
    this.orderNo = options.order_no
    this.from = options.from || ''
  },
  methods: {
    async submit() {
      if (!this.score) return uni.showToast({ title: '请选择评分', icon: 'none' })
      this.loading = true
      try {
        await orderApi.reviewOrder(this.orderNo, { score: this.score, content: this.content })
        uni.showToast({ title: '评价成功', icon: 'success' })
        setTimeout(() => uni.navigateBack(), 600)
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
.center {
  text-align: center;
}
.hint {
  color: #606266;
}
.stars {
  margin: 20rpx 0 10rpx;
}
.star {
  font-size: 72rpx;
  color: #dcdfe6;
  padding: 0 12rpx;
}
.star.on {
  color: #ff9900;
}
.area {
  width: 100%;
  height: 200rpx;
  border: 1rpx solid #dcdfe6;
  border-radius: 10rpx;
  padding: 16rpx;
  box-sizing: border-box;
}
</style>

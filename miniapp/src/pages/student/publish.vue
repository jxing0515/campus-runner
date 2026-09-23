<template>
  <view class="page">
    <view class="card">
      <view class="label">需求描述</view>
      <textarea v-model="form.description" class="area" placeholder="例如：帮取快递，中通驿站 3 号柜" maxlength="200" />

      <view class="label">取件地址</view>
      <input v-model="form.pickup_address" class="input" placeholder="请输入取件地址" />

      <view class="label">送达地址</view>
      <input v-model="form.delivery_address" class="input" placeholder="请输入送达地址" />

      <view class="label">期望时间窗</view>
      <view class="row gap">
        <picker mode="multiSelector" :range="range" :value="startValue" @change="onStart" @columnchange="onStartCol">
          <view class="picker">{{ form.time_window_start || '开始时间' }}</view>
        </picker>
        <text class="muted">至</text>
        <picker mode="multiSelector" :range="range" :value="endValue" @change="onEnd" @columnchange="onEndCol">
          <view class="picker">{{ form.time_window_end || '结束时间' }}</view>
        </picker>
      </view>

      <view class="label">跑腿酬金（元）</view>
      <input v-model="form.runner_fee" class="input" type="digit" placeholder="如 5.00" />

      <view class="label">物品费代付方式</view>
      <radio-group @change="onMode">
        <label class="radio" v-for="m in modes" :key="m.value">
          <radio :value="m.value" :checked="form.item_fee_mode === m.value" color="#2979ff" />
          <text>{{ m.label }}</text>
        </label>
      </radio-group>

      <view v-if="form.item_fee_mode === 'platform'">
        <view class="label">物品费预估（元）</view>
        <input v-model="form.item_fee_estimate" class="input" type="digit" placeholder="平台代付时的预估价" />
      </view>

      <button class="btn-primary gap" :loading="loading" @click="submit">提交并去支付</button>
    </view>
  </view>
</template>

<script>
import orderApi from '../../api/order'

const pad = (n) => String(n).padStart(2, '0')
const fmtDate = (d) => `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`
const fmtTime = (d) => `${pad(d.getHours())}:${pad(d.getMinutes())}`

export default {
  data() {
    const now = new Date()
    const hours = Array.from({ length: 24 }, (_, i) => `${pad(i)}:00`)
    const minutes = ['00', '30']
    const days = Array.from({ length: 7 }, (_, i) => {
      const d = new Date(now.getTime() + i * 86400000)
      return `${fmtDate(d)} 周${'日一二三四五六'[d.getDay()]}`
    })
    return {
      loading: false,
      modes: [
        { value: 'none', label: '无需代付' },
        { value: 'offline', label: '线下代付' },
        { value: 'platform', label: '平台代付（需填预估价）' },
      ],
      range: [days, hours, minutes],
      startValue: [0, now.getHours(), 0],
      endValue: [0, Math.min(now.getHours() + 1, 23), 0],
      form: {
        description: '',
        pickup_address: '',
        delivery_address: '',
        time_window_start: '',
        time_window_end: '',
        runner_fee: '',
        item_fee_mode: 'none',
        item_fee_estimate: '',
      },
    }
  },
  methods: {
    onStartCol(e) {
      this.startValue[e.detail.column] = e.detail.value
    },
    onEndCol(e) {
      this.endValue[e.detail.column] = e.detail.value
    },
    onStart(e) {
      this.startValue = e.detail.value
      this.form.time_window_start = this.pick(e.detail.value)
    },
    onEnd(e) {
      this.endValue = e.detail.value
      this.form.time_window_end = this.pick(e.detail.value)
    },
    pick(v) {
      const day = this.range[0][v[0]]
      return `${day.split(' ')[0]} ${this.range[1][v[1]]}:${this.range[2][v[2]]}:00`
    },
    onMode(e) {
      this.form.item_fee_mode = e.detail.value
    },
    check() {
      const f = this.form
      if (!f.description.trim()) return '请填写需求描述'
      if (!f.pickup_address.trim()) return '请填写取件地址'
      if (!f.delivery_address.trim()) return '请填写送达地址'
      if (!f.time_window_start || !f.time_window_end) return '请选择时间窗'
      if (!(Number(f.runner_fee) > 0)) return '跑腿酬金需大于 0'
      if (f.item_fee_mode === 'platform' && !(Number(f.item_fee_estimate) >= 0)) return '请填写物品费预估'
      return ''
    },
    async submit() {
      const err = this.check()
      if (err) return uni.showToast({ title: err, icon: 'none' })
      this.loading = true
      try {
        const payload = { ...this.form, runner_fee: Number(this.form.runner_fee).toFixed(2) }
        if (payload.item_fee_mode !== 'platform') payload.item_fee_estimate = '0.00'
        else payload.item_fee_estimate = Number(this.form.item_fee_estimate).toFixed(2)
        const order = await orderApi.createOrder(payload)
        uni.redirectTo({ url: `/pages/student/pay?order_no=${order.order_no}` })
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
  margin: 24rpx 0 8rpx;
}
.input,
.picker {
  border: 1rpx solid #dcdfe6;
  border-radius: 10rpx;
  padding: 18rpx 20rpx;
  font-size: 28rpx;
}
.picker {
  min-width: 260rpx;
  color: #303133;
}
.area {
  width: 100%;
  height: 140rpx;
  border: 1rpx solid #dcdfe6;
  border-radius: 10rpx;
  padding: 16rpx;
  box-sizing: border-box;
  font-size: 28rpx;
}
.radio {
  display: flex;
  align-items: center;
  padding: 12rpx 0;
  font-size: 28rpx;
}
</style>

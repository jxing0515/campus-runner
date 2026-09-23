<template>
  <view class="page">
    <view class="card">
      <view class="title">送达打卡</view>
      <view class="muted">订单 {{ orderNo }}</view>
      <view class="muted gap">送达地址：{{ order.delivery_address || '--' }}</view>

      <view v-if="prepay">
        <view class="label">实际物品费（元，代付模式必填）</view>
        <input v-model="actualItemFee" class="input" type="digit" :placeholder="`预估价 ¥${order.item_fee_estimate || '0.00'}`" />
        <view class="muted gap">代付模式（{{ order.item_fee_mode === 'platform' ? '平台代付' : '线下代付' }}）必须填写实际物品费，将与预估价一并结算。</view>
      </view>

      <view class="label">上传送达凭证（jpg/png，≤ 2MB，最多 3 张）</view>
      <view class="proofs">
        <image v-for="(p, i) in photos" :key="i" class="proof" :src="p.path" mode="aspectFill" @click="remove(i)" />
        <view class="proof add" v-if="photos.length < 3" @click="choose">＋</view>
      </view>

      <button class="btn-primary gap" :loading="loading" @click="submit">提交送达打卡</button>
      <view class="muted gap">提交后订单进入「待确认」，学生确认后酬金结算到余额。</view>
    </view>
  </view>
</template>

<script>
import orderApi from '../../api/order'
import { upload } from '../../utils/request'

export default {
  data() {
    return { orderNo: '', order: {}, photos: [], actualItemFee: '', loading: false }
  },
  computed: {
    prepay() {
      return this.order.item_fee_mode === 'offline' || this.order.item_fee_mode === 'platform'
    },
  },
  onLoad(options) {
    this.orderNo = options.order_no
    this.load()
  },
  methods: {
    async load() {
      try {
        this.order = await orderApi.orderDetail(this.orderNo)
        if (this.order.actual_item_fee) this.actualItemFee = this.order.actual_item_fee
      } catch (e) {
        /* 已 toast */
      }
    },
    remove(i) {
      this.photos.splice(i, 1)
    },
    choose() {
      uni.chooseImage({
        count: 3 - this.photos.length,
        sizeType: ['compressed'],
        success: async (res) => {
          for (const path of res.tempFilePaths) {
            try {
              const info = await new Promise((resolve, reject) => uni.getFileInfo({ filePath: path, success: resolve, fail: reject }))
              if (info.size > 2 * 1024 * 1024) {
                uni.showToast({ title: '单张图片不能超过 2MB', icon: 'none' })
                continue
              }
              this.photos.push({ path })
            } catch (e) {
              this.photos.push({ path })
            }
          }
        },
      })
    },
    async submit() {
      if (!this.photos.length) return uni.showToast({ title: '请至少上传 1 张送达凭证', icon: 'none' })
      if (this.prepay && !(Number(this.actualItemFee) >= 0) ) return uni.showToast({ title: '请填写实际物品费', icon: 'none' })
      this.loading = true
      try {
        const file_ids = []
        for (const p of this.photos) {
          const f = await upload(p.path, 'evidence')
          file_ids.push(f.id)
        }
        const payload = { file_ids }
        if (this.prepay) payload.actual_item_fee = Number(this.actualItemFee).toFixed(2)
        await orderApi.deliverOrder(this.orderNo, payload)
        uni.showToast({ title: '送达打卡成功', icon: 'success' })
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
.title {
  font-weight: 600;
  font-size: 32rpx;
  margin-bottom: 10rpx;
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
  flex-wrap: wrap;
  gap: 16rpx;
}
.proof {
  width: 180rpx;
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

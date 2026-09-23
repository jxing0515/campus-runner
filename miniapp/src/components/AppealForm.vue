<template>
  <view class="wrap">
    <view class="card">
      <view class="label">申诉类型</view>
      <picker :range="typeLabels" :value="typeIndex" @change="onType">
        <view class="picker">{{ typeLabels[typeIndex] }}</view>
      </picker>

      <view class="label">问题描述</view>
      <textarea v-model="description" class="area" maxlength="300" placeholder="请描述事实经过，最多 300 字" />

      <view class="label">上传凭证（jpg/png，单张 ≤ 2MB，最多 3 张）</view>
      <view class="proofs">
        <image v-for="(p, i) in photos" :key="i" class="proof" :src="p.path" mode="aspectFill" @click="remove(i)" />
        <view class="proof add" v-if="photos.length < 3" @click="choose">＋</view>
      </view>

      <button class="btn-primary gap" :loading="loading" @click="submit">提交申诉</button>
      <view class="muted gap">申诉期间订单资金保留在平台托管，由管理员仲裁后分配。</view>
    </view>
  </view>
</template>

<script>
import orderApi from '../api/order'
import { upload } from '../utils/request'
import { APPEAL_TYPES } from '../utils/config'

// 学生 / 跑腿员共用；订单号由页面通过 prop 传入
export default {
  name: 'AppealForm',
  props: {
    orderNo: { type: String, required: true },
  },
  data() {
    return {
      typeIndex: 0,
      description: '',
      photos: [],
      loading: false,
    }
  },
  computed: {
    typeLabels() {
      return APPEAL_TYPES.map((t) => t.label)
    },
  },
  methods: {
    onType(e) {
      this.typeIndex = Number(e.detail.value)
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
              const info = await new Promise((resolve, reject) =>
                uni.getFileInfo({ filePath: path, success: resolve, fail: reject })
              )
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
      if (!this.description.trim()) return uni.showToast({ title: '请填写问题描述', icon: 'none' })
      if (!this.photos.length) return uni.showToast({ title: '请至少上传 1 张凭证', icon: 'none' })
      this.loading = true
      try {
        const card_file_ids = []
        for (const p of this.photos) {
          const file = await upload(p.path, 'appeal')
          card_file_ids.push(file.id)
        }
        await orderApi.appealOrder(this.orderNo, {
          appeal_type: APPEAL_TYPES[this.typeIndex].value,
          description: this.description,
          card_file_ids,
        })
        uni.showToast({ title: '申诉已提交', icon: 'success' })
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
.label {
  font-size: 26rpx;
  color: #606266;
  margin: 24rpx 0 8rpx;
}
.picker,
.area {
  border: 1rpx solid #dcdfe6;
  border-radius: 10rpx;
  padding: 18rpx;
  font-size: 28rpx;
}
.area {
  width: 100%;
  height: 200rpx;
  box-sizing: border-box;
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

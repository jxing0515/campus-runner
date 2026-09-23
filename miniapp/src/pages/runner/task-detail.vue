<template>
  <view class="page">
    <view class="hd">
      <view class="status">{{ statusMap[order.status] || order.status || '--' }}</view>
      <view class="muted">订单号 {{ order.order_no }}</view>
    </view>

    <view class="card">
      <view class="desc">{{ order.description }}</view>
      <view class="line"><text class="muted">取件地址</text><text class="right">{{ order.pickup_address }}</text></view>
      <view class="line"><text class="muted">送达地址</text><text class="right">{{ order.delivery_address }}</text></view>
      <view class="line"><text class="muted">时间窗</text><text class="right">{{ order.time_window_start }} ~ {{ order.time_window_end }}</text></view>
      <view class="line"><text class="muted">酬金</text><text class="right fee">¥{{ order.runner_fee }}</text></view>
      <view class="line"><text class="muted">物品费代付</text><text class="right">{{ modeText }}</text></view>
      <view class="line" v-if="order.item_fee_estimate && order.item_fee_mode !== 'none'">
        <text class="muted">物品费预估</text><text class="right">¥{{ order.item_fee_estimate }}</text>
      </view>
      <view class="line" v-if="order.actual_item_fee"><text class="muted">实际物品费</text><text class="right">¥{{ order.actual_item_fee }}</text></view>
      <view class="line" v-if="order.student"><text class="muted">学生</text><text class="right">{{ order.student.name || order.student.username }}</text></view>
    </view>

    <StatusTimeline :logs="logs" :status-map="statusMap" />

    <view class="card" v-if="files.length">
      <view class="title">凭证</view>
      <view class="proofs">
        <image v-for="f in files" :key="f.id" class="proof" :src="proofSrc(f)" mode="aspectFill" @click="viewFile(f.id)" />
      </view>
    </view>

    <view class="card" v-if="reviews.length">
      <view class="title">收到的评价</view>
      <view v-for="r in reviews" :key="r.id" class="review">
        <view class="row">
          <text>{{ r.from_user?.name || '学生' }}</text>
          <text class="score">{{ r.score }} 分</text>
        </view>
        <view class="muted">{{ r.content || '（无文字评价）' }}</view>
      </view>
    </view>

    <view class="actions">
      <button v-if="order.status === 'accepted'" size="mini" class="btn-primary" @click="go('pickup')">取件打卡</button>
      <button v-if="['picked', 'delivering'].includes(order.status)" size="mini" class="btn-primary" @click="go('deliver')">送达打卡</button>
      <button v-if="order.status === 'completed'" size="mini" @click="goReview">评价学生</button>
      <button v-if="['completed', 'pending_confirm', 'abnormal'].includes(order.status)" size="mini" @click="goAppeal">申诉</button>
      <button size="mini" @click="load">刷新</button>
    </view>
  </view>
</template>

<script>
import StatusTimeline from '../../components/StatusTimeline.vue'
import orderApi from '../../api/order'
import { fileDataUrl, viewFile } from '../../utils/request'
import { ORDER_STATUS } from '../../utils/config'

export default {
  components: { StatusTimeline },
  data() {
    return { orderNo: '', order: {}, statusMap: ORDER_STATUS, proofMap: {}, timer: null }
  },
  computed: {
    logs() {
      return this.order.status_logs || this.order.logs || []
    },
    files() {
      return this.order.files || this.order.proofs || []
    },
    reviews() {
      return this.order.reviews || []
    },
    modeText() {
      return { offline: '线下代付', platform: '平台代付', none: '无需代付' }[this.order.item_fee_mode] || '--'
    },
  },
  onLoad(options) {
    this.orderNo = options.order_no
    this.load()
    this.timer = setInterval(this.load, 8000)
  },
  onUnload() {
    if (this.timer) clearInterval(this.timer)
  },
  methods: {
    viewFile,
    proofSrc(f) {
      if (f.url) return f.url
      // #ifdef H5
      if (!this.proofMap[f.id]) {
        fileDataUrl(f.id)
          .then((src) => {
            this.proofMap[f.id] = src
          })
          .catch(() => {})
        return ''
      }
      return this.proofMap[f.id]
      // #endif
      // #ifndef H5
      return f.tempFilePath || ''
      // #endif
    },
    async load() {
      try {
        this.order = await orderApi.orderDetail(this.orderNo)
      } catch (e) {
        /* 已 toast */
      }
    },
    go(page) {
      uni.navigateTo({ url: `/pages/runner/${page}?order_no=${this.orderNo}` })
    },
    goReview() {
      uni.navigateTo({ url: `/pages/student/review?order_no=${this.orderNo}&from=runner` })
    },
    goAppeal() {
      uni.navigateTo({ url: `/pages/runner/appeal?order_no=${this.orderNo}` })
    },
  },
}
</script>

<style scoped>
.hd {
  background: #2979ff;
  color: #fff;
  padding: 40rpx 32rpx;
}
.hd .muted {
  color: rgba(255, 255, 255, 0.82);
}
.status {
  font-size: 40rpx;
  font-weight: 600;
}
.desc {
  font-size: 32rpx;
  font-weight: 600;
  margin-bottom: 12rpx;
}
.title {
  font-weight: 600;
  margin-bottom: 16rpx;
}
.line {
  display: flex;
  justify-content: space-between;
  padding-top: 14rpx;
}
.right {
  max-width: 62%;
  text-align: right;
}
.fee {
  color: #fa3534;
  font-weight: 600;
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
.review {
  padding-top: 12rpx;
}
.score {
  color: #ff9900;
}
.actions {
  display: flex;
  flex-wrap: wrap;
  gap: 20rpx;
  padding: 20rpx 30rpx 60rpx;
}
</style>

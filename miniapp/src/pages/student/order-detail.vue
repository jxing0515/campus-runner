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
      <view class="line"><text class="muted">跑腿酬金</text><text class="right">¥{{ order.runner_fee }}</text></view>
      <view class="line" v-if="order.item_fee_mode !== 'none'">
        <text class="muted">物品费（{{ modeText }}）</text>
        <text class="right">¥{{ order.item_fee_estimate }}</text>
      </view>
      <view class="line" v-if="order.actual_item_fee">
        <text class="muted">实际物品费</text>
        <text class="right">¥{{ order.actual_item_fee }}</text>
      </view>
      <view class="line" v-if="order.runner"><text class="muted">跑腿员</text><text class="right">{{ order.runner.name || order.runner.username }}</text></view>
      <view class="line" v-if="order.student"><text class="muted">学生</text><text class="right">{{ order.student.name || order.student.username }}</text></view>
    </view>

    <StatusTimeline :logs="logs" :status-map="statusMap" />

    <view class="card" v-if="files.length">
      <view class="title">凭证</view>
      <view class="proofs">
        <image
          v-for="f in files"
          :key="f.id"
          class="proof"
          :src="proofSrc(f)"
          mode="aspectFill"
          @click="viewFile(f.id)"
        />
      </view>
    </view>

    <view class="card" v-if="reviews.length">
      <view class="title">评价</view>
      <view v-for="r in reviews" :key="r.id" class="review">
        <view class="row">
          <text>{{ r.from_user?.name || r.from?.name || '用户' }}</text>
          <text class="score">{{ r.score }} 分</text>
        </view>
        <view class="muted">{{ r.content || '（无文字评价）' }}</view>
      </view>
    </view>

    <view class="card" v-if="flows.length">
      <view class="title">资金流水</view>
      <view v-for="(f, i) in flows" :key="i" class="line">
        <text class="muted">{{ f.type || f.flow_type }} · {{ f.created_at }}</text>
        <text class="right">¥{{ f.amount }}</text>
      </view>
    </view>

    <view class="actions" v-if="actions.length">
      <button
        v-for="a in actions"
        :key="a.key"
        size="mini"
        :class="a.primary && 'btn-primary'"
        @click="run(a.key)"
      >
        {{ a.label }}
      </button>
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
    return { orderNo: '', order: {}, statusMap: ORDER_STATUS, polling: null, proofMap: {} }
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
    flows() {
      return this.order.fund_flows || []
    },
    modeText() {
      return { offline: '线下代付', platform: '平台代付' }[this.order.item_fee_mode] || '--'
    },
    actions() {
      const s = this.order.status
      const list = []
      if (s === 'pending_pay') list.push({ key: 'pay', label: '去支付', primary: true })
      if (['pending_accept', 'accepted'].includes(s)) list.push({ key: 'cancel', label: '取消订单' })
      if (s === 'pending_confirm') list.push({ key: 'confirm', label: '确认完成', primary: true })
      if (s === 'completed') list.push({ key: 'review', label: '评价', primary: true })
      if (['completed', 'abnormal', 'refunded'].includes(s)) list.push({ key: 'appeal', label: '申诉' })
      return list
    },
  },
  onLoad(options) {
    this.orderNo = options.order_no
    this.load()
    // 状态可能被跑腿员推进，详情页轻量轮询
    this.polling = setInterval(this.load, 8000)
  },
  onUnload() {
    if (this.polling) clearInterval(this.polling)
  },
  methods: {
    viewFile,
    // <image> 无法带 Authorization 头，H5 下先鉴权下载再内联展示
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
    run(key) {
      if (key === 'pay') return uni.navigateTo({ url: `/pages/student/pay?order_no=${this.orderNo}` })
      if (key === 'review') return uni.navigateTo({ url: `/pages/student/review?order_no=${this.orderNo}` })
      if (key === 'appeal') return uni.navigateTo({ url: `/pages/student/appeal?order_no=${this.orderNo}` })
      if (key === 'confirm') return this.confirm()
      if (key === 'cancel') return this.cancel()
    },
    async confirm() {
      const ok = await new Promise((res) => uni.showModal({ title: '确认完成', content: '确认后酬金结算给跑腿员', success: (x) => res(x.confirm) }))
      if (!ok) return
      try {
        await orderApi.confirmOrder(this.orderNo)
        uni.showToast({ title: '已确认完成', icon: 'success' })
        this.load()
      } catch (e) {
        /* 已 toast */
      }
    },
    async cancel() {
      const r = await new Promise((res) => uni.showModal({ title: '取消订单', editable: true, placeholderText: '请输入取消原因', success: (x) => res(x) }))
      if (!r.confirm) return
      try {
        await orderApi.cancelOrder(this.orderNo, r.content || '用户取消')
        uni.showToast({ title: '已取消', icon: 'success' })
        this.load()
      } catch (e) {
        /* 已 toast */
      }
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

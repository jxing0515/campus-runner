<template>
  <view class="page">
    <view class="hd">
      <view class="score">{{ info.score ?? '--' }}</view>
      <view class="level">{{ levelText }}</view>
      <view class="muted lv-desc">信用分 ≥90 优秀 / 80-89 良好 / 60-79 一般 / &lt;60 受限</view>
    </view>

    <view class="card">
      <view class="title">当前权益</view>
      <view class="row line">
        <text>可发布需求</text>
        <text :class="limits.can_publish ? 'ok' : 'no'">{{ limits.can_publish ? '允许' : '受限' }}</text>
      </view>
      <view class="row line">
        <text>可接单</text>
        <text :class="limits.can_accept ? 'ok' : 'no'">{{ limits.can_accept ? '允许' : '受限' }}</text>
      </view>
      <view class="row line">
        <text>可平台代付</text>
        <text :class="limits.can_prepay ? 'ok' : 'no'">{{ limits.can_prepay ? '允许' : '受限' }}</text>
      </view>
      <view class="muted gap" v-if="!limits.can_publish || !limits.can_accept || !limits.can_prepay">
        受限说明：信用分低于 60 时平台会限制发单 / 接单 / 代付能力，按时完成订单可逐步恢复；如有异议可在订单内提交申诉。
      </view>
    </view>

    <view class="card">
      <view class="row">
        <text class="title">变动记录</text>
        <text class="muted" @click="loadLogs">刷新</text>
      </view>
      <view v-for="(l, i) in logs" :key="i" class="log">
        <view class="row">
          <text>{{ reasonText(l) }}</text>
          <text :class="delta(l) >= 0 ? 'ok' : 'no'">{{ delta(l) >= 0 ? '+' : '' }}{{ delta(l) }}</text>
        </view>
        <view class="muted">{{ l.created_at }} · {{ l.score_before }} → {{ l.score_after }}</view>
      </view>
      <view class="muted" v-if="!logs.length">暂无变动记录</view>
    </view>
  </view>
</template>

<script>
import creditApi from '../api/credit'
import { CREDIT_LEVEL } from '../utils/config'

// 学生 / 跑腿员共用；页面在 onShow 里调 reload()，组件内不写页面生命周期
export default {
  name: 'CreditPanel',
  data() {
    return { info: {}, logs: [] }
  },
  computed: {
    levelText() {
      return CREDIT_LEVEL[this.info.level] || '--'
    },
    limits() {
      return this.info.limits || {}
    },
  },
  methods: {
    reload() {
      this.load()
      this.loadLogs()
    },
    delta(l) {
      if (l.delta != null) return Number(l.delta)
      return Number(l.score_after || 0) - Number(l.score_before || 0)
    },
    reasonText(l) {
      return l.reason_text || l.reason || l.reason_code || '信用调整'
    },
    async load() {
      try {
        this.info = await creditApi.myCredit()
      } catch (e) {
        /* 已 toast */
      }
    },
    async loadLogs() {
      try {
        const res = await creditApi.creditLogs({ page: 1, page_size: 50 })
        this.logs = res?.results || res || []
      } catch (e) {
        /* 已 toast */
      }
    },
  },
}
</script>

<style scoped>
.hd {
  background: linear-gradient(135deg, #2979ff, #5cadff);
  color: #fff;
  padding: 50rpx 32rpx;
  text-align: center;
}
.score {
  font-size: 96rpx;
  font-weight: 700;
  line-height: 1.1;
}
.level {
  font-size: 32rpx;
  margin-top: 8rpx;
}
.lv-desc {
  color: rgba(255, 255, 255, 0.82);
  margin-top: 12rpx;
}
.title {
  font-weight: 600;
}
.line {
  padding-top: 16rpx;
}
.ok {
  color: #19be6b;
}
.no {
  color: #fa3534;
}
.log {
  padding: 16rpx 0;
  border-bottom: 1rpx solid #f2f3f5;
}
</style>

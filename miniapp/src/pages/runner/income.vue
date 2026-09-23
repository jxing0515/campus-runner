<template>
  <view class="page">
    <view class="hd">
      <view class="row">
        <view>
          <view class="muted">累计收入（元）</view>
          <view class="big">{{ data.total_income || '0.00' }}</view>
        </view>
        <view>
          <view class="muted">可提现余额（元）</view>
          <view class="big">{{ data.balance || '0.00' }}</view>
        </view>
      </view>
      <button class="btn-primary gap" @click="go('/pages/runner/withdraw')">申请提现</button>
    </view>

    <view class="card">
      <view class="title">收入明细</view>
      <view v-for="(r, i) in records" :key="i" class="line">
        <view>
          <view>{{ r.title || r.remark || '订单结算' }}</view>
          <view class="muted">{{ r.created_at }}{{ r.order_no ? ' · ' + r.order_no : '' }}</view>
        </view>
        <text :class="Number(r.amount) >= 0 ? 'in' : 'out'">{{ Number(r.amount) >= 0 ? '+' : '' }}{{ r.amount }}</text>
      </view>
      <view class="muted" v-if="!records.length">暂无收入记录</view>
    </view>
  </view>
</template>

<script>
import runnerApi from '../../api/runner'

export default {
  data() {
    return { data: {}, records: [] }
  },
  onShow() {
    this.load()
  },
  onPullDownRefresh() {
    this.load().finally(uni.stopPullDownRefresh)
  },
  methods: {
    async load() {
      try {
        const res = await runnerApi.income()
        this.data = res || {}
        this.records = res?.records || []
      } catch (e) {
        /* 已 toast */
      }
    },
    go(url) {
      uni.navigateTo({ url })
    },
  },
}
</script>

<style scoped>
.hd {
  background: linear-gradient(135deg, #2979ff, #5cadff);
  color: #fff;
  padding: 40rpx 32rpx;
}
.hd .muted {
  color: rgba(255, 255, 255, 0.82);
}
.hd .btn-primary {
  background: #fff;
  color: #2979ff;
}
.big {
  font-size: 44rpx;
  font-weight: 700;
}
.title {
  font-weight: 600;
  margin-bottom: 12rpx;
}
.line {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 16rpx 0;
  border-bottom: 1rpx solid #f2f3f5;
}
.in {
  color: #19be6b;
  font-weight: 600;
}
.out {
  color: #fa3534;
  font-weight: 600;
}
</style>

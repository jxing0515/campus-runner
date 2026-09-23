<template>
  <view class="page">
    <view class="card">
      <view class="row">
        <text class="muted">可提现余额</text>
        <text class="big">¥{{ data.balance || '0.00' }}</text>
      </view>
      <view class="split"></view>

      <view class="label">提现金额（元）</view>
      <input v-model="form.amount" class="input" type="digit" placeholder="请输入提现金额" />

      <view class="label">提现方式</view>
      <picker :range="methods" :value="methodIndex" @change="onMethod">
        <view class="picker">{{ methods[methodIndex] }}</view>
      </picker>

      <view class="label">收款账号</view>
      <input v-model="form.account" class="input" placeholder="支付宝账号 / 微信号 / 银行卡号" />

      <button class="btn-primary gap" :loading="loading" @click="submit">提交提现申请</button>
      <view class="muted gap">提交后金额立即冻结并扣减余额，管理员审核通过后打款；驳回会原路退回。</view>
    </view>

    <view class="card">
      <view class="row">
        <text class="title">我的提现</text>
        <text class="muted" @click="loadList">刷新</text>
      </view>
      <view v-for="w in list" :key="w.id" class="line">
        <view>
          <view>¥{{ w.amount }} · {{ w.method }}</view>
          <view class="muted">{{ w.created_at }} · {{ w.account }}</view>
        </view>
        <text :class="statusClass(w.status)">{{ statusText(w.status) }}</text>
      </view>
      <view class="muted" v-if="!list.length">暂无提现记录</view>
    </view>
  </view>
</template>

<script>
import runnerApi from '../../api/runner'
import { WITHDRAW_METHODS } from '../../utils/config'

export default {
  data() {
    return {
      data: {},
      list: [],
      loading: false,
      methodIndex: 0,
      methods: WITHDRAW_METHODS,
      form: { amount: '', account: '' },
    }
  },
  onShow() {
    this.loadIncome()
    this.loadList()
  },
  methods: {
    statusText(s) {
      return { pending: '审核中', approved: '已打款', rejected: '已驳回' }[s] || s
    },
    statusClass(s) {
      return { pending: 'wait', approved: 'in', rejected: 'out' }[s] || ''
    },
    onMethod(e) {
      this.methodIndex = Number(e.detail.value)
    },
    async loadIncome() {
      try {
        this.data = (await runnerApi.income()) || {}
      } catch (e) {
        /* 已 toast */
      }
    },
    async loadList() {
      try {
        const res = await runnerApi.withdrawals({ page: 1, page_size: 20 })
        this.list = res?.results || res || []
      } catch (e) {
        /* 已 toast */
      }
    },
    async submit() {
      const amount = Number(this.form.amount)
      if (!(amount > 0)) return uni.showToast({ title: '请输入正确的提现金额', icon: 'none' })
      if (amount > Number(this.data.balance || 0)) return uni.showToast({ title: '超出可提现余额', icon: 'none' })
      if (!this.form.account.trim()) return uni.showToast({ title: '请填写收款账号', icon: 'none' })
      this.loading = true
      try {
        await runnerApi.applyWithdrawal({
          amount: amount.toFixed(2),
          method: this.methods[this.methodIndex],
          account: this.form.account,
        })
        uni.showToast({ title: '已提交，等待审核', icon: 'success' })
        this.form.amount = ''
        this.loadIncome()
        this.loadList()
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
.big {
  font-size: 40rpx;
  font-weight: 700;
  color: #fa3534;
}
.split {
  height: 1rpx;
  background: #ebeef5;
  margin: 24rpx 0;
}
.label {
  font-size: 26rpx;
  color: #606266;
  margin: 20rpx 0 8rpx;
}
.input,
.picker {
  border: 1rpx solid #dcdfe6;
  border-radius: 10rpx;
  padding: 18rpx;
  font-size: 28rpx;
}
.title {
  font-weight: 600;
}
.line {
  display: flex;
  justify-content: space-between;
  padding: 16rpx 0;
  border-bottom: 1rpx solid #f2f3f5;
}
.in {
  color: #19be6b;
}
.out {
  color: #fa3534;
}
.wait {
  color: #ff9900;
}
</style>

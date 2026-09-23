<template>
  <view class="card">
    <view class="title">状态时间线</view>
    <view v-for="(log, i) in logs" :key="i" class="item">
      <view class="dot-col">
        <view class="dot" :class="i === logs.length - 1 && 'on'"></view>
        <view class="line" v-if="i < logs.length - 1"></view>
      </view>
      <view class="body">
        <view class="st">{{ statusMap[log.to_status || log.status] || log.to_status || log.status || '--' }}</view>
        <view class="muted">{{ log.created_at || log.time }}</view>
        <view class="muted" v-if="log.remark || log.reason">{{ log.remark || log.reason }}</view>
      </view>
    </view>
    <view v-if="!logs.length" class="muted">暂无状态记录</view>
  </view>
</template>

<script>
export default {
  name: 'StatusTimeline',
  props: {
    logs: { type: Array, default: () => [] },
    statusMap: { type: Object, required: true },
  },
}
</script>

<style scoped>
.title {
  font-weight: 600;
  margin-bottom: 20rpx;
}
.item {
  display: flex;
}
.dot-col {
  width: 40rpx;
  display: flex;
  flex-direction: column;
  align-items: center;
}
.dot {
  width: 16rpx;
  height: 16rpx;
  border-radius: 50%;
  background: #c0c4cc;
  margin-top: 10rpx;
}
.dot.on {
  background: #2979ff;
}
.line {
  flex: 1;
  width: 2rpx;
  background: #ebeef5;
}
.body {
  flex: 1;
  padding-bottom: 24rpx;
}
.st {
  font-size: 28rpx;
}
</style>

<template>
  <view class="card" @click="$emit('tap', order)">
    <view class="row">
      <text class="no">{{ order.order_no }}</text>
      <uni-tag :text="statusMap[order.status] || order.status" type="primary" size="small" :inverted="true" />
    </view>
    <view class="desc">{{ order.description }}</view>
    <view class="muted">取件：{{ order.pickup_address }}</view>
    <view class="muted">送达：{{ order.delivery_address }}</view>
    <view class="muted" v-if="order.time_window_start">时间窗：{{ order.time_window_start }} ~ {{ order.time_window_end }}</view>
    <view class="row gap">
      <text class="fee">酬金 ¥{{ order.runner_fee }}</text>
      <text class="muted">{{ order.item_fee_mode === 'platform' ? '平台代付' : order.item_fee_mode === 'offline' ? '线下代付' : '无需代付' }}</text>
    </view>
    <slot></slot>
  </view>
</template>

<script>
export default {
  name: 'OrderCard',
  props: {
    order: { type: Object, required: true },
    statusMap: { type: Object, required: true },
  },
  emits: ['tap'],
}
</script>

<style scoped>
.no {
  font-size: 24rpx;
  color: #909399;
}
.desc {
  font-size: 30rpx;
  font-weight: 600;
  margin: 12rpx 0;
}
.fee {
  color: #fa3534;
  font-weight: 600;
}
</style>

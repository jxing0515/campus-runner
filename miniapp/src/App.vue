<script>
import store from './store'
export default {
  onLaunch() {
    store.hydrate()
  },
}
</script>

<style>
page {
  background: #f5f6f8;
  font-size: 28rpx;
  color: #303133;
  --primary: #2979ff;
}
.card {
  background: #fff;
  border-radius: 16rpx;
  padding: 24rpx;
  margin: 20rpx;
  box-shadow: 0 2rpx 12rpx rgba(0, 0, 0, 0.04);
}
.row {
  display: flex;
  align-items: center;
  justify-content: space-between;
}
.muted {
  color: #909399;
  font-size: 24rpx;
}
.gap {
  margin-top: 16rpx;
}
.btn-primary {
  background: var(--primary);
  color: #fff;
}
.banner {
  margin: 20rpx;
  padding: 16rpx;
  border-radius: 12rpx;
  background: #fff7e6;
  color: #d48806;
  font-size: 24rpx;
  text-align: center;
}
</style>

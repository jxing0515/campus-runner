<template>
  <AppealForm v-if="orderNo" :order-no="orderNo" />
</template>

<script>
// 跑腿员申诉：与学生侧共用表单，仅入口不同
import AppealForm from '../../components/AppealForm.vue'

export default {
  components: { AppealForm },
  data() {
    return { orderNo: '' }
  },
  onLoad(options) {
    this.orderNo = options.order_no || ''
  },
}
</script>

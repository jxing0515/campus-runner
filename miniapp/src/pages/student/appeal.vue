<template>
  <AppealForm v-if="orderNo" :order-no="orderNo" />
</template>

<script>
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

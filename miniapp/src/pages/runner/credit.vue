<template>
  <CreditPanel ref="panel" />
</template>

<script>
// 跑腿员信用中心：与学生侧共用同一面板，仅入口不同
import CreditPanel from '../../components/CreditPanel.vue'

export default {
  components: { CreditPanel },
  onShow() {
    this.$refs.panel?.reload()
  },
}
</script>

<template>
  <CreditPanel ref="panel" />
</template>

<script>
import CreditPanel from '../../components/CreditPanel.vue'

export default {
  components: { CreditPanel },
  onShow() {
    this.$refs.panel?.reload()
  },
}
</script>

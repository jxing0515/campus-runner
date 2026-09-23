<template>
  <div class="page">
    <div class="stat-grid">
      <el-card shadow="never">
        <div class="label">Σ 托管中流水</div>
        <div class="value">{{ fmtMoney(data.escrow_total ?? data.escrow_amount ?? data.total) }}</div>
      </el-card>
      <el-card shadow="never">
        <div class="label">平台账户余额</div>
        <div class="value">{{ fmtMoney(data.platform_balance ?? data.platform_account) }}</div>
      </el-card>
      <el-card shadow="never">
        <div class="label">差额（应为 0）</div>
        <div class="value" :style="{ color: diff === 0 ? '#67c23a' : '#f56c6c' }">{{ fmtMoney(diff) }}</div>
      </el-card>
      <el-card shadow="never">
        <div class="label">托管中订单数</div>
        <div class="value">{{ data.order_count ?? data.escrow_count ?? '-' }}</div>
      </el-card>
    </div>

    <el-card shadow="never">
      <div class="toolbar">
        <span class="muted">列表为托管中的资金流水（学生已付款、尚未结算/退款）</span>
        <el-button size="small" @click="load">刷新</el-button>
      </div>
      <el-table v-loading="loading" :data="rows" border stripe>
        <el-table-column prop="id" label="ID" width="70" />
        <el-table-column prop="order_no" label="订单号" min-width="160" />
        <el-table-column label="类型" width="110">
          <template #default="{ row }">{{ label(FUND_FLOW_TYPE, row.type) }}</template>
        </el-table-column>
        <el-table-column label="费用构成" width="110">
          <template #default="{ row }">{{ label(FEE_PART, row.fee_part) }}</template>
        </el-table-column>
        <el-table-column label="托管金额" width="120">
          <template #default="{ row }">{{ fmtMoney(row.amount) }}</template>
        </el-table-column>
        <el-table-column prop="username" label="付款人" min-width="110" />
        <el-table-column label="时间" width="170">
          <template #default="{ row }">{{ fmtDate(row.created_at) }}</template>
        </el-table-column>
      </el-table>
    </el-card>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import { adminApi } from '../api/request'
import { FEE_PART, FUND_FLOW_TYPE, label } from '../utils/constants'
import { fmtDate, fmtMoney } from '../utils/format'

const loading = ref(false)
const data = ref({})
const rows = computed(() => data.value.flows || data.value.results || [])

const diff = computed(() => {
  const a = Number(data.value.escrow_total ?? data.value.escrow_amount ?? data.value.total ?? 0)
  const b = Number(data.value.platform_balance ?? data.value.platform_account ?? 0)
  return Number((a - b).toFixed(2))
})

async function load() {
  loading.value = true
  try {
    data.value = (await adminApi.escrow()) || {}
  } finally {
    loading.value = false
  }
}

onMounted(load)
</script>

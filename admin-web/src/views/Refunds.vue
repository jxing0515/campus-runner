<template>
  <div class="page">
    <el-card shadow="never">
      <div class="filter-bar">
        <el-select v-model="query.status" placeholder="退款状态" clearable style="width: 160px" @change="reload">
          <el-option label="待退款" value="pending" />
          <el-option label="已退款" value="refunded" />
          <el-option label="已驳回" value="rejected" />
        </el-select>
        <el-input v-model="query.order_no" placeholder="订单号" clearable style="width: 200px" @keyup.enter="reload" />
        <el-button type="primary" @click="reload">查询</el-button>
        <el-button @click="reset">重置</el-button>
      </div>

      <el-table v-loading="loading" :data="rows" border stripe>
        <el-table-column prop="id" label="ID" width="70" />
        <el-table-column prop="order_no" label="订单号" min-width="160" />
        <el-table-column label="退款金额" width="120">
          <template #default="{ row }">{{ fmtMoney(row.amount) }}</template>
        </el-table-column>
        <el-table-column label="费用构成" width="120">
          <template #default="{ row }">{{ label(FEE_PART, row.fee_part) }}</template>
        </el-table-column>
        <el-table-column prop="username" label="收款用户" min-width="110" />
        <el-table-column label="状态" width="110">
          <template #default="{ row }">
            <el-tag size="small" :type="tag(FUND_STATUS, row.status)">{{ label(FUND_STATUS, row.status) }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="reason" label="退款原因" min-width="160" show-overflow-tooltip />
        <el-table-column label="时间" width="170">
          <template #default="{ row }">{{ fmtDate(row.created_at) }}</template>
        </el-table-column>
      </el-table>

      <div class="pager">
        <el-pagination
          v-model:current-page="page.page"
          v-model:page-size="page.page_size"
          :total="total"
          :page-sizes="[10, 20, 50, 100]"
          layout="total, sizes, prev, pager, next, jumper"
          @current-change="load"
          @size-change="reload"
        />
      </div>
    </el-card>
  </div>
</template>

<script setup>
import { onMounted, reactive } from 'vue'
import { adminApi } from '../api/request'
import { useTable } from '../composables/useTable'
import { FEE_PART, REFUND_STATUS as FUND_STATUS, label, tag } from '../utils/constants'
import { fmtDate, fmtMoney } from '../utils/format'

const query = reactive({ status: '', order_no: '' })
const { rows, total, loading, page, load, reload } = useTable(adminApi.refunds, query)

function reset() {
  query.status = ''
  query.order_no = ''
  reload()
}

onMounted(load)
</script>

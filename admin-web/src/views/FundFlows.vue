<template>
  <div class="page">
    <el-card shadow="never">
      <div class="filter-bar">
        <el-select v-model="query.type" placeholder="流水类型" clearable style="width: 160px" @change="reload">
          <el-option v-for="o in typeOpts" :key="o.value" :label="o.label" :value="o.value" />
        </el-select>
        <el-select v-model="query.fee_part" placeholder="费用构成" clearable style="width: 160px" @change="reload">
          <el-option v-for="o in feeOpts" :key="o.value" :label="o.label" :value="o.value" />
        </el-select>
        <el-input v-model="query.order_no" placeholder="订单号" clearable style="width: 200px" @keyup.enter="reload" />
        <el-button type="primary" @click="reload">查询</el-button>
        <el-button @click="reset">重置</el-button>
        <span class="grow" />
        <el-button type="success" plain @click="exportCsv">导出 CSV</el-button>
      </div>

      <el-table v-loading="loading" :data="rows" border stripe>
        <el-table-column prop="id" label="ID" width="70" />
        <el-table-column prop="order_no" label="订单号" min-width="160" />
        <el-table-column label="类型" width="110">
          <template #default="{ row }">
            <el-tag size="small">{{ label(FUND_FLOW_TYPE, row.type) }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="费用构成" width="110">
          <template #default="{ row }">{{ label(FEE_PART, row.fee_part) }}</template>
        </el-table-column>
        <el-table-column label="金额" width="120">
          <template #default="{ row }">{{ fmtMoney(row.amount) }}</template>
        </el-table-column>
        <el-table-column prop="username" label="用户" min-width="110">
          <template #default="{ row }">{{ row.username || row.user?.username || '-' }}</template>
        </el-table-column>
        <el-table-column label="方向" width="90">
          <template #default="{ row }">
            <el-tag size="small" :type="row.direction === 'out' ? 'warning' : 'success'">
              {{ row.direction === 'out' ? '支出' : row.direction === 'in' ? '收入' : '-' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="remark" label="备注" min-width="150" show-overflow-tooltip />
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
import { computed, onMounted, reactive } from 'vue'
import { adminApi } from '../api/request'
import { useTable } from '../composables/useTable'
import { FEE_PART, FUND_FLOW_TYPE, label } from '../utils/constants'
import { saveCsv } from '../utils/export'
import { fmtDate, fmtMoney } from '../utils/format'

const typeOpts = computed(() => Object.entries(FUND_FLOW_TYPE).map(([value, v]) => ({ value, label: v })))
const feeOpts = computed(() => Object.entries(FEE_PART).map(([value, v]) => ({ value, label: v })))
const query = reactive({ type: '', fee_part: '', order_no: '' })
const { rows, total, loading, page, load, reload } = useTable(adminApi.fundFlows, query)

function reset() {
  query.type = ''
  query.fee_part = ''
  query.order_no = ''
  reload()
}

async function exportCsv() {
  saveCsv(await adminApi.exportFundFlows({ ...query }), `fund-flows-${Date.now()}.csv`)
}

onMounted(load)
</script>

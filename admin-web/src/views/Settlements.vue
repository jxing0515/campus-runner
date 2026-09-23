<template>
  <div class="page">
    <el-card shadow="never">
      <div class="filter-bar">
        <el-input v-model="query.order_no" placeholder="订单号" clearable style="width: 200px" @keyup.enter="reload" />
        <el-button type="primary" @click="reload">查询</el-button>
        <el-button @click="reset">重置</el-button>
      </div>

      <el-table v-loading="loading" :data="rows" border stripe>
        <el-table-column prop="id" label="ID" width="70" />
        <el-table-column prop="order_no" label="订单号" min-width="160" />
        <el-table-column label="跑腿费" width="110">
          <template #default="{ row }">{{ fmtMoney(row.runner_fee) }}</template>
        </el-table-column>
        <el-table-column label="平台服务费" width="120">
          <template #default="{ row }">{{ fmtMoney(row.platform_fee) }}</template>
        </el-table-column>
        <el-table-column label="实结给跑腿员" width="130">
          <template #default="{ row }">{{ fmtMoney(row.runner_income ?? row.amount) }}</template>
        </el-table-column>
        <el-table-column label="状态" width="110">
          <template #default="{ row }">
            <el-tag size="small" :type="row.status === 'settled' ? 'success' : 'warning'">{{ row.status || '已结算' }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="结算时间" width="170">
          <template #default="{ row }">{{ fmtDate(row.created_at || row.settled_at) }}</template>
        </el-table-column>
        <el-table-column prop="remark" label="备注" min-width="140" show-overflow-tooltip />
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
import { fmtDate, fmtMoney } from '../utils/format'

const query = reactive({ order_no: '' })
const { rows, total, loading, page, load, reload } = useTable(adminApi.settlements, query)

function reset() {
  query.order_no = ''
  reload()
}

onMounted(load)
</script>

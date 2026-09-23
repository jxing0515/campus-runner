<template>
  <div class="page">
    <el-card shadow="never">
      <div class="filter-bar">
        <el-input v-model="query.keyword" placeholder="操作人 / 动作 / 对象" clearable style="width: 220px" @keyup.enter="reload" />
        <el-input v-model="query.action" placeholder="动作码" clearable style="width: 160px" @keyup.enter="reload" />
        <el-date-picker
          v-model="range"
          type="daterange"
          value-format="YYYY-MM-DD"
          start-placeholder="开始日期"
          end-placeholder="结束日期"
          @change="reload"
        />
        <el-button type="primary" @click="reload">查询</el-button>
        <el-button @click="reset">重置</el-button>
        <span class="grow" />
        <el-button type="success" plain @click="exportCsv">导出 CSV</el-button>
      </div>

      <el-table v-loading="loading" :data="rows" border stripe>
        <el-table-column prop="id" label="ID" width="70" />
        <el-table-column label="操作人" width="130">
          <template #default="{ row }">{{ row.username || row.operator || '-' }}</template>
        </el-table-column>
        <el-table-column label="角色" width="110">
          <template #default="{ row }">{{ row.role || '-' }}</template>
        </el-table-column>
        <el-table-column prop="action" label="动作" min-width="150" />
        <el-table-column prop="target_type" label="对象类型" width="120" />
        <el-table-column prop="target_id" label="对象 ID" width="100" />
        <el-table-column prop="remark" label="详情" min-width="240" show-overflow-tooltip />
        <el-table-column prop="ip" label="IP" width="140" />
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
import { onMounted, reactive, ref, watch } from 'vue'
import { adminApi } from '../api/request'
import { useTable } from '../composables/useTable'
import { saveCsv } from '../utils/export'
import { fmtDate } from '../utils/format'

const query = reactive({ keyword: '', action: '', date_from: '', date_to: '' })
const { rows, total, loading, page, load, reload } = useTable(adminApi.operationLogs, query)
const range = ref([])

watch(range, (v) => {
  query.date_from = v?.[0] || ''
  query.date_to = v?.[1] || ''
})

function reset() {
  query.keyword = ''
  query.action = ''
  range.value = []
  reload()
}

async function exportCsv() {
  saveCsv(await adminApi.exportOperationLogs({ ...query }), `operation-logs-${Date.now()}.csv`)
}

onMounted(load)
</script>

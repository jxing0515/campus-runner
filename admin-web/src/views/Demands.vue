<template>
  <div class="page">
    <el-card shadow="never">
      <div class="filter-bar">
        <el-select v-model="query.status" placeholder="需求状态" clearable style="width: 160px" @change="reload">
          <el-option v-for="o in statusOpts" :key="o.value" :label="o.label" :value="o.value" />
        </el-select>
        <el-date-picker
          v-model="range"
          type="daterange"
          value-format="YYYY-MM-DD"
          start-placeholder="开始日期"
          end-placeholder="结束日期"
          @change="reload"
        />
        <el-input v-model="query.keyword" placeholder="描述 / 发单人" clearable style="width: 200px" @keyup.enter="reload" />
        <el-button type="primary" @click="reload">查询</el-button>
        <el-button @click="reset">重置</el-button>
      </div>

      <el-table v-loading="loading" :data="rows" border stripe>
        <el-table-column prop="id" label="ID" width="70" />
        <el-table-column prop="order_no" label="单号" min-width="150" />
        <el-table-column prop="student_name" label="发单人" min-width="110">
          <template #default="{ row }">{{ row.student_name || row.student?.name || '-' }}</template>
        </el-table-column>
        <el-table-column prop="description" label="需求描述" min-width="220" show-overflow-tooltip />
        <el-table-column prop="pickup_address" label="取件地" min-width="150" show-overflow-tooltip />
        <el-table-column prop="delivery_address" label="送达地" min-width="150" show-overflow-tooltip />
        <el-table-column label="跑腿费" width="100">
          <template #default="{ row }">{{ fmtMoney(row.runner_fee) }}</template>
        </el-table-column>
        <el-table-column label="状态" width="100">
          <template #default="{ row }">
            <el-tag :type="tag(ORDER_STATUS, row.status)">{{ label(ORDER_STATUS, row.status) }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="发单时间" width="170">
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
import { computed, onMounted, reactive, ref, watch } from 'vue'
import { adminApi } from '../api/request'
import { useTable } from '../composables/useTable'
import { ORDER_STATUS, label, tag } from '../utils/constants'
import { fmtDate, fmtMoney } from '../utils/format'

const statusOpts = computed(() => Object.entries(ORDER_STATUS).map(([value, it]) => ({ value, label: it[0] })))
const query = reactive({ status: '', keyword: '', date_from: '', date_to: '' })
const { rows, total, loading, page, load, reload } = useTable(adminApi.demands, query)
const range = ref([])

watch(range, (v) => {
  query.date_from = v?.[0] || ''
  query.date_to = v?.[1] || ''
})

function reset() {
  query.status = ''
  query.keyword = ''
  range.value = []
  reload()
}

onMounted(load)
</script>

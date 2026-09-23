<template>
  <div class="page">
    <el-card shadow="never">
      <div class="filter-bar">
        <el-select v-model="query.status" placeholder="审核状态" clearable style="width: 160px" @change="reload">
          <el-option label="待审核" value="pending" />
          <el-option label="已通过" value="approved" />
          <el-option label="已驳回" value="rejected" />
        </el-select>
        <el-input v-model="query.keyword" placeholder="跑腿员账号 / 姓名" clearable style="width: 200px" @keyup.enter="reload" />
        <el-button type="primary" @click="reload">查询</el-button>
        <el-button @click="reset">重置</el-button>
      </div>

      <el-table v-loading="loading" :data="rows" border stripe>
        <el-table-column prop="id" label="ID" width="70" />
        <el-table-column prop="username" label="跑腿员" min-width="110">
          <template #default="{ row }">{{ row.username || row.runner_name || '-' }}</template>
        </el-table-column>
        <el-table-column label="提现金额" width="120">
          <template #default="{ row }">{{ fmtMoney(row.amount) }}</template>
        </el-table-column>
        <el-table-column prop="method" label="方式" width="110" />
        <el-table-column prop="account" label="收款账号" min-width="150" />
        <el-table-column label="状态" width="110">
          <template #default="{ row }">
            <el-tag :type="tag(WITHDRAW_STATUS, row.status)">{{ label(WITHDRAW_STATUS, row.status) }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="reason" label="驳回原因" min-width="140" show-overflow-tooltip />
        <el-table-column label="申请时间" width="170">
          <template #default="{ row }">{{ fmtDate(row.created_at) }}</template>
        </el-table-column>
        <el-table-column label="操作" width="150" fixed="right">
          <template #default="{ row }">
            <el-button link type="success" :disabled="row.status !== 'pending'" @click="audit(row, true)">通过</el-button>
            <el-button link type="danger" :disabled="row.status !== 'pending'" @click="audit(row, false)">驳回</el-button>
          </template>
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
import { ElMessage, ElMessageBox } from 'element-plus'
import { adminApi } from '../api/request'
import { useTable } from '../composables/useTable'
import { WITHDRAW_STATUS, label, tag } from '../utils/constants'
import { fmtDate, fmtMoney } from '../utils/format'

const query = reactive({ status: 'pending', keyword: '' })
const { rows, total, loading, page, load, reload } = useTable(adminApi.withdrawals, query)

function reset() {
  query.status = ''
  query.keyword = ''
  reload()
}

async function audit(row, approve) {
  let reason = ''
  if (!approve) {
    const r = await ElMessageBox.prompt('请输入驳回原因（解冻并退回余额）', '驳回提现', {
      inputValidator: (v) => (v ? true : '原因不能为空'),
    }).catch(() => null)
    if (!r) return
    reason = r.value
  } else {
    await ElMessageBox.confirm(`确认通过 ${row.username || row.runner_name || ''} 的提现 ${row.amount}？`, '通过提现', {
      type: 'warning',
    })
  }
  await adminApi.auditWithdrawal(row.id, { approve, reason })
  ElMessage.success(approve ? '已通过' : '已驳回')
  load()
}

onMounted(load)
</script>

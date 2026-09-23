<template>
  <div class="page">
    <el-card shadow="never">
      <div class="filter-bar">
        <el-select v-model="query.status" placeholder="认证状态" clearable style="width: 160px" @change="reload">
          <el-option v-for="o in statusOpts" :key="o.value" :label="o.label" :value="o.value" />
        </el-select>
        <el-input v-model="query.keyword" placeholder="学号 / 姓名" clearable style="width: 200px" @keyup.enter="reload" />
        <el-button type="primary" @click="reload">查询</el-button>
        <el-button @click="reset">重置</el-button>
      </div>

      <el-table v-loading="loading" :data="rows" border stripe>
        <el-table-column prop="id" label="ID" width="70" />
        <el-table-column prop="student_no" label="学号" min-width="120" />
        <el-table-column prop="real_name" label="真实姓名" min-width="100" />
        <el-table-column prop="username" label="账号" min-width="120" />
        <el-table-column label="学生证" width="100">
          <template #default="{ row }">
            <el-button link type="primary" :disabled="!row.card_file_id" @click="viewCard(row)">查看</el-button>
          </template>
        </el-table-column>
        <el-table-column label="状态" width="100">
          <template #default="{ row }">
            <el-tag :type="tag(CERT_STATUS, row.status)">{{ label(CERT_STATUS, row.status) }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="reason" label="驳回原因" min-width="140" show-overflow-tooltip />
        <el-table-column label="提交时间" width="170">
          <template #default="{ row }">{{ fmtDate(row.created_at) }}</template>
        </el-table-column>
        <el-table-column label="操作" width="150" fixed="right">
          <template #default="{ row }">
            <el-button link type="success" :disabled="row.status === 'approved'" @click="audit(row, true)">通过</el-button>
            <el-button link type="danger" :disabled="row.status === 'rejected'" @click="audit(row, false)">驳回</el-button>
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
import { CERT_STATUS, label, tag } from '../utils/constants'
import { fmtDate } from '../utils/format'

const statusOpts = [
  { value: 'pending', label: '待审核' },
  { value: 'approved', label: '已通过' },
  { value: 'rejected', label: '已驳回' },
]
const query = reactive({ status: 'pending', keyword: '' })
const { rows, total, loading, page, load, reload } = useTable(adminApi.certifications, query)

function reset() {
  query.status = ''
  query.keyword = ''
  reload()
}

async function audit(row, approve) {
  const input = approve
    ? ''
    : (
        await ElMessageBox.prompt('请输入驳回原因', '驳回认证', {
          inputValidator: (v) => (v ? true : '原因不能为空'),
        }).catch(() => null)
      )?.value
  if (!approve && input === undefined) return
  await adminApi.auditCertification(row.id, { approve, reason: input || '' })
  ElMessage.success(approve ? '已通过' : '已驳回')
  load()
}

function viewCard(row) {
  window.open(`/api/v1/files/${row.card_file_id}`, '_blank')
}

onMounted(load)
</script>

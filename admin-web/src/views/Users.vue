<template>
  <div class="page">
    <el-card shadow="never">
      <div class="filter-bar">
        <el-input v-model="query.keyword" placeholder="账号 / 姓名 / 学号" clearable style="width: 220px" @keyup.enter="reload" />
        <el-select v-model="query.banned" placeholder="封禁状态" clearable style="width: 150px" @change="reload">
          <el-option label="正常" :value="0" />
          <el-option label="已封禁" :value="1" />
        </el-select>
        <el-select v-model="query.is_runner" placeholder="是否跑腿员" clearable style="width: 150px" @change="reload">
          <el-option label="是" :value="1" />
          <el-option label="否" :value="0" />
        </el-select>
        <el-button type="primary" @click="reload">查询</el-button>
        <el-button @click="reset">重置</el-button>
      </div>

      <el-table v-loading="loading" :data="rows" border stripe>
        <el-table-column prop="id" label="ID" width="70" />
        <el-table-column prop="username" label="账号" min-width="120" />
        <el-table-column prop="name" label="姓名" min-width="100" />
        <el-table-column label="角色" width="110">
          <template #default="{ row }">
            <el-tag size="small" :type="row.role === 'admin' ? 'danger' : 'info'">
              {{ row.role === 'admin' ? '管理员' : row.is_runner ? '跑腿员' : '学生' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="认证" width="100">
          <template #default="{ row }">
            <el-tag size="small" :type="tag(CERT_STATUS, row.cert_status)">{{ label(CERT_STATUS, row.cert_status) }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="信用分" width="110">
          <template #default="{ row }">
            {{ row.credit_score }}
            <el-tag size="small" :type="tag(CREDIT_LEVEL, row.credit_level)">{{ label(CREDIT_LEVEL, row.credit_level) }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="completed_count" label="完成单" width="90" />
        <el-table-column label="好评率" width="90">
          <template #default="{ row }">{{ row.good_rate != null ? Math.round(row.good_rate * 100) + '%' : '-' }}</template>
        </el-table-column>
        <el-table-column label="余额" width="110">
          <template #default="{ row }">{{ fmtMoney(row.runner_balance) }}</template>
        </el-table-column>
        <el-table-column label="状态" width="90">
          <template #default="{ row }">
            <el-tag size="small" :type="row.banned ? 'danger' : 'success'">{{ row.banned ? '已封禁' : '正常' }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="190" fixed="right">
          <template #default="{ row }">
            <el-button link type="primary" @click="openCredit(row)">调信用分</el-button>
            <el-button v-perm link type="danger" @click="toggleBan(row)">{{ row.banned ? '解封' : '封禁' }}</el-button>
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

    <el-dialog v-model="creditVisible" title="手动调整信用分" width="420px">
      <el-form :model="creditForm" label-width="90px">
        <el-form-item label="用户">{{ creditForm.name }}</el-form-item>
        <el-form-item label="变动值" required>
          <el-input-number v-model="creditForm.delta" :min="-100" :max="100" />
          <span class="muted"> 正数加分，负数扣分</span>
        </el-form-item>
        <el-form-item label="原因" required>
          <el-input v-model="creditForm.reason" type="textarea" :rows="3" placeholder="必填，写入操作日志" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="creditVisible = false">取消</el-button>
        <el-button type="primary" :disabled="!creditForm.delta || !creditForm.reason" @click="submitCredit">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { onMounted, reactive, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { adminApi } from '../api/request'
import { useTable } from '../composables/useTable'
import { CERT_STATUS, CREDIT_LEVEL, label, tag } from '../utils/constants'
import { fmtMoney } from '../utils/format'

const query = reactive({ keyword: '', banned: '', is_runner: '' })
const { rows, total, loading, page, load, reload } = useTable(adminApi.users, query)

const creditVisible = ref(false)
const creditForm = reactive({ id: null, name: '', delta: 0, reason: '' })

function reset() {
  query.keyword = ''
  query.banned = ''
  query.is_runner = ''
  reload()
}

function openCredit(row) {
  Object.assign(creditForm, { id: row.id, name: row.name || row.username, delta: 0, reason: '' })
  creditVisible.value = true
}

async function submitCredit() {
  await adminApi.creditUser(creditForm.id, { delta: creditForm.delta, reason: creditForm.reason })
  ElMessage.success('信用分已调整')
  creditVisible.value = false
  load()
}

async function toggleBan(row) {
  const next = !row.banned
  const reason = (
    await ElMessageBox.prompt(next ? '请输入封禁原因' : '请输入解封原因', next ? '封禁用户' : '解封用户', {
      inputValidator: (v) => (v ? true : '原因不能为空'),
    }).catch(() => null)
  )?.value
  if (!reason) return
  await adminApi.banUser(row.id, { banned: next, reason })
  ElMessage.success(next ? '已封禁，JWT 已拉黑' : '已解封')
  load()
}

onMounted(load)
</script>

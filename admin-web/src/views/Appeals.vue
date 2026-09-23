<template>
  <div class="page">
    <el-card shadow="never">
      <div class="filter-bar">
        <el-select v-model="query.status" placeholder="仲裁状态" clearable style="width: 160px" @change="reload">
          <el-option label="待仲裁" value="pending" />
          <el-option label="已裁决" value="resolved" />
        </el-select>
        <el-button type="primary" @click="reload">查询</el-button>
      </div>

      <el-table v-loading="loading" :data="rows" border stripe>
        <el-table-column prop="id" label="ID" width="70" />
        <el-table-column prop="order_no" label="订单号" min-width="160" />
        <el-table-column prop="appeal_type" label="申诉类型" width="130" />
        <el-table-column prop="description" label="申诉说明" min-width="200" show-overflow-tooltip />
        <el-table-column label="申诉人" width="110">
          <template #default="{ row }">{{ row.appellant_name || row.appellant || row.username || '-' }}</template>
        </el-table-column>
        <el-table-column label="状态" width="110">
          <template #default="{ row }">
            <el-tag :type="row.status === 'resolved' ? 'success' : 'warning'">
              {{ row.status === 'resolved' ? '已裁决' : '待仲裁' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="裁决结果" min-width="160">
          <template #default="{ row }">
            <span v-if="row.status !== 'resolved'" class="muted">-</span>
            <span v-else>
              {{ winnerText(row.winner) }}
              <template v-if="row.winner === 'partial'">（学生 {{ row.student_ratio }}%）</template>
            </span>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="120" fixed="right">
          <template #default="{ row }">
            <el-button link type="primary" :disabled="row.status === 'resolved'" @click="openArbitrate(row)">仲裁</el-button>
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

    <el-dialog v-model="visible" title="争议仲裁 · 资金分配" width="520px">
      <el-form ref="formRef" :model="form" :rules="rules" label-width="130px">
        <el-form-item label="订单号">{{ form.order_no }}</el-form-item>
        <el-form-item label="胜诉方" prop="winner">
          <el-radio-group v-model="form.winner">
            <el-radio v-for="o in APPEAL_WINNER" :key="o.value" :value="o.value">{{ o.label }}</el-radio>
          </el-radio-group>
        </el-form-item>
        <el-form-item v-if="form.winner === 'partial'" label="学生分配比例" prop="student_ratio">
          <el-slider v-model="form.student_ratio" :min="0" :max="100" show-input />
          <span class="muted">学生 {{ form.student_ratio }}% / 跑腿员 {{ 100 - form.student_ratio }}%</span>
        </el-form-item>
        <el-form-item label="仲裁备注" prop="remark">
          <el-input v-model="form.remark" type="textarea" :rows="3" placeholder="裁决依据，写入操作日志" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="visible = false">取消</el-button>
        <el-button type="danger" @click="submit">确认裁决并分配资金</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { onMounted, reactive, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { adminApi } from '../api/request'
import { useTable } from '../composables/useTable'
import { APPEAL_WINNER } from '../utils/constants'

const winnerText = (w) => (APPEAL_WINNER.find((o) => o.value === w) || {}).label || w || '-'
const query = reactive({ status: 'pending' })
const { rows, total, loading, page, load, reload } = useTable(adminApi.appeals, query)

const visible = ref(false)
const formRef = ref()
const form = reactive({ id: null, order_no: '', winner: 'student', student_ratio: 50, remark: '' })
const rules = {
  winner: [{ required: true, message: '请选择胜诉方', trigger: 'change' }],
  remark: [{ required: true, message: '请填写仲裁备注', trigger: 'blur' }],
}

function openArbitrate(row) {
  Object.assign(form, { id: row.id, order_no: row.order_no, winner: 'student', student_ratio: 50, remark: '' })
  visible.value = true
}

async function submit() {
  if (!(await formRef.value.validate().catch(() => false))) return
  await adminApi.arbitrate(form.id, {
    winner: form.winner,
    student_ratio: form.winner === 'partial' ? form.student_ratio : form.winner === 'student' ? 100 : 0,
    remark: form.remark,
  })
  ElMessage.success('裁决已生效，资金已分配')
  visible.value = false
  load()
}

onMounted(load)
</script>

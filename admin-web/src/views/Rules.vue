<template>
  <div class="page">
    <el-card shadow="never">
      <div class="toolbar">
        <span class="muted">仅 super_admin 可编辑；保存后后端删除规则缓存</span>
        <el-button type="primary" plain :disabled="!dirty" @click="saveAll">保存全部改动</el-button>
      </div>

      <el-table v-loading="loading" :data="rows" border stripe>
        <el-table-column prop="id" label="ID" width="70" />
        <el-table-column prop="key" label="规则键" min-width="160">
          <template #default="{ row }">{{ row.key || row.code }}</template>
        </el-table-column>
        <el-table-column prop="name" label="说明" min-width="180" show-overflow-tooltip />
        <el-table-column label="值" min-width="160">
          <template #default="{ row }">
            <el-input v-model="row.value" size="small" />
          </template>
        </el-table-column>
        <el-table-column prop="updated_at" label="更新时间" width="170">
          <template #default="{ row }">{{ fmtDate(row.updated_at) }}</template>
        </el-table-column>
        <el-table-column label="操作" width="100" fixed="right">
          <template #default="{ row }">
            <el-button link type="primary" @click="saveOne(row)">保存</el-button>
          </template>
        </el-table-column>
      </el-table>

      <el-divider />

      <el-form ref="formRef" :model="form" :rules="rules" inline label-width="90px">
        <el-form-item label="规则键" prop="key">
          <el-input v-model="form.key" placeholder="如 credit.publish_min" style="width: 220px" />
        </el-form-item>
        <el-form-item label="说明" prop="name">
          <el-input v-model="form.name" style="width: 200px" />
        </el-form-item>
        <el-form-item label="值" prop="value">
          <el-input v-model="form.value" style="width: 160px" />
        </el-form-item>
        <el-form-item>
          <el-button type="success" @click="create">新增规则</el-button>
        </el-form-item>
      </el-form>
    </el-card>
  </div>
</template>

<script setup>
import { onMounted, reactive, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { adminApi } from '../api/request'
import { fmtDate } from '../utils/format'

const loading = ref(false)
const rows = ref([])
const dirty = ref(false)
const formRef = ref()
const form = reactive({ key: '', name: '', value: '' })
const rules = {
  key: [{ required: true, message: '请输入规则键', trigger: 'blur' }],
  value: [{ required: true, message: '请输入值', trigger: 'blur' }],
}

async function load() {
  loading.value = true
  try {
    const data = await adminApi.rules()
    rows.value = data?.results || data || []
    dirty.value = false
  } finally {
    loading.value = false
  }
}

async function saveOne(row) {
  await adminApi.updateRule(row.id, { value: row.value, name: row.name, key: row.key || row.code })
  ElMessage.success(`已保存：${row.key || row.code}`)
  dirty.value = false
  load()
}

async function saveAll() {
  for (const row of rows.value) {
    await adminApi.updateRule(row.id, { value: row.value, name: row.name, key: row.key || row.code })
  }
  ElMessage.success('全部规则已保存')
  load()
}

async function create() {
  if (!(await formRef.value.validate().catch(() => false))) return
  await adminApi.createRule({ ...form })
  ElMessage.success('规则已新增')
  Object.assign(form, { key: '', name: '', value: '' })
  load()
}

onMounted(load)
</script>

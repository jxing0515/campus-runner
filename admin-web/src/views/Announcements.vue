<template>
  <div class="page">
    <el-card shadow="never">
      <el-divider content-position="left">发布公告</el-divider>
      <el-form ref="formRef" :model="form" :rules="rules" label-width="90px">
        <el-form-item label="标题" prop="title">
          <el-input v-model="form.title" placeholder="公告标题" style="max-width: 420px" />
        </el-form-item>
        <el-form-item label="内容" prop="content">
          <el-input v-model="form.content" type="textarea" :rows="4" placeholder="公告正文，发布时投递通知给用户" />
        </el-form-item>
        <el-form-item>
          <el-button type="primary" :loading="saving" @click="publish">发布公告</el-button>
        </el-form-item>
      </el-form>

      <el-divider content-position="left">已发布公告</el-divider>
      <el-table v-loading="loading" :data="rows" border stripe>
        <el-table-column prop="id" label="ID" width="70" />
        <el-table-column prop="title" label="标题" min-width="180" show-overflow-tooltip />
        <el-table-column prop="content" label="内容" min-width="260" show-overflow-tooltip />
        <el-table-column label="发布人" width="120">
          <template #default="{ row }">{{ row.publisher_name || row.created_by || '-' }}</template>
        </el-table-column>
        <el-table-column label="发布时间" width="170">
          <template #default="{ row }">{{ fmtDate(row.created_at) }}</template>
        </el-table-column>
        <el-table-column label="操作" width="100" fixed="right">
          <template #default="{ row }">
            <el-button link type="danger" @click="remove(row)">删除</el-button>
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
import { onMounted, reactive, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { adminApi } from '../api/request'
import { useTable } from '../composables/useTable'
import { fmtDate } from '../utils/format'

const query = reactive({})
const { rows, total, loading, page, load, reload } = useTable(adminApi.announcements, query)

const saving = ref(false)
const formRef = ref()
const form = reactive({ title: '', content: '' })
const rules = {
  title: [{ required: true, message: '请输入标题', trigger: 'blur' }],
  content: [{ required: true, message: '请输入内容', trigger: 'blur' }],
}

async function publish() {
  if (!(await formRef.value.validate().catch(() => false))) return
  saving.value = true
  try {
    await adminApi.createAnnouncement({ ...form })
    ElMessage.success('公告已发布并投递通知')
    Object.assign(form, { title: '', content: '' })
    reload()
  } finally {
    saving.value = false
  }
}

async function remove(row) {
  await ElMessageBox.confirm(`确认删除公告「${row.title}」？`, '删除公告', { type: 'warning' })
  await adminApi.deleteAnnouncement(row.id)
  ElMessage.success('已删除')
  load()
}

onMounted(load)
</script>

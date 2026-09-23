<template>
  <div class="login-wrap">
    <el-card class="login-card">
      <h2>校园互助跑腿 · 管理后台</h2>
      <p class="muted">仅平台管理员可登录（super_admin / operator）</p>
      <el-form ref="formRef" :model="form" :rules="rules" label-position="top" @keyup.enter="submit">
        <el-form-item label="账号" prop="username">
          <el-input v-model="form.username" placeholder="请输入管理员账号" clearable />
        </el-form-item>
        <el-form-item label="密码" prop="password">
          <el-input v-model="form.password" type="password" show-password placeholder="请输入密码" />
        </el-form-item>
        <el-button type="primary" class="submit" :loading="loading" @click="submit">登录</el-button>
      </el-form>
    </el-card>
  </div>
</template>

<script setup>
import { reactive, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { authApi } from '../api/request'
import { useAuthStore } from '../stores/auth'

const route = useRoute()
const router = useRouter()
const auth = useAuthStore()
const formRef = ref()
const loading = ref(false)
const form = reactive({ username: '', password: '' })
const rules = {
  username: [{ required: true, message: '请输入账号', trigger: 'blur' }],
  password: [{ required: true, message: '请输入密码', trigger: 'blur' }],
}

async function submit() {
  if (!(await formRef.value.validate().catch(() => false))) return
  loading.value = true
  try {
    const data = await authApi.login({ ...form })
    auth.setLogin(data)
    ElMessage.success(`欢迎，${data.user?.name || data.user?.username || '管理员'}`)
    router.replace(route.query.redirect || '/dashboard')
  } catch {
    /* 错误提示由拦截器统一弹出 */
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.login-wrap { height: 100%; display: flex; align-items: center; justify-content: center; background: #f0f2f5; }
.login-card { width: 380px; padding: 8px 6px; }
h2 { margin: 0 0 6px; font-size: 18px; }
.muted { margin: 0 0 18px; }
.submit { width: 100%; margin-top: 6px; }
</style>

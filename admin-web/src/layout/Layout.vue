<template>
  <el-container class="shell">
    <el-aside width="210px" class="aside">
      <div class="brand">校园互助 · 管理后台</div>
      <el-menu router :default-active="active" background-color="#2b3648" text-color="#c6ccd8" active-text-color="#fff">
        <el-menu-item v-for="m in visibleMenus" :key="m.path" :index="m.path">
          <el-icon><component :is="m.icon" /></el-icon>
          <span>{{ m.title }}</span>
        </el-menu-item>
      </el-menu>
    </el-aside>

    <el-container>
      <el-header class="header">
        <span class="muted">当前角色：{{ roleText }}</span>
        <div class="right">
          <span>{{ user?.name || user?.username || '未登录' }}</span>
          <el-tag size="small" :type="isSuper ? 'danger' : 'info'">{{ roleText }}</el-tag>
          <el-button link type="primary" @click="logout">退出</el-button>
        </div>
      </el-header>
      <el-main class="main">
        <router-view />
      </el-main>
    </el-container>
  </el-container>
</template>

<script setup>
import { computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessageBox } from 'element-plus'
import { menus } from '../router/menus'
import { useAuthStore } from '../stores/auth'

const route = useRoute()
const router = useRouter()
const auth = useAuthStore()

const user = computed(() => auth.user)
const isSuper = computed(() => auth.isSuper)
const roleText = computed(() => (isSuper.value ? '超级管理员' : '运营管理员'))
const active = computed(() => '/' + route.path.split('/')[1])
const visibleMenus = computed(() => menus.filter((m) => !m.perm || m.perm === user.value?.role))

async function logout() {
  await ElMessageBox.confirm('确认退出登录？', '提示', { type: 'warning' })
  await auth.logout()
  router.push('/login')
}
</script>

<style scoped>
.shell { height: 100%; }
.aside { background: #2b3648; overflow-y: auto; }
.brand { color: #fff; font-size: 15px; font-weight: 600; padding: 18px 16px; border-bottom: 1px solid #3a465c; }
.aside :deep(.el-menu) { border-right: none; }
.header {
  background: #fff;
  border-bottom: 1px solid #ebeef5;
  display: flex;
  align-items: center;
  justify-content: space-between;
}
.header .right { display: flex; align-items: center; gap: 10px; }
.main { background: #f5f7fa; padding: 0; }
</style>

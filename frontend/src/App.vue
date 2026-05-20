<template>
  <el-container class="app-container">
    <!-- Header -->
    <el-header class="app-header">
      <div class="header-content">
        <h1 class="app-title">CR代码分析平台</h1>
        <el-menu
          :default-active="activeMenu"
          mode="horizontal"
          :ellipsis="false"
          @select="handleMenuSelect"
          class="nav-menu"
        >
          <el-menu-item index="/">
            <el-icon><HomeFilled /></el-icon>
            <span>首页</span>
          </el-menu-item>
          <el-menu-item index="/history">
            <el-icon><Clock /></el-icon>
            <span>历史记录</span>
          </el-menu-item>
        </el-menu>
      </div>
    </el-header>

    <!-- Main Content -->
    <el-main class="app-main">
      <router-view />
    </el-main>

    <!-- Footer -->
    <el-footer class="app-footer">
      <span>CR代码分析平台 &copy; {{ currentYear }}</span>
    </el-footer>
  </el-container>
</template>

<script setup>
import { computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { HomeFilled, Clock } from '@element-plus/icons-vue'

const route = useRoute()
const router = useRouter()

const activeMenu = computed(() => {
  if (route.path.startsWith('/report')) {
    return '/'
  }
  return route.path
})

const currentYear = computed(() => new Date().getFullYear())

const handleMenuSelect = (index) => {
  router.push(index)
}
</script>

<style>
* {
  margin: 0;
  padding: 0;
  box-sizing: border-box;
}

body {
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, 'Open Sans', 'Helvetica Neue', sans-serif;
  -webkit-font-smoothing: antialiased;
  -moz-osx-font-smoothing: grayscale;
  background-color: #f5f7fa;
}

.app-container {
  min-height: 100vh;
}

.app-header {
  background-color: #fff;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
  height: auto !important;
  padding: 0 24px;
  position: sticky;
  top: 0;
  z-index: 100;
}

.header-content {
  display: flex;
  align-items: center;
  justify-content: space-between;
  max-width: 1400px;
  margin: 0 auto;
  height: 60px;
}

.app-title {
  font-size: 20px;
  font-weight: 600;
  color: #409eff;
  margin: 0;
}

.nav-menu {
  border-bottom: none !important;
  background: transparent;
}

.app-main {
  max-width: 1400px;
  margin: 0 auto;
  padding: 24px;
  width: 100%;
}

.app-footer {
  background-color: #fff;
  border-top: 1px solid #e4e7ed;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #909399;
  font-size: 14px;
}
</style>

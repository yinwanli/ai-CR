<template>
  <div class="home">
    <!-- Analysis Input Card -->
    <el-card class="input-card" shadow="hover">
      <template #header>
        <div class="card-header">
          <span>开始分析</span>
        </div>
      </template>
      <el-form :model="form" :rules="rules" ref="formRef" label-width="100px">
        <el-form-item label="发布版本号" prop="release_no">
          <el-input
            v-model="form.release_no"
            placeholder="请输入发布版本号，例如：v1.0.0"
            clearable
            @keyup.enter="handleAnalyze"
          />
        </el-form-item>
        <el-form-item>
          <el-button
            type="primary"
            :loading="loading"
            @click="handleAnalyze"
          >
            <el-icon v-if="!loading"><VideoPlay /></el-icon>
            开始分析
          </el-button>
        </el-form-item>
      </el-form>
    </el-card>

    <!-- Recent Analyses Card -->
    <el-card class="recent-card" shadow="hover">
      <template #header>
        <div class="card-header">
          <span>最近分析</span>
          <el-button text type="primary" @click="goToHistory">
            查看全部
            <el-icon><ArrowRight /></el-icon>
          </el-button>
        </div>
      </template>
      <el-table
        :data="recentAnalyses"
        v-loading="tableLoading"
        stripe
        style="width: 100%"
        @row-click="handleRowClick"
      >
        <el-table-column prop="release_no" label="版本号" min-width="120" />
        <el-table-column prop="status" label="状态" width="100">
          <template #default="{ row }">
            <el-tag :type="getStatusType(row.status)" size="small">
              {{ getStatusText(row.status) }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="coverage" label="覆盖率" width="100">
          <template #default="{ row }">
            <span v-if="row.coverage !== null && row.coverage !== undefined">
              {{ (row.coverage * 100).toFixed(1) }}%
            </span>
            <span v-else>-</span>
          </template>
        </el-table-column>
        <el-table-column prop="created_at" label="分析时间" width="180">
          <template #default="{ row }">
            {{ formatDate(row.created_at) }}
          </template>
        </el-table-column>
        <el-table-column label="操作" width="80" fixed="right">
          <template #default="{ row }">
            <el-button
              text
              type="primary"
              size="small"
              @click.stop="goToReport(row.id)"
            >
              查看
            </el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { VideoPlay, ArrowRight } from '@element-plus/icons-vue'
import { analyze, getHistory } from '../api'

const router = useRouter()

const formRef = ref(null)
const form = ref({
  release_no: ''
})
const rules = {
  release_no: [
    { required: true, message: '请输入发布版本号', trigger: 'blur' }
  ]
}
const loading = ref(false)
const tableLoading = ref(false)
const recentAnalyses = ref([])

const getStatusType = (status) => {
  const types = {
    pending: 'info',
    running: 'warning',
    completed: 'success',
    failed: 'danger'
  }
  return types[status] || 'info'
}

const getStatusText = (status) => {
  const texts = {
    pending: '待处理',
    running: '进行中',
    completed: '已完成',
    failed: '失败'
  }
  return texts[status] || status
}

const formatDate = (dateStr) => {
  if (!dateStr) return '-'
  const date = new Date(dateStr)
  return date.toLocaleString('zh-CN', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit'
  })
}

const handleAnalyze = async () => {
  if (!formRef.value) return

  try {
    await formRef.value.validate()
    loading.value = true

    const result = await analyze(form.value.release_no)

    ElMessage.success('分析任务已创建')

    // Navigate to report page
    router.push(`/report/${result.task_id}`)
  } catch (error) {
    if (error.message) {
      ElMessage.error(error.message)
    }
  } finally {
    loading.value = false
  }
}

const loadRecentAnalyses = async () => {
  try {
    tableLoading.value = true
    const data = await getHistory(5)
    // 兼容多种返回形态: 数组 / { data: [...] } / { list: [...] } / 其它 → 兜底为 []
    let list = []
    if (Array.isArray(data)) {
      list = data
    } else if (data && typeof data === 'object') {
      if (Array.isArray(data.data)) list = data.data
      else if (Array.isArray(data.list)) list = data.list
      else if (Array.isArray(data.items)) list = data.items
    }
    recentAnalyses.value = list
  } catch (error) {
    recentAnalyses.value = []
    console.error('Failed to load recent analyses:', error)
  } finally {
    tableLoading.value = false
  }
}

const goToReport = (taskId) => {
  router.push(`/report/${taskId}`)
}

const goToHistory = () => {
  router.push('/history')
}

const handleRowClick = (row) => {
  goToReport(row.id)
}

onMounted(() => {
  loadRecentAnalyses()
})
</script>

<style scoped>
.home {
  max-width: 900px;
  margin: 0 auto;
}

.input-card {
  margin-bottom: 24px;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-weight: 600;
}

.recent-card {
  margin-bottom: 24px;
}

.el-table {
  cursor: pointer;
}

:deep(.el-table__row:hover) {
  background-color: #ecf5ff;
}
</style>

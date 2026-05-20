<template>
  <div class="report" v-loading="pageLoading">
    <!-- Task Status Card -->
    <el-card class="status-card" shadow="hover" v-if="task">
      <template #header>
        <div class="card-header">
          <div class="header-left">
            <span class="release-no">{{ task.release_no }}</span>
            <el-tag :type="getStatusType(task.status)" size="large">
              {{ getStatusText(task.status) }}
            </el-tag>
          </div>
          <el-button text @click="refreshData" :loading="refreshing">
            <el-icon><Refresh /></el-icon>
            刷新
          </el-button>
        </div>
      </template>

      <!-- Coverage Dashboard -->
      <div class="dashboard" v-if="report">
        <el-row :gutter="24">
          <!-- Coverage Progress -->
          <el-col :span="8">
            <div class="coverage-section">
              <h3>测试覆盖率</h3>
              <el-progress
                type="circle"
                :percentage="coveragePercent"
                :width="150"
                :stroke-width="12"
                :color="getCoverageColor(coveragePercent)"
              />
              <p class="coverage-text">{{ coveragePercent.toFixed(1) }}%</p>
            </div>
          </el-col>

          <!-- File Stats -->
          <el-col :span="8">
            <div class="stats-section">
              <h3>文件统计</h3>
              <div class="stat-item">
                <span class="stat-label">后端文件</span>
                <span class="stat-value backend">{{ fileStats.backend }}</span>
              </div>
              <div class="stat-item">
                <span class="stat-label">前端文件</span>
                <span class="stat-value frontend">{{ fileStats.frontend }}</span>
              </div>
              <div class="stat-item">
                <span class="stat-label">总计</span>
                <span class="stat-value">{{ fileStats.total }}</span>
              </div>
            </div>
          </el-col>

          <!-- Summary -->
          <el-col :span="8">
            <div class="summary-section">
              <h3>分析摘要</h3>
              <div class="stat-item">
                <span class="stat-label">需求数量</span>
                <span class="stat-value">{{ summary.requirementCount }}</span>
              </div>
              <div class="stat-item">
                <span class="stat-label">问题数量</span>
                <span class="stat-value warning">{{ summary.issueCount }}</span>
              </div>
              <div class="stat-item">
                <span class="stat-label">分析时间</span>
                <span class="stat-value small">{{ formatDate(task.created_at) }}</span>
              </div>
            </div>
          </el-col>
        </el-row>
      </div>

      <!-- Loading State for Running Task -->
      <div class="loading-state" v-else-if="task.status === 'running'">
        <el-icon class="loading-icon"><Loading /></el-icon>
        <p>分析进行中，请稍候...</p>
      </div>

      <!-- Error State -->
      <div class="error-state" v-else-if="task.status === 'failed'">
        <el-icon class="error-icon"><CircleClose /></el-icon>
        <p>分析失败</p>
        <p class="error-message">{{ task.error_message || '未知错误' }}</p>
      </div>
    </el-card>

    <!-- Requirements Table -->
    <el-card class="requirements-card" shadow="hover" v-if="report && report.requirements">
      <template #header>
        <div class="card-header">
          <span>需求列表</span>
          <el-tag type="info">{{ report.requirements.length }} 条</el-tag>
        </div>
      </template>
      <el-table :data="report.requirements" stripe style="width: 100%">
        <el-table-column prop="key" label="需求ID" width="150" />
        <el-table-column prop="summary" label="需求摘要" min-width="200" show-overflow-tooltip />
        <el-table-column prop="type" label="类型" width="100">
          <template #default="{ row }">
            <el-tag size="small" :type="row.type === 'bug' ? 'danger' : 'primary'">
              {{ row.type === 'bug' ? 'Bug' : '需求' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="coverage" label="覆盖率" width="120">
          <template #default="{ row }">
            <el-progress
              :percentage="(row.coverage || 0) * 100"
              :stroke-width="8"
              :show-text="false"
              :color="getCoverageColor((row.coverage || 0) * 100)"
            />
            <span class="coverage-label">{{ ((row.coverage || 0) * 100).toFixed(0) }}%</span>
          </template>
        </el-table-column>
        <el-table-column prop="status" label="状态" width="100">
          <template #default="{ row }">
            <el-tag
              size="small"
              :type="row.status === 'covered' ? 'success' : row.status === 'partial' ? 'warning' : 'info'"
            >
              {{ getRequirementStatusText(row.status) }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="100" fixed="right">
          <template #default="{ row }">
            <el-button
              text
              type="primary"
              size="small"
              @click="handleMark('requirement', row.key, 'reviewed')"
            >
              标记
            </el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <!-- Issues Table -->
    <el-card class="issues-card" shadow="hover" v-if="report && report.issues">
      <template #header>
        <div class="card-header">
          <span>问题列表</span>
          <el-tag type="warning">{{ report.issues.length }} 条</el-tag>
        </div>
      </template>
      <el-table :data="report.issues" stripe style="width: 100%">
        <el-table-column prop="file" label="文件" min-width="200" show-overflow-tooltip />
        <el-table-column prop="line" label="行号" width="80" />
        <el-table-column prop="severity" label="严重程度" width="100">
          <template #default="{ row }">
            <el-tag
              size="small"
              :type="getSeverityType(row.severity)"
            >
              {{ row.severity }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="message" label="问题描述" min-width="250" show-overflow-tooltip />
        <el-table-column prop="status" label="状态" width="100">
          <template #default="{ row }">
            <el-tag
              size="small"
              :type="row.status === 'confirmed' ? 'success' : row.status === 'dismissed' ? 'info' : 'warning'"
            >
              {{ getIssueStatusText(row.status) }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="160" fixed="right">
          <template #default="{ row }">
            <el-button
              text
              type="success"
              size="small"
              @click="handleMark('issue', row.id, 'confirmed')"
            >
              确认
            </el-button>
            <el-button
              text
              type="info"
              size="small"
              @click="handleMark('issue', row.id, 'dismissed')"
            >
              忽略
            </el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <!-- Analysis Summary -->
    <el-card class="analysis-summary-card" shadow="hover" v-if="report && report.summary">
      <template #header>
        <div class="card-header">
          <span>分析总结</span>
        </div>
      </template>
      <div class="summary-content">
        <p>{{ report.summary }}</p>
      </div>
    </el-card>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { useRoute } from 'vue-router'
import { ElMessage } from 'element-plus'
import { Refresh, Loading, CircleClose } from '@element-plus/icons-vue'
import { getTask, getReport, mark } from '../api'

const route = useRoute()
const taskId = route.params.id

const task = ref(null)
const report = ref(null)
const pageLoading = ref(true)
const refreshing = ref(false)
let pollingTimer = null

const coveragePercent = computed(() => {
  if (report.value && report.value.coverage !== null) {
    return report.value.coverage * 100
  }
  return 0
})

const fileStats = computed(() => {
  if (report.value && report.value.file_stats) {
    return {
      backend: report.value.file_stats.backend || 0,
      frontend: report.value.file_stats.frontend || 0,
      total: (report.value.file_stats.backend || 0) + (report.value.file_stats.frontend || 0)
    }
  }
  return { backend: 0, frontend: 0, total: 0 }
})

const summary = computed(() => {
  return {
    requirementCount: report.value?.requirements?.length || 0,
    issueCount: report.value?.issues?.length || 0
  }
})

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

const getRequirementStatusText = (status) => {
  const texts = {
    covered: '已覆盖',
    partial: '部分覆盖',
    uncovered: '未覆盖'
  }
  return texts[status] || status
}

const getIssueStatusText = (status) => {
  const texts = {
    open: '待处理',
    confirmed: '已确认',
    dismissed: '已忽略'
  }
  return texts[status] || status
}

const getSeverityType = (severity) => {
  const types = {
    critical: 'danger',
    high: 'danger',
    medium: 'warning',
    low: 'info',
    info: 'info'
  }
  return types[severity?.toLowerCase()] || 'info'
}

const getCoverageColor = (percentage) => {
  if (percentage >= 80) return '#67c23a'
  if (percentage >= 50) return '#e6a23c'
  return '#f56c6c'
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

const loadTask = async () => {
  try {
    task.value = await getTask(taskId)
  } catch (error) {
    ElMessage.error('获取任务信息失败')
    console.error(error)
  }
}

const loadReport = async () => {
  try {
    report.value = await getReport(taskId)
  } catch (error) {
    console.error('Failed to load report:', error)
  }
}

const refreshData = async () => {
  refreshing.value = true
  try {
    await loadTask()
    if (task.value?.status === 'completed') {
      await loadReport()
    }
  } finally {
    refreshing.value = false
  }
}

const handleMark = async (type, id, status) => {
  try {
    await mark(taskId, { type, id, status })
    ElMessage.success('操作成功')
    await loadReport()
  } catch (error) {
    ElMessage.error(error.message || '操作失败')
  }
}

const startPolling = () => {
  pollingTimer = setInterval(async () => {
    if (task.value?.status === 'running' || task.value?.status === 'pending') {
      await loadTask()
      if (task.value?.status === 'completed') {
        await loadReport()
        stopPolling()
      }
    }
  }, 3000)
}

const stopPolling = () => {
  if (pollingTimer) {
    clearInterval(pollingTimer)
    pollingTimer = null
  }
}

onMounted(async () => {
  try {
    pageLoading.value = true
    await loadTask()
    if (task.value?.status === 'completed') {
      await loadReport()
    } else if (task.value?.status === 'running' || task.value?.status === 'pending') {
      startPolling()
    }
  } finally {
    pageLoading.value = false
  }
})

onUnmounted(() => {
  stopPolling()
})
</script>

<style scoped>
.report {
  max-width: 1200px;
  margin: 0 auto;
}

.status-card {
  margin-bottom: 24px;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.header-left {
  display: flex;
  align-items: center;
  gap: 12px;
}

.release-no {
  font-size: 18px;
  font-weight: 600;
}

.dashboard {
  padding: 20px 0;
}

.coverage-section,
.stats-section,
.summary-section {
  text-align: center;
  padding: 16px;
}

.coverage-section h3,
.stats-section h3,
.summary-section h3 {
  margin-bottom: 20px;
  color: #303133;
  font-size: 16px;
}

.coverage-text {
  margin-top: 12px;
  font-size: 24px;
  font-weight: 600;
  color: #409eff;
}

.stat-item {
  display: flex;
  justify-content: space-between;
  padding: 12px 0;
  border-bottom: 1px solid #ebeef5;
}

.stat-item:last-child {
  border-bottom: none;
}

.stat-label {
  color: #909399;
}

.stat-value {
  font-weight: 600;
  font-size: 18px;
}

.stat-value.backend {
  color: #67c23a;
}

.stat-value.frontend {
  color: #409eff;
}

.stat-value.warning {
  color: #e6a23c;
}

.stat-value.small {
  font-size: 14px;
  font-weight: normal;
}

.loading-state,
.error-state {
  text-align: center;
  padding: 60px 20px;
  color: #909399;
}

.loading-icon {
  font-size: 48px;
  animation: spin 1s linear infinite;
  color: #409eff;
}

.error-icon {
  font-size: 48px;
  color: #f56c6c;
}

.error-message {
  margin-top: 8px;
  color: #f56c6c;
  font-size: 14px;
}

@keyframes spin {
  from {
    transform: rotate(0deg);
  }
  to {
    transform: rotate(360deg);
  }
}

.requirements-card,
.issues-card,
.analysis-summary-card {
  margin-bottom: 24px;
}

.coverage-label {
  font-size: 12px;
  color: #606266;
  margin-left: 8px;
}

.summary-content {
  line-height: 1.8;
  color: #606266;
  white-space: pre-wrap;
}
</style>

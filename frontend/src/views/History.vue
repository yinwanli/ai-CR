<template>
  <div class="history">
    <el-card shadow="hover">
      <template #header>
        <div class="card-header">
          <span>分析历史</span>
          <el-button text type="primary" @click="loadHistory" :loading="loading">
            <el-icon><Refresh /></el-icon>
            刷新
          </el-button>
        </div>
      </template>
      <el-table
        v-if="loading || historyData.length > 0"
        :data="historyData"
        v-loading="loading"
        stripe
        style="width: 100%"
        @row-click="handleRowClick"
      >
        <el-table-column prop="release_no" label="版本号" min-width="150">
          <template #default="{ row }">
            <span class="release-no-link">{{ row.release_no }}</span>
          </template>
        </el-table-column>
        <el-table-column prop="status" label="状态" width="100">
          <template #default="{ row }">
            <el-tag :type="getStatusType(row.status)" size="small">
              {{ getStatusText(row.status) }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="coverage" label="测试覆盖率" width="120">
          <template #default="{ row }">
            <div v-if="row.coverage !== null && row.coverage !== undefined" class="coverage-cell">
              <el-progress
                :percentage="row.coverage * 100"
                :stroke-width="6"
                :show-text="false"
                :color="getCoverageColor(row.coverage * 100)"
              />
              <span class="coverage-text">{{ (row.coverage * 100).toFixed(1) }}%</span>
            </div>
            <span v-else>-</span>
          </template>
        </el-table-column>
        <el-table-column prop="requirement_count" label="需求数" width="80">
          <template #default="{ row }">
            <span>{{ row.requirement_count || 0 }}</span>
          </template>
        </el-table-column>
        <el-table-column prop="issue_count" label="问题数" width="80">
          <template #default="{ row }">
            <el-tag
              v-if="row.issue_count > 0"
              type="warning"
              size="small"
            >
              {{ row.issue_count }}
            </el-tag>
            <span v-else>{{ row.issue_count || 0 }}</span>
          </template>
        </el-table-column>
        <el-table-column prop="created_at" label="创建时间" width="180">
          <template #default="{ row }">
            {{ formatDate(row.created_at) }}
          </template>
        </el-table-column>
        <el-table-column prop="completed_at" label="完成时间" width="180">
          <template #default="{ row }">
            {{ formatDate(row.completed_at) }}
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
              详情
            </el-button>
          </template>
        </el-table-column>
      </el-table>

      <!-- Pagination -->
      <div class="pagination-container" v-if="total > pageSize">
        <el-pagination
          v-model:current-page="currentPage"
          :page-size="pageSize"
          :total="total"
          layout="prev, pager, next"
          @current-change="handlePageChange"
        />
      </div>

      <!-- Empty State -->
      <el-empty v-if="!loading && historyData.length === 0" description="暂无分析记录" />
    </el-card>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { Refresh } from '@element-plus/icons-vue'
import { getHistory } from '../api'

const router = useRouter()

const loading = ref(false)
const historyData = ref([])
const currentPage = ref(1)
const pageSize = ref(20)
const total = ref(0)

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

const loadHistory = async () => {
  try {
    loading.value = true
    const data = await getHistory(100) // Get all records, pagination is handled on frontend
    // 兼容多种返回形态: 数组 / { data: [...] } / { list: [...] } / 其它 → 兜底为 []
    let list = []
    if (Array.isArray(data)) {
      list = data
    } else if (data && typeof data === 'object') {
      if (Array.isArray(data.data)) list = data.data
      else if (Array.isArray(data.list)) list = data.list
      else if (Array.isArray(data.items)) list = data.items
    }
    historyData.value = list
    total.value = list.length
  } catch (error) {
    historyData.value = []
    total.value = 0
    ElMessage.error('获取历史记录失败')
    console.error(error)
  } finally {
    loading.value = false
  }
}

const handlePageChange = (page) => {
  currentPage.value = page
}

const goToReport = (taskId) => {
  router.push(`/report/${taskId}`)
}

const handleRowClick = (row) => {
  goToReport(row.id)
}

onMounted(() => {
  loadHistory()
})
</script>

<style scoped>
.history {
  max-width: 1200px;
  margin: 0 auto;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-weight: 600;
}

.el-table {
  cursor: pointer;
}

:deep(.el-table__row:hover) {
  background-color: #ecf5ff;
}

.release-no-link {
  color: #409eff;
  font-weight: 500;
}

.coverage-cell {
  display: flex;
  align-items: center;
  gap: 8px;
}

.coverage-text {
  font-size: 12px;
  color: #606266;
  white-space: nowrap;
}

.pagination-container {
  display: flex;
  justify-content: center;
  margin-top: 20px;
  padding: 16px 0;
}
</style>

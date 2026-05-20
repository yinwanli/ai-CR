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
        <el-form-item label="发布版本" prop="release_no">
          <el-select
            v-model="form.release_no"
            placeholder="选择本版本 commit（将对比分支上一版）"
            filterable
            clearable
            allow-create
            default-first-option
            :loading="commitsLoading"
            style="width: 100%"
            @change="onReleaseChange"
          >
            <el-option
              v-for="item in commitOptions"
              :key="item.sha"
              :label="optionLabel(item)"
              :value="item.short_sha"
            />
          </el-select>
          <div v-if="selectedCommit?.base_sha" class="compare-hint">
            将分析：{{ selectedCommit.short_sha }} 相对上一版 {{ selectedCommit.base_sha.slice(0, 7) }} 的改动
          </div>
          <div v-else-if="selectedCommit && !selectedCommit.base_sha" class="compare-hint warn">
            该提交为分支首个版本，无法与上一版对比
          </div>
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
              @click.stop="goToReport(row.task_id)"
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
import { analyze, getHistory, getGithubCommits } from '../api'

const router = useRouter()

const formRef = ref(null)
const form = ref({
  release_no: ''
})
const rules = {
  release_no: [
    { required: true, message: '请选择或输入发布版本', trigger: 'change' }
  ]
}
const loading = ref(false)
const commitsLoading = ref(false)
const tableLoading = ref(false)
const recentAnalyses = ref([])
const commitOptions = ref([])
const selectedCommit = ref(null)

const optionLabel = (item) => {
  const msg = item.message ? item.message.slice(0, 40) : ''
  return `${item.short_sha} · ${msg}`
}

const onReleaseChange = (shortSha) => {
  const found = commitOptions.value.find(
    (c) => c.short_sha === shortSha || c.sha.startsWith(shortSha)
  )
  selectedCommit.value = found || null
}

const loadCommits = async () => {
  commitsLoading.value = true
  try {
    const res = await getGithubCommits()
    const payload = res?.data ?? res
    const list = payload?.commits
    commitOptions.value = Array.isArray(list) ? list : []
    if (commitOptions.value.length && !form.value.release_no) {
      const first = commitOptions.value[0]
      if (first.base_sha) {
        form.value.release_no = first.short_sha
        selectedCommit.value = first
      }
    }
  } catch (error) {
    commitOptions.value = []
    ElMessage.warning(error.message || '加载 GitHub 提交列表失败，可手动输入版本号')
  } finally {
    commitsLoading.value = false
  }
}

const getStatusType = (status) => {
  const types = {
    pending: 'info',
    analyzing: 'warning',
    success: 'success',
    failed: 'danger'
  }
  return types[status] || 'info'
}

const getStatusText = (status) => {
  const texts = {
    pending: '待处理',
    analyzing: '分析中',
    success: '已完成',
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

    const commit = selectedCommit.value
    if (commit && !commit.base_sha) {
      ElMessage.warning('该版本为分支首个提交，请选择有上一版的 commit')
      return
    }

    loading.value = true

    const result = await analyze({
      release_no: form.value.release_no,
      head_sha: commit?.sha || form.value.release_no,
      base_sha: commit?.base_sha || null
    })

    ElMessage.success('分析任务已创建')

    const taskId = result?.data?.task_id ?? result?.task_id
    router.push(`/report/${taskId}`)
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
      // 后端标准包: { code, message, data: HistoryItem[] }
      const inner = data.data
      if (Array.isArray(inner)) list = inner
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
  goToReport(row.task_id)
}

onMounted(() => {
  loadCommits()
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

.compare-hint {
  margin-top: 6px;
  font-size: 12px;
  color: #909399;
  line-height: 1.4;
}

.compare-hint.warn {
  color: #e6a23c;
}

.el-table {
  cursor: pointer;
}

:deep(.el-table__row:hover) {
  background-color: #ecf5ff;
}
</style>

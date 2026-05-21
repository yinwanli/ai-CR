<template>
  <div class="home">
    <el-card class="input-card" shadow="hover">
      <template #header>
        <div class="card-header">
          <span>开始分析</span>
        </div>
      </template>
      <el-form :model="form" :rules="rules" ref="formRef" label-width="100px">
        <el-form-item label="代码模块" prop="module_id">
          <el-select
            v-model="form.module_id"
            placeholder="选择代码模块"
            :loading="modulesLoading"
            style="width: 100%"
            @change="onModuleChange"
          >
            <el-option
              v-for="m in moduleOptions"
              :key="m.id"
              :label="`${m.name} (${m.repo})`"
              :value="m.id"
            />
          </el-select>
        </el-form-item>

        <el-form-item label="分支" prop="branch">
          <el-select
            v-model="form.branch"
            placeholder="选择分支"
            filterable
            allow-create
            :loading="branchesLoading"
            :disabled="!form.module_id"
            style="width: 100%"
            @change="onBranchChange"
          >
            <el-option
              v-for="b in branchOptions"
              :key="b.name"
              :label="b.name"
              :value="b.name"
            />
          </el-select>
        </el-form-item>

        <el-form-item label="对比范围">
          <el-radio-group v-model="form.compare_mode" @change="onCompareModeChange">
            <el-radio label="prev_commit">相邻提交（本提交 vs 分支上一版）</el-radio>
            <el-radio label="vs_master">相对基线（本提交 vs {{ baselineBranch }}）</el-radio>
          </el-radio-group>
        </el-form-item>

        <el-form-item label="发布版本" prop="release_no">
          <el-select
            v-model="form.release_no"
            placeholder="选择 commit"
            filterable
            clearable
            allow-create
            :loading="commitsLoading"
            :disabled="!form.branch"
            style="width: 100%"
            @change="onReleaseChange"
          >
            <el-option
              v-for="item in commitOptions"
              :key="item.sha"
              :label="item.short_sha"
              :value="item.short_sha"
            >
              <span class="commit-option-sha">{{ item.short_sha }}</span>
              <span v-if="item.message" class="commit-option-msg">{{ item.message }}</span>
            </el-option>
          </el-select>
        </el-form-item>
        <el-form-item v-if="form.branch && compareHintText" label=" " class="hint-form-item">
          <div class="compare-hint" :class="{ warn: compareHintWarn }">
            {{ compareHintText }}
          </div>
        </el-form-item>

        <el-form-item>
          <el-button type="primary" :loading="loading" :disabled="!form.module_id" @click="handleAnalyze">
            <el-icon v-if="!loading"><VideoPlay /></el-icon>
            开始分析
          </el-button>
        </el-form-item>
      </el-form>
    </el-card>

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
        <el-table-column prop="release_no" label="版本号" min-width="180">
          <template #default="{ row }">
            {{ formatReleaseNo(row.release_no) }}
          </template>
        </el-table-column>
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
            <el-button text type="primary" size="small" @click.stop="goToReport(row.task_id)">
              查看
            </el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { VideoPlay, ArrowRight } from '@element-plus/icons-vue'
import {
  analyze,
  getHistory,
  getCodeModules,
  getGithubBranches,
  getGithubCommits,
  extractTaskId
} from '../api'

const router = useRouter()

const formRef = ref(null)
const form = ref({
  module_id: '',
  branch: '',
  compare_mode: 'prev_commit',
  release_no: ''
})

const rules = {
  module_id: [{ required: true, message: '请选择代码模块', trigger: 'change' }],
  branch: [{ required: true, message: '请选择分支', trigger: 'change' }],
  release_no: [{ required: true, message: '请选择发布版本', trigger: 'change' }]
}

const loading = ref(false)
const modulesLoading = ref(false)
const branchesLoading = ref(false)
const commitsLoading = ref(false)
const tableLoading = ref(false)

const moduleOptions = ref([])
const branchOptions = ref([])
const commitOptions = ref([])
const selectedCommit = ref(null)
const recentAnalyses = ref([])
const baselineBranch = ref('main')

const selectedModule = computed(() =>
  moduleOptions.value.find((m) => m.id === form.value.module_id)
)

const compareHintText = computed(() => {
  if (!form.value.branch) return ''
  if (form.value.compare_mode === 'vs_master') {
    if (selectedCommit.value) {
      return `将分析 ${selectedCommit.value.short_sha}（${form.value.branch}）相对 ${baselineBranch.value} 基线的全部改动`
    }
    return `相对基线：所选 commit 将与 ${baselineBranch.value} 分支当前版本对比`
  }
  if (selectedCommit.value?.base_sha) {
    return `将分析 ${selectedCommit.value.short_sha} 相对上一提交 ${selectedCommit.value.base_sha.slice(0, 7)} 的改动`
  }
  if (selectedCommit.value && !selectedCommit.value.base_sha) {
    return '该提交为分支首个版本，无法做相邻提交对比，请改用「相对基线」或选择其他 commit'
  }
  return '相邻提交：所选 commit 将与其在分支上的上一提交对比'
})

const compareHintWarn = computed(
  () =>
    form.value.compare_mode === 'prev_commit' &&
    selectedCommit.value &&
    !selectedCommit.value.base_sha
)

const formatReleaseNo = (releaseNo) => {
  if (!releaseNo) return '-'
  let s = releaseNo
  const vsMaster = s.endsWith('@vs-master')
  if (vsMaster) s = s.replace('@vs-master', '')
  const colon = s.indexOf(':')
  const modulePart = colon > 0 ? s.slice(0, colon) : ''
  const shaPart = colon > 0 ? s.slice(colon + 1) : s
  const suffix = vsMaster ? ' (vs 基线)' : ''
  return modulePart ? `${modulePart} / ${shaPart}${suffix}` : `${shaPart}${suffix}`
}

const resetBranchAndRelease = () => {
  form.value.branch = ''
  form.value.release_no = ''
  branchOptions.value = []
  commitOptions.value = []
  selectedCommit.value = null
}

const resetRelease = () => {
  form.value.release_no = ''
  commitOptions.value = []
  selectedCommit.value = null
}

const loadModules = async () => {
  modulesLoading.value = true
  try {
    const res = await getCodeModules()
    const list = res?.data ?? res
    moduleOptions.value = Array.isArray(list) ? list : []
    if (moduleOptions.value.length === 1 && !form.value.module_id) {
      form.value.module_id = moduleOptions.value[0].id
      baselineBranch.value = moduleOptions.value[0].baseline_branch || 'main'
      await loadBranches()
    }
  } catch (error) {
    moduleOptions.value = []
    ElMessage.warning(error.message || '加载代码模块失败')
  } finally {
    modulesLoading.value = false
  }
}

const loadBranches = async () => {
  if (!form.value.module_id) return
  branchesLoading.value = true
  try {
    const res = await getGithubBranches(form.value.module_id)
    const payload = res?.data ?? res
    const list = payload?.branches
    branchOptions.value = Array.isArray(list) ? list : []
    if (payload?.baseline_branch) baselineBranch.value = payload.baseline_branch
    const mod = selectedModule.value
    const defaultBr = payload?.default_branch || mod?.default_branch
    if (defaultBr && !form.value.branch) {
      const has = branchOptions.value.some((b) => b.name === defaultBr)
      form.value.branch = has ? defaultBr : branchOptions.value[0]?.name || defaultBr
      await loadCommits()
    }
  } catch (error) {
    branchOptions.value = []
    ElMessage.warning(error.message || '加载分支列表失败')
  } finally {
    branchesLoading.value = false
  }
}

const loadCommits = async () => {
  if (!form.value.module_id || !form.value.branch) return
  commitsLoading.value = true
  try {
    const res = await getGithubCommits(form.value.module_id, form.value.branch)
    const payload = res?.data ?? res
    commitOptions.value = Array.isArray(payload?.commits) ? payload.commits : []
    if (payload?.baseline_branch) baselineBranch.value = payload.baseline_branch

    if (commitOptions.value.length && !form.value.release_no) {
      const first = commitOptions.value[0]
      if (form.value.compare_mode === 'vs_master' || first.base_sha) {
        form.value.release_no = first.short_sha
        selectedCommit.value = first
      }
    }
  } catch (error) {
    commitOptions.value = []
    ElMessage.warning(error.message || '加载提交列表失败')
  } finally {
    commitsLoading.value = false
  }
}

const onModuleChange = async () => {
  const mod = selectedModule.value
  if (mod?.baseline_branch) baselineBranch.value = mod.baseline_branch
  resetBranchAndRelease()
  await loadBranches()
}

const onBranchChange = async () => {
  resetRelease()
  await loadCommits()
}

const onCompareModeChange = () => {
  // 切换对比范围时仅更新下方灰色说明，发布版本框只保留 commit 短 SHA
}

const onReleaseChange = (shortSha) => {
  const found = commitOptions.value.find(
    (c) => c.short_sha === shortSha || c.sha.startsWith(shortSha)
  )
  selectedCommit.value = found || null
}

const handleAnalyze = async () => {
  if (!formRef.value) return
  try {
    await formRef.value.validate()
    const commit = selectedCommit.value
    if (form.value.compare_mode === 'prev_commit' && commit && !commit.base_sha) {
      ElMessage.warning('该提交为分支首个版本，请换 commit 或改用「相对基线」')
      return
    }

    loading.value = true
    const result = await analyze({
      module_id: form.value.module_id,
      release_no: form.value.release_no,
      head_sha: commit?.sha || form.value.release_no,
      base_sha: form.value.compare_mode === 'prev_commit' ? (commit?.base_sha || null) : null,
      compare_mode: form.value.compare_mode,
      branch: form.value.branch
    })

    const taskId = extractTaskId(result)
    if (taskId == null) {
      ElMessage.error('创建成功但未返回任务 ID')
      await loadRecentAnalyses()
      return
    }
    ElMessage.success('分析任务已创建')
    router.push(`/report/${taskId}`)
  } catch (error) {
    if (error.message) ElMessage.error(error.message)
  } finally {
    loading.value = false
  }
}

const getStatusType = (status) => {
  const types = { pending: 'info', analyzing: 'warning', success: 'success', failed: 'danger' }
  return types[status] || 'info'
}

const getStatusText = (status) => {
  const texts = { pending: '待处理', analyzing: '分析中', success: '已完成', failed: '失败' }
  return texts[status] || status
}

const formatDate = (dateStr) => {
  if (!dateStr) return '-'
  return new Date(dateStr).toLocaleString('zh-CN', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit'
  })
}

const loadRecentAnalyses = async () => {
  try {
    tableLoading.value = true
    const data = await getHistory(5)
    let list = []
    if (Array.isArray(data)) list = data
    else if (data && typeof data === 'object') {
      if (Array.isArray(data.data)) list = data.data
      else if (Array.isArray(data.list)) list = data.list
    }
    recentAnalyses.value = list
  } catch {
    recentAnalyses.value = []
  } finally {
    tableLoading.value = false
  }
}

const goToReport = (taskId) => {
  if (taskId == null || taskId === '' || taskId === 'undefined') {
    ElMessage.warning('无法打开报告：缺少任务 ID')
    return
  }
  router.push(`/report/${taskId}`)
}

const goToHistory = () => router.push('/history')

const handleRowClick = (row) => goToReport(row.task_id)

onMounted(async () => {
  await loadModules()
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

.hint-form-item :deep(.el-form-item__label) {
  visibility: hidden;
}

.commit-option-sha {
  font-weight: 500;
  margin-right: 8px;
}

.commit-option-msg {
  font-size: 12px;
  color: #909399;
}

.compare-hint {
  font-size: 12px;
  color: #909399;
  line-height: 1.5;
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

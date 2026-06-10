<template>
  <div class="profile-page">
    <!-- Personal Info Card -->
    <h2 class="page-title">个人信息</h2>
    <div class="page-card">
      <el-form :model="editForm" label-width="80px" size="default">
        <el-row :gutter="16">
          <el-col :span="12">
            <el-form-item label="邮箱">
              <el-input :model-value="userStore.currentUser?.email" disabled />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="余额">
              <el-tag type="warning" size="large">{{ ((userStore.currentUser?.balance || 0) / 100).toFixed(2) }}</el-tag>
              <el-button size="small" style="margin-left: 8px" @click="showRecharge">充值</el-button>
            </el-form-item>
          </el-col>
        </el-row>
        <el-row :gutter="16">
          <el-col :span="12">
            <el-form-item label="手机号">
              <el-input v-model="editForm.phone" placeholder="请输入手机号" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="收货地址">
              <el-input v-model="editForm.address" placeholder="请输入收货地址" />
            </el-form-item>
          </el-col>
        </el-row>
        <el-row :gutter="16">
          <el-col :span="12">
            <el-form-item label="新密码">
              <el-input v-model="editForm.password" type="password" placeholder="留空则不修改" show-password />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item>
              <el-button type="primary" :loading="saving" @click="saveProfile">保存修改</el-button>
            </el-form-item>
          </el-col>
        </el-row>
      </el-form>
    </div>

    <!-- Consumption Report -->
    <h2 class="page-title" style="margin-top: 24px">我的消费报告</h2>

    <!-- New User Prompt -->
    <div v-if="rfmData && rfmData.my_segment === '新用户'" class="page-card new-user-card">
      <el-icon :size="48" color="#409EFF"><UserFilled /></el-icon>
      <h3>{{ rfmData.my_segment_advice }}</h3>
      <p>完成首笔订单后，即可查看您的专属消费分析报告</p>
      <el-button type="primary" @click="router.push({ name: 'Home' })">去逛逛</el-button>
    </div>

    <template v-else>
      <!-- RFM Segment -->
      <div class="page-card" v-if="rfmData">
        <h3 class="section-title">用户分群</h3>
        <div class="segment-info">
          <el-tag :type="segmentTagType" size="large" effect="dark">{{ rfmData.my_segment }}</el-tag>
          <p class="segment-advice">{{ rfmData.my_segment_advice }}</p>
        </div>
      </div>

      <!-- RFM Radar Chart -->
      <div class="page-card" v-if="rfmData && rfmData.radar">
        <h3 class="section-title">RFM 雷达图</h3>
        <div ref="radarChartRef" style="height: 350px"></div>
      </div>

      <!-- Spending Trend -->
      <div class="page-card">
        <h3 class="section-title">消费趋势</h3>
        <div ref="trendChartRef" style="height: 300px"></div>
        <div v-if="!trendData.length" class="empty-state" style="padding: 20px">暂无消费记录</div>
      </div>

      <!-- Category Preference -->
      <div class="page-card">
        <h3 class="section-title">品类偏好</h3>
        <div ref="categoryChartRef" style="height: 300px"></div>
        <div v-if="!categoryData.length" class="empty-state" style="padding: 20px">暂无消费记录</div>
      </div>
    </template>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onBeforeUnmount, nextTick } from 'vue'
import { useRouter } from 'vue-router'
import { UserFilled } from '@element-plus/icons-vue'
import { analyticsApi, authApi } from '../api'
import { useUserStore } from '../stores/user'
import { ElMessage, ElMessageBox } from 'element-plus'
import * as echarts from 'echarts'

const router = useRouter()
const userStore = useUserStore()

const editForm = ref({
  phone: userStore.currentUser?.phone || '',
  address: userStore.currentUser?.address || '',
  password: '',
})
const saving = ref(false)

async function saveProfile() {
  saving.value = true
  try {
    const res = await authApi.updateMe({
      phone: editForm.value.phone,
      address: editForm.value.address,
      password: editForm.value.password,
    })
    userStore.currentUser = res.data
    editForm.value.password = ''
    ElMessage.success('个人信息已更新')
  } catch {
    ElMessage.error('更新失败')
  } finally {
    saving.value = false
  }
}

async function showRecharge() {
  try {
    const { value: rawAmount } = await ElMessageBox.prompt('请输入充值金额（元）', '账户充值', {
      confirmButtonText: '确认充值',
      cancelButtonText: '取消',
      inputPattern: /^\d+(\.\d{1,2})?$/,
      inputErrorMessage: '请输入有效金额',
    })
    const amount = Math.round(parseFloat(rawAmount) * 100)
    const res = await authApi.recharge(amount)
    userStore.currentUser = res.data
    ElMessage.success(`充值成功 ¥${rawAmount}`)
  } catch {
    // cancelled
  }
}
const rfmData = ref(null)
const trendData = ref([])
const categoryData = ref([])
const radarChartRef = ref(null)
const trendChartRef = ref(null)
const categoryChartRef = ref(null)

// ECharts 实例管理，防止内存泄漏
const chartInstances = []
function createChart(dom) {
  const existing = echarts.getInstanceByDom(dom)
  if (existing) existing.dispose()
  const chart = echarts.init(dom)
  chartInstances.push(chart)
  return chart
}
function handleResize() { chartInstances.forEach(c => c.resize()) }
onMounted(() => window.addEventListener('resize', handleResize))
onBeforeUnmount(() => {
  chartInstances.forEach(c => c.dispose())
  chartInstances.length = 0
  window.removeEventListener('resize', handleResize)
})

const segmentTagType = computed(() => {
  const map = { '高价值客户': 'success', '潜力客户': 'warning', '一般客户': '', '流失预警': 'danger', '低价值客户': 'info' }
  return map[rfmData.value?.my_segment] || ''
})

async function loadRfm() {
  try {
    const res = await analyticsApi.getUserRfm()
    rfmData.value = res.data
    if (res.data.radar && res.data.my_segment !== '新用户') {
      await nextTick()
      renderRadarChart(res.data.radar)
    }
  } catch {
    rfmData.value = null
  }
}

async function loadTrend() {
  try {
    const res = await analyticsApi.getUserTrend()
    trendData.value = res.data || []
    if (trendData.value.length) {
      await nextTick()
      renderTrendChart()
    }
  } catch {
    trendData.value = []
  }
}

async function loadCategory() {
  try {
    const res = await analyticsApi.getUserCategoryPreference()
    categoryData.value = res.data || []
    if (categoryData.value.length) {
      await nextTick()
      renderCategoryChart()
    }
  } catch {
    categoryData.value = []
  }
}

function renderRadarChart(radar) {
  const chart = createChart(radarChartRef.value)
  chart.setOption({
    tooltip: {},
    legend: { data: ['我的评分', '平均评分'], bottom: 0 },
    radar: {
      indicator: [
        { name: 'Recency (最近购买)', max: 5 },
        { name: 'Frequency (购买频次)', max: 5 },
        { name: 'Monetary (消费金额)', max: 5 },
      ],
    },
    series: [{
      type: 'radar',
      data: [
        { value: radar.my_scores, name: '我的评分', areaStyle: { opacity: 0.2 } },
        { value: radar.avg_scores, name: '平均评分', areaStyle: { opacity: 0.1 } },
      ],
    }],
    color: ['#409EFF', '#E6A23C'],
  })
}

function renderTrendChart() {
  const chart = createChart(trendChartRef.value)
  chart.setOption({
    tooltip: { trigger: 'axis' },
    legend: { data: ['消费金额', '订单数'], bottom: 0 },
    xAxis: { type: 'category', data: trendData.value.map(t => t.month) },
    yAxis: [
      { type: 'value', name: '消费金额 (元)', position: 'left' },
      { type: 'value', name: '订单数', position: 'right' },
    ],
    series: [
      { name: '消费金额', type: 'line', data: trendData.value.map(t => (t.amount / 100).toFixed(2)), smooth: true, areaStyle: { opacity: 0.15 }, yAxisIndex: 0 },
      { name: '订单数', type: 'bar', data: trendData.value.map(t => t.count), yAxisIndex: 1 },
    ],
    color: ['#409EFF', '#67C23A'],
  })
}

function renderCategoryChart() {
  const chart = createChart(categoryChartRef.value)
  chart.setOption({
    tooltip: { trigger: 'item', formatter: '{b}: {c} ({d}%)' },
    series: [{
      type: 'pie',
      radius: ['40%', '70%'],
      data: categoryData.value.map(c => ({ name: c.category, value: c.amount })),
      label: { formatter: '{b}\n{d}%' },
    }],
    color: ['#409EFF', '#67C23A', '#E6A23C', '#F56C6C', '#909399', '#66B1FF', '#B37FEB'],
  })
}

onMounted(() => {
  loadRfm()
  loadTrend()
  loadCategory()
})
</script>

<style scoped>
.new-user-card {
  text-align: center;
  padding: 48px 24px;
}
.new-user-card h3 {
  margin: 16px 0 8px;
  font-size: 18px;
}
.new-user-card p {
  color: var(--text-secondary);
  margin-bottom: 20px;
}
.section-title {
  font-size: 16px;
  font-weight: 600;
  margin-bottom: 16px;
}
.segment-info {
  display: flex;
  align-items: center;
  gap: 16px;
}
.segment-advice {
  color: var(--text-regular);
  font-size: 14px;
}
</style>

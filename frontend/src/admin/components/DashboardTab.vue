<template>
  <div>
    <h2 class="page-title">数据看板</h2>
    <el-row :gutter="16" class="stat-cards">
      <el-col :span="dashboardStats.length > 4 ? 4 : 6" v-for="stat in dashboardStats" :key="stat.label">
        <div class="stat-card">
          <div class="stat-value">{{ stat.value }}</div>
          <div class="stat-label">{{ stat.label }}</div>
        </div>
      </el-col>
    </el-row>
    <el-row :gutter="16">
      <el-col :span="12">
        <div class="kpi-card">
          <h3 class="card-title">销售趋势</h3>
          <div ref="dashTrendRef" class="chart-box" style="height:280px"></div>
        </div>
      </el-col>
      <el-col :span="12">
        <div class="kpi-card">
          <h3 class="card-title">品类销售占比</h3>
          <div ref="dashCategoryRef" class="chart-box" style="height:280px"></div>
        </div>
      </el-col>
    </el-row>
    <el-row :gutter="16" class="mt-md">
      <el-col :span="12">
        <div class="kpi-card">
          <h3 class="card-title">客户分群概览</h3>
          <div ref="dashRfmRef" class="chart-box" style="height:280px"></div>
        </div>
      </el-col>
      <el-col :span="12">
        <div class="kpi-card">
          <h3 class="card-title">流失风险分布</h3>
          <div ref="dashChurnRef" class="chart-box" style="height:280px"></div>
        </div>
      </el-col>
    </el-row>
    <el-row :gutter="16" class="mt-md">
      <el-col :span="24">
        <div class="kpi-card">
          <h3 class="card-title">关键指标仪表盘</h3>
          <div ref="dashGaugeRef" class="chart-box" style="height:220px"></div>
        </div>
      </el-col>
    </el-row>
    <el-row :gutter="16" class="mt-md">
      <el-col :span="24">
        <div class="kpi-card" style="border: 1px solid #E6A23C">
          <h3 class="card-title" style="color:#E6A23C">系统维护</h3>
          <div style="padding:8px 0">
            <p style="margin-bottom:12px;color:#909399;font-size:13px">
              <b>重置账户：</b>恢复管理员/测试账户为默认信息。<br>
              <b>清空测试数据：</b>仅清理测试产生的订单、购物车、评价和分析结果，UCI原始商品/订单/用户不受影响。<br>
              <b>导入数据：</b>将 UCI Online Retail 数据集导入系统（如已导入则跳过）。
            </p>
            <el-button type="warning" size="small" style="margin-right:8px" @click="resetAccounts" :loading="resetting">重置系统账户</el-button>
            <el-button type="danger" size="small" style="margin-right:8px" @click="resetAll" :loading="resetting">清空测试数据</el-button>
            <el-button type="success" size="small" @click="importUciData" :loading="importing">导入 UCI 数据</el-button>
          </div>
        </div>
      </el-col>
    </el-row>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, nextTick } from 'vue'
import { adminAnalyticsApi, adminApi } from '../../api'
import { ElMessage, ElMessageBox } from 'element-plus'
import { useECharts } from '../composables/useECharts'

const { chartInstances, initChart, disposeChartRefs, handleResize, safeRender } = useECharts()

const dashboard = ref(null)
const dashTrendRef = ref(null), dashCategoryRef = ref(null), dashRfmRef = ref(null), dashChurnRef = ref(null)
const dashGaugeRef = ref(null)

const resetting = ref(false)
const importing = ref(false)

const dashboardStats = computed(() => {
  if (!dashboard.value) return []
  const d = dashboard.value
  const stats = [
    { label: '总用户', value: (d.total_users || 0).toLocaleString() },
    { label: '总商品', value: (d.total_products || 0).toLocaleString() },
    { label: '总订单', value: (d.total_orders || 0).toLocaleString() },
    { label: '总销售额', value: '¥' + ((d.total_revenue || 0) / 100).toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 }) },
  ]
  if (d.clustering_k) stats.push({ label: '客户分群K', value: d.clustering_k })
  if (d.churn_auc) stats.push({ label: '流失AUC', value: d.churn_auc.toFixed(3) })
  if (d.forecast_smape) stats.push({ label: '预测sMAPE', value: (d.forecast_smape * 100).toFixed(2) + '%' })
  if (d.association_rules_count) stats.push({ label: '关联规则数', value: d.association_rules_count })
  return stats
})

async function loadDashboard() {
  try {
    const res = await adminAnalyticsApi.getDashboard()
    dashboard.value = res.data
    await loadDashboardCharts()
  } catch { dashboard.value = null }
}

async function loadDashboardCharts() {
  try {
    const [trendRes, catRes, rfmRes, churnRes] = await Promise.all([
      adminAnalyticsApi.getSalesTrend(),
      adminAnalyticsApi.getHotProducts({ limit: 50 }),
      adminAnalyticsApi.getRfmSummary(),
      adminAnalyticsApi.getChurnList({ per_page: 15000 }),
    ])
    await nextTick()
    safeRender(() => renderDashTrend(trendRes.data || []))
    safeRender(() => renderDashCategory(catRes.data?.products || []))
    safeRender(() => renderDashRfm(rfmRes.data?.segments || []))
    safeRender(() => renderDashChurn(churnRes.data?.predictions || []))
    safeRender(() => renderDashGauge(dashboard.value))
  } catch {}
}

function renderDashTrend(trend) {
  const chart = initChart(dashTrendRef)
  if (!chart || !trend.length) return
  const fmtY = (v) => {
    if (Math.abs(v) >= 1e4) return (v / 1e4).toFixed(0) + '万'
    return v.toFixed(0)
  }
  chart.setOption({
    tooltip: { confine: true, extraCssText: 'z-index:1;', trigger: 'axis' },
    grid: { left: 60, right: 15, top: 15, bottom: 25 },
    xAxis: { type: 'category', data: trend.slice(-12).map(t => (t.date || '').slice(5)), axisLabel: { fontSize: 10 } },
    yAxis: { type: 'value', name: '销售额 (元)', axisLabel: { formatter: fmtY, fontSize: 10 } },
    animationDuration: 600,
    series: [{ type: 'bar', data: trend.slice(-12).map(t => +(((t.amount || 0) / 100).toFixed(2))), itemStyle: { color: '#409EFF', borderRadius: [4, 4, 0, 0] }, animationDelay: idx => idx * 40 }],
  })
}

function renderDashCategory(products) {
  const chart = initChart(dashCategoryRef)
  if (!chart || !products.length) return
  const catMap = {}
  products.forEach(p => { catMap[p.category_name || '其他'] = (catMap[p.category_name || '其他'] || 0) + 1 })
  const data = Object.entries(catMap).sort((a, b) => b[1] - a[1]).slice(0, 8)
  chart.setOption({
    tooltip: { trigger: 'item', confine: true, extraCssText: 'z-index:1;', formatter: '{b}: {c} ({d}%)' },
    series: [{ type: 'pie', radius: ['42%', '72%'], center: ['50%', '52%'], data: data.map(d => ({ name: d[0], value: d[1] })), label: { fontSize: 10 }, itemStyle: { borderRadius: 3, borderColor: '#fff', borderWidth: 2 }, animationDuration: 600 }],
    color: ['#409EFF', '#67C23A', '#E6A23C', '#F56C6C', '#909399', '#36CFC9', '#597EF7', '#9254DE'],
  })
}

function renderDashRfm(segments) {
  const chart = initChart(dashRfmRef)
  if (!chart || !segments.length) return
  chart.setOption({
    tooltip: { trigger: 'item', confine: true, extraCssText: 'z-index:1;', formatter: '{b}: {c}人 ({d}%)' },
    series: [{ type: 'pie', radius: ['42%', '72%'], center: ['50%', '52%'], data: segments.map(s => ({ name: s.segment, value: s.count })), label: { fontSize: 11 }, animationDuration: 600 }],
    color: ['#67C23A', '#409EFF', '#E6A23C', '#F56C6C', '#909399'],
  })
}

function renderDashChurn(predictions) {
  const chart = initChart(dashChurnRef)
  if (!chart || !predictions.length) return
  const bins = { low: 0, medium: 0, high: 0 }
  predictions.forEach(p => {
    const level = p.risk_level || 'low'
    if (level === 'high') bins.high++
    else if (level === 'medium') bins.medium++
    else bins.low++
  })
  chart.setOption({
    tooltip: { confine: true, extraCssText: 'z-index:1;', trigger: 'axis' },
    grid: { left: 50, right: 15, top: 15, bottom: 25 },
    xAxis: { type: 'category', data: ['低风险', '中风险', '高风险'] },
    yAxis: { type: 'value', name: '人' },
    animationDuration: 600,
    series: [{ type: 'bar', data: [{ value: bins.low, itemStyle: { color: '#67C23A' } }, { value: bins.medium, itemStyle: { color: '#E6A23C' } }, { value: bins.high, itemStyle: { color: '#F56C6C' } }], label: { show: true, position: 'top', fontSize: 12, fontWeight: 600 } }],
  })
}

function renderDashGauge(d) {
  const chart = initChart(dashGaugeRef)
  if (!chart || !d) return
  const totalUsers = d.total_users || 1
  const orderRate = d.total_orders > 0 ? Math.min((d.paid_orders || 0) / d.total_orders * 100, 100) : 0
  const churnRate = Math.min(((d.churn_risk_count || 0) / totalUsers) * 100, 100)
  const revenuePerUser = ((d.total_revenue || 0) / 100 / totalUsers).toFixed(2)
  chart.setOption({
    series: [
      { type: 'gauge', center: ['16%', '52%'], radius: '70%', startAngle: 220, endAngle: -40, min: 0, max: 100, title: { offsetCenter: [0, '92%'], fontSize: 11 }, detail: { fontSize: 16, fontWeight: 700, formatter: '{value}%', offsetCenter: [0, '55%'] }, data: [{ value: +orderRate.toFixed(1), name: '订单完成率' }], axisLine: { lineStyle: { width: 10, color: [[0.5, '#67C23A'], [0.8, '#E6A23C'], [1, '#F56C6C']] } }, animationDuration: 800 },
      { type: 'gauge', center: ['50%', '52%'], radius: '70%', startAngle: 220, endAngle: -40, min: 0, max: 100, title: { offsetCenter: [0, '92%'], fontSize: 11 }, detail: { fontSize: 16, fontWeight: 700, formatter: '{value}%', offsetCenter: [0, '55%'] }, data: [{ value: +churnRate.toFixed(1), name: '流失风险率' }], axisLine: { lineStyle: { width: 10, color: [[0.3, '#67C23A'], [0.6, '#E6A23C'], [1, '#F56C6C']] } }, animationDuration: 800 },
      { type: 'gauge', center: ['84%', '52%'], radius: '70%', startAngle: 220, endAngle: -40, min: 0, max: Math.max(+revenuePerUser * 2 || 100, 100), title: { offsetCenter: [0, '92%'], fontSize: 11 }, detail: { fontSize: 16, fontWeight: 700, formatter: '¥{value}', offsetCenter: [0, '55%'] }, data: [{ value: +revenuePerUser, name: '人均消费(元)' }], axisLine: { lineStyle: { width: 10, color: [[0.5, '#409EFF'], [0.8, '#66B1FF'], [1, '#36CFC9']] } }, animationDuration: 800 },
    ],
  })
}

async function resetAccounts() {
  try {
    await ElMessageBox.confirm('确认将管理员和测试账户恢复为默认信息？', '重置账户', { confirmButtonText: '确认重置', cancelButtonText: '取消', type: 'warning' })
    resetting.value = true
    await adminApi.resetSystem('accounts')
    ElMessage.success('系统账户已重置为默认信息')
  } catch {} finally { resetting.value = false }
}

async function resetAll() {
  try {
    await ElMessageBox.confirm('确认清空所有测试数据？\n将删除：测试订单、购物车记录、评价、分析数据（RFM/预测/关联规则/流失预警）\n并将管理员和测试账户恢复为默认信息。\nUCI原始商品/订单/用户不受影响。\n此操作不可撤销！', '清空测试数据', { confirmButtonText: '确认清空', cancelButtonText: '取消', type: 'error' })
    resetting.value = true
    await adminApi.resetSystem('all')
    ElMessage.success('已清空测试数据，UCI原始数据不受影响')
    setTimeout(() => location.reload(), 1500)
  } catch {} finally { resetting.value = false }
}

async function importUciData() {
  try {
    await ElMessageBox.confirm('将 UCI Online Retail 数据集导入系统？\n如果已导入过则会跳过。', '导入数据', { confirmButtonText: '确认导入', cancelButtonText: '取消', type: 'info' })
    importing.value = true
    await adminApi.importData()
    ElMessage.success('数据导入已启动，请稍后刷新页面查看')
  } catch {} finally { importing.value = false }
}

onMounted(() => {
  loadDashboard()
})
</script>

<style scoped>
.admin-page { margin: -20px; }
.admin-sidebar { background: var(--bg-card); border-right: 1px solid var(--border-color); min-height: calc(100vh - 60px); display: flex; flex-direction: column; }
.sidebar-brand { padding: 20px; border-bottom: 1px solid var(--border-color); text-align: center; }
.sidebar-brand strong { display: block; font-size: 18px; color: var(--color-primary); }
.sidebar-brand span { font-size: 12px; color: var(--text-secondary); }
.sidebar-footer { margin-top: auto; padding: 16px; border-top: 1px solid var(--border-color); }
.compute-time { font-size: 12px; color: var(--text-secondary); margin-bottom: 8px; display: flex; align-items: center; gap: 4px; }
.admin-main { padding: 24px; background: var(--bg-page); min-height: calc(100vh - 60px); }

/* Bento Box card */
.kpi-card {
  background: var(--bg-card);
  border-radius: 12px;
  padding: 20px 24px;
  margin-bottom: 16px;
  box-shadow: 0 1px 3px rgba(0,0,0,.04), 0 1px 2px rgba(0,0,0,.06);
  border: 1px solid var(--border-color);
  transition: box-shadow .25s ease, border-color .25s ease;
}
.kpi-card:hover { box-shadow: 0 4px 12px rgba(0,0,0,.08); border-color: #d0d5dd; }
.card-title { font-size: 15px; font-weight: 600; margin-bottom: 14px; color: var(--text-primary); letter-spacing: .01em; }
.card-toolbar { display: flex; justify-content: space-between; align-items: center; margin-bottom: 14px; }

.stat-cards { margin-bottom: 16px; }
.stat-card {
  background: var(--bg-card);
  border-radius: 12px;
  padding: 22px 16px;
  text-align: center;
  box-shadow: 0 1px 3px rgba(0,0,0,.04), 0 1px 2px rgba(0,0,0,.06);
  border: 1px solid var(--border-color);
  transition: box-shadow .25s ease, transform .2s ease;
}
.stat-card:hover { box-shadow: 0 4px 12px rgba(0,0,0,.08); transform: translateY(-2px); }
.stat-value { font-size: 26px; font-weight: 700; color: var(--color-primary); letter-spacing: -.01em; }
.stat-label { font-size: 12px; color: var(--text-secondary); margin-top: 6px; text-transform: uppercase; letter-spacing: .05em; }

.mini-kpi {
  background: var(--bg-card);
  border-radius: 10px;
  padding: 16px;
  text-align: center;
  box-shadow: 0 1px 3px rgba(0,0,0,.04);
  border: 1px solid var(--border-color);
}
.mini-kpi-label { font-size: 11px; color: var(--text-secondary); margin-bottom: 6px; letter-spacing: .03em; }
.mini-kpi-value { font-size: 24px; font-weight: 700; }

/* A. 语义化分级 KPI 卡片 */
.metric-card {
  background: var(--bg-card);
  border-radius: 10px;
  padding: 16px 18px;
  box-shadow: 0 1px 3px rgba(0,0,0,.04);
  border: 1px solid var(--border-color);
  border-left: 3px solid var(--border-color);
  height: 120px;
  display: flex;
  flex-direction: column;
  justify-content: space-between;
  transition: box-shadow .2s, transform .2s;
  overflow: hidden;
}
.metric-card:hover { box-shadow: 0 4px 14px rgba(0,0,0,.08); transform: translateY(-1px); }
.metric-card--blue { border-left-color: #409EFF; }
.metric-card--green { border-left-color: #67C23A; }
.metric-card--orange { border-left-color: #E6A23C; }
.metric-card--red { border-left-color: #F56C6C; }
.metric-card__head { display: flex; align-items: center; gap: 6px; color: var(--text-secondary); }
.metric-card--blue .metric-card__head .metric-card__icon { color: #409EFF; }
.metric-card--green .metric-card__head .metric-card__icon { color: #67C23A; }
.metric-card--orange .metric-card__head .metric-card__icon { color: #E6A23C; }
.metric-card--red .metric-card__head .metric-card__icon { color: #F56C6C; }
.metric-card__icon { font-size: 16px; }
.metric-card__title { font-size: 13px; font-weight: 500; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.metric-card__value { display: flex; align-items: baseline; gap: 4px; }
.metric-card__number {
  font-size: 24px;
  font-weight: 700;
  letter-spacing: -.01em;
  color: var(--text-primary);
}
.metric-card__unit { font-size: 12px; color: var(--text-secondary); font-weight: 400; }
.metric-card__foot { display: flex; align-items: center; justify-content: space-between; gap: 8px; }
.metric-card__hint { font-size: 11px; color: var(--text-secondary); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }

.metric-key { color: var(--color-primary); font-weight: 600; }

.chart-box { width: 100%; position: relative; z-index: 1; }

.mt-md { margin-top: 16px; }
.mb-md { margin-bottom: 16px; }
.sub-tabs { margin-bottom: 16px; }

.demo-rfm { text-align: center; }
.demo-rfm-header { padding: 20px; }
.demo-rfm-header h3 { font-size: 18px; margin: 12px 0 8px; }
.demo-rfm-header p { color: var(--text-secondary); font-size: 13px; max-width: 500px; margin: 0 auto; }
.demo-card {
  background: var(--bg-page);
  border-radius: 10px;
  padding: 16px;
  border-left: 4px solid;
  text-align: left;
  margin-bottom: 12px;
  min-height: 100px;
  border: 1px solid var(--border-color);
  transition: box-shadow .2s ease;
}
.demo-card:hover { box-shadow: 0 2px 8px rgba(0,0,0,.06); }
.demo-card-name { font-size: 15px; font-weight: 600; margin-bottom: 6px; }
.demo-card-desc { font-size: 12px; color: var(--text-secondary); margin-bottom: 6px; }
.demo-card-action { font-size: 12px; color: var(--color-primary); font-weight: 500; }

.empty-state { text-align: center; padding: 60px 20px; color: var(--text-secondary); font-size: 16px; }
.text-muted { color: var(--text-secondary); font-size: 13px; }

/* Model metrics */
.model-header { display: flex; justify-content: space-between; align-items: center; cursor: pointer; padding: 4px 0; position: relative; z-index: 10; }
.model-header:hover { opacity: 0.85; }
.model-header-right { display: flex; align-items: center; gap: 0; }
.expand-icon { transition: transform .25s ease; margin-left: 8px; font-size: 14px; color: var(--text-secondary); }
.expand-icon.is-expanded { transform: rotate(90deg); }
.model-key-metrics { margin-top: 16px; }
.model-metric-card {
  background: var(--bg-page);
  border-radius: 10px;
  padding: 14px 12px;
  text-align: center;
  border: 1px solid var(--border-color);
  transition: box-shadow .2s ease;
}
.model-metric-card:hover { box-shadow: 0 2px 8px rgba(0,0,0,.06); }
.model-metric-value { font-size: 20px; font-weight: 700; color: var(--color-primary); }
.model-metric-name { font-size: 11px; color: var(--text-secondary); margin-top: 4px; }
.model-detail-section { margin-top: 12px; }
.model-expand-btn {
  display: flex; align-items: center; justify-content: center; gap: 4px;
  margin-top: 12px; padding: 8px 0; cursor: pointer;
  color: var(--color-primary); font-size: 13px; font-weight: 500;
  border-top: 1px dashed var(--border-color);
  transition: background .2s ease;
}
.model-expand-btn:hover { background: var(--bg-page); }
.model-expand-btn .expand-icon { font-size: 12px; }

/* Model viz section */
.model-viz-section { margin-top: 20px; padding-top: 20px; border-top: 1px dashed var(--border-color); }
.viz-chart-title { display: flex; align-items: center; gap: 6px; font-size: 13px; font-weight: 600; color: var(--text-primary); margin-bottom: 10px; }
.viz-chart-title .el-icon { color: var(--color-primary); }
.viz-summary-card { background: var(--bg-page); border: 1px solid var(--border-color); border-radius: 10px; padding: 16px; height: 100%; display: flex; flex-direction: column; }
.viz-summary-title { font-size: 13px; font-weight: 600; color: var(--text-primary); margin-bottom: 8px; }
.viz-summary-text { font-size: 12px; color: var(--text-secondary); line-height: 1.7; flex: 1; }
.viz-action-row { display: flex; justify-content: center; margin-top: 10px; }
.viz-action-row:first-of-type { margin-top: 12px; }
.viz-action-row .viz-action-btn { display: inline-flex; align-items: center; justify-content: center; gap: 4px; min-width: 0; }
.viz-action-row .viz-action-btn .el-icon { margin-right: 2px; }
.viz-action-row .viz-action-btn span { white-space: nowrap; }

/* Constrain chart z-index so tooltip never covers model-header (see .chart-box above) */

.dialog-content { padding: 0 4px; }
.dialog-loading { text-align: center; padding: 60px 0; color: var(--text-secondary); font-size: 14px; }
.dialog-loading .el-icon { margin-right: 8px; }
.dialog-meta { padding: 8px 0 16px; border-bottom: 1px solid var(--border-color); margin-bottom: 16px; display: flex; flex-wrap: wrap; align-items: center; gap: 0; }
.dialog-version-hint { font-size: 11px; color: var(--text-secondary); margin-left: auto; padding: 2px 8px; background: var(--bg-page); border-radius: 4px; }
.dialog-chart-title { font-size: 13px; font-weight: 600; color: var(--text-primary); margin-bottom: 8px; padding-left: 8px; border-left: 3px solid var(--color-primary); }
.mt-sm { margin-top: 8px; }

/* Dialog header padding for breathing room around X close button */
.model-viz-dialog .el-dialog__header { padding: 20px 24px 16px; }
.model-viz-dialog .el-dialog__title { font-size: 16px; font-weight: 600; }
.model-viz-dialog .el-dialog__headerbtn { top: 18px; right: 20px; width: 32px; height: 32px; }
.model-viz-dialog .el-dialog__headerbtn .el-dialog__close { font-size: 18px; }
.model-viz-dialog .el-dialog__body { padding: 12px 24px 24px; }
</style>

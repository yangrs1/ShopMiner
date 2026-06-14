<template>
  <div>
    <h2 class="page-title">流失预警</h2>
    <el-row :gutter="16" class="mb-md">
      <el-col :span="8">
        <div class="mini-kpi"><div class="mini-kpi-label">高风险用户</div><div class="mini-kpi-value" style="color:#F56C6C">{{ churnHighRisk }}</div></div>
      </el-col>
      <el-col :span="8">
        <div class="mini-kpi"><div class="mini-kpi-label">中风险用户</div><div class="mini-kpi-value" style="color:#E6A23C">{{ churnMediumRisk }}</div></div>
      </el-col>
      <el-col :span="8">
        <div class="mini-kpi"><div class="mini-kpi-label">已解决</div><div class="mini-kpi-value" style="color:#67C23A">{{ churnResolved }}</div></div>
      </el-col>
    </el-row>
    <div class="kpi-card">
      <div class="card-toolbar">
        <el-checkbox v-model="churnRiskOnly" @change="loadChurnList">仅显示高风险</el-checkbox>
      </div>
      <el-table :data="churnList" stripe v-loading="loadingChurn">
        <el-table-column prop="user_id" label="ID" width="60" />
        <el-table-column prop="user_name" label="用户" width="110" />
        <el-table-column prop="segment" label="RFM分群" width="100" />
        <el-table-column prop="churn_probability" label="流失概率" width="130">
          <template #default="{ row }"><el-progress :percentage="Math.round(row.churn_probability * 100)" :color="churnColor(row.churn_probability)" :stroke-width="14" /></template>
        </el-table-column>
        <el-table-column prop="risk_level" label="风险" width="80">
          <template #default="{ row }"><el-tag :type="row.risk_level==='high'?'danger':row.risk_level==='medium'?'warning':'success'" size="small">{{ {high:'高',medium:'中',low:'低'}[row.risk_level]||row.risk_level }}</el-tag></template>
        </el-table-column>
        <el-table-column prop="status" label="状态" width="100">
          <template #default="{ row }"><el-select v-model="row.status" size="small" @change="updateChurnStatus(row)"><el-option label="待处理" value="pending"/><el-option label="已联系" value="contacted"/><el-option label="已解决" value="resolved"/></el-select></template>
        </el-table-column>
        <el-table-column prop="prediction_date" label="预测日期" width="110" />
      </el-table>
      <el-pagination v-if="churnTotal>churnPerPage" v-model:current-page="churnPage" :page-size="churnPerPage" :total="churnTotal" layout="prev,pager,next" class="mt-md" @current-change="loadChurnList" />
    </div>
    <el-row :gutter="16">
      <el-col :span="12">
        <div class="kpi-card mt-md"><h3 class="card-title">流失趋势</h3><div ref="churnTrendChartRef" class="chart-box" style="height:280px"></div></div>
      </el-col>
      <el-col :span="12">
        <div class="kpi-card mt-md"><h3 class="card-title">特征重要性</h3><div ref="importanceChartRef" class="chart-box" style="height:280px"></div></div>
      </el-col>
    </el-row>
  </div>
</template>

<script setup>
import { ref, onMounted, nextTick } from 'vue'
import { adminAnalyticsApi } from '../../api'
import { ElMessage } from 'element-plus'
import { useECharts } from '../composables/useECharts'
import * as echarts from 'echarts'

const { chartInstances, initChart, disposeChartRefs, handleResize, safeRender } = useECharts()

const churnList = ref([])
const churnPage = ref(1), churnTotal = ref(0), churnPerPage = 20
const churnRiskOnly = ref(false), loadingChurn = ref(false)
const churnHighRisk = ref(0), churnMediumRisk = ref(0), churnResolved = ref(0)
const importanceChartRef = ref(null), churnTrendChartRef = ref(null)

function churnColor(p) { return p > 0.7 ? '#F56C6C' : p > 0.4 ? '#E6A23C' : '#67C23A' }

async function loadChurnList() {
  loadingChurn.value = true
  try {
    const r = await adminAnalyticsApi.getChurnList({ page: churnPage.value, per_page: churnPerPage, risk_only: churnRiskOnly.value ? '1' : '0' })
    churnList.value = r.data.predictions || []
    churnTotal.value = r.data.total || 0
    if (r.data.summary) {
      churnHighRisk.value = r.data.summary.high || 0
      churnMediumRisk.value = r.data.summary.medium || 0
      churnResolved.value = r.data.summary.resolved || 0
    }
  } catch { churnList.value = [] }
  finally { loadingChurn.value = false }
}

async function updateChurnStatus(row) {
  try { await adminAnalyticsApi.updateChurnStatus(row.id, row.status); ElMessage.success('状态已更新') } catch {}
}

async function loadChurnImportance() {
  try { const r = await adminAnalyticsApi.getChurnImportance(); const d = r.data || {}; await nextTick(); safeRender(() => renderImportanceChart(d)) } catch {}
}

function renderImportanceChart(data) {
  const chart = initChart(importanceChartRef)
  if (!chart) return
  const features = data.feature_counts || []
  if (!features.length) return
  const sorted = [...features].sort((a, b) => b.count - a.count).slice(0, 12)
  chart.setOption({
    tooltip: { trigger: 'axis', axisPointer: { type: 'shadow' }, confine: true, extraCssText: 'z-index:1;' },
    grid: { left: 100, right: 40, top: 8, bottom: 15 },
    xAxis: { type: 'value' },
    yAxis: { type: 'category', data: sorted.map(s => s.feature), inverse: true, axisLabel: { fontSize: 10 } },
    animationDuration: 600,
    series: [{ type: 'bar', data: sorted.map(s => ({ value: s.count, itemStyle: { color: new echarts.graphic.LinearGradient(0, 0, 1, 0, [{ offset: 0, color: '#409EFF' }, { offset: 1, color: '#66B1FF' }]) } })), label: { show: true, position: 'right', fontSize: 10 } }],
  })
}

async function loadChurnTrend() {
  try { const r = await adminAnalyticsApi.getChurnTrend(); const d = r.data || []; await nextTick(); safeRender(() => renderChurnTrend(d)) } catch {}
}

function renderChurnTrend(data) {
  const chart = initChart(churnTrendChartRef)
  if (!chart || !data.length) return
  chart.setOption({
    tooltip: { trigger: 'axis', axisPointer: { type: 'shadow' }, confine: true, extraCssText: 'z-index:1;', formatter: function(params) { const d = data[params[0].dataIndex]; return d.bucket + '<br/>用户数: ' + d.count + '<br/>占比: ' + d.rate + '%' } },
    grid: { left: 55, right: 30, top: 15, bottom: 25 },
    xAxis: { type: 'category', data: data.map(d => d.bucket), axisLabel: { fontSize: 11 } },
    yAxis: { type: 'value', name: '用户数' },
    animationDuration: 600,
    series: [{
      type: 'bar', data: data.map(d => ({
        value: d.count,
        itemStyle: { color: d.bucket.includes('80') || d.bucket.includes('60') ? '#F56C6C' : d.bucket.includes('40') ? '#E6A23C' : '#67C23A' }
      })),
      label: { show: true, position: 'top', formatter: function(p) { return data[p.dataIndex].rate + '%' }, fontSize: 11 },
      barWidth: '40%',
    }],
  })
}

onMounted(() => {
  loadChurnList()
  loadChurnImportance()
  loadChurnTrend()
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

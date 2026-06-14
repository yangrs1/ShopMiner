<template>
  <div>
    <h2 class="page-title">销售分析</h2>
    <el-tabs v-model="salesSubTab" type="card" class="sub-tabs">
      <el-tab-pane label="销售趋势" name="trend">
        <div class="kpi-card">
          <h3 class="card-title">销售趋势</h3>
          <div ref="salesTrendChartRef" class="chart-box" style="height:350px"></div>
        </div>
      </el-tab-pane>
      <el-tab-pane label="销售预测" name="prediction">
        <el-row :gutter="16" class="mb-md" v-if="predictionMetricsLoaded">
          <el-col :span="6" v-for="card in predictionMetricCards" :key="card.key">
            <div class="metric-card" :class="`metric-card--${card.tone}`">
              <div class="metric-card__head">
                <el-icon class="metric-card__icon"><component :is="card.icon" /></el-icon>
                <span class="metric-card__title">{{ card.title }}</span>
              </div>
              <div class="metric-card__value">
                <span class="metric-card__number">{{ card.number }}</span>
                <span v-if="card.unit" class="metric-card__unit">{{ card.unit }}</span>
              </div>
              <div class="metric-card__foot">
                <span class="metric-card__hint">{{ card.hint }}</span>
              </div>
            </div>
          </el-col>
        </el-row>
        <div class="kpi-card">
          <h3 class="card-title">销售预测 (LightGBM)</h3>
          <div ref="salesPredChartRef" class="chart-box" style="height:350px"></div>
          <el-table :data="salesPredTableData" stripe class="mt-md" v-if="salesPredTableData.length" size="small">
            <el-table-column prop="date" label="预测月份" width="120" align="center" />
            <el-table-column prop="amount" label="预测销售额 (元)" min-width="160" align="right"><template #default="{ row }">{{ fmtMoney(row.amount) }}</template></el-table-column>
            <el-table-column prop="lower" label="下限 (95%)" min-width="140" align="right"><template #default="{ row }">{{ row.lower ? fmtMoney(row.lower) : '-' }}</template></el-table-column>
            <el-table-column prop="upper" label="上限 (95%)" min-width="140" align="right"><template #default="{ row }">{{ row.upper ? fmtMoney(row.upper) : '-' }}</template></el-table-column>
          </el-table>
          <div v-else class="empty-state" style="padding:20px">暂无预测数据</div>
        </div>
      </el-tab-pane>
    </el-tabs>
  </div>
</template>

<script setup>
import { ref, watch, nextTick, markRaw, onMounted } from 'vue'
import { Cpu, TrendCharts, DataLine, Warning } from '@element-plus/icons-vue'
import { adminAnalyticsApi } from '../../api'
import { useECharts, fmtMoney } from '../composables/useECharts'

const { chartInstances, initChart, disposeChartRefs, handleResize, safeRender } = useECharts()

const salesSubTab = ref('trend')
const salesTrendChartRef = ref(null), salesPredChartRef = ref(null)
const salesPredTableData = ref([])
const predictionMetricsLoaded = ref(false)
const predictionMetricCards = ref([])
const salesPredData = ref(null)
const salesTrendData = ref([])

async function loadSales() {
  try {
    const [trendRes, predRes] = await Promise.all([
      adminAnalyticsApi.getSalesTrend(),
      adminAnalyticsApi.getSalesPrediction(),
    ])
    salesTrendData.value = trendRes.data || []
    salesPredData.value = predRes.data || {}
    await nextTick()
    safeRender(() => renderSalesTrendChart(salesTrendData.value))

    const predData = predRes.data || {}
    const preds = predData.predictions || []
    salesPredTableData.value = preds.map(p => ({
      date: p.month || '',
      amount: p.pred_amount || 0,
      lower: p.pred_lower || 0,
      upper: p.pred_upper || 0,
    }))

    try {
      const metRes = await adminAnalyticsApi.getPredictionMetrics()
      const metData = metRes.data || {}

      // 取第一个模型下的 4 个关键指标
      const firstModel = Object.values(metData)[0] || {}
      const bestMae = firstModel.best_mae
      const bestR2 = firstModel.best_r2
      const bestSmape = firstModel.best_smape
      const cvSmape = firstModel.cv_smape_mean

      const cards = []
      if (bestMae) {
        const num = +bestMae.value
        const v = isNaN(num) ? bestMae.value : num.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })
        cards.push({
          key: 'mae', title: '最优 MAE', icon: markRaw(Cpu),
          number: v, unit: '元',
          hint: '平均绝对误差 · 越低越好',
          tone: 'blue',
        })
      }
      if (bestR2) {
        const num = +bestR2.value
        const v = isNaN(num) ? bestR2.value : num.toFixed(4)
        cards.push({
          key: 'r2', title: '最优 R²', icon: markRaw(TrendCharts),
          number: v, unit: '/ 1.0',
          hint: '拟合优度 · 越接近 1 越好',
          tone: 'green',
        })
      }
      if (bestSmape) {
        const num = +bestSmape.value
        cards.push({
          key: 'smape', title: '最优 sMAPE', icon: markRaw(DataLine),
          number: num.toFixed(2) + '%', unit: '',
          hint: '对称平均误差 · 越低越好',
          tone: 'orange',
        })
      }
      if (cvSmape) {
        const num = +cvSmape.value
        const numStd = +(firstModel.cv_smape_std?.value || 0)
        cards.push({
          key: 'cv', title: 'CV sMAPE', icon: markRaw(Warning),
          number: num.toFixed(2) + '%', unit: '± ' + numStd.toFixed(2) + '%',
          hint: '5 折交叉验证 · 越稳定越好',
          tone: num < 5 ? 'green' : num < 10 ? 'orange' : 'red',
        })
      }
      if (cards.length) { predictionMetricCards.value = cards; predictionMetricsLoaded.value = true }
    } catch {}
  } catch {}
}

watch(salesSubTab, (tab) => {
  if (tab === 'prediction' && salesPredData.value) {
    nextTick(() => { safeRender(() => renderSalesPredChart(salesPredData.value)) })
  } else if (tab === 'trend' && salesTrendData.value.length) {
    nextTick(() => { safeRender(() => renderSalesTrendChart(salesTrendData.value)) })
  }
})

function renderSalesTrendChart(trend) {
  const chart = initChart(salesTrendChartRef)
  if (!trend || !trend.length) return
  // Convert Order.total_amount (pence) → yuan (£) for display
  const seriesData = trend.map(t => +(((t.amount || 0) / 100).toFixed(2)))
  const fmtY = (v) => {
    if (Math.abs(v) >= 1e4) return (v / 1e4).toFixed(1) + '万'
    return v.toFixed(0)
  }
  const xInterval = trend.length > 18 ? Math.floor(trend.length / 12) : 0
  chart.setOption({
    tooltip: { confine: true, extraCssText: 'z-index:1;', trigger: 'axis' },
    legend: { data: ['销售额', '订单数'], bottom: 0 },
    grid: { left: 70, right: 60, top: 25, bottom: 50 },
    xAxis: { type: 'category', data: trend.map(t => t.date), axisLabel: { rotate: 45, fontSize: 10, interval: xInterval } },
    yAxis: [
      { type: 'value', name: '销售额 (元)', axisLabel: { formatter: fmtY, fontSize: 10 } },
      { type: 'value', name: '订单数', axisLabel: { fontSize: 10 } },
    ],
    animationDuration: 600,
    series: [
      { name: '销售额', type: 'bar', data: seriesData, yAxisIndex: 0, itemStyle: { color: '#409EFF' } },
      { name: '订单数', type: 'line', data: trend.map(t => t.count), yAxisIndex: 1, itemStyle: { color: '#67C23A' }, smooth: true },
    ],
  })
}

function renderSalesPredChart(data) {
  const chart = initChart(salesPredChartRef)
  if (!chart) return
  const historical = data.historical || []
  const predictions = data.predictions || []
  const histMonths = historical.map(h => h.month)
  const predMonths = predictions.map(p => p.month)
  // Convert Order/SalesPrediction values (pence ×100 scale) → yuan for display
  const toYuan = (v) => +(((v || 0) / 100).toFixed(2))
  const histVals = historical.map(h => toYuan(h.amount))
  const predVals = predictions.map(p => toYuan(p.pred_amount))
  const upper = predictions.map(p => toYuan(p.pred_upper))
  const lower = predictions.map(p => toYuan(p.pred_lower))
  const H = histVals.length, P = predVals.length
  const histData = predVals.length ? [...histVals, predVals[0], ...new Array(P - 1).fill(null)] : [...histVals]
  const predData = predVals.length ? [...new Array(H).fill(null), ...predVals] : []
  const upperData = [...new Array(H).fill(null), ...upper]
  const lowerData = [...new Array(H).fill(null), ...lower]

  const allCats = [...histMonths, ...predMonths]
  const yMax = Math.max(...histVals, ...predVals, ...upper, 0) * 1.1
  const yMin = 0

  const fmtY = (v) => {
    if (Math.abs(v) >= 1e4) return (v / 1e4).toFixed(1) + '万'
    return v.toFixed(0)
  }
  const fmtTooltip = (params) => {
    if (!params || !params.length) return ''
    const date = params[0].axisValue
    let html = `<div style="font-weight:600;margin-bottom:4px">${date}</div>`
    for (const p of params) {
      if (p.value == null) continue
      const seriesName = p.seriesName
      const val = Number(p.value).toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })
      html += `<div style="display:flex;justify-content:space-between;gap:12px"><span>${p.marker} ${seriesName}</span><span style="font-weight:600">¥${val}</span></div>`
    }
    return html
  }

  const xInterval = allCats.length > 18 ? Math.floor(allCats.length / 12) : 0

  chart.setOption({
    tooltip: { confine: true, extraCssText: 'z-index:1;', trigger: 'axis', formatter: fmtTooltip },
    legend: { data: ['历史', '预测', '95% 置信区间'], bottom: 0, textStyle: { fontSize: 12 } },
    grid: { left: 70, right: 30, top: 25, bottom: 50 },
    xAxis: {
      type: 'category', data: allCats,
      axisLabel: { rotate: 45, fontSize: 10, interval: xInterval },
      axisLine: { lineStyle: { color: '#909399' } },
    },
    yAxis: {
      type: 'value', name: '销售额 (元)', min: yMin, max: yMax,
      axisLabel: { formatter: fmtY, fontSize: 10 },
      splitLine: { lineStyle: { type: 'dashed', color: '#E4E7ED' } },
    },
    animationDuration: 600,
    series: [
      { name: '历史', type: 'line', data: histData, itemStyle: { color: '#409EFF' }, lineStyle: { width: 2 }, smooth: true, connectNulls: false, symbol: 'circle', symbolSize: 5, z: 3 },
      { name: '预测', type: 'line', data: predData, itemStyle: { color: '#E6A23C' }, lineStyle: { type: 'dashed', color: '#E6A23C', width: 2 }, smooth: true, connectNulls: true, symbol: 'diamond', symbolSize: 7, z: 3 },
      { name: '95% 置信区间', type: 'line', data: upperData, lineStyle: { opacity: 0 }, symbol: 'none', stack: 'ci_band', areaStyle: { color: 'rgba(230,162,60,0.15)' }, z: 1 },
      { name: '95% 置信区间', type: 'line', data: lowerData.map((l, i) => l - (upperData[i] || 0)), lineStyle: { opacity: 0 }, symbol: 'none', stack: 'ci_band', z: 2 },
    ],
  })
}

onMounted(() => {
  loadSales()
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

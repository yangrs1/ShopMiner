<template>
  <div>
    <h2 class="page-title">关联规则</h2>
    <div class="kpi-card">
      <el-table :data="associationRules" stripe v-loading="loadingAssociation">
        <el-table-column prop="antecedent" label="前件" min-width="120" />
        <el-table-column prop="consequent" label="后件" min-width="120" />
        <el-table-column prop="support" label="支持度" width="100"><template #default="{ row }">{{ (row.support * 100).toFixed(2) }}%</template></el-table-column>
        <el-table-column prop="confidence" label="置信度" width="100"><template #default="{ row }">{{ (row.confidence * 100).toFixed(2) }}%</template></el-table-column>
        <el-table-column prop="lift" label="提升度" width="100"><template #default="{ row }">{{ row.lift.toFixed(2) }}</template></el-table-column>
      </el-table>
      <el-pagination v-if="associationTotal > associationPerPage" v-model:current-page="associationPage" :page-size="associationPerPage" :total="associationTotal" layout="prev,pager,next" class="mt-md" @current-change="loadAssociationRules" />
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { adminAnalyticsApi } from '../../api'

const associationRules = ref([])
const associationPage = ref(1), associationTotal = ref(0), associationPerPage = 50
const loadingAssociation = ref(false)

async function loadAssociationRules() {
  loadingAssociation.value = true
  try { const r = await adminAnalyticsApi.getAssociationList({ page: associationPage.value, per_page: associationPerPage }); associationRules.value = r.data.rules || []; associationTotal.value = r.data.total || 0 } catch { associationRules.value = [] }
  finally { loadingAssociation.value = false }
}

onMounted(() => {
  loadAssociationRules()
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

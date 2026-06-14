import { nextTick, onMounted, onBeforeUnmount } from 'vue'
import * as echarts from 'echarts'

export function useECharts() {
  const chartInstances = []

  function initChart(domRef) {
    if (!domRef.value) return null
    const dom = domRef.value
    const existing = echarts.getInstanceByDom(dom)
    if (existing) existing.dispose()
    const chart = echarts.init(dom)
    chartInstances.push(chart)
    return chart
  }

  function disposeChartRefs(refList) {
    refList.forEach(r => {
      if (!r.value) return
      const inst = echarts.getInstanceByDom(r.value)
      if (inst) { inst.dispose(); const i = chartInstances.indexOf(inst); if (i > -1) chartInstances.splice(i, 1) }
    })
  }

  function handleResize() { chartInstances.forEach(c => { try { c.resize() } catch(e){} }) }

  function safeRender(renderFn) {
    nextTick(() => { requestAnimationFrame(() => { renderFn() }) })
  }

  onMounted(() => window.addEventListener('resize', handleResize))
  onBeforeUnmount(() => {
    chartInstances.forEach(c => c.dispose())
    chartInstances.length = 0
    window.removeEventListener('resize', handleResize)
  })

  return { chartInstances, initChart, disposeChartRefs, handleResize, safeRender }
}

export function fmtMoney(v) {
  if (v == null || isNaN(v)) return '-'
  return '¥' + Number(v / 100).toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })
}

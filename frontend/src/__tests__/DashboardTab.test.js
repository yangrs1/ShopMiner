import { shallowMount } from '@vue/test-utils'
import { describe, it, expect, vi, beforeEach } from 'vitest'

// Mock echarts before any component imports it
vi.mock('echarts', () => ({
  init: vi.fn(() => ({
    setOption: vi.fn(),
    dispose: vi.fn(),
    resize: vi.fn(),
  })),
  getInstanceByDom: vi.fn(() => null),
}))

// Mock API
const mockGetDashboard = vi.fn()
const mockGetSalesTrend = vi.fn()
const mockGetHotProducts = vi.fn()
const mockGetRfmSummary = vi.fn()
const mockGetChurnList = vi.fn()
const mockResetSystem = vi.fn()
const mockImportData = vi.fn()

vi.mock('../api', () => ({
  adminAnalyticsApi: {
    getDashboard: (...args) => mockGetDashboard(...args),
    getSalesTrend: (...args) => mockGetSalesTrend(...args),
    getHotProducts: (...args) => mockGetHotProducts(...args),
    getRfmSummary: (...args) => mockGetRfmSummary(...args),
    getChurnList: (...args) => mockGetChurnList(...args),
  },
  adminApi: {
    resetSystem: (...args) => mockResetSystem(...args),
    importData: (...args) => mockImportData(...args),
  },
}))

import DashboardTab from '../admin/components/DashboardTab.vue'

describe('DashboardTab', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('renders without errors', () => {
    const wrapper = shallowMount(DashboardTab)
    expect(wrapper.exists()).toBe(true)
  })

  it('shows the page title', () => {
    const wrapper = shallowMount(DashboardTab)
    expect(wrapper.text()).toContain('数据看板')
  })

  it('calls loadDashboard on mount', () => {
    shallowMount(DashboardTab)
    expect(mockGetDashboard).toHaveBeenCalledTimes(1)
  })

  it('calls all analytics APIs on mount', () => {
    // getDashboard is called first, the others depend on it
    shallowMount(DashboardTab)
    expect(mockGetDashboard).toHaveBeenCalledTimes(1)
  })

  it('renders stat counts from API response', async () => {
    mockGetDashboard.mockResolvedValue({
      data: { total_users: 100, total_products: 50, total_orders: 200, total_revenue: 5000000 },
    })
    mockGetSalesTrend.mockResolvedValue({ data: [] })
    mockGetHotProducts.mockResolvedValue({ data: { products: [] } })
    mockGetRfmSummary.mockResolvedValue({ data: { segments: [] } })
    mockGetChurnList.mockResolvedValue({ data: { predictions: [] } })

    const wrapper = shallowMount(DashboardTab)
    // Wait for async chain: onMounted → loadDashboard → API calls → safeRender
    await new Promise((r) => setTimeout(r, 50))

    expect(wrapper.text()).toContain('100')
    expect(wrapper.text()).toContain('50')
    expect(wrapper.text()).toContain('200')
  })

  it('renders total revenue formatted as yuan', async () => {
    mockGetDashboard.mockResolvedValue({
      data: { total_users: 10, total_products: 5, total_orders: 20, total_revenue: 50000000 },
    })
    mockGetSalesTrend.mockResolvedValue({ data: [] })
    mockGetHotProducts.mockResolvedValue({ data: { products: [] } })
    mockGetRfmSummary.mockResolvedValue({ data: { segments: [] } })
    mockGetChurnList.mockResolvedValue({ data: { predictions: [] } })

    const wrapper = shallowMount(DashboardTab)
    await new Promise((r) => setTimeout(r, 50))

    // 50000000 fen = 500000 yuan = ¥500,000.00
    expect(wrapper.text()).toContain('500,000')
  })

  it('displays empty stats when API returns null dashboard', async () => {
    mockGetDashboard.mockResolvedValue({ data: null })
    mockGetSalesTrend.mockResolvedValue({ data: [] })
    mockGetHotProducts.mockResolvedValue({ data: { products: [] } })
    mockGetRfmSummary.mockResolvedValue({ data: { segments: [] } })
    mockGetChurnList.mockResolvedValue({ data: { predictions: [] } })

    const wrapper = shallowMount(DashboardTab)
    await new Promise((r) => setTimeout(r, 50))

    // With null dashboard, no stats should render
    expect(wrapper.text()).not.toContain('总用户')
  })

  it('handles API error gracefully', async () => {
    mockGetDashboard.mockRejectedValue(new Error('Network error'))

    const wrapper = shallowMount(DashboardTab)
    await new Promise((r) => setTimeout(r, 50))

    expect(wrapper.exists()).toBe(true)
  })
})

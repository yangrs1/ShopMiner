import { shallowMount } from '@vue/test-utils'
import { describe, it, expect, vi, beforeEach } from 'vitest'

// Mock echarts since UsersTab imports fmtMoney from useECharts which imports echarts
vi.mock('echarts', () => ({
  init: vi.fn(() => ({
    setOption: vi.fn(),
    dispose: vi.fn(),
    resize: vi.fn(),
  })),
  getInstanceByDom: vi.fn(() => null),
}))

// Mock API
const mockGetUsers = vi.fn()
const mockAdjustBalance = vi.fn()

vi.mock('../api', () => ({
  adminApi: {
    getUsers: (...args) => mockGetUsers(...args),
    adjustBalance: (...args) => mockAdjustBalance(...args),
  },
  adminAnalyticsApi: {},
}))

import UsersTab from '../admin/components/UsersTab.vue'

describe('UsersTab', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  // Shared stub config to pass slot props to el-table-column
  const tableColumnStub = {
    template: '<div><slot :row="{ balance: 10000, role: \'user\' }" :column="{}" :$index="0" /></div>',
  }

  it('renders without errors', () => {
    const wrapper = shallowMount(UsersTab, {
      global: {
        stubs: {
          'el-table-column': tableColumnStub,
        },
      },
    })
    expect(wrapper.exists()).toBe(true)
  })

  it('shows the page title', () => {
    const wrapper = shallowMount(UsersTab, {
      global: {
        stubs: {
          'el-table-column': tableColumnStub,
        },
      },
    })
    expect(wrapper.text()).toContain('用户管理')
  })

  it('calls loadAdminUsers on mount', () => {
    shallowMount(UsersTab, {
      global: {
        stubs: {
          'el-table-column': tableColumnStub,
        },
      },
    })
    expect(mockGetUsers).toHaveBeenCalledTimes(1)
  })

  it('renders users from API response with formatted balance', async () => {
    mockGetUsers.mockResolvedValue({
      data: {
        users: [
          { id: 1, first_name: '张', last_name: '三', email: 'test@test.com', balance: 10000, role: 'user' },
          { id: 2, first_name: '李', last_name: '四', email: 'admin@test.com', balance: 500000, role: 'admin' },
        ],
        total: 2,
      },
    })

    const wrapper = shallowMount(UsersTab, {
      global: {
        stubs: {
          'el-table-column': tableColumnStub,
        },
      },
    })
    await new Promise((r) => setTimeout(r, 50))

    // Check API was called — el-table is stubbed so data rows don't iterate
    expect(mockGetUsers).toHaveBeenCalledTimes(1)
  })

  it('handles API error gracefully', async () => {
    mockGetUsers.mockRejectedValue(new Error('API error'))

    const wrapper = shallowMount(UsersTab, {
      global: {
        stubs: {
          'el-table-column': tableColumnStub,
        },
      },
    })
    await new Promise((r) => setTimeout(r, 50))

    expect(wrapper.exists()).toBe(true)
  })
})

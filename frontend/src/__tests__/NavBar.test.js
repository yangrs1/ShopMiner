import { shallowMount } from '@vue/test-utils'
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { setActivePinia, createPinia } from 'pinia'
import { useUserStore } from '../stores/user'

// Mock vue-router since the component uses useRouter()
// Partially mock vue-router — keep createRouter/createWebHashHistory for the router module
vi.mock('vue-router', async (importOriginal) => {
  const actual = await importOriginal()
  return {
    ...actual,
    useRouter: () => ({ push: vi.fn() }),
    useRoute: () => ({ query: {} }),
  }
})

import NavBar from '../components/NavBar.vue'

describe('NavBar', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
  })

  it('renders without errors', () => {
    const wrapper = shallowMount(NavBar, {
      global: { stubs: ['router-link', 'router-view'] },
    })
    expect(wrapper.exists()).toBe(true)
  })

  it('contains the brand name ShopMiner', () => {
    const wrapper = shallowMount(NavBar, {
      global: { stubs: ['router-link', 'router-view'] },
    })
    expect(wrapper.text()).toContain('ShopMiner')
  })

  it('shows login and register when user is not logged in', () => {
    const wrapper = shallowMount(NavBar, {
      global: { stubs: ['router-link', 'router-view'] },
    })
    expect(wrapper.text()).toContain('登录')
    expect(wrapper.text()).toContain('注册')
  })

  function createWrapper(options = {}) {
    const { stubs = {} } = options
    return shallowMount(NavBar, {
      global: {
        stubs: {
          'router-link': true,
          'router-view': true,
          // el-sub-menu stub must render named title slot for displayName
          'el-sub-menu': {
            template: '<div><slot name="title" /><slot /></div>',
          },
          ...stubs,
        },
      },
    })
  }

  it('shows user name when user is logged in', () => {
    const store = useUserStore()
    store.token = 'fake-jwt-token'
    store.currentUser = { first_name: 'Test', last_name: 'User', role: 'user' }

    const wrapper = createWrapper()
    expect(wrapper.text()).toContain('Test User')
  })

  it('shows admin link when logged in as admin', () => {
    const store = useUserStore()
    store.token = 'admin-token'
    store.currentUser = { first_name: 'Admin', last_name: 'Root', role: 'admin' }

    const wrapper = createWrapper()
    expect(wrapper.text()).toContain('Admin Root')
    expect(wrapper.text()).toContain('管理')
  })

  it('hides admin link when logged in as regular user', () => {
    const store = useUserStore()
    store.token = 'user-token'
    store.currentUser = { first_name: 'Normal', last_name: 'User', role: 'user' }

    const wrapper = createWrapper()
    expect(wrapper.text()).toContain('Normal User')
    // Admin link should NOT be present
    expect(wrapper.text()).not.toContain('管理')
  })
})

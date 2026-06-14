import { shallowMount } from '@vue/test-utils'
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { setActivePinia, createPinia } from 'pinia'
import { useUserStore } from '../stores/user'

// Mock API to avoid actual requests
vi.mock('../api', () => ({
  productApi: {
    getProductRating: vi.fn().mockRejectedValue(new Error('mock error')),
  },
  cartApi: {
    addToCart: vi.fn(),
  },
}))

// Mock vue-router
vi.mock('vue-router', async (importOriginal) => {
  const actual = await importOriginal()
  return {
    ...actual,
    useRouter: () => ({ push: vi.fn() }),
    useRoute: () => ({}),
  }
})

// Mock element-plus
vi.mock('element-plus', () => ({
  ElMessage: {
    warning: vi.fn(),
    success: vi.fn(),
  },
}))

import ProductCard from '../components/ProductCard.vue'

const mockProduct = {
  id: 1,
  name: '测试商品',
  price: 2999,
  original_price: 3999,
  image: '/img/test.jpg',
  stock: 100,
  sales: 50,
  rating: 4.5,
  category_name: '测试分类',
}

describe('ProductCard', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
  })

  it('renders product name', () => {
    const wrapper = shallowMount(ProductCard, {
      props: { product: mockProduct },
      global: { stubs: ['router-link'] },
    })
    expect(wrapper.text()).toContain('测试商品')
  })

  it('renders formatted price correctly (2999 fen = 29.99 yuan)', () => {
    const wrapper = shallowMount(ProductCard, {
      props: { product: mockProduct },
      global: { stubs: ['router-link'] },
    })
    expect(wrapper.text()).toContain('29.99')
  })

  it('shows add to cart button when stock > 0', () => {
    const wrapper = shallowMount(ProductCard, {
      props: { product: mockProduct },
      global: { stubs: ['router-link'] },
    })
    expect(wrapper.text()).toContain('加入购物车')
  })

  it('shows no rating text when ratings not loaded', () => {
    const wrapper = shallowMount(ProductCard, {
      props: { product: mockProduct },
      global: { stubs: ['router-link'] },
    })
    expect(wrapper.text()).toContain('暂无评价')
  })

  it('shows out of stock badge when stock is 0', () => {
    const outOfStock = { ...mockProduct, stock: 0 }
    const wrapper = shallowMount(ProductCard, {
      props: { product: outOfStock },
      global: { stubs: ['router-link'] },
    })
    expect(wrapper.text()).toContain('已售罄')
  })

  it('renders the product image', () => {
    const wrapper = shallowMount(ProductCard, {
      props: { product: mockProduct },
      global: { stubs: ['router-link'] },
    })
    const img = wrapper.find('img')
    expect(img.exists()).toBe(true)
    expect(img.attributes('alt')).toBe('测试商品')
  })

  it('renders default placeholder image when product has no image', () => {
    const noImage = { ...mockProduct, image: '' }
    const wrapper = shallowMount(ProductCard, {
      props: { product: noImage },
      global: { stubs: ['router-link'] },
    })
    const img = wrapper.find('img')
    expect(img.exists()).toBe(true)
  })

  it('renders product description', () => {
    const withDesc = { ...mockProduct, description: '这是一个测试商品描述' }
    const wrapper = shallowMount(ProductCard, {
      props: { product: withDesc },
      global: { stubs: ['router-link'] },
    })
    expect(wrapper.text()).toContain('这是一个测试商品描述')
  })
})
